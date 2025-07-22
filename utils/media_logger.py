import os
import base64
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional

DEFAULT_MEDIA_DIR = "log_media"
DEFAULT_MAX_FILES = 25

def ensure_media_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def clean_old_files(path: Path, max_files: int):
    files = sorted(path.glob("*"), key=os.path.getmtime)
    while len(files) > max_files:
        files[0].unlink()
        files.pop(0)

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def save_base64_media(b64_data: str, protocol: str, port: int, sequence: Optional[str]=None, ext="jpg", max_files=DEFAULT_MAX_FILES):
    sub_dir = Path(DEFAULT_MEDIA_DIR) / f"{protocol}_{port}"
    ensure_media_dir(sub_dir)
    clean_old_files(sub_dir, max_files)

    timestamp = get_timestamp()
    sequence_str = f"{sequence}_" if sequence else ""
    filename = sub_dir / f"photo_{sequence_str}{timestamp}.{ext}"

    try:
        with open(filename, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return filename
    except Exception as e:
        return f"[Error saving base64 file: {e}]"

def save_url_media(url: str, protocol: str, port: int, sequence: Optional[str]=None, max_files=DEFAULT_MAX_FILES):
    sub_dir = Path(DEFAULT_MEDIA_DIR) / f"{protocol}_{port}"
    ensure_media_dir(sub_dir)
    clean_old_files(sub_dir, max_files)

    timestamp = get_timestamp()
    sequence_str = f"{sequence}_" if sequence else ""

    url_path = urlparse(url).path
    ext = Path(url_path).suffix or ".jpg"
    filename = sub_dir / f"photo_{sequence_str}{timestamp}{ext}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        return filename
    except Exception as e:
        return f"[Error saving URL file: {e}]"

def save_binary_media(binary_data: bytes, protocol: str, port: int, sequence: Optional[str]=None, ext="jpg", max_files=DEFAULT_MAX_FILES):
    sub_dir = Path(DEFAULT_MEDIA_DIR) / f"{protocol}_{port}"
    ensure_media_dir(sub_dir)
    clean_old_files(sub_dir, max_files)

    timestamp = get_timestamp()
    sequence_str = f"{sequence}_" if sequence else ""
    filename = sub_dir / f"photo_{sequence_str}{timestamp}.{ext}"

    try:
        with open(filename, "wb") as f:
            f.write(binary_data)
        return filename
    except Exception as e:
        return f"[Error saving binary file: {e}]"
