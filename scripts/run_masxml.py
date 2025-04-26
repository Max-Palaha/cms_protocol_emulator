import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from utils.registry_tools import get_protocol_handler
from utils.constants import Receiver
from utils.tools import logger

import protocols.masxml.handler  # ensure handler is registered


async def main():
    logger.info("Launching MASXML emulator...")
    logger.debug("Getting MASXML protocol class...")
    protocol_class = get_protocol_handler(Receiver.CMS_MASXML)

    logger.debug("Instantiating protocol...")
    protocol_instance = protocol_class()

    logger.debug("Calling protocol_instance.run()...")
    await protocol_instance.run()

    try:
        logger.debug("Running forever until interrupted...")
        await asyncio.Future()  # Keeps the process alive
    except asyncio.CancelledError:
        logger.warning("MASXML main task cancelled.")
    finally:
        logger.info("Shutting down MASXML emulator...")
        await protocol_instance.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("MASXML emulator stopped by user.")
    except Exception as e:
        logger.error(f"Unhandled exception in __main__: {e}")