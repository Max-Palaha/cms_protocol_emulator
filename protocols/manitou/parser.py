import re
from typing import Union, Dict
from utils.tools import logger

# compile regex to capture header length and body
MANITOU_HEADER_PATTERN = re.compile(
    r'^(?P<crc>[A-Fa-f0-9]{4})'         # CRC (4 hex chars)
    r'(?P<length>\d{4})"'             # Length (4 digits) + double-quote
    r'(?P<body>.+?)'                    # Body content (non-greedy)
    r'"_(?P<timestamp>.+)$'            # Timestamp after underscore
)

def parse_manitou_message(message: Union[str, bytes]) -> Dict[str, str]:
    """
    Parse Manitou framing: extract sequence, body, and timestamp.
    Returns a dict with keys: sequence, body, timestamp.
    """
    msg = message.decode('utf-8', errors='ignore') if isinstance(message, (bytes, bytearray)) else message
    result = {"sequence": "0000", "body": msg, "timestamp": ""}
    try:
        match = MANITOU_HEADER_PATTERN.search(msg)
        if match:
            result['sequence'] = match.group('length')
            result['body'] = match.group('body')
            result['timestamp'] = match.group('timestamp')
        else:
            logger.trace(f"(MANITOU) Header regex did not match message: {msg}")
    except Exception as e:
        logger.error(f"(MANITOU) Failed to parse Manitou message: {e}")
    return result


def is_ping(message: Union[str, bytes]) -> bool:
    """Detect ping by looking for NULL payload."""
    msg = message.decode('utf-8', errors='ignore') if isinstance(message, (bytes, bytearray)) else message
    return '"NULL"' in msg