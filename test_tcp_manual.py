import socket

HOST = "127.0.0.1"
PORT = 4556

message = b'4AA9003C"BR"0000R0L0A0#acct[]\r'

with socket.create_connection((HOST, PORT), timeout=3) as sock:
    print(f"[CLIENT] Sending: {message}")
    sock.sendall(message)
    response = sock.recv(4096)
    print(f"[CLIENT] Received: {response}")
