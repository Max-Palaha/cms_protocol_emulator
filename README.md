# CMS Protocol Emulator

A modular Python emulator designed to simulate various CMS communication protocols including **SIA DC-09** and **MASXML**.  
Ideal for testing alarm events, acknowledgments, and emulation modes in CMS systems.

---

## 🚀 Features

- ✅ Supports multiple protocols (easily extendable)
- ⚙️ Configurable emulation modes:
  - `ack`, `nak`, `no-response`
  - `only-ping`, `drop N`, `delay N`
  - Custom timestamp mode (`time YYYY-MM-DD HH:MM:SS once|N|forever`)
- 📜 Logging to file with millisecond precision
- 🧪 Interactive command-line mode
- 📂 Protocol-specific structure for clean architecture

---

## 📂 Project Structure

```
cms_protocol_server/
├── protocols/
│   ├── masxml/
│   │   ├── handler.py
│   │   ├── parser.py
│   │   └── responses.py
│   └── sia_dc09/
│       ├── handler.py
│       ├── parser.py
│       └── responses.py
├── utils/
│   ├── constants.py
│   ├── tools.py
│   ├── config_loader.py
│   └── mode_manager.py
├── scripts/
│   ├── run_masxml.py
│   └── run_sia.py
└── config_signalling.yaml
```

---

## 🖥️ Running Emulators

```bash
# Start SIA-DC09 emulator
python scripts/run_sia.py

# Start MASXML emulator
python scripts/run_masxml.py
```

### 🔁 Interactive commands (via terminal)

- `ack [N]` — respond with ACK (optionally N times)
- `nak [N]` — respond with NAK (optionally N times)
- `no-response [N]` — skip replies
- `only-ping` — only answer ping messages
- `drop N` — drop next N packets
- `delay N` — delay reply by N seconds
- `time 2024-08-26 14:46:14 [once|5|forever]` — respond with custom timestamp
- `loglevel DEBUG` — adjust logging level

---

## 🛠️ Requirements

- Python 3.10+
- Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## 👤 Author

Developed by [Maksym Palazhchenko](https://github.com/Max-Palaha)  
📅 Last updated: 2025-04-14

---

## 📃 License

MIT License (or proprietary if internal use)
