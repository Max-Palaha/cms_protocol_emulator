import re
from typing import Union, Dict
from utils.logger import logger

# compile one regex to capture all header fields at once
SIA_HEADER_PATTERN = re.compile(
    r'^(?P<crc>[A-F0-9]{4})'            # CRC (4 hex chars)
    r'(?P<length>\d{4})"'               # Length (4 digits) + double-quote
    r'(?P<message_type>ACK|NAK|NULL)"'  # Message type in quotes
    r'(?P<sequence>\d{4})'              # Sequence number (4 digits)
    r'(?P<receiver>R\d)'                # Receiver, e.g. R0 or R1
    r'(?P<line>L\d)'                    # Line, e.g. L0
    r'(?P<area>A\d)'                    # Area, e.g. A0
    r'#(?P<account>\w+)'                # Account after '#'
)

def parse_sia_message(message: Union[str, bytes]) -> Dict[str, str]:
    """
    parse SIA-DC09 header fields from incoming message
    Returns a dict with keys: sequence, receiver, line, area, account.
    """
    # Normalize input to str
    msg = message.decode('utf-8', errors='ignore') if isinstance(message, (bytes, bytearray)) else message

    # default values if regex fails
    result = {
        "sequence": "0000",
        "receiver": "R0",
        "line":     "L0",
        "area":     "A0",
        "account":  "unknown",
    }

    try:
        match = SIA_HEADER_PATTERN.search(msg)
        if match:
            # update only the captured fields
            result.update({
                "sequence": match.group("sequence"),
                "receiver": match.group("receiver"),
                "line":     match.group("line"),
                "area":     match.group("area"),
                "account":  match.group("account"),
            })
        else:
            logger.trace(f"(SIA_DC09) Header regex did not match message: {msg}")

        logger.trace(f"(SIA_DC09) Parsed SIA message: {result}")
    except Exception as e:
        logger.error(f"(SIA_DC09) Failed to parse SIA message: {e}")

    return result

def is_ping(message: str) -> bool:
    return '"NULL"' in message
