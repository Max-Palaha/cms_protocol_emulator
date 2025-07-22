import asyncio
from utils.tools import logger


async def start_command_server(host, port, mode_switcher):
    server = await asyncio.start_server(
        lambda r, w: handle_command(r, w, mode_switcher), host, port
    )
    addr = server.sockets[0].getsockname()
    logger.info(f"[CMD] Command server started on {addr}")
    return server

async def handle_command(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, mode_switcher):
    addr = writer.get_extra_info('peername')
    try:
        data = await reader.read(1024)
        message = data.decode(errors="replace").strip()
        logger.info(f"[CMD] Received command from {addr}: {message}")

        if not message:
            logger.warning(f"[CMD] Empty message received from {addr}")
            writer.write(b"OK\n")
            await writer.drain()
            return

        if mode_switcher:
            try:
                mode_switcher.handle_command(message)
                writer.write(b"OK\n")
                await writer.drain()
            except Exception as e:
                logger.error(f"[CMD] Failed to handle command '{message}': {e}")
                writer.write(b"ERROR\n")
                await writer.drain()
        else:
            logger.error("[CMD] No mode_switcher available")
            writer.write(b"ERROR\n")
            await writer.drain()

    except Exception as e:
        logger.error(f"[CMD] Exception during command handling: {e}")
    finally:
        if not writer.is_closing():
            writer.close()
            await writer.wait_closed()