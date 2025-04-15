import yaml
import logging
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config_signalling.yaml"

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

PORTS = CONFIG.get("environment", {}).get("ports", {})

def get_port(protocol_name) -> int:
    if hasattr(protocol_name, "value"):
        protocol_name = protocol_name.value

    protocol_key = str(protocol_name).lower().replace("_", "-")
    port = PORTS.get(protocol_key)

    if port is None:
        raise ValueError(f"Port for protocol '{protocol_key}' not found in config_signalling.yaml")
    return port

# For backward compatibility
get_port_by_key = get_port

def load_config(force_reload: bool = False) -> dict:
    global CONFIG, PORTS

    if CONFIG is not None and not force_reload:
        return CONFIG

    try:
        with open(CONFIG_PATH, "r") as f:
            CONFIG = yaml.safe_load(f)
            PORTS = CONFIG.get("environment", {}).get("ports", {})
            return CONFIG
    except Exception as e:
        logging.error(f"Failed to load config from {CONFIG_PATH}: {e}")
        CONFIG = None
        PORTS = {}
        return None


def get_logging_level() -> int:
    level_str = CONFIG.get("logging", {}).get("level", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)
