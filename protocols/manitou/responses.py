import random
import string
from typing import Optional
from utils.logger import logger

def generate_random_str12() -> str:
    """Generate a random 12-character alphanumeric string."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

def convert_ack(packet_id: Optional[str] = None) -> bytes:
    """
    Build a standard ACK response for Manitou.
    If packet_id is provided, include RawNo tag. Otherwise, return <Ack/> only.
    Format: [STX]<?xml version="1.0"?><Ack>[<RawNo>packet_id</RawNo>]</Ack>[ETX]
    """
    if packet_id:
        payload = f'<?xml version="1.0"?><Ack><RawNo>{generate_random_str12()}</RawNo></Ack>'
    else:
        payload = '<?xml version="1.0"?><Ack/>'
    message = f'{chr(0x02)}{payload}{chr(0x03)}'
    logger.debug(f"(MANITOU) → ACK payload: {payload}")
    return message.encode()

def convert_nak(code: int = 10, index: Optional[str] = None) -> bytes:
    """
    Build a NAK response for Manitou.
    Format: [STX]<?xml version="1.0"?><Nak Index="{index}" Code="{code}"/>[ETX]
    If index is not provided, generate a random string.
    """
    index_val = index or generate_random_str12()
    payload = f'<?xml version="1.0"?><Nak Index="{index_val}" Code="{code}"/>'
    message = f'{chr(0x02)}{payload}{chr(0x03)}'
    logger.debug(f"(MANITOU) → NAK payload: {payload}")
    return message.encode()