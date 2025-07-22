import logging
import sys
from logging.handlers import RotatingFileHandler

class SafeFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "protocol"):
            record.protocol = "-"
        if not hasattr(record, "client_ip"):
            record.client_ip = "-"
        return super().format(record)

def get_formatter():
    return SafeFormatter(
        '%(levelname)-8s %(asctime)s (%(protocol)s) (%(client_ip)s) %(message)s',
        datefmt='%y-%m-%d %H:%M:%S'
    )

def setup_logger(
    log_file='logs/cms_protocol.log',
    max_bytes=5 * 1024 * 1024,
    backup_count=2,
    level=logging.INFO
):
    logger = logging.getLogger("cms_protocol_logger")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.hasHandlers():
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(get_formatter())
        logger.addHandler(ch)

        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        fh.setFormatter(get_formatter())
        logger.addHandler(fh)

    return logger

logger = setup_logger()
