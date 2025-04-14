import asyncio
import logging
import protocols  # noqa: F401
from utils.config_loader import load_config
from utils.constants import Receiver
from protocols.registry import get_protocol_handler

logger = logging.getLogger("log")

async def start_server(protocol_name: str):
    config = load_config()
    handler_cls = get_protocol_handler(protocol_name)
    port = config.get("ports", {}).get(protocol_name.lower())

    if not handler_cls:
        logger.error(f"Protocol handler not found: {protocol_name}")
        return
    if not port:
        logger.error(f"Port not configured for: {protocol_name}")
        return

    server = handler_cls(port=port, receiver=protocol_name)
    await server.run()

def start_server_by_name(protocol_name: str):
    asyncio.run(start_server(protocol_name))

if __name__ == "__main__":
    print("Please run one of the specific run_*.py files.")
