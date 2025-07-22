import asyncio
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from .parser import parse_microkey_sequence, is_ping_microkey
from .responses import generate_ack, generate_nak
from utils.logger import logger
from utils.registry_tools import register_protocol

@register_protocol(Receiver.MICROKEY)
class MicrokeyProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.MICROKEY)
        self.protocol_mode = mode_manager.get(self.receiver.value)

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value),
        )

    async def handle(self, reader, writer, client_ip, client_port, message: str):
        current_mode = self.protocol_mode.mode  # Save current mode BEFORE response

        if current_mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver.value}) NO_RESPONSE mode: skipping reply")
            return

        timestamp = self.protocol_mode.get_response_timestamp()
        sequence = parse_microkey_sequence(message)
        if sequence is None:
            logger.warning(f"({self.receiver.value}) Invalid message format from {client_ip}:{client_port}: {message!r}")
            return

        if is_ping_microkey(message):
            if current_mode in [EmulationMode.ONLY_PING, EmulationMode.ACK, EmulationMode.NAK]:
                if current_mode == EmulationMode.NAK:
                    nak = generate_nak(sequence)
                    logger.info(f"({self.receiver.value}) ({client_ip}) -->> {nak.strip()}")
                    writer.write(nak)
                else:
                    ack = generate_ack(sequence)
                    logger.info(f"({self.receiver.value}) ({client_ip}) -->> {ack.strip()}")
                    writer.write(ack)
                await writer.drain()
            else:
                logger.info(f"({self.receiver.value}) ({client_ip}) PING received — skipped due to mode: {current_mode.value}")
            return

        if current_mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver.value}) ONLY_PING mode: skipping event")
            return

        if current_mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver.value}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if current_mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver.value}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        if current_mode == EmulationMode.NAK:
            nak = generate_nak(sequence)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> {nak.strip()}")
            writer.write(nak)
        else:
            ack = generate_ack(sequence)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> {ack.strip()}")
            writer.write(ack)

        await writer.drain()
        self.protocol_mode.consume_packet()
