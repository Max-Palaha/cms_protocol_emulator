# protocols/sentinel/handler.py

import re
from typing import Optional
from protocols.sentinel.mode_switcher import SentinelModeSwitcher
from protocols.sentinel.parser import parse_event
from protocols.sentinel.responses import get_ack, get_nak
from core.connection_handler import BaseProtocol
from utils.registry_tools import register_protocol
from utils.constants import Receiver
from utils.mode_switcher import mode_manager
from utils.tools import logger


@register_protocol(Receiver.SENTINEL)
class SentinelProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.SENTINEL)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self.mode_switcher = SentinelModeSwitcher()

        # Regexes to detect and manipulate URLs inside pipe-delimited fields
        # Example segments: |MediaUrl=https://...|, |LinkUrl=ajax-pro-desktop://...
        self._media_re = re.compile(r'\|MediaUrl=([^|]+)')  # capture value until next '|'
        self._link_re  = re.compile(r'\|LinkUrl=([^|]+)')   # capture value until next '|'

    # ---------------- helpers ----------------

    def _bytes_as_angle_hex(self, data: bytes, limit: int = 64) -> str:
        """
        Render bytes as <0xHH ...>. Truncate after `limit` bytes with an ellipsis.
        Intended for small control replies/handshakes in INFO and for readability.
        """
        if not data:
            return "<>"
        shown = data[:limit]
        body = " ".join(f"0x{b:02X}" for b in shown)
        if len(data) > limit:
            body += " …"
        return f"<{body}>"

    def _bytes_to_visible_str(self, data: bytes) -> str:
        """
        Render incoming bytes as a single-line string:
        - printable ASCII (0x20..0x7E) as-is (newline/tab normalized)
        - control / invisible bytes shown inline as <0xHH>
        """
        out = []
        for b in data:
            if 0x20 <= b <= 0x7E:
                ch = chr(b)
                out.append(ch if ch not in '\r\n' else f'<0x{b:02X}>')
            elif b == 0x09:
                out.append(' ')
            else:
                out.append(f'<0x{b:02X}>')
        return ''.join(out)

    def _collapse_media_urls_once(self, s: str):
        """
        Keep the first '|MediaUrl=…' intact and replace the remaining ones with a single '|+N more photos'.
        Returns (collapsed_string, total_count).
        """
        matches = list(self._media_re.finditer(s))
        n = len(matches)
        if n <= 1:
            return s, n

        parts, last = [], 0
        for i, m in enumerate(matches):
            parts.append(s[last:m.start()])
            if i == 0:
                parts.append(m.group(0))  # keep first MediaUrl as-is
            elif i == 1:
                parts.append(f'|+{n-1} more photos')  # single placeholder
            # skip actual text for 2nd+ occurrences
            last = m.end()
        parts.append(s[last:])
        return ''.join(parts), n

    def _bytes_to_hex_block(self, data: bytes, limit: int = 512) -> str:
        """Return a long hex dump for DEBUG (space-separated, truncated)."""
        if not data:
            return ""
        shown = data[:limit]
        hex_str = " ".join(f"{b:02X}" for b in shown)
        if len(data) > limit:
            hex_str += f" …(+{len(data) - limit} bytes)"
        return hex_str

    def _preview_bytes(self, data: bytes, limit: int = 4096) -> str:
        """Long single-line text preview for DEBUG."""
        try:
            s = data.decode(errors='ignore')
        except Exception:
            return f'<{len(data)} bytes>'
        s = s.replace('\r', ' ').replace('\n', ' ')
        return s if len(s) <= limit else s[:limit] + '…'

    def _label_for_incoming(self, data: bytes, parsed: Optional[dict], has_link: bool) -> str:
        """
        Consistent label used in INFO logs.
        Priority:
          - PING
          - LINK (if LinkUrl present)
          - PHOTO (if MediaUrl(s) present per parser)
          - EVENT (with code if present)
        """
        if data == b"\x06\x14":
            return "PING"

        code = parsed.get("event_code") if parsed else None
        is_photo = parsed.get("is_photo") if parsed else False

        if has_link:
            return f"LINK {code}" if code else "LINK"
        if is_photo and code:
            return f"PHOTO {code}"
        if is_photo:
            return "PHOTO"
        if code:
            return f"EVENT {code}"
        return "EVENT"

    # keep compatibility if BaseProtocol expects this
    def get_label(self, data: bytes) -> Optional[str]:
        try:
            s = data.decode(errors="ignore")
            parsed = parse_event(s)
        except Exception:
            parsed, s = None, ""
        has_link = bool(self._link_re.search(s))
        return self._label_for_incoming(data, parsed, has_link)

    # ---------------- main ----------------

    async def handle(self, reader, writer, client_ip, client_port, data: bytes):
        # Parse (for code/is_photo) and detect LinkUrl
        try:
            decoded = data.decode(errors="ignore")
            parsed = parse_event(decoded)
        except Exception:
            decoded = ""
            parsed = None

        # Detect LinkUrl from both decoded and visible forms (robust to control bytes)
        has_link = bool(self._link_re.search(decoded))
        if not has_link:
            has_link = bool(self._link_re.search(self._bytes_to_visible_str(data)))

        label = self._label_for_incoming(data, parsed, has_link)

        # INFO input line:
        if data == b"\x06\x14":
            # Control handshake displayed as angle-hex only
            logger.info(f"(SENTINEL) ({client_ip}) <<-- [PING] {self._bytes_as_angle_hex(data)}")
        else:
            # Build visible string; special collapsing for PHOTO only
            visible_str = self._bytes_to_visible_str(data)
            is_photo = parsed.get("is_photo", False) if parsed else False
            if is_photo:
                visible_str, count = self._collapse_media_urls_once(visible_str)
                if count > 1 and not label.endswith(f"x{count}"):
                    label = f"{label} x{count}"
            logger.info(f"(SENTINEL) ({client_ip}) <<-- [{label}] {visible_str}")

        # DEBUG: raw + hex + preview + parsed
        logger.debug(f"(SENTINEL) ({client_ip}) [IN RAW]  bytes={data!r}")
        logger.debug(f"(SENTINEL) ({client_ip}) [IN HEX]  {self._bytes_to_hex_block(data)}")
        logger.debug(f"(SENTINEL) ({client_ip}) [PREVIEW] '{self._preview_bytes(data)}'")
        if parsed is not None:
            logger.debug(
                f"(SENTINEL) ({client_ip}) [PARSED] fields={parsed.get('fields')} "
                f"is_photo={parsed.get('is_photo')} event_code={parsed.get('event_code')}"
            )

        # PING (\x06\x14) -> ACK (0x06)
        if data == b"\x06\x14":
            response = get_ack()
            try:
                writer.write(response)
                await writer.drain()
            except Exception as ex:
                logger.debug(f"(SENTINEL) ({client_ip}) [SEND ERROR] {ex!r}")
            # INFO outgoing: angle-hex style
            logger.info(f"(SENTINEL) ({client_ip}) -->> [ACK] {self._bytes_as_angle_hex(response)}")
            # DEBUG outgoing: raw + hex
            logger.debug(f"(SENTINEL) ({client_ip}) [OUT RAW] bytes={response!r}")
            logger.debug(f"(SENTINEL) ({client_ip}) [OUT HEX] {self._bytes_to_hex_block(response)}")
            return

        # Emulation mode
        mode = self.mode_switcher.get_mode()
        if mode == "no_response":
            logger.info(f"(SENTINEL) ({client_ip}) -->> [NO_RESPONSE mode]")
            return

        if mode == "nak":
            response = get_nak()
            try:
                writer.write(response)
                await writer.drain()
            except Exception as ex:
                logger.debug(f"(SENTINEL) ({client_ip}) [SEND ERROR] {ex!r}")
            logger.info(f"(SENTINEL) ({client_ip}) -->> [NAK] {self._bytes_as_angle_hex(response)}")
            logger.debug(f"(SENTINEL) ({client_ip}) [OUT RAW] bytes={response!r}")
            logger.debug(f"(SENTINEL) ({client_ip}) [OUT HEX] {self._bytes_to_hex_block(response)}")
            return

        # default -> ACK
        response = get_ack()
        try:
            writer.write(response)
            await writer.drain()
        except Exception as ex:
            logger.debug(f"(SENTINEL) ({client_ip}) [SEND ERROR] {ex!r}")
        logger.info(f"(SENTINEL) ({client_ip}) -->> [ACK] {self._bytes_as_angle_hex(response)}")
        logger.debug(f"(SENTINEL) ({client_ip}) [OUT RAW] bytes={response!r}")
        logger.debug(f"(SENTINEL) ({client_ip}) [OUT HEX] {self._bytes_to_hex_block(response)}")
