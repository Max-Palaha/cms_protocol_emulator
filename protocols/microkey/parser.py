import re
from typing import Union, List, Dict, Tuple

# -------- Normalization --------

def _to_text(message: Union[str, bytes]) -> str:
    """Normalize incoming payload to text. Try UTF-8, then CP1252 fallback."""
    if isinstance(message, str):
        return message
    try:
        return message.decode("utf-8")
    except UnicodeDecodeError:
        return message.decode("cp1252", errors="replace")

# -------- Frame boundaries --------
# Match a full Micro Key frame: <Signals ...></Signals><Checksum>XXXX</Checksum>
_FRAME_RE = re.compile(
    r"(<Signals\b.*?</Signals>\s*<Checksum>[0-9A-Fa-f]{4}</Checksum>)",
    re.DOTALL,
)

def split_complete_frames(buffer_text: str) -> Tuple[List[str], str]:
    """
    From an accumulated text buffer, extract all COMPLETE frames and return (frames, remainder).
    A complete frame ends with </Signals><Checksum>XXXX</Checksum>.
    Anything after the last complete match stays as remainder (possibly partial).
    """
    frames: List[str] = []
    remainder = buffer_text

    matches = list(_FRAME_RE.finditer(buffer_text))
    if matches:
        last_end = 0
        for m in matches:
            frames.append(m.group(1))
            last_end = m.end()
        remainder = buffer_text[last_end:]
    return frames, remainder

# -------- Simple fields --------

def parse_microkey_sequence(message: Union[str, bytes]) -> str | None:
    """Extract <Sequence>...</Sequence> as string or None if not found."""
    msg = _to_text(message)
    m = re.search(r"<Sequence>(\d+)</Sequence>", msg)
    return m.group(1) if m else None

def is_ping_microkey(message: Union[str, bytes]) -> bool:
    """
    Heuristics for Micro Key ping/heartbeat frames.
    - If <SignalCount>0</SignalCount> => treat as ping
    - Or explicit <Ping...> style frames (if used)
    - Or <Status>PING</Status> (fallback)
    """
    msg = _to_text(message)
    if re.search(r"<SignalCount>\s*0\s*</SignalCount>", msg):
        return True
    return ("<Ping" in msg) or ("<Status>PING</Status>" in msg)

# -------- Rich signal parsing --------

_SIG_RE = re.compile(r"<Signal>(.*?)</Signal>", re.DOTALL)

# URL detectors:
#  - any URL (http/https/custom scheme, e.g., ajax://, app://, ajax-pro-desktop://)
_URL_ANY_SCHEME_RE = re.compile(r"\b(?:[a-z][a-z0-9+.\-]*://\S+)", re.IGNORECASE)
#  - image URL (has explicit image extension BEFORE optional query)
_IMAGE_EXT_URL_RE = re.compile(
    r"\b(?:[a-z][a-z0-9+.\-]*://\S+?\.(?:jpg|jpeg|png|gif|webp|bmp|tif|tiff))(?:\?\S+)?\b",
    re.IGNORECASE,
)

# --- Heuristic "image-like" CDN patterns (no extension in URL) ---
# Consider as image when URL contains an "imagesvc/app_video-svc/app_company-svc" path and:
#   - '/s/' short form, or
#   - 'image_' token, or
#   - '/original/' folder.
_IMAGE_HOST_HINT_RE = re.compile(r"imagesvc", re.IGNORECASE)
_IMAGE_PATH_HINT_RE = re.compile(r"(?:/s/|image_|/original/)", re.IGNORECASE)
_SERVICE_HINT_RE     = re.compile(r"(?:app_video-svc|app_company-svc)", re.IGNORECASE)

def _looks_like_image_url(text: str) -> bool:
    """Best-effort detection of image URLs, even without file extensions."""
    if _IMAGE_EXT_URL_RE.search(text):
        return True
    # Common CDN/service hints (S3 or internal CDN without extensions)
    if _IMAGE_HOST_HINT_RE.search(text) and _IMAGE_PATH_HINT_RE.search(text):
        return True
    if _SERVICE_HINT_RE.search(text) and _IMAGE_PATH_HINT_RE.search(text):
        return True
    return False

# PHOTO by code (explicit whitelist) — extend as needed
PHOTO_CODES: set[str] = {"E130"}

# Explicit per-code overrides: "photo" / "link" / "event"
# NOTE: do NOT force E761 to "link" — we want E761 with image-like URLs to be PHOTO.
CODE_CATEGORY_OVERRIDES: Dict[str, str] = {
    "E130": "photo",
    # "E761": "link",  # intentionally omitted
}

