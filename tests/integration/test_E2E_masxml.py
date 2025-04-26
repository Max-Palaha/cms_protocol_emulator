import asyncio
import pytest
import socket
import subprocess
import time
import sys
import os
import signal
import atexit
import traceback
import threading

from contextlib import closing
from utils.config_loader import get_port

HOST = "127.0.0.1"
PORT = get_port("cms_masxml")

def is_port_open(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0

def wait_for_port(host, port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False

@pytest.fixture(scope="module")
def run_masxml_server():
    print("[TEST] Starting MASXML process...")
    process = subprocess.Popen(
        [sys.executable, "scripts/run_masxml.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True
    )

    started = False

    # Читання stdout в окремому потоці (не блокує)
    def stream_output():
        nonlocal started
        for line in process.stdout:
            print("[SERVER]", line.strip())
            if "Command server started on" in line:
                started = True

    thread = threading.Thread(target=stream_output, daemon=True)
    thread.start()

    def cleanup():
        if process.poll() is None:
            print("[CLEANUP] Terminating leftover MASXML process...")
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("[CLEANUP] Force killing MASXML process...")
                process.kill()
                process.wait()
        try:
            if process.stdout:
                process.stdout.close()
        except Exception:
            pass

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda signum, frame: cleanup())
    signal.signal(signal.SIGINT, lambda signum, frame: cleanup())

    # Очікування запуску
    for _ in range(50):
        if started and is_port_open(HOST, PORT):
            break
        time.sleep(0.2)
    else:
        cleanup()
        raise RuntimeError("MASXML server failed to start (no startup log or port open)")

    print("[TEST] MASXML server is running.")
    yield process

    print("[TEST] Tearing down MASXML process...")
    cleanup()

async def send_masxml_event(timeout=3):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(HOST, PORT), timeout=timeout
        )
        message = '''<AjaxMessage>
<MessageType>Event</MessageType>
<SourceID>999</SourceID>
<MessageSequenceNo>123456</MessageSequenceNo>
<KeyValuePair>
    <Key>EventType</Key>
    <Value>Alarm</Value>
</KeyValuePair>
</AjaxMessage>'''
        print("[TEST] Sending MASXML event...")
        writer.write(message.encode("utf-8"))
        await writer.drain()

        response = await asyncio.wait_for(reader.read(2048), timeout=timeout)
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1)
        except Exception as e:
            print(f"[WARN] writer.wait_closed() failed: {e}")


        decoded = response.decode("utf-8").strip()
        print(f"[TEST] Received:\n{decoded}")
        return decoded
    except asyncio.TimeoutError:
        print("[ERROR] Timeout during send_masxml_event()")
        return ""
    except Exception as e:
        print(f"[ERROR] Unexpected error in send_masxml_event(): {e}")
        traceback.print_exc()
        return ""

async def send_tcp_command(command: str):
    try:
        print(f"[TEST] Sending TCP command: {command}")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", 6688), timeout=3
        )
        writer.write((command + "\n").encode("utf-8"))
        await writer.drain()
        await asyncio.wait_for(reader.read(1024), timeout=3)
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1)
        except Exception as e:
            print(f"[WARN] writer.wait_closed() failed: {e}")
        print(f"[TEST] Command '{command}' sent and acknowledged")
    except Exception as e:
        print(f"[ERROR] Unexpected error in send_masxml_event(): {e}")
        traceback.print_exc()
        return ""

@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_nak9_response(run_masxml_server):
    print("[TEST] Running test_nak9_response")
    await send_tcp_command("nak9")
    await asyncio.sleep(0.5)
    response = await send_masxml_event()
    assert "<ResultCode>9</ResultCode>" in response

@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_nak10_response(run_masxml_server):
    print("[TEST] Running test_nak10_response")
    await send_tcp_command("nak10")
    await asyncio.sleep(0.5)
    response = await send_masxml_event()
    assert "<ResultCode>10</ResultCode>" in response

@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_nak_2_then_ack(run_masxml_server):
    print("[TEST] Running test_nak_2_then_ack_response")
    await send_tcp_command("nak 2 then ack")
    await asyncio.sleep(0.5)

    response1 = await send_masxml_event()
    response2 = await send_masxml_event()
    response3 = await send_masxml_event()

    assert any(code in response1 for code in ["<ResultCode>1</ResultCode>", "<ResultCode>9</ResultCode>", "<ResultCode>10</ResultCode>"])
    assert any(code in response2 for code in ["<ResultCode>1</ResultCode>", "<ResultCode>9</ResultCode>", "<ResultCode>10</ResultCode>"])
    assert "<ResultCode>0</ResultCode>" in response3
