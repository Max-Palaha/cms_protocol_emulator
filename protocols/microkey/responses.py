ACK_PATTERN = '\r<Response><Sequence>{}</Sequence><Status>ACK</Status></Response><Checksum>{}</Checksum>\n'
NAK_PATTERN = '\r<Response><Sequence>{}</Sequence><Status>NAK</Status><Error>{}</Error></Response><Checksum>{}</Checksum>\n'

def generate_ack(sequence: str, checksum: str = '4FE9') -> bytes:
    return ACK_PATTERN.format(sequence, checksum).encode()

def generate_nak(sequence: str, error: str = 'Checksum error', checksum: str = '0000') -> bytes:
    return NAK_PATTERN.format(sequence, error, checksum).encode()
