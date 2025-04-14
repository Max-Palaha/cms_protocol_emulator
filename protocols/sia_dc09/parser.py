import re
from utils.tools import logger

def parse_sia_message(message: str) -> dict:
    result = {
        "sequence": "0000",
        "receiver": "R0",
        "line": "L0",
        "area": "A0",
        "account": "acct",
    }

    try:
        match = re.search(r'"[A-Z\-]+"\s*(\d{4})L(\d)#(\w+)', message)
        if match:
            result["sequence"] = match.group(1)
            result["line"] = f"L{match.group(2)}"
            result["account"] = match.group(3)

        if re.match(r'[A-F0-9]{4}', message):
            result["receiver"] = "R0"

        area_match = re.search(r'/PA(\d+)', message)
        if area_match:
            result["area"] = f"A{area_match.group(1)}"

        logger.trace(f"(SIA_DC09) Parsed SIA message: {result}")
    except Exception as e:
        logger.error(f"(SIA_DC09) Failed to parse SIA message: {e}")

    return result


def is_ping(message: str) -> bool:
    return '"NULL"' in message
