import asyncio
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from protocols.sia_dc09.parser import parse_sia_message, is_ping
from protocols.sia_dc09.responses import convert_sia_ack, convert_sia_nak
from utils.tools import logger
from utils.registry_tools import register_protocol


@register_protocol(Receiver.CMS_SIA_DCS)
class SIADC09Protocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.CMS_SIA_DCS)
        self.protocol_mode = mode_manager.get(self.receiver.value)

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value),
        )

    async def handle(self, reader, writer, client_ip, client_port, message: str):
        current_mode = self.protocol_mode.mode  # Save current mode BEFORE response

        if current_mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver}) NO_RESPONSE mode: skipping reply")
            return

        timestamp = self.protocol_mode.get_response_timestamp()

        if is_ping(message):
            if current_mode in [EmulationMode.ONLY_PING, EmulationMode.ACK, EmulationMode.NAK]:
                if current_mode == EmulationMode.NAK:
                    nak = convert_sia_nak(
                        sequence="0005",
                        receiver="R0",
                        line="L0",
                        account="#000",
                        timestamp=timestamp,
                    )
                    logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
                    writer.write(nak.encode())
                else:
                    ack = convert_sia_ack(
                        sequence="0005",
                        receiver="R0",
                        line="L0",
                        account="#000",
                        timestamp=timestamp,
                    )
                    logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
                    writer.write(ack.encode())
                await writer.drain()
            else:
                logger.info(f"({self.receiver}) ({client_ip}) PING received — skipped due to mode: {current_mode.value}")
            return

        if current_mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver}) ONLY_PING mode: skipping event")
            return

        if current_mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if current_mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        parsed = parse_sia_message(message)

        if current_mode == EmulationMode.NAK:
            nak = convert_sia_nak(**parsed, timestamp=timestamp)
            logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
            writer.write(nak.encode())
        else:
            ack = convert_sia_ack(**parsed, timestamp=timestamp)
            logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
            writer.write(ack.encode())

        await writer.drain()
        self.protocol_mode.consume_packet()
