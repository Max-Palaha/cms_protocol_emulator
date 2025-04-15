import pytest
from utils.event_utils import to_hex, from_hex, detect_event_format, is_adm_cid_event, is_sia_dc09_event


def test_to_hex_and_from_hex():
    original = b'\x12\x34\x56'
    hexed = to_hex(original)
    assert hexed == '123456'
    assert from_hex(hexed) == original


@pytest.mark.parametrize("event,expected", [
    ("E120", True),
    ("R999", True),
    ("BR", False),
    ("123", False),
    ("", False),
])
def test_is_adm_cid_event(event, expected):
    assert is_adm_cid_event(event) == expected


@pytest.mark.parametrize("event,expected", [
    ("BR", True),
    ("PI", True),
    ("E120", False),
    ("R999", False),
    ("", False),
])
def test_is_sia_dc09_event(event, expected):
    assert is_sia_dc09_event(event) == expected


@pytest.mark.parametrize("message,expected", [
    ("E120", "ADM-CID"),
    ("BR", "SIA-DC09"),
    ("something", "UNKNOWN"),
])
def test_detect_event_format(message, expected):
    assert detect_event_format(message) == expected