def extract_signals(message: Union[str, bytes]) -> List[Dict[str, str]]:
    """
    Extract all <Signal>...</Signal> blocks and return dictionaries with parsed fields.
    Include 'raw' to allow URL detection across any child tag (VideoFile/Image/Url/Hyperlink/...).
    """
    msg = _to_text(message)
    signals: List[Dict[str, str]] = []

    def get(field: str, src: str) -> str:
        m = re.search(fr"<{field}>(.*?)</{field}>", src, flags=re.DOTALL)
        return m.group(1).strip() if m else ""

    for raw in _SIG_RE.findall(msg):
        signals.append({
            "raw":    raw,  # keep raw to check URLs anywhere inside signal
            "account": get("Account", raw),
            "date":    get("Date", raw),
            "time":    get("Time", raw),
            "code":    get("SignalIdentifier", raw),
            "zone":    get("PhysicalZone", raw),
            "area":    get("Area", raw),
            "data":    get("Data", raw),
        })
    return signals

def classify_signals(signals: List[Dict[str, str]]) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
    """
    Split signals into PHOTO/LINK/EVENT buckets (per code) and return counts.

    Priority (highest first):
      1) CODE_CATEGORY_OVERRIDES (photo/link/event)
      2) Has *image-like* URL anywhere (explicit image extension OR CDN hints) -> PHOTO
      3) PHOTO_CODES (by code whitelist)                                     -> PHOTO
      4) Has any URL (web or desktop deep-link, e.g., ajax-pro-desktop://)   -> LINK
      5) Otherwise                                                            -> EVENT
    """
    photo_by_code: Dict[str, int] = {}
    link_by_code: Dict[str, int] = {}
    event_by_code: Dict[str, int] = {}

    for s in signals:
        code = (s.get("code") or "").strip()
        raw  = (s.get("raw")  or "").strip()

        # 1) explicit override
        override = CODE_CATEGORY_OVERRIDES.get(code)
        if override == "photo":
            photo_by_code[code] = photo_by_code.get(code, 0) + 1
            continue
        elif override == "link":
            link_by_code[code] = link_by_code.get(code, 0) + 1
            continue
        elif override == "event":
            event_by_code[code] = event_by_code.get(code, 0) + 1
            continue

        # 2) image-like URL wins over everything
        if _looks_like_image_url(raw):
            photo_by_code[code] = photo_by_code.get(code, 0) + 1
            continue

        # 3) PHOTO by known codes
        if code in PHOTO_CODES:
            photo_by_code[code] = photo_by_code.get(code, 0) + 1
            continue

        # 4) Any URL → LINK (includes desktop schemes)
        if _URL_ANY_SCHEME_RE.search(raw):
            link_by_code[code] = link_by_code.get(code, 0) + 1
            continue

        # 5) Otherwise → EVENT
        event_by_code[code] = event_by_code.get(code, 0) + 1

    return photo_by_code, link_by_code, event_by_code

def build_labels_for_message(message: Union[str, bytes]) -> str:
    """
    Build labels like:
      [PING]
      [EVENT R145]
      [LINK E761 x3]
      [PHOTO E130 x3] [LINK E761] [EVENT R145]
    """
    msg = _to_text(message)
    if is_ping_microkey(msg):
        return "[PING]"

    signals = extract_signals(msg)
    if not signals:
        return ""  # Keep log clean for malformed/partial buffers

    photo_by_code, link_by_code, event_by_code = classify_signals(signals)

    labels: List[str] = []

    for code, count in photo_by_code.items():
        labels.append(f"[PHOTO {code}{(' x'+str(count)) if count > 1 else ''}]")

    for code, count in link_by_code.items():
        labels.append(f"[LINK {code}{(' x'+str(count)) if count > 1 else ''}]")

    if event_by_code:
        if len(event_by_code) == 1:
            code, count = next(iter(event_by_code.items()))
            labels.append(f"[EVENT {code}{(' x'+str(count)) if count > 1 else ''}]")
        else:
            codes = ",".join(event_by_code.keys())
            labels.append(f"[EVENT {codes}]")

    return " ".join(labels)

# -------- Log compactor for huge XML --------

_MEDIA_TAG_RE = re.compile(r"<(VideoFile|Image|Url|Link|Hyperlink)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)

def shrink_media_for_log(message: Union[str, bytes], keep_per_signal: int = 1, max_chars: int = 1200) -> str:
    """
    Reduce noise in long XML messages:
      - In each <Signal>, keep only `keep_per_signal` media URLs (VideoFile/Image/Url/Link/Hyperlink),
        replace the rest with '...'.
      - If the final string is still too long, hard-truncate to max_chars and append a note.

    Returns a best-effort compacted XML string for logging only.
    """
    msg = _to_text(message)

    def _shrink_signal(m: re.Match) -> str:
        block = m.group(0)
        kept = 0
        def _repl(media_m: re.Match) -> str:
            nonlocal kept
            kept += 1
            if kept <= keep_per_signal:
                return media_m.group(0)
            tag = media_m.group(1)
            return f"<{tag}>...</{tag}>"
        return _MEDIA_TAG_RE.sub(_repl, block)

    compact = re.sub(r"<Signal>.*?</Signal>", _shrink_signal, msg, flags=re.DOTALL)
    if len(compact) > max_chars:
        omitted = len(compact) - max_chars
        compact = compact[:max_chars] + f"... [+{omitted} chars]"
    return compact
