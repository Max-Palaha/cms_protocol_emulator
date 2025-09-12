from datetime import datetime
from utils.mode_manager import EmulationMode, TimeModeDuration
from utils.logger import logger


class ManitouModeSwitcher:
    """
    CLI-like switcher for runtime emulation modes (stdin commands), MASXML-style.
    Supported commands:
      ack [N] | nak [N] | no-response [N] | only-ping
      drop N  | delay N
      time YYYY-MM-DD HH:MM:SS [once|N|forever]
    """

    def __init__(self, protocol_mode):
        self.protocol_mode = protocol_mode

    def handle_command(self, command: str):
        tokens = command.strip().split()
        if not tokens:
            return

        cmd = tokens[0].lower()

        if cmd in ["ack", "nak", "no-response", "only-ping"]:
            self._handle_basic_mode(cmd, tokens)
        elif cmd == "drop" and len(tokens) >= 2:
            self._handle_drop(tokens)
        elif cmd == "delay" and len(tokens) >= 2:
            self._handle_delay(tokens)
        elif cmd == "time" and len(tokens) >= 4:
            self._handle_time(tokens)
        else:
            logger.warning(f"[ManitouModeSwitcher] Unknown command: {command}")
            self._print_available_commands()

    def _handle_basic_mode(self, mode_name: str, tokens: list):
        try:
            mode = EmulationMode(mode_name)
        except ValueError:
            logger.warning(f"[ManitouModeSwitcher] Invalid mode: {mode_name}")
            return

        count = None
        next_mode = None

        if len(tokens) >= 2:
            try:
                count = int(tokens[1])
            except ValueError:
                pass

        if "then" in tokens:
            try:
                idx = tokens.index("then")
                next_mode = EmulationMode(tokens[idx + 1])
            except Exception:
                logger.warning(f"[ManitouModeSwitcher] Invalid 'then' clause in command: {' '.join(tokens)}")

        self.protocol_mode.set_mode(mode, count=count, next_mode=next_mode)

    def _handle_drop(self, tokens: list):
        try:
            count = int(tokens[1])
            self.protocol_mode.set_drop(count)
        except ValueError:
            logger.warning(f"[ManitouModeSwitcher] Invalid drop count: {tokens[1]}")

    def _handle_delay(self, tokens: list):
        try:
            seconds = int(tokens[1])
            self.protocol_mode.set_delay(seconds)
        except ValueError:
            logger.warning(f"[ManitouModeSwitcher] Invalid delay seconds: {tokens[1]}")

    def _handle_time(self, tokens: list):
        try:
            date_str = tokens[1] + " " + tokens[2]
            timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            duration_token = tokens[3]

            if duration_token == "once":
                duration = TimeModeDuration.ONCE
                count = 1
            elif duration_token.isdigit():
                duration = TimeModeDuration.TIMES
                count = int(duration_token)
            elif duration_token == "forever":
                duration = TimeModeDuration.FOREVER
                count = -1
            else:
                raise ValueError("Invalid time duration")

            self.protocol_mode.set_time(timestamp, duration, count)
        except Exception as e:
            logger.warning(f"[ManitouModeSwitcher] Invalid time command: {' '.join(tokens)}. Error: {e}")

    def _print_available_commands(self):
        logger.info(
            "[STDIN] Available commands:\n"
            "  ack [N]                 - respond with ACK (optionally N times)\n"
            "  nak [N]                 - suppress acks for events (simulate NAK)\n"
            "  no-response [N]         - skip responses (optionally N times)\n"
            "  only-ping               - respond only to pings, skip events\n"
            "  drop N                  - drop next N packets\n"
            "  delay N                 - delay each response by N seconds\n"
            "  time YYYY-MM-DD HH:MM:SS [once|N|forever] - override timestamp\n"
            "  loglevel LEVEL          - change log level (DEBUG, INFO, TRACE...)\n"
        )
