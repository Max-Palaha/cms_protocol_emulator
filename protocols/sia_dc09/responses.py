from datetime import datetime

def convert_sia_ack(sequence="0000", receiver="R0", line="L0", area="A0", account="acct") -> str:
    return f'4AA90LLL"ACK"{sequence}{receiver}{line}{area}#{account}[]\r'


def convert_sia_nak(sequence="0000", receiver="R0", line="L0", area="A0", account="acct") -> str:
    timestamp = datetime.now().strftime("_%H:%M:%S,%m-%d-%Y")
    crc = "4B89"
    lll = "007B"
    msg_id = "0001"
    body = f'"NAK"{sequence}{receiver}{line}{area}#{account}[]{timestamp}'
    return f"{crc}{lll}{msg_id}{body}\r"
