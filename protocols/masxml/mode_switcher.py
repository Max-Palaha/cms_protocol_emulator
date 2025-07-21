from datetime import datetime
from utils.mode_manager import EmulationMode, TimeModeDuration
from utils.logger import logger


class MasxmlModeSwitcher:
    def __init__(self, protocol_mode):
        self.protocol_mode = protocol_mode

    def handle_command(self, command: str):
        tokens = command.strip().split()
        if not tokens:
            return

        cmd = tokens[0].lower()

        # Handle nak with specific ResultCode like nak9, nak10
        if cmd.startswith("nak") and len(cmd) > 3:
            code_str = cmd[3:]
            if code_str.isdigit():
                result_code = int(code_str)
                count = int(tokens[1]) if len(tokens) >= 2 and tokens[1].isdigit() else None
                self.protocol_mode.nak_result_code = result_code
                self.protocol_mode.set_mode(EmulationMode.NAK, count=count)
                logger.info(f"[MasxmlModeSwitcher] Switched to NAK mode with ResultCode {result_code}")
                return

        if cmd in ["ack", "nak", "no-response", "only-ping"]:
            self._handle_basic_mode(cmd, tokens)
        elif cmd == "drop" and len(tokens) >= 2:
            self._handle_drop(tokens)
        elif cmd == "delay" and len(tokens) >= 2:
            self._handle_delay(tokens)
        elif cmd == "time" and len(tokens) >= 4:
            self._handle_time(tokens)
        else:
            logger.warning(f"[MasxmlModeSwitcher] Unknown command: {command}")
            self._print_available_commands()

    def _handle_basic_mode(self, mode_name: str, tokens: list):
        try:
            mode = EmulationMode(mode_name)
        except ValueError:
            logger.warning(f"[MasxmlModeSwitcher] Invalid mode: {mode_name}")
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
                logger.warning(f"[MasxmlModeSwitcher] Invalid 'then' clause in command: {' '.join(tokens)}")

        self.protocol_mode.set_mode(mode, count=count, next_mode=next_mode)

    def _handle_drop(self, tokens: list):
        try:
            count = int(tokens[1])
            self.protocol_mode.set_drop(count)
        except ValueError:
            logger.warning(f"[MasxmlModeSwitcher] Invalid drop count: {tokens[1]}")

    def _handle_delay(self, tokens: list):
        try:
            seconds = int(tokens[1])
            self.protocol_mode.set_delay(seconds)
        except ValueError:
            logger.warning(f"[MasxmlModeSwitcher] Invalid delay seconds: {tokens[1]}")

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
            logger.warning(f"[MasxmlModeSwitcher] Invalid time command: {' '.join(tokens)}. Error: {e}")

    def _print_available_commands(self):
        logger.info(
            "[STDIN] Available commands:\n"
            "  ack [N]                 - respond with ACK (optionally N times)\n"
            "  nak [N]                 - respond with NAK (default ResultCode)\n"
            "  nak<code> [N]           - respond with NAK and custom ResultCode (e.g., nak9, nak10)\n"
            "  no-response [N]         - skip responses (optionally N times)\n"
            "  only-ping               - respond only to pings, skip events\n"
            "  drop N                  - drop next N packets\n"
            "  delay N                 - delay each response by N seconds\n"
            "  time YYYY-MM-DD HH:MM:SS [once|N|forever] - override timestamp\n"
            "  loglevel LEVEL          - change log level (DEBUG, INFO, TRACE...)\n"
        )
