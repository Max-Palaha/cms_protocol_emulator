import os
import sys
import socket
import subprocess
import time
import pytest
import asyncio

from utils.tools import logger

HOST = "127.0.0.1"
PORT = 4556
CMD_PORT = 6688

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0

def read_stdout_until(process, marker, timeout=5):
    start_time = time.time()
    output_lines = []

    while time.time() - start_time < timeout:
        if process.poll() is not None:
            break  # Process exited
        line = process.stdout.readline()
        if not line:
            continue
        decoded = line.decode("utf-8", errors="ignore").strip()
        output_lines.append(decoded)
        if marker in decoded:
            return output_lines
    return output_lines

@pytest.fixture(scope="module")
def run_sia_server():
    env = os.environ.copy()
    process = subprocess.Popen(
        [sys.executable, "scripts/run_sia.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )

    try:
        output = read_stdout_until(process, "Command server started", timeout=5)
        if not is_port_open(HOST, PORT):
            print("\n[ERROR] Port is not open. Full process output:")
            print("\n".join(output))
        assert is_port_open(HOST, PORT)
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

async def send_tcp_command(command: str):
    reader, writer = await asyncio.open_connection(HOST, CMD_PORT)
    writer.write((command + "\n").encode())
    await writer.drain()

    response = await reader.read(1024)
    decoded_response = response.decode(errors="replace").strip()

    writer.close()
    await writer.wait_closed()

    logger.info(f"[TEST] Command response: {decoded_response}")

    if decoded_response != "OK":
        raise Exception(f"Did not receive OK after command '{command}', got '{decoded_response}'")

async def send_event_and_receive_response(event: bytes) -> str:
    reader, writer = await asyncio.open_connection(HOST, PORT)
    writer.write(event)
    await writer.drain()
    await asyncio.sleep(0.1)
    logger.info(f"[TEST] Sent: {event}")

    try:
        data = await asyncio.wait_for(reader.read(4096), timeout=3)
        response = data.decode(errors="replace").strip()
        logger.info(f"[TEST] Received: {response}")
        return response
    except asyncio.TimeoutError:
        logger.warning("[TEST] No response within timeout")
        return "[ERROR] No response within timeout"
    except Exception as e:
        logger.error(f"[TEST] Error: {e}")
        return "[ERROR] Exception"
    finally:
        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_ack_response(run_sia_server):
    event = b'4AA9003C"BR"0000R0L0A0#acct[]'
    response = await send_event_and_receive_response(event)
    assert "ACK" in response

@pytest.mark.asyncio
async def test_nak_response(run_sia_server):
    await send_tcp_command("nak")
    event = b'4AA9003C"BR"0000R0L0A0#acct[]'
    response = await send_event_and_receive_response(event)
    assert "NAK" in response
    assert "_20" in response

@pytest.mark.asyncio
async def test_nak_2_then_ack(run_sia_server):
    await send_tcp_command("nak 2 then ack")
    event = b'4AA9003C"BR"0000R0L0A0#acct[]'

    r1 = await send_event_and_receive_response(event)
    await asyncio.sleep(0.2)

    r2 = await send_event_and_receive_response(event)
    await asyncio.sleep(0.2)

    event2 = b'4AA9003C"BR"0001R0L0A0#acct[]'
    r3 = await send_event_and_receive_response(event2)

    assert r1.startswith("4B89") and "NAK" in r1
    assert r2.startswith("4B89") and "NAK" in r2
    assert r3.startswith("4AA9") and "ACK" in r3

@pytest.mark.asyncio
async def test_time_custom_response(run_sia_server):
    custom_time = "2020-08-26 14:46:14"
    await send_tcp_command(f"time {custom_time} once")
    event = b'4AA9003C"BR"0000R0L0A0#acct[]'
    response1 = await send_event_and_receive_response(event)
    assert "NAK" in response1 and "_14:46:14,08-26-2020" in response1

    event2 = b'4AA9003C"BR"0001R0L0A0#acct[]'
    response2 = await send_event_and_receive_response(event2)
    assert "ACK" in response2
    assert "_14:46:14" not in response2
