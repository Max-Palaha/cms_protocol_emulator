import asyncio
import dataclasses
import json
import logging
import pathlib
import sys
from binascii import hexlify
from datetime import datetime
from logging.handlers import RotatingFileHandler

from utils.config_loader import get_port_by_key, get_logging_level
from utils.constants import LOGS_FILE_PATH

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


class MillisecondFormatter(logging.Formatter):
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s


def setup_logger(
    name: str,
    logs_file_path: pathlib.Path,
    file_handler_backup_count: int = 10,
) -> logging.Logger:
    if not logs_file_path.parent.exists():
        logs_file_path.parent.mkdir(parents=True)

    logger_obj = logging.getLogger(name)

    config_level = get_logging_level()
    logger_obj.setLevel(config_level)

    def trace_fn(msg, *args, **kwargs):
        if logger_obj.isEnabledFor(TRACE_LEVEL):
            logger_obj._log(TRACE_LEVEL, msg, args, **kwargs)

    setattr(logger_obj, "trace", trace_fn)

    file_handler = RotatingFileHandler(
        logs_file_path,
        maxBytes=1024 * 1024 * 50,
        backupCount=file_handler_backup_count,
        mode="wt",
        encoding="utf8",
    )
    file_handler.setLevel(config_level)

    formatter = MillisecondFormatter(
        "%(levelname)-8s %(asctime)s %(message)s",
        datefmt="%y-%m-%d %H:%M:%S.%f",
    )
    file_handler.setFormatter(formatter)

    handler_console = logging.StreamHandler(stream=sys.stdout)
    handler_console.setFormatter(formatter)
    handler_console.setLevel(config_level)

    logger_obj.handlers = [file_handler, handler_console]
    return logger_obj


logger = setup_logger(
    name="log",
    logs_file_path=LOGS_FILE_PATH,
)


def str_to_hex(str_value: str) -> str:
    return hexlify(str_value.encode()).decode(errors="ignore")


def detect_event_format(message: str) -> str:
    if '"NULL"' in message:
        return "PING"
    if "|0000" in message or "|5555" in message:
        return "ADM-CID"
    if 'SIA-DCS' in message:
        return "SIA-DCS"
    return "UNKNOWN"


async def tcp_client(internal_message, receiver: str):
    try:
        port = get_port_by_key("main")
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        message = json.dumps(dataclasses.asdict(internal_message))
        logger.info(f"({receiver}) Send to internal server: {message}")
        writer.write(message.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception as err:
        logger.info(f"({receiver}) Failed to send to internal server: {err}")