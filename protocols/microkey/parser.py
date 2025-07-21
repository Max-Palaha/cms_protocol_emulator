import re

def parse_microkey_sequence(message: str) -> str:
    match = re.search(r"<Sequence>(\d+)</Sequence>", message)
    return match.group(1) if match else None

def is_ping_microkey(message: str) -> bool:
    return "<Ping" in message or "<Status>PING</Status>" in message
