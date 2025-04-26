import asyncio
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.command_server import start_command_server
from protocols.sia_dc09.parser import parse_sia_message, is_ping
from protocols.sia_dc09.responses import convert_sia_ack, convert_sia_nak
from utils.tools import logger
from utils.registry_tools import register_protocol
from utils.mode_switcher import BaseModeSwitcher
from utils.mode_manager import EmulationMode, ProtocolMode


class SiaModeSwitcher(BaseModeSwitcher):
    def handle_command(self, command: str):
        logger.debug(f"[SiaModeSwitcher] Received command: {command}")
        tokens = command.strip().lower().split()
        if not tokens:
            self._invalid_command(command)
            return

        cmd = tokens[0]
        if cmd in ["ack", "nak", "none", "no-response", "only-ping"]:
            times = None
            next_mode = None
            if len(tokens) >= 2 and tokens[1].isdigit():
                times = int(tokens[1])
            if len(tokens) >= 4 and tokens[2] == "then":
                next_mode = tokens[3].upper()

            try:
                mode = EmulationMode[cmd.upper().replace("-", "_")]
                self.protocol_mode.set_mode(mode, times=times, next_mode=next_mode)
                logger.info(f"[SiaModeSwitcher] Switched to {mode.name} for {times or '∞'} times, then {next_mode or 'ACK'}")
            except KeyError:
                self._invalid_command(command)

        elif cmd == "drop" and len(tokens) == 2:
            try:
                self.protocol_mode.set_drop(int(tokens[1]))
                logger.info(f"[SiaModeSwitcher] Dropping next {tokens[1]} packets")
            except ValueError:
                self._invalid_command(command)

        elif cmd == "delay" and len(tokens) == 2:
            try:
                self.protocol_mode.set_delay(float(tokens[1]))
                logger.info(f"[SiaModeSwitcher] Delay set to {tokens[1]} seconds")
            except ValueError:
                self._invalid_command(command)

        elif cmd == "time" and len(tokens) >= 2:
            try:
                from utils.tools import parse_custom_time
                time_str = " ".join(tokens[1:3])
                duration = tokens[3] if len(tokens) > 3 else "once"
                dt = parse_custom_time(time_str)
                self.protocol_mode.set_custom_time(dt, duration)
                logger.info(f"[SiaModeSwitcher] Time override set to {dt} for {duration}")
            except Exception as e:
                logger.warning(f"[SiaModeSwitcher] Invalid time command: {e}")
                self._invalid_command(command)
        else:
            self._invalid_command(command)


@register_protocol(Receiver.CMS_SIA_DCS)
class SIADC09Protocol(BaseProtocol):
    def __init__(self, protocol_mode: ProtocolMode):
        super().__init__(receiver=Receiver.CMS_SIA_DCS)
        self.protocol_mode = protocol_mode
        self.mode_switcher = SiaModeSwitcher(self.protocol_mode)
        self.command_server = None

    async def run(self):
        protocol_task = asyncio.create_task(super().run())
        self.command_server = await start_command_server("127.0.0.1", 6688, self.mode_switcher)
        return protocol_task

    async def shutdown(self):
        if self.command_server:
            self.command_server.close()
            await self.command_server.wait_closed()
            logger.info(f"({self.receiver}) Command server shut down")

    async def handle(self, reader, writer, client_ip, client_port, message: str):
        logger.debug(f"[DIAG] Received message from {client_ip}:{client_port} -> {message!r}")
        current_mode = self.protocol_mode.mode
        timestamp = self.protocol_mode.get_response_timestamp()

        if current_mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver}) NO_RESPONSE mode: skipping reply")
            return

        if is_ping(message):
            if current_mode in [EmulationMode.ONLY_PING, EmulationMode.ACK, EmulationMode.NAK]:
                response_func = convert_sia_nak if current_mode == EmulationMode.NAK else convert_sia_ack
                payload = response_func(
                    sequence="0005",
                    receiver="R0",
                    line="L0",
                    account="#000",
                    timestamp=timestamp,
                )
                logger.info(f"({self.receiver}) ({client_ip}) -->> {payload.strip()}")
                writer.write(payload.encode("utf-8", errors="replace"))
                logger.info(f"({self.receiver}) Sent: {payload.strip()}")
                await writer.drain()
                self.protocol_mode.consume_packet()
            else:
                logger.info(f"({self.receiver}) PING received — skipped due to mode: {current_mode.value}")
            return

        if current_mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver}) ONLY_PING mode: skipping event")
            return

        if current_mode == EmulationMode.DROP_N and self.protocol_mode.drop_count > 0:
            self.protocol_mode.drop_count -= 1
            logger.info(f"({self.receiver}) Dropped message (remaining: {self.protocol_mode.drop_count})")
            return
        elif current_mode == EmulationMode.DROP_N:
            self.protocol_mode.set_mode(EmulationMode.ACK)

        if current_mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        parsed = parse_sia_message(message)
        logger.debug(f"[DIAG] Parsed message: {parsed}")
        if not parsed or "account" not in parsed:
            logger.warning("[DIAG] Parsed result invalid — skipping response")
            return

        if current_mode == EmulationMode.NAK:
            response = convert_sia_nak(**parsed, timestamp=timestamp)
        else:
            response = convert_sia_ack(**parsed, timestamp=timestamp)

        logger.info(f"({self.receiver}) ({client_ip}) -->> {response.strip()}")
        writer.write(response.encode("utf-8", errors="replace"))
        logger.info(f"({self.receiver}) Sent: {response.strip()}")
        await writer.drain()
        self.protocol_mode.consume_packet()
