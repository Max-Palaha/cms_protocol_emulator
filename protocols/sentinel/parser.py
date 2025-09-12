def parse_event(message: str):
    """
    Parse event message for Sentinel protocol (ADM-CID, SIA-DCS, etc).
    Returns dict with all fields and is_photo flag based on MediaUrl presence.
    """
    result = {
        "raw": message,
        "fields": {},
        "is_photo": False,
        "has_media_url": False,
        "event_code": None,
    }
    try:
        parts = message.strip().split('|')
        for part in parts:
            if '=' in part:
                k, v = part.split('=', 1)
                k = k.strip()
                v = v.strip()
                result["fields"][k] = v
                if k == "Event":
                    result["event_code"] = v
                if k.lower() == "mediaurl":
                    result["is_photo"] = True
                    result["has_media_url"] = True
    except Exception as ex:
        result["error"] = str(ex)
    return result
