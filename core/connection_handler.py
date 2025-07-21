import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from utils.tools import logger
from utils.config_loader import get_port_by_key


class BaseProtocol(ABC):
    def __init__(self, receiver):
        self.receiver = receiver
        self.port = get_port_by_key(receiver)

    def get_label(self, data: bytes) -> Optional[str]:
        return None

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
    protocol_name = protocol.receiver.value.split(".")[-1]
    logger.debug(f"({protocol_name}) ({client_ip}:{client_port}) connection opened")

    try:
        while not reader.at_eof():
            data = await reader.read(4096)
            if not data:
                break

            label = protocol.get_label(data)
            if label is None:
                label = ""

            logger.log_bytes("<<--", protocol_name, client_ip, data, label=label)

            await protocol.handle(reader, writer, client_ip, client_port, data)

    except Exception as e:
        logger.error(f"({protocol_name}) Error while handling connection from {client_ip}:{client_port}: {e}")
    finally:
        logger.info(f"({protocol_name}) Connection closed by {client_ip}:{client_port}")
        writer.close()
        await writer.wait_closed()
