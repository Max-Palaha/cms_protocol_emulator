from utils.mode_manager import EmulationMode, TimeModeDuration
from utils.tools import logger
from utils.mode_switcher import BaseModeSwitcher


class SiaModeSwitcher(BaseModeSwitcher):
    def handle_command(self, command: str):
        logger.debug(f"[SiaModeSwitcher] Received: '{command}'")
        tokens = command.strip().lower().split()
        if not tokens:
            logger.warning("[SiaModeSwitcher] Empty command received")
            return

        cmd = tokens[0]

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
            self.print_help()

    def _handle_simple_mode(self, mode: EmulationMode, args: list[str]):
        count = 1
        next_mode = EmulationMode.ACK
        if args:
            try:
                count = int(args[0])
                if len(args) >= 2 and args[1] == "then" and len(args) >= 3:
                    next_mode = self._parse_mode(args[2])
                elif len(args) == 2:
                    # If 'then' was omitted but another token exists, assume it's next mode
                    next_mode = self._parse_mode(args[1])
            except Exception as e:
                logger.warning(f"[SiaModeSwitcher] Failed to parse mode command: {args} — {e}")
                self.print_help()
                return

        self.protocol_mode.set_mode(mode, count=count, next_mode=next_mode)
        logger.info(f"[SiaModeSwitcher] Switched to {mode.name} for {count} times, then {next_mode.name}")

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

    def print_help(self):
        logger.warning("[SiaModeSwitcher] Unknown command. Supported:")
        logger.warning("  ack [N] [then MODE]")
        logger.warning("  nak [N] [then MODE]")
        logger.warning("  no-response [N] [then MODE]")
        logger.warning("  only-ping")
        logger.warning("  drop N")
        logger.warning("  delay N")
        logger.warning("  time YYYY-MM-DD HH:MM:SS once|5|forever")
