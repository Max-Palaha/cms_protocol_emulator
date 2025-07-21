import asyncio
import dataclasses
import json
from binascii import hexlify
from utils.logger import logger
from utils.config_loader import get_port_by_key
from utils.constants import LOGS_FILE_PATH

def str_to_hex(str_value: str) -> str:
    return hexlify(str_value.encode()).decode(errors="ignore")


def detect_event_format(message: str) -> str:
    if '"NULL"' in message:
        return "PING"
    if "ADM-CID" in message:
        return "ADM-CID"
    if 'SIA-DCS' in message:
        return "SIA-DCS"
    return "UNKNOWN"


async def tcp_client(internal_message, receiver: str):
    try:
        port = get_port_by_key("main")
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        message = json.dumps(dataclasses.asdict(internal_message))
        logger.info(f"({receiver}) Send to internal server: {message}")
        writer.write(message.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception as err:
        logger.info(f"({receiver}) Failed to send to internal server: {err}")
