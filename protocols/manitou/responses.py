import random
import string
from utils.tools import logger


def generate_random_str12() -> str:
    """Generate a random 12-character alphanumeric string."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))


def convert_manitou_ack() -> bytes:
    """
    Build a standard ACK response for Manitou.
    Format: [STX]<?xml version="1.0"?><Ack><RawNo>{random12}</RawNo></Ack>[ETX]
    """
    raw_no = generate_random_str12()
    payload = f'<?xml version="1.0"?><Ack><RawNo>{raw_no}</RawNo></Ack>'
    message = f'{chr(0x02)}{payload}{chr(0x03)}'
    logger.debug(f"(MANITOU) → ACK payload: {payload}")
    return message.encode()


def convert_manitou_nak(reason_code: int = 0) -> bytes:
    """
    Build a NAK response for Manitou with an optional reason code.
    Format: [STX]<?xml version="1.0"?><Nak><Code>{reason_code}</Code></Nak>[ETX]
    """
    payload = f'<?xml version="1.0"?><Nak><Code>{reason_code}</Code></Nak>'
    message = f'{chr(0x02)}{payload}{chr(0x03)}'
    logger.debug(f"(MANITOU) → NAK payload: {payload}")
    return message.encode()