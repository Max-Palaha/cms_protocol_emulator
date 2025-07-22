import asyncio
import re
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from utils.logger import logger
from protocols.masxml.parser import is_ping
from protocols.masxml.responses import convert_masxml_ack, convert_masxml_nak
from utils.registry_tools import register_protocol
from protocols.masxml.mode_switcher import MasxmlModeSwitcher
from utils.media_logger import save_base64_media

@register_protocol(Receiver.MASXML)
class MasxmlProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.MASXML)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self.mode_switcher = MasxmlModeSwitcher(self.protocol_mode)
        self._recv_buffer = ""

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value, self.mode_switcher),
        )

    async def handle(self, reader, writer, client_ip, client_port, data):
        """Main entry for connection_handler.py; processes incoming data chunk-wise."""
        if isinstance(data, bytes):
            chunk = data.decode(errors="ignore")
        else:
            chunk = data
        self._recv_buffer += chunk

        end_tag = "</XMLMessageClass>"
        while end_tag in self._recv_buffer:
            msg_end = self._recv_buffer.index(end_tag) + len(end_tag)
            full_xml = self._recv_buffer[:msg_end]
            self._recv_buffer = self._recv_buffer[msg_end:]

            await self._handle_xml_message(full_xml, writer, client_ip)

    async def _handle_xml_message(self, raw_message, writer, client_ip):
        mode = self.protocol_mode.mode

        if mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver}) NO_RESPONSE mode: skipping reply")
            return

        sequence = re.search(r"<MessageSequenceNo>(\d+)</MessageSequenceNo>", raw_message)
        sequence_num = sequence.group(1) if sequence else "unknown"

        # Mask and save base64 if present
        display_message = raw_message
        if "<PacketData>" in raw_message:
            b64_data_match = re.search(r"<PacketData>(.*?)</PacketData>", raw_message, re.DOTALL)
            if b64_data_match:
                b64_data = b64_data_match.group(1)
                img_path = save_base64_media(
                    b64_data,
                    protocol=self.receiver.value,
                    port=self.port,
                    sequence=sequence_num,
                )
                display_message = raw_message.replace(
                    f"<PacketData>{b64_data}</PacketData>",
                    f"<PacketData>[PHOTO BASE64, len={len(b64_data)}]</PacketData>"
                )
                logger.info(f"[MASXML PHOTO SAVED]: {img_path}")

        # Log parsed XML with masked base64 (no duplicate logs!)
        logger.info(f"({self.receiver}) ({client_ip}) <<-- {display_message.strip()}")

        # Handle ping
        if is_ping(raw_message):
            if mode == EmulationMode.NAK:
                nak = convert_masxml_nak(
                    raw_message,
                    text="Ping rejected due to emulation mode",
                    code=self.protocol_mode.nak_result_code or 10,
                )
                logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
                writer.write(nak.encode() if isinstance(nak, str) else nak)
            elif mode in [EmulationMode.ONLY_PING, EmulationMode.ACK]:
                ack = convert_masxml_ack(raw_message)
                logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
                writer.write(ack.encode() if isinstance(ack, str) else ack)
            else:
                logger.info(f"({self.receiver}) ({client_ip}) PING received — skipped due to mode: {mode.value}")
            await writer.drain()
            return

        if mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver}) ONLY_PING mode: skipping event")
            return

        if mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        # NAK or ACK event
        if mode == EmulationMode.NAK:
            nak = convert_masxml_nak(
                raw_message,
                text="Command rejected due to emulation mode",
                code=self.protocol_mode.nak_result_code or 10,
            )
            logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
            writer.write(nak.encode() if isinstance(nak, str) else nak)
        else:
            ack = convert_masxml_ack(raw_message)
            logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
            writer.write(ack.encode() if isinstance(ack, str) else ack)

        await writer.drain()
        self.protocol_mode.consume_packet()
