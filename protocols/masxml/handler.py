import asyncio
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from utils.tools import logger
from protocols.masxml.parser import is_ping
from protocols.masxml.responses import convert_masxml_ack, convert_masxml_nak
from utils.registry_tools import register_protocol


@register_protocol(Receiver.CMS_MASXML)
class MasxmlProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.CMS_MASXML)
        self.protocol_mode = mode_manager.get(self.receiver.value)

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value),
        )

    async def handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        client_ip: str,
        client_port: int,
        raw_message: str,
    ):
        mode = self.protocol_mode.mode  # capture mode before response

        # NO_RESPONSE
        if mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver}) NO_RESPONSE mode: skipping reply")
            return

        # PING
        if is_ping(raw_message):
            if mode == EmulationMode.NAK:
                nak = convert_masxml_nak(raw_message, text="Ping rejected due to emulation mode")
                logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
                writer.write(nak.encode())
                await writer.drain()
            elif mode in [EmulationMode.ONLY_PING, EmulationMode.ACK, EmulationMode.TIME_CUSTOM]:
                ack = convert_masxml_ack(raw_message)
                logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
                writer.write(ack.encode())
                await writer.drain()
            else:
                logger.info(f"({self.receiver}) ({client_ip}) PING received — skipped due to mode: {mode.value}")
            return

        # ONLY_PING (skip all events)
        if mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver}) ONLY_PING mode: skipping event")
            return

        # DROP_N
        if mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        # DELAY_N
        if mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        # NAK
        if mode == EmulationMode.NAK:
            nak = convert_masxml_nak(raw_message, text="Command rejected due to emulation mode")
            logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
            writer.write(nak.encode())
        else:
            # ACK or TIME_CUSTOM
            ack = convert_masxml_ack(raw_message)
            logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
            writer.write(ack.encode())

        await writer.drain()
        self.protocol_mode.consume_packet()  # move to end of handling
