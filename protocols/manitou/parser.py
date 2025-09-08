import re
from typing import Dict, Optional, Union

STX = "\x02"
ETX = "\x03"


def strip_stx_etx(data: Union[str, bytes]) -> str:
    """Remove leading STX and trailing ETX; return pure XML string."""
    if isinstance(data, bytes):
        data = data.decode(errors="ignore")
    s = data.strip()
    if s and s[0] == STX:
        s = s[1:]
    if s and s[-1] == ETX:
        s = s[:-1]
    return s


def sanitize_for_log(data: Union[str, bytes]) -> str:
    """
    Redact <Data>...</Data> body from Binary packets for safe logging.
    Keeps attributes (Ext, Length, RawNo, FrameNo, Data Length), replaces body with marker.
    """
    s = strip_stx_etx(data)

    def _repl(m: re.Match) -> str:
        open_tag = m.group(1)
        length_attr = re.search(r'Length="(\d+)"', open_tag, flags=re.IGNORECASE)
        length_val = length_attr.group(1) if length_attr else "?"
        return f"{open_tag}[BINARY REDACTED len={length_val}]</Data>"

    s = re.sub(r"(<Data\b[^>]*>)(.*?)(</Data>)", _repl, s, flags=re.DOTALL | re.IGNORECASE)
    return s


def is_binary_payload(message: Union[str, bytes]) -> bool:
    s = strip_stx_etx(message)
    return "<Binary" in s


def is_ping(message: Union[str, bytes]) -> bool:
    """
    Heartbeat / Ping detection (case-insensitive).
    Typical frames:
      <Heartbeat/>   OR   <Ping/>   OR   <MessageType>HEARTBEAT</MessageType>
    """
    s = strip_stx_etx(message)
    if re.search(r"<\s*(heartbeat|ping)\b", s, flags=re.IGNORECASE):
        return True
    if re.search(r"<\s*MessageType\s*>\s*HEARTBEAT\s*</\s*MessageType\s*>", s, flags=re.IGNORECASE):
        return True
    return False


def parse_manitou_message(data: Union[str, bytes]) -> Dict[str, Optional[str]]:
    """
    Parse a Manitou XML frame (without STX/ETX) into a typed dict.

    Returns keys:
      type: "signal" | "binary" | "unknown"
      raw_text: sanitized xml string (safe for logs)
      # signal:
      event_code, evtype, area, area_info, zone, point_id, url
      # binary:
      rawno, ext, frame_no (str), length (str), data_len (str)
    """
    xml = strip_stx_etx(data)

    # Binary
    if "<Binary" in xml:
        bin_open = re.search(r"<Binary\b([^>]*)>", xml, flags=re.IGNORECASE)
        attrs = bin_open.group(1) if bin_open else ""
        ext = _extract_attr(attrs, "Ext")
        rawno = _extract_attr(attrs, "RawNo")
        frame_no = _extract_attr(attrs, "FrameNo") or _extract_attr(attrs, "Frame")
        length = _extract_attr(attrs, "Length")

        data_open = re.search(r"<Data\b([^>]*)>", xml, flags=re.IGNORECASE)
        data_len = _extract_attr(data_open.group(1), "Length") if data_open else None

        return {
            "type": "binary",
            "raw_text": sanitize_for_log(xml),
            "ext": ext,
            "rawno": rawno,
            "frame_no": frame_no,
            "length": length,
            "data_len": data_len,
        }

    # Signal
    sig = re.search(r"<Signal\b([^>]*)>(.*?)</Signal>", xml, flags=re.IGNORECASE | re.DOTALL)
    if sig:
        sig_attrs = sig.group(1)
        inner = sig.group(2)
        evtype = _extract_attr(sig_attrs, "EvType")
        event = _extract_attr(sig_attrs, "Event")  # ← attribute, not inner tag
        area = _extract_inner(inner, "Area")
        area_info = _extract_inner(inner, "AreaInfo")
        zone = _extract_inner(inner, "Zone")
        point_id = _extract_inner(inner, "PointID")
        url = _extract_inner(inner, "URL")

        return {
            "type": "signal",
            "raw_text": sanitize_for_log(xml),
            "evtype": evtype,
            "event_code": event,
            "area": area,
            "area_info": area_info,
            "zone": zone,
            "point_id": point_id,
            "url": url,
        }

    return {"type": "unknown", "raw_text": sanitize_for_log(xml)}


def _extract_attr(attrs: str, name: str) -> Optional[str]:
    m = re.search(rf'\b{name}="([^"]+)"', attrs, flags=re.IGNORECASE)
    return m.group(1) if m else None


def _extract_inner(blob: str, tag: str) -> Optional[str]:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", blob, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None
