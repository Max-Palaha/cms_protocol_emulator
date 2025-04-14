import re

def convert_masxml_ack(
    message: bytes | str,
    text: str = "ok",
    code: int = 0
) -> str:
    if isinstance(message, bytes):
        message = message.decode(errors="ignore")

    sequence = _extract_sequence(message)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<AckNakClass>\n'
        f'    <MessageSequenceNo>{sequence}</MessageSequenceNo>\n'
        f'    <ResultCode>{code}</ResultCode>\n'
        f'    <ResultText>{text}</ResultText>\n'
        '</AckNakClass>'
    )


def convert_masxml_nak(
    message: bytes | str,
    text: str = "Invalid XML",
    code: int = 10
) -> str:
    if isinstance(message, bytes):
        message = message.decode(errors="ignore")

    sequence = _extract_sequence(message)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<AckNakClass>\n'
        f'    <MessageSequenceNo>{sequence}</MessageSequenceNo>\n'
        f'    <ResultCode>{code}</ResultCode>\n'
        f'    <ResultText>{text}</ResultText>\n'
        '</AckNakClass>'
    )


def _extract_sequence(message: str) -> str:
    match = re.search(r"<MessageSequenceNo>(\d+)</MessageSequenceNo>", message)
    return match.group(1) if match else "0000"
