import asyncio

async def main():
    host = "127.0.0.1"
    port = 6667

    # Повідомлення MASXML у вигляді простого AJAX запиту
    test_message = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Message>'
        '<MessageType>AJAX</MessageType>'
        '<SourceID>Test</SourceID>'
        '<MessageSequenceNo>1</MessageSequenceNo>'
        '<KeyValuePair>'
        '<Key>Type</Key>'
        '<Value>HEARTBEAT</Value>'
        '</KeyValuePair>'
        '</Message>'
    )

    print(f"[CLIENT] Connecting to {host}:{port}...")
    try:
        reader, writer = await asyncio.open_connection(host, port)

        print("[CLIENT] Sending MASXML message...")
        writer.write(test_message.encode())
        await writer.drain()

        response = await asyncio.wait_for(reader.read(4096), timeout=5)
        print(f"[CLIENT] Received:\n{response.decode(errors='ignore')}")
    except Exception as e:
        print(f"[CLIENT] Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        print("[CLIENT] Connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
