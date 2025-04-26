import asyncio
from core.connection_handler import BaseProtocol
from utils.command_server import start_command_server
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.tools import logger
from protocols.masxml.parser import is_ping
from protocols.masxml.responses import convert_masxml_ack, convert_masxml_nak
from utils.registry_tools import register_protocol
from protocols.masxml.mode_switcher import MasxmlModeSwitcher


@register_protocol(Receiver.CMS_MASXML)
class MasxmlProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.CMS_MASXML)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self.mode_switcher = MasxmlModeSwitcher(self.protocol_mode)

    async def run(self):
        protocol_task = asyncio.create_task(super().run())
        self.command_server = await start_command_server("127.0.0.1", 6688, self.mode_switcher)
        return protocol_task
    
    async def shutdown(self):
        if hasattr(self, "command_server") and self.command_server:
            self.command_server.close()
            await self.command_server.wait_closed()
            logger.info(f"({self.receiver}) Command server shut down")

    async def handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        client_ip: str,
        client_port: int,
        raw_message: str,
    ):
        print(f"[DEBUG] handle() called with message:\n{raw_message!r}")

        try:
            mode = self.protocol_mode.mode

            if mode == EmulationMode.NO_RESPONSE:
                logger.info(f"({self.receiver}) NO_RESPONSE mode: skipping reply")
                return

            if is_ping(raw_message):
                await self._handle_ping(writer, raw_message, client_ip)
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

            if mode == EmulationMode.NAK:
                await self._send_nak(writer, raw_message, client_ip, reason="Command rejected due to emulation mode")
            else:
                await self._send_ack(writer, raw_message, client_ip)

            await writer.drain()
            self.protocol_mode.consume_packet()

        except Exception as e:
            logger.error(f"({self.receiver}) ({client_ip}) Error in handle(): {e}")

    async def _handle_ping(self, writer, raw_message, client_ip):
        mode = self.protocol_mode.mode
        if mode == EmulationMode.NAK:
            await self._send_nak(writer, raw_message, client_ip, reason="Ping rejected due to emulation mode")
        elif mode in [EmulationMode.ONLY_PING, EmulationMode.ACK]:
            await self._send_ack(writer, raw_message, client_ip)
        else:
            logger.info(f"({self.receiver}) ({client_ip}) PING received — skipped due to mode: {mode.value}")

    async def _send_ack(self, writer, raw_message, client_ip):
        ack = convert_masxml_ack(raw_message)
        logger.info(f"({self.receiver}) ({client_ip}) -->> {ack.strip()}")
        writer.write(ack.encode("utf-8", errors="replace"))

    async def _send_nak(self, writer, raw_message, client_ip, reason="Rejected"):
        code = self.protocol_mode.get_nak_code()
        print(f"[DEBUG] EmulationMode: NAK")
        print(f"[DEBUG] nak_result_code = {code}")
        nak = convert_masxml_nak(
            raw_message,
            text=reason,
            code=code,
        )
        logger.info(f"({self.receiver}) ({client_ip}) -->> {nak.strip()}")
        print(f"[DEBUG] Sending NAK with code = {code}")
        writer.write(nak.encode("utf-8", errors="replace"))
