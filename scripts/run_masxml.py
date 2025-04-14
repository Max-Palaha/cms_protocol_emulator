import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from utils.registry_tools import get_protocol_handler
from utils.constants import Receiver
from utils.tools import logger

import protocols.masxml.handler

async def main():
    logger.info("Launching MASXML emulator...")
    protocol_class = get_protocol_handler(Receiver.CMS_MASXML)
    protocol_instance = protocol_class()
    await protocol_instance.run()

if __name__ == "__main__":
    asyncio.run(main())
