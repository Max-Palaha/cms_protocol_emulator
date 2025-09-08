import asyncio
import logging
import re
from typing import Dict, Any

from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from utils.logger import logger
from utils.registry_tools import register_protocol
from utils.media_logger import save_base64_media

from .parser import (
    strip_stx_etx,
    sanitize_for_log,
    parse_manitou_message,
    is_binary_payload,
    is_ping,
)
from .responses import convert_ack
from .mode_switcher import ManitouModeSwitcher


@register_protocol(Receiver.MANITOU)
class ManitouProtocol(BaseProtocol):
    """
    Manitou handler, MASXML-style.
    Default logging:
      - Binary (photos): compact one-liner with key attrs; RAW XML only in DEBUG.
      - Everything else (PING/EVENT/LINK/UNKNOWN): full incoming XML in INFO.
    """

    def __init__(self):
        super().__init__(receiver=Receiver.MANITOU)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self.mode_switcher = ManitouModeSwitcher(self.protocol_mode)
        self._recv_buffer: bytes = b""

        # RawNo issued in our last ACK for a Signal; used to tag Binary -> event code
        self._rawno_eventcode: Dict[str, str] = {}

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value, self.mode_switcher),
        )

    async def handle(self, reader, writer, client_ip, client_port, data):
        """Consume raw TCP chunks, split by ETX, and process complete XML frames."""
        chunk = data.encode() if isinstance(data, str) else data
        self._recv_buffer += chunk

        while True:
            etx_pos = self._recv_buffer.find(b"\x03")
            if etx_pos < 0:
                break

            frame = self._recv_buffer[: etx_pos + 1]
            self._recv_buffer = self._recv_buffer[etx_pos + 1 :]

            stx_pos = frame.find(b"\x02")
            frame = frame[stx_pos:] if stx_pos >= 0 else b"\x02" + frame

            await self._handle_frame(frame, writer, client_ip)

    # ---------- core ----------

    async def _handle_frame(self, frame: bytes, writer, client_ip: str):
        xml_text = strip_stx_etx(frame)
        safe_text = sanitize_for_log(frame)

        # Decide logging style: compact only for binary; full raw XML for everything else
        is_bin = is_binary_payload(xml_text)
        label, meta = self._label_incoming(xml_text)

        if is_bin:
            # Compact one-liner on INFO; RAW redacted XML in DEBUG
            if meta:
                logger.info(f"({self.receiver.value}) ({client_ip}) <<-- [{label}] {meta}")
            else:
                logger.info(f"({self.receiver.value}) ({client_ip}) <<-- [{label}]")
            logger.debug(f"RAW XML: {safe_text}")
        else:
            # Full raw (redacted) XML on INFO for non-binary
            logger.info(f"({self.receiver.value}) ({client_ip}) <<-- [{label}] {safe_text}")

        # Modes
        mode = self.protocol_mode.mode
        if mode == EmulationMode.NO_RESPONSE:
            return

        if is_ping(xml_text):
            await self._reply_ping(writer, client_ip)
            return

        if mode == EmulationMode.ONLY_PING:
            return

        if mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver.value}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if mode == EmulationMode.DELAY_N:
            await asyncio.sleep(self.protocol_mode.delay_seconds)

        # Parse once (safe for use below)
        msg = parse_manitou_message(frame)

        # Signal -> ACK (remember RawNo -> event_code)
        if msg.get("type") == "signal":
            if mode == EmulationMode.NAK:
                logger.info(f"({self.receiver.value}) ({client_ip}) NAK mode: skip ACK for event {msg.get('event_code')}")
                return

            ack, rawno = convert_ack(return_rawno=True)
            event_code = msg.get("event_code")
            if event_code:
                self._rawno_eventcode[rawno] = event_code

            writer.write(ack)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [ACK {event_code or 'EVENT'}] {ack!r}")
            await writer.drain()
            self.protocol_mode.consume_packet()
            return

        # Binary -> save EACH frame separately (no concatenation)
        if msg.get("type") == "binary":
            if mode != EmulationMode.NAK:
                # Extract base64 from original (unredacted) XML
                m = re.search(r"<Data\b[^>]*>(.*?)</Data>", xml_text, flags=re.DOTALL | re.IGNORECASE)
                if m:
                    b64 = "".join(m.group(1).split())
                    rawno = msg.get("rawno") or "-"
                    frame_no = msg.get("frame_no") or "0"
                    event_code = self._rawno_eventcode.get(rawno)

                    try:
                        path = save_base64_media(
                            b64,
                            protocol=self.receiver.value,
                            port=self.port,
                            sequence=frame_no,           # separate file per frame
                            event_code=event_code,
                        )
                        logger.info(f"[MANITOU PHOTO SAVED] RawNo={rawno} Frame={frame_no} Path={path}")
                    except Exception as e:
                        logger.error(f"[MANITOU PHOTO SAVE ERROR] RawNo={rawno} Frame={frame_no} err={e}")

                ack = convert_ack()
                writer.write(ack)
                logger.info(f"({self.receiver.value}) ({client_ip}) -->> [ACK BINARY] {ack!r}")
                await writer.drain()
                self.protocol_mode.consume_packet()
            return

        # Unknown -> generic ACK
        if mode != EmulationMode.NAK:
            ack = convert_ack()
            writer.write(ack)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [ACK UNKNOWN] {ack!r}")
            await writer.drain()
            self.protocol_mode.consume_packet()

    async def _reply_ping(self, writer, client_ip: str):
        """Reply to heartbeat/ping according to mode."""
        mode = self.protocol_mode.mode
        if mode in [EmulationMode.ACK, EmulationMode.ONLY_PING, EmulationMode.DELAY_N, EmulationMode.DROP_N]:
            ack = convert_ack()
            writer.write(ack)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [ACK PING] {ack!r}")
            await writer.drain()
        elif mode == EmulationMode.NAK:
            logger.info(f"({self.receiver.value}) ({client_ip}) PING received — NAK mode (skip ACK)")

    # ---------- helpers ----------

    def _label_incoming(self, xml: str) -> tuple[str, str]:
        """
        Produce a compact label and short meta for INFO (used only for binary).
        For non-binary we still include full XML; label is kept for quick scanning.
        """
        # Ping?
        if is_ping(xml):
            return "PING", ""

        # Binary
        m_bin = re.search(r"<Binary\b([^>]*)>", xml, flags=re.IGNORECASE)
        if m_bin:
            attrs = m_bin.group(1)
            ext = _attr(attrs, "Ext") or "-"
            rawno = _attr(attrs, "RawNo") or "-"
            frame_no = _attr(attrs, "FrameNo") or _attr(attrs, "Frame") or "-"
            length = _attr(attrs, "Length") or "-"
            return "PHOTO " + ext, f"RawNo={rawno} Frame={frame_no} Len={length}"

        # Signal
        m_sig = re.search(r"<Signal\b([^>]*)>(.*?)</Signal>", xml, flags=re.DOTALL | re.IGNORECASE)
        if m_sig:
            attrs, _inner = m_sig.group(1), m_sig.group(2)
            code = _attr(attrs, "Event") or "UNKNOWN"
            return f"EVENT {code}", ""

        return "UNKNOWN", ""


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}="([^"]+)"', attrs, flags=re.IGNORECASE)
    return m.group(1) if m else None
