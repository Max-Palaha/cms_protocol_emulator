ACK = b'\x06'
NAK = b'\x15'

def get_ack():
    """Return ACK byte response for Sentinel protocol."""
    return ACK

def get_nak():
    """Return NAK byte response for Sentinel protocol."""
    return NAK