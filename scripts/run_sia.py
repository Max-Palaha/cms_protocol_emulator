import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from utils.registry_tools import get_protocol_handler
from utils.constants import Receiver
from utils.tools import logger
from utils.command_server import start_command_server

import protocols.sia_dc09.handler  # Ensure handler is registered
from utils.mode_manager import mode_manager


async def main():
    logger.info("Launching SIA-DC09 emulator...")
    protocol_class = get_protocol_handler(Receiver.CMS_SIA_DCS)
    protocol_mode = mode_manager.get(Receiver.CMS_SIA_DCS.value)
    protocol_instance = protocol_class(protocol_mode)

    protocol_task = await protocol_instance.run()

    try:
        await asyncio.Future()  # Keeps the process alive
    except asyncio.CancelledError:
        logger.warning("SIA-DC09 main task cancelled.")
    finally:
        logger.info("Shutting down SIA-DC09 emulator...")
        await protocol_instance.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("SIA-DC09 emulator stopped by user.")
    except Exception as e:
        logger.error(f"Unhandled exception in __main__: {e}")
