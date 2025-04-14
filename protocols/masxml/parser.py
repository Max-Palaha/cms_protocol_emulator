def is_ping(message: str) -> bool:
    return '"NULL"' in message or "<MessageType>HEARTBEAT</MessageType>" in message
