import re


def is_ping(message: str) -> bool:
    """Check if the message is a ping (NULL event)."""
    return '"NULL"' in message or message.strip() == ''


def parse_sia_message(message: str) -> dict:
    """Parse SIA-DC09 formatted message into components."""
    result = {
        "sequence": "0000",
        "receiver": "R0",
        "line": "L0",
        "area": "A0",
        "account": "acct",
    }

    # Log raw message for debugging
    from utils.tools import logger
    logger.debug(f"[DIAG] Raw message: {message}")

    try:
        # Accept with or without space: '"BR"0000...' or '"BR" 0000...'
        match = re.search(r'"[A-Z\-]+"(\s*)(\d{4})R(\d)L(\d)A(\d+)#(\w+)', message)
        if match:
            result["sequence"] = match.group(2)
            result["receiver"] = f"R{match.group(3)}"
            result["line"] = f"L{match.group(4)}"
            result["area"] = f"A{match.group(5)}"
            result["account"] = match.group(6)
    except Exception as e:
        logger.warning(f"[SIA Parser] Failed to parse message: {e}")

    return result
