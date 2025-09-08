import os
import random
import string
from typing import Optional, Tuple


STX = b"\x02"
ETX = b"\x03"


def _random_rawno(n: int = 12) -> str:
    """Generate a RawNo compatible token (alnum), e.g. 'ER9ReRiXVWRl'."""
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def convert_ack(rawno: Optional[str] = None, return_rawno: bool = False) -> "bytes|Tuple[bytes,str]":
    """
    Build Manitou ACK frame:
      STX + <?xml version="1.0"?><Ack><RawNo>...</RawNo></Ack> + ETX

    If return_rawno=True, returns (bytes, rawno) so handler can map Binary.RawNo to the originating Signal.
    """
    token = rawno or _random_rawno()
    xml = f'<?xml version="1.0"?><Ack><RawNo>{token}</RawNo></Ack>'
    frame = STX + xml.encode("utf-8") + ETX
    return (frame, token) if return_rawno else frame
