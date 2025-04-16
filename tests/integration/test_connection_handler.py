import asyncio
import socket
import pytest

from core.connection_handler import BaseProtocol, start_server


class DummyProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver="dummy")
        self.received_messages = []

    async def handle(self, reader, writer, client_ip, client_port, message: str):
        self.received_messages.append((client_ip, message))
        writer.write(f"ACK:{message}".encode())
        await writer.drain()


@pytest.mark.asyncio
async def test_tcp_server_receives_data():
    loop = asyncio.get_running_loop()
    protocol = DummyProtocol()

    # Переоприділяємо порт вручну для тесту, наприклад, на 9999
    protocol.port = 9999

    server_task = loop.create_task(start_server(protocol))
    await asyncio.sleep(0.1)  # дати серверу час стартувати

    reader, writer = await asyncio.open_connection("127.0.0.1", 9999)
    test_message = "HelloTest"
    writer.write(test_message.encode())
    await writer.drain()

    data = await reader.read(4096)
    writer.close()
    await writer.wait_closed()

    await asyncio.sleep(0.1)  # дочекатись обробки

    assert ("127.0.0.1", test_message) in protocol.received_messages
    assert data.decode() == f"ACK:{test_message}"

    server_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await server_task
