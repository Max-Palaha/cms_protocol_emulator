import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional, Dict

from utils.tools import logger


class EmulationMode(Enum):
    ACK = "ack"
    NAK = "nak"
    NO_RESPONSE = "no-response"
    ONLY_PING = "only-ping"
    DROP_N = "drop"
    DELAY_N = "delay"


class TimeModeDuration(Enum):
    ONCE = "once"
    TIMES = "times"
    FOREVER = "forever"


class ProtocolMode:
    def __init__(self):
        self.mode: EmulationMode = EmulationMode.ACK
        self.previous_mode: Optional[EmulationMode] = None
        self.mode_packet_count: Optional[int] = None
        self.next_mode: Optional[EmulationMode] = None

        self.drop_count = 0
        self.delay_seconds = 0

        self.time_override: Optional[datetime] = None
        self.time_mode_duration: Optional[TimeModeDuration] = None
        self.time_left = 0

    def set_mode(self, mode: EmulationMode, count: Optional[int] = None, next_mode: Optional[EmulationMode] = None):
        if count is not None and self.mode != mode:
            self.previous_mode = self.mode

        self.mode = mode
        self.mode_packet_count = count
        self.next_mode = next_mode

        count_info = f" for next {count} packets" if count is not None else ""
        next_info = f" then switch to {next_mode.value}" if next_mode else ""
        logger.info(f"[MODE_MANAGER] Switched to mode: {mode.value}{count_info}{next_info}")

    def consume_packet(self) -> bool:
        if self.mode_packet_count is not None:
            self.mode_packet_count -= 1
            if self.mode_packet_count <= 0:
                if self.next_mode:
                    logger.info(f"[MODE_MANAGER] Mode {self.mode.value} completed. Switching to next mode: {self.next_mode.value}")
                    self.set_mode(self.next_mode)
                elif self.previous_mode:
                    logger.info(f"[MODE_MANAGER] Mode {self.mode.value} completed. Switching to previous mode: {self.previous_mode.value}")
                    self.set_mode(self.previous_mode)
                else:
                    logger.info(f"[MODE_MANAGER] Mode {self.mode.value} completed. Switching to default ACK")
                    self.set_mode(EmulationMode.ACK)
                return True
        return False

    def set_drop(self, count: int):
        self.set_mode(EmulationMode.DROP_N)
        self.drop_count = count
        logger.info(f"[MODE_MANAGER] Dropping next {count} packets")

    def set_delay(self, seconds: int):
        self.set_mode(EmulationMode.DELAY_N)
        self.delay_seconds = seconds
        logger.info(f"[MODE_MANAGER] Delaying responses by {seconds} seconds")

    def set_time(self, new_time: datetime, duration: TimeModeDuration, count: int = 1):
        self.time_override = new_time
        self.time_mode_duration = duration
        self.time_left = count if duration == TimeModeDuration.TIMES else -1
        logger.info(f"[MODE_MANAGER] Setting custom timestamp {new_time} with duration {duration.value}")

    def get_response_timestamp(self) -> str:
        if self.time_override:
            timestamp = self.time_override.strftime("%H:%M:%S,%m-%d-%Y")

            if self.time_mode_duration == TimeModeDuration.ONCE:
                self._clear_time_override()
            elif self.time_mode_duration == TimeModeDuration.TIMES:
                self.time_left -= 1
                if self.time_left <= 0:
                    self._clear_time_override()

            return timestamp

        return datetime.now().strftime("%H:%M:%S,%m-%d-%Y")

    def _clear_time_override(self):
        logger.debug("[MODE_MANAGER] Clearing custom timestamp override")
        self.time_override = None
        self.time_mode_duration = None
        self.time_left = 0


class ModeManager:
    def __init__(self):
        self._modes: Dict[str, ProtocolMode] = {}

    def get(self, protocol_name: str) -> ProtocolMode:
        if protocol_name not in self._modes:
            self._modes[protocol_name] = ProtocolMode()
        return self._modes[protocol_name]

    def reset_all(self):
        self._modes.clear()
        logger.info("[MODE_MANAGER] All modes have been reset")


mode_manager = ModeManager()
