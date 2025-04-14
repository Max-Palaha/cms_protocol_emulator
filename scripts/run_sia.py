import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from utils.registry_tools import get_protocol_handler
from utils.constants import Receiver
from utils.tools import logger

import protocols.sia_dc09.handler

async def main():
    logger.info("Launching SIA-DC09 emulator...")
    protocol_class = get_protocol_handler(Receiver.CMS_SIA_DCS)
    protocol_instance = protocol_class()
    await protocol_instance.run()

if __name__ == "__main__":
    asyncio.run(main())
