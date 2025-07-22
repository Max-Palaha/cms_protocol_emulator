from utils.mode_manager import EmulationMode, TimeModeDuration
from utils.tools import logger
from utils.mode_switcher import BaseModeSwitcher


class SiaModeSwitcher(BaseModeSwitcher):
    def handle_command(self, command: str):
        logger.debug(f"[SiaModeSwitcher] Received command: '{command}'")
        tokens = command.strip().lower().split()

        if not tokens:
            logger.warning("[SiaModeSwitcher] Empty command received")
            return

        cmd = tokens[0]

        try:
            if cmd == "ack":
                self._handle_simple_mode(EmulationMode.ACK, tokens[1:])
            elif cmd == "nak":
                self._handle_simple_mode(EmulationMode.NAK, tokens[1:])
            elif cmd in ("none", "no-response"):
                self._handle_simple_mode(EmulationMode.NO_RESPONSE, tokens[1:])
            elif cmd == "only-ping":
                self.protocol_mode.set_mode(EmulationMode.ONLY_PING)
                logger.info("[SiaModeSwitcher] Switched to ONLY_PING mode")
            elif cmd == "drop":
                self._handle_drop(tokens[1:])
            elif cmd == "delay":
                self._handle_delay(tokens[1:])
            elif cmd == "time":
                self._handle_time(tokens[1:])
            else:
                raise ValueError(f"Unknown command: {cmd}")

        except Exception as e:
            logger.error(f"[SiaModeSwitcher] Error handling command '{command}': {e}")
            raise

    def _handle_simple_mode(self, mode: EmulationMode, args: list[str]):
        count = 1
        next_mode = EmulationMode.ACK

        try:
            if args:
                count = int(args[0])
                if len(args) >= 2 and args[1] == "then" and len(args) >= 3:
                    next_mode = self._parse_mode(args[2])
                elif len(args) == 2:
                    next_mode = self._parse_mode(args[1])
        except ValueError as e:
            logger.warning(f"[SiaModeSwitcher] Failed to parse arguments {args}: {e}")
            pass

        self.protocol_mode.set_mode(mode, count=count, next_mode=next_mode)
        logger.info(f"[SiaModeSwitcher] Mode set to {mode.name} for {count} times, then {next_mode.name}")


    def _handle_drop(self, args: list[str]):
        if not args:
            raise ValueError("Usage: drop N")
        try:
            count = int(args[0])
            self.protocol_mode.set_mode(EmulationMode.DROP, count=count)
            logger.info(f"[SiaModeSwitcher] Mode set to DROP for {count} times")
        except ValueError:
            raise ValueError("Invalid count for drop")

    def _handle_delay(self, args: list[str]):
        if not args:
            raise ValueError("Usage: delay N")
        try:
            count = int(args[0])
            self.protocol_mode.set_mode(EmulationMode.DELAY, count=count)
            logger.info(f"[SiaModeSwitcher] Mode set to DELAY for {count} times")
        except ValueError:
            raise ValueError("Invalid count for delay")


    def _handle_time(self, args: list[str]):
        if len(args) < 3:
            raise ValueError("Usage: time YYYY-MM-DD HH:MM:SS once|5|forever")

        date = args[0]
        time = args[1]
        full_timestamp = f"{date} {time}"

        duration = args[2]
        if duration == "once":
            times = 1
        elif duration == "forever":
            times = None
        else:
            times = int(duration)

        self.protocol_mode.set_custom_time(full_timestamp, times)
        logger.info(f"[SiaModeSwitcher] Custom time set to {full_timestamp}, repeats: {times}")

    def _parse_mode(self, value: str) -> EmulationMode:
        value = value.lower()
        if value == "ack":
            return EmulationMode.ACK
        elif value == "nak":
            return EmulationMode.NAK
        elif value in ("none", "no-response"):
            return EmulationMode.NO_RESPONSE
        elif value == "only-ping":
            return EmulationMode.ONLY_PING
        else:
            raise ValueError(f"Unknown mode: {value}")
