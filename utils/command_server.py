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
    data = await reader.read(1024)
    message = data.decode().strip()
    logger.info(f"[CMD] Mode before: {mode_switcher.protocol_mode.mode}")
    logger.info(f"[CMD] Received command from {addr}: {message}")
    if mode_switcher:
        print(f"[DEBUG] Delegating to handle_command: {message}")
        mode_switcher.handle_command(message)
    logger.info(f"[CMD] Mode after: {mode_switcher.protocol_mode.mode}")
    logger.info(f"[CMD] NAK code after: {getattr(mode_switcher.protocol_mode, 'nak_result_code', None)}")
    writer.write(b"OK\n")
    await writer.drain()
    writer.close()
    await writer.wait_closed()
