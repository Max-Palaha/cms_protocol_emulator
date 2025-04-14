import asyncio
import sys
import logging
from datetime import datetime

from utils.mode_manager import EmulationMode, TimeModeDuration, mode_manager
from utils.tools import logger


VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "TRACE"]
MODES_WITH_COUNT = ["ack", "nak", "no-response"]
ALL_MODES = [m.value for m in EmulationMode]


async def stdin_listener(protocol_key: str):
    logger.info(
        f"[STDIN] Type commands to control '{protocol_key}' emulation (e.g., 'ack', 'nak 3', 'drop 2', 'time 2024-08-26 14:46:14 5', 'loglevel DEBUG')"
    )
    loop = asyncio.get_event_loop()

    while True:
        command = await loop.run_in_executor(None, sys.stdin.readline)
        command = command.strip()

        if not command:
            continue

        parts = command.split()
        protocol_mode = mode_manager.get(protocol_key)
        cmd = parts[0].lower()

        # Handle dynamic modes with count and optional 'then'
        if cmd in MODES_WITH_COUNT:
            count = None
            next_mode = None

            if len(parts) > 1:
                if parts[1].isdigit():
                    count = int(parts[1])
                if len(parts) > 3 and parts[2].lower() == "then":
                    next_raw = parts[3].lower()
                    if next_raw in ALL_MODES:
                        next_mode = EmulationMode(next_raw)
                    else:
                        logger.warning(f"[STDIN] Invalid next mode: {next_raw}")
                        continue

            protocol_mode.set_mode(EmulationMode(cmd), count, next_mode)
            continue

        match cmd:
            case "only-ping":
                protocol_mode.set_mode(EmulationMode.ONLY_PING)
            case "drop" if len(parts) > 1 and parts[1].isdigit():
                protocol_mode.set_drop(int(parts[1]))
            case "delay" if len(parts) > 1 and parts[1].isdigit():
                protocol_mode.set_delay(int(parts[1]))
            case "time" if len(parts) >= 3:
                try:
                    new_time = datetime.strptime(f"{parts[1]} {parts[2]}", "%Y-%m-%d %H:%M:%S")
                    duration = TimeModeDuration.FOREVER
                    count = -1

                    if len(parts) == 4:
                        if parts[3].lower() == "once":
                            duration = TimeModeDuration.ONCE
                            count = 1
                        elif parts[3].isdigit():
                            duration = TimeModeDuration.TIMES
                            count = int(parts[3])

                    protocol_mode.set_time(new_time, duration, count)
                except Exception as e:
                    logger.warning(f"[STDIN] Invalid time command: {e}")
            case "loglevel" if len(parts) == 2:
                level = parts[1].upper()
                if level in VALID_LOG_LEVELS:
                    logger.setLevel(getattr(logging, level))
                    logger.info(f"[STDIN] Log level changed to {level}")
                else:
                    logger.warning(f"[STDIN] Invalid log level '{parts[1]}'. Valid: {', '.join(VALID_LOG_LEVELS)}")
            case _:
                logger.warning(f"[STDIN] Unknown command: {command}")
                logger.info(
                    "[STDIN] Available commands:\n"
                    "  ack [N]                 - respond with ACK (optionally N times)\n"
                    "  nak [N]                 - respond with NAK (optionally N times)\n"
                    "  no-response [N]         - skip responses (optionally N times)\n"
                    "  only-ping               - respond only to pings, skip events\n"
                    "  drop N                  - drop next N packets\n"
                    "  delay N                 - delay each response by N seconds\n"
                    "  time YYYY-MM-DD HH:MM:SS [once|N|forever] - override timestamp\n"
                    "  loglevel LEVEL          - change log level (DEBUG, INFO, TRACE...)\n"
                )

