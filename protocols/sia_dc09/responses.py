from datetime import datetime
from typing import Optional


def convert_sia_ack(
    sequence: str = "0000",
    receiver: str = "R0",
    line: str = "L0",
    area: str = "A0",
    account: str = "acct",
    timestamp: Optional[str] = None,
) -> str:
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M:%S,%m-%d-%Y")
    return f'4AA90LLL"ACK"{sequence}{receiver}{line}{area}#{account}[]_{timestamp}\r'


def convert_sia_nak(
    sequence: str = "0000",
    receiver: str = "R0",
    line: str = "L0",
    area: str = "A0",
    account: str = "acct",
    timestamp: Optional[str] = None,
) -> str:
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M:%S,%m-%d-%Y")

    crc = "4B89"
    lll = "007B"
    msg_id = "0001"
    body = f'"NAK"{sequence}{receiver}{line}{area}#{account}[]_{timestamp}'
    return f"{crc}{lll}{msg_id}{body}\r"
