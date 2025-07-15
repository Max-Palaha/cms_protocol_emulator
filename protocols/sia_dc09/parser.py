import re
from typing import Union, Dict
from utils.tools import logger

# compile regex to capture all header fields at once (support ADM-CID with hex length)
SIA_HEADER_PATTERN = re.compile(
    r'^(?P<crc>[A-F0-9]{4})'               # CRC (4 hex chars)
    r'(?P<length>[A-F0-9]{4})"'            # Length (4 hex chars or digits) + "
    r'(?P<message_type>ACK|NAK|NULL|ADM-CID)"'  # Message type
    r'(?P<sequence>\d{4})'                 # Sequence number (4 digits)
    r'(?P<line>L\d)'                       # Line, e.g. L0
    r'#(?P<account>[^[]*)'                 # Account: anything up to '['
)

def parse_sia_message(message: Union[str, bytes]) -> Dict[str, str]:
    """
    parse SIA-DC09 header fields from incoming message
    Returns a dict with keys: sequence, receiver, line, account
    """
    # normalize input to str
    msg = (
        message.decode('utf-8', errors='ignore')
        if isinstance(message, (bytes, bytearray))
        else message
    )

    # defaults if regex fails
    result = {
        "sequence": "0000",
        "receiver": "R0",
        "line":     "L0",
        "account":  "unknown",
    }

    try:
        match = SIA_HEADER_PATTERN.search(msg)
        if match:
            # update only the captured fields
            result.update({
                "sequence": match.group("sequence"),
                "line":     match.group("line"),
                "account":  match.group("account") or "unknown",
            })
        else:
            logger.trace(f"(SIA_DC09) Header regex did not match message: {msg}")

        logger.trace(f"(SIA_DC09) Parsed SIA message: {result}")
    except Exception as e:
        logger.error(f"(SIA_DC09) Failed to parse SIA message: {e}")

    return result

def is_ping(message: str) -> bool:
    return '"NULL"' in message
