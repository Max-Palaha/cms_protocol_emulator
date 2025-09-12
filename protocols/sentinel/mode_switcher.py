import threading

class SentinelModeSwitcher:
    def __init__(self):
        self._mode = "ack"
        self._lock = threading.Lock()
        self._start_stdin_listener()

    def _start_stdin_listener(self):
        thread = threading.Thread(target=self._stdin_listener, daemon=True)
        thread.start()

    def _stdin_listener(self):
        import sys
        print("[Sentinel ModeSwitcher] Type: ack | nak | no_response")
        while True:
            cmd = sys.stdin.readline().strip().lower()
            with self._lock:
                if cmd == "ack":
                    self._mode = "ack"
                    print("[ModeSwitcher] Mode set to ACK")
                elif cmd == "nak":
                    self._mode = "nak"
                    print("[ModeSwitcher] Mode set to NAK")
                elif cmd == "no_response":
                    self._mode = "no_response"
                    print("[ModeSwitcher] Mode set to NO_RESPONSE")
                else:
                    print("[ModeSwitcher] Unknown command! Use: ack | nak | no_response")

    def get_mode(self):
        with self._lock:
            return self._mode
