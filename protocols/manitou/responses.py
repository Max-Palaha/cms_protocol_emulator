import os
import base64
import random
import string
from typing import Optional, Tuple


STX = b"\x02"
ETX = b"\x03"


def _gen_index(length: int = 12) -> str:
    """Generate URL-safe pseudo-random index for Nak challenges."""
    # 9 bytes -> ~12 urlsafe chars; trim to exact length
    return base64.urlsafe_b64encode(os.urandom(9)).decode().rstrip("=").replace("-", "").replace("_", "")[:length]

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

def convert_nak(code: int = 10, return_index: bool = False):
    """
    Build Manitou-style NAK with Index and Code.
    Returns bytes, and (optionally) the generated index.
    """
    index = _gen_index()
    xml = f'<?xml version="1.0"?><Nak Index="{index}" Code="{code}"/>'
    payload = STX + xml.encode() + ETX
    return (payload, index) if return_index else payload