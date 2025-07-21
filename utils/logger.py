import sys
import pathlib
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from utils.constants import LOGS_FILE_PATH

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")

class MillisecondFormatter(logging.Formatter):
    """Formatter with millisecond timestamp."""
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s

class BytesLoggingMixin:
    def log_bytes(self, direction, receiver, client_ip, data: bytes, label: str = ""):
        msg = f"({receiver}) ({client_ip}) {direction} [{label}] {data!r}"
        self.info(msg)

class ExtendedLogger(logging.Logger, BytesLoggingMixin):
    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)

logging.setLoggerClass(ExtendedLogger)

def setup_logger(
    name: str = "log",
    logs_file_path: pathlib.Path = LOGS_FILE_PATH,
    file_level=logging.DEBUG,
    console_level=logging.DEBUG,
    file_handler_backup_count: int = 10,
    main_logging_level: int = logging.DEBUG,
) -> logging.Logger:
    if not logs_file_path.parent.exists():
        logs_file_path.parent.mkdir(parents=True, exist_ok=True)

    logger_obj = logging.getLogger(name)
    logger_obj.setLevel(main_logging_level)

    if logger_obj.handlers:
        return logger_obj  # prevent duplicate handlers

    file_handler = RotatingFileHandler(
        logs_file_path,
        maxBytes=1024 * 1024 * 50,
        backupCount=file_handler_backup_count,
        mode="wt",
        encoding="utf8",
    )
    file_handler.setLevel(file_level)

    formatter = MillisecondFormatter(
        "%(levelname)-8s %(asctime)s %(message)s",
        datefmt="%y-%m-%d %H:%M:%S.%f",
    )
    file_handler.setFormatter(formatter)

    handler_console = logging.StreamHandler(stream=sys.stdout)
    handler_console.setFormatter(formatter)
    handler_console.setLevel(console_level)

    logger_obj.handlers = [file_handler, handler_console]
    return logger_obj

logger = setup_logger()
