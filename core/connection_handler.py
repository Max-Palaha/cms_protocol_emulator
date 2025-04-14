import asyncio
from abc import ABC, abstractmethod
from utils.tools import logger
from utils.config_loader import get_port_by_key


class BaseProtocol(ABC):
    def __init__(self, receiver):
        self.receiver = receiver
        self.port = get_port_by_key(receiver)

    async def run(self):
        logger.info(f"({self.receiver}) Starting server on port {self.port}")
        await start_server(self)


async def start_server(protocol: BaseProtocol):
    server = await asyncio.start_server(
        lambda r, w: _handle_connection(protocol, r, w),
        host="0.0.0.0",
        port=protocol.port,
    )

    addr = server.sockets[0].getsockname()
    logger.info(f"({protocol.receiver}) Serving on {addr}")
    async with server:
        await server.serve_forever()


async def _handle_connection(protocol: BaseProtocol, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peername = writer.get_extra_info("peername")
    client_ip, client_port = peername[0], peername[1]
    logger.debug(f"({protocol.receiver}) ({client_ip}:{client_port}) connection opened")

    try:
        while not reader.at_eof():
            data = await reader.read(4096)
            if not data:
                break

            message = data.decode(errors="ignore").strip()
            if message:
                logger.info(f"({protocol.receiver}) ({client_ip}) <<-- {message}")
                await protocol.handle(reader, writer, client_ip, client_port, message)

    except Exception as e:
        logger.error(f"({protocol.receiver}) Error while handling connection from {client_ip}:{client_port}: {e}")
    finally:
        logger.info(f"({protocol.receiver}) Connection closed by {client_ip}:{client_port}")
        writer.close()
        await writer.wait_closed()
