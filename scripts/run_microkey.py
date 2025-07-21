import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from utils.registry_tools import get_protocol_handler
from utils.constants import Receiver
from utils.logger import logger

import protocols.microkey.handler

async def main():
    logger.info("Launching Micro Key emulator...")
    protocol_class = get_protocol_handler(Receiver.MICROKEY)
    protocol_instance = protocol_class()
    await protocol_instance.run()

if __name__ == "__main__":
    asyncio.run(main())
