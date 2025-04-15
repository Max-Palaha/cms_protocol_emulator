import re

def to_hex(data: bytes) -> str:
    return data.hex()

def from_hex(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)

def is_adm_cid_event(event_code: str) -> bool:
    return bool(re.fullmatch(r"[ER]\d{3}", event_code))

def is_sia_dc09_event(event_code: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{2}", event_code))

def detect_event_format(message: str) -> str:
    if is_adm_cid_event(message):
        return "ADM-CID"
    elif is_sia_dc09_event(message):
        return "SIA-DC09"
    return "UNKNOWN"
