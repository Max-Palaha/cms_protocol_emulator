import asyncio
from abc import ABC, abstractmethod
from utils.tools import logger
from utils.config_loader import get_port_by_key


class BaseProtocol(ABC):
    def __init__(self, receiver):
        self.receiver = receiver
        self.port = get_port_by_key(receiver)
        self.server = None
        self._serve_task = None  # Store task created for serve_forever

    async def run(self):
        logger.info(f"({self.receiver}) Starting server on port {self.port}")
        self.server = await asyncio.start_server(
            lambda r, w: _handle_connection(self, r, w),
            host="0.0.0.0",
            port=self.port,
        )

        addr = self.server.sockets[0].getsockname()
        logger.info(f"({self.receiver}) Serving on {addr}")

        self._serve_task = asyncio.create_task(self.server.serve_forever())

    async def shutdown(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info(f"({self.receiver}) Server shut down")

        if self._serve_task:
            self._serve_task.cancel()
            try:
                await self._serve_task
            except asyncio.CancelledError:
                logger.info(f"({self.receiver}) serve_forever() task cancelled")


async def _handle_connection(protocol: BaseProtocol, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peername = writer.get_extra_info("peername")
    client_ip, client_port = peername[0], peername[1]
    logger.debug(f"({protocol.receiver}) ({client_ip}:{client_port}) connection opened")

    try:
        while True:
            try:
                data = await asyncio.wait_for(reader.read(4096), timeout=5)
            except asyncio.TimeoutError:
                logger.warning(f"({protocol.receiver}) ({client_ip}) Timeout waiting for data")
                break

            if not data:
                break

            message = None
            for encoding in ["utf-8", "windows-1252"]:
                try:
                    message = data.decode(encoding).strip()
                    break
                except UnicodeDecodeError:
                    continue

            if message:
                logger.info(f"({protocol.receiver}) ({client_ip}) <<-- {message}")
                await protocol.handle(reader, writer, client_ip, client_port, message)
            else:
                logger.warning(f"({protocol.receiver}) ({client_ip}) Unable to decode message")
    except Exception as e:
        logger.error(f"({protocol.receiver}) Error from {client_ip}:{client_port}: {e}")
    finally:
        logger.info(f"({protocol.receiver}) Connection closed by {client_ip}:{client_port}")
        try:
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), timeout=3)
        except Exception as e:
            logger.warning(f"({protocol.receiver}) Error while closing writer: {e}")
