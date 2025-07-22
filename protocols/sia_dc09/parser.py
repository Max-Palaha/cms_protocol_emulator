import re
from typing import Union, Dict
from utils.logger import logger

def parse_sia_message(message: Union[str, bytes]) -> Dict[str, str]:
    """
    Parse SIA-DC09 header fields from incoming message.
    Returns a dict with keys: sequence, account.
    """
    msg = message.decode('utf-8', errors='ignore') if isinstance(message, (bytes, bytearray)) else message
    msg = msg.strip()

    result = {
        "sequence": "0000",
        "account":  "unknown",
    }

    account_match = re.search(r'L0#(\w+)', msg)
    if account_match:
        result["account"] = account_match.group(1)

    seq_match = re.search(r'"[A-Z0-9\-]+"\s*(\d{4})L0#', msg)
    if seq_match:
        result["sequence"] = seq_match.group(1)
    else:
        seq_match2 = re.search(r'(\d{4})L0#', msg)
        if seq_match2:
            result["sequence"] = seq_match2.group(1)

    return result

def is_ping(message: str) -> bool:
    return '"NULL"' in message
