import re
from typing import Union, Dict
from utils.logger import logger

# Compile regex to capture SIA-DC09 header fields (supports ADM-CID with hex length)
SIA_HEADER_PATTERN = re.compile(
    r'^(?P<crc>[A-F0-9]{4})'                     # CRC (4 hex chars)
    r'(?P<length>[A-F0-9]{4})"'                  # Length (4 hex chars) + "
    r'(?P<message_type>ACK|NAK|NULL|ADM-CID)"'   # Message type
    r'(?P<sequence>\d{4})'                       # Sequence number (4 digits)
    r'(?P<line>L\d)'                             # Line, e.g. L0
    r'#(?P<account>[^[]*)'                       # Account: anything up to '['
)

def parse_sia_message(message: Union[str, bytes]) -> Dict[str, str]:
    """
    Parse SIA-DC09 header fields from incoming message.
    Returns a dict with keys at least: sequence, account.
    (Also returns line and receiver when available for future compatibility.)
    """
    # Normalize to str and trim newlines/spaces
    msg = message.decode('utf-8', errors='ignore') if isinstance(message, (bytes, bytearray)) else message
    msg = msg.strip()

    # Defaults if regex fails
    result: Dict[str, str] = {
        "sequence": "0000",
        "account":  "000",
        "receiver": "R0",
        "line":     "L0",
    }

    try:
        match = SIA_HEADER_PATTERN.search(msg)
        if match:
            result.update({
                "sequence": match.group("sequence"),
                "line":     match.group("line"),
                "account":  (match.group("account") or "000").strip(),
            })
        else:
            # Low-noise trace log for rare debug sessions
            logger.trace(f"(SIA_DC09) Header regex did not match message: {msg}")
    except Exception as e:
        logger.trace(f"(SIA_DC09) Header parse error: {e}; raw: {msg}")

    # Extra fallbacks to extract sequence when header regex didn't match
    if result["sequence"] == "0000":
        seq_match = re.search(r'"[A-Z0-9\-]+"\s*(\d{4})L0#', msg)
        if seq_match:
            result["sequence"] = seq_match.group(1)
        else:
            seq_match2 = re.search(r'(\d{4})L0#', msg)
            if seq_match2:
                result["sequence"] = seq_match2.group(1)

    return result

def is_ping(message: str) -> bool:
    # Keep simple ping detection by literal "NULL"
    return '"NULL"' in message
