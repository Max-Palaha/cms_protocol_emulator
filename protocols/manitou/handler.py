import asyncio

from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from protocols.manitou.parser import parse_manitou_message, is_ping
from protocols.manitou.responses import convert_manitou_ack, convert_manitou_nak
from utils.tools import logger
from utils.registry_tools import register_protocol

@register_protocol(Receiver.MANITOU)
class ManitouProtocol(BaseProtocol):
    """Manitou protocol emulator."""

    def __init__(self):
        # initialize BaseProtocol with MANITOU receiver
        super().__init__(receiver=Receiver.MANITOU)
        # get the mode manager instance for this protocol
        self.protocol_mode = mode_manager.get(self.receiver.value)

    async def run(self):
        """Start TCP server and command listener concurrently."""
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value),
        )

    async def handle(self, reader, writer, client_ip, client_port, message: str):
        """Handle a single incoming Manitou message."""
        current_mode = self.protocol_mode.mode

        # NO_RESPONSE: do not reply
        if current_mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver.value}) NO_RESPONSE mode: skipping reply")
            return

        # parse message (extract sequence, body, timestamp)
        info = parse_manitou_message(message)

        # ping messages
        if is_ping(message):
            if current_mode in (EmulationMode.ACK, EmulationMode.ONLY_PING, EmulationMode.NAK):
                if current_mode == EmulationMode.NAK:
                    resp = convert_manitou_nak()
                else:
                    resp = convert_manitou_ack()
                logger.info(
                    f"({self.receiver.value}) ({client_ip}) --> {resp.decode(errors='ignore').strip()}"
                )
                writer.write(resp)
                await writer.drain()
            else:
                logger.info(
                    f"({self.receiver.value}) ({client_ip}) ping skipped in mode {current_mode.value}"
                )
            return

        # ONLY_PING: skip non-ping events
        if current_mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver.value}) ONLY_PING mode: skipping event")
            return

        # DROP_N: drop configured number of events, then revert to ACK
        if current_mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(
                    f"({self.receiver.value}) dropped event (remaining drops: {self.protocol_mode.drop_count})"
                )
                return
            self.protocol_mode.set_mode(EmulationMode.ACK)

        # DELAY_N: delay response by configured seconds then continue
        if current_mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver.value}) delaying response by {delay}s")
            await asyncio.sleep(delay)

        # final NAK or ACK for events
        if current_mode == EmulationMode.NAK:
            resp = convert_manitou_nak()
        else:
            resp = convert_manitou_ack()

        logger.info(
            f"({self.receiver.value}) ({client_ip}) --> {resp.decode(errors='ignore').strip()}"
        )
        writer.write(resp)
        await writer.drain()

        # consume one packet (decrement counters) in the mode manager
        self.protocol_mode.consume_packet()