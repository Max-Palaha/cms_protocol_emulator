from typing import Optional
from protocols.sentinel.mode_switcher import SentinelModeSwitcher
from protocols.sentinel.parser import parse_event
from protocols.sentinel.responses import get_ack, get_nak
from core.connection_handler import BaseProtocol
from utils.registry_tools import register_protocol
from utils.constants import Receiver
from utils.mode_switcher import mode_manager
from utils.logger import logger

@register_protocol(Receiver.SENTINEL)
class SentinelProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.SENTINEL)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self.mode_switcher = SentinelModeSwitcher()

    def get_label(self, data: bytes) -> Optional[str]:
        if data == b'\x06\x14':
            return "PING"

        try:
            msg_str = data.decode(errors="ignore")
            event = parse_event(msg_str)
            event_code = event.get("fields", {}).get("Event")

            if event.get("is_photo"):
                return f"PHOTO {event_code}" if event_code else "PHOTO"
            elif event_code:
                return f"EVENT {event_code}"
            else:
                return "EVENT"
        except:
            return "UNKNOWN"

    async def handle(self, reader, writer, client_ip, client_port, data):
        protocol_name = self.receiver.value.split(".")[-1]

        if data == b'\x06\x14':
            response = get_ack()
            writer.write(response)
            await writer.drain()
            logger.info("-->>", protocol_name, client_ip, response, label="ACK (PING)")
            return

        try:
            msg_str = data.decode(errors="ignore")
        except Exception as ex:
            response = get_nak()
            writer.write(response)
            await writer.drain()
            logger.info("-->>", protocol_name, client_ip, response, label="NAK (decode error)")
            return

        mode = self.mode_switcher.get_mode()
        if mode == "no_response":
            logger.info(f"({protocol_name}) ({client_ip}) -->> NO_RESPONSE (mode)")
            return
        elif mode == "nak":
            response = get_nak()
            writer.write(response)
            await writer.drain()
            logger.info("-->>", protocol_name, client_ip, response, label="NAK")
        else:
            response = get_ack()
            writer.write(response)
            await writer.drain()
            logger.info("-->>", protocol_name, client_ip, response, label="ACK")