import asyncio
import re
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from utils.logger import logger
from utils.registry_tools import register_protocol
from utils.media_logger import save_base64_media
from protocols.manitou.responses import convert_ack, convert_nak

@register_protocol(Receiver.MANITOU)
class ManitouProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.MANITOU)
        self.protocol_mode = mode_manager.get(self.receiver.value)

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value, None),
        )

    async def handle(self, reader, writer, client_ip, client_port, data):
        raw = data.decode(errors="ignore").strip()

        # Extract from Packet and Signal XML
        packet_id = re.search(r'<Packet ID="(.*?)"', raw)
        event_type = re.search(r'<Signal[^>]*Event="(\w+)"', raw)
        b64_data_match = re.search(r"<PacketData>(.*?)</PacketData>", raw, re.DOTALL)

        packet_id_val = packet_id.group(1) if packet_id else "unknown"
        event_code_val = event_type.group(1) if event_type else "UNKNOWN"

        # Detect and mask photo payload
        display_msg = raw
        if b64_data_match:
            b64_data = b64_data_match.group(1)
            img_path = save_base64_media(
                b64_data,
                protocol=self.receiver.value,
                port=self.port,
                sequence=packet_id_val,
                event_code=event_code_val
            )
            logger.info(f"[MANITOU PHOTO SAVED]: {img_path}")
            display_msg = raw.replace(
                f"<PacketData>{b64_data}</PacketData>",
                f"<PacketData>[PHOTO BASE64, len={len(b64_data)}]</PacketData>"
            )

        # Label generation
        is_ping = "<Heartbeat" in raw
        if is_ping:
            label = "PING"
        elif b64_data_match:
            label = f"PHOTO {event_code_val}"
        else:
            label = f"EVENT {event_code_val}"

        logger.info(f"({self.receiver.value}) ({client_ip}) <<-- [{label}] {display_msg}")

        mode = self.protocol_mode.mode

        if mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver.value}) NO_RESPONSE mode: skipping reply")
            return

        if mode == EmulationMode.ONLY_PING and not is_ping:
            logger.info(f"({self.receiver.value}) ONLY_PING mode: skipping non-ping")
            return

        if mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver.value}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver.value}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        if mode == EmulationMode.NAK:
            nak = convert_nak(code=self.protocol_mode.nak_result_code or 10)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [NAK {event_code_val}] {nak.strip()}")
            writer.write(nak)
        else:
            ack = convert_ack(packet_id_val if not is_ping else None)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [ACK {event_code_val if not is_ping else 'PING'}] {ack.strip()}")
            writer.write(ack)

        await writer.drain()
        self.protocol_mode.consume_packet()
