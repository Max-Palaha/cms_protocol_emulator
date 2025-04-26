from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Union


def _prettify_xml(elem) -> str:
    """Returns a pretty-printed XML string for the Element."""
    rough_string = tostring(elem, encoding="utf-8")
    return rough_string.decode("utf-8")


def convert_masxml_ack(data: Union[str, bytes]) -> str:
    if isinstance(data, bytes):
        data = data.decode()

    seq_no = _extract_sequence_no(data)

    root = Element("AckNakClass")
    SubElement(root, "MessageSequenceNo").text = seq_no
    SubElement(root, "ResultCode").text = "0"
    SubElement(root, "ResultText").text = "ok"

    return _prettify_xml(root)


def convert_masxml_nak(
    data: Union[str, bytes],
    text: str = "Poorly formed XML",
    code: Union[int, str] = 10,
) -> str:
    print(f"[DEBUG] Generating NAK with ResultCode: {code}")
    if isinstance(data, bytes):
        data = data.decode()

    seq_no = _extract_sequence_no(data)

    root = Element("AckNakClass")
    SubElement(root, "MessageSequenceNo").text = seq_no
    SubElement(root, "ResultCode").text = str(code)
    SubElement(root, "ResultText").text = text

    return _prettify_xml(root)


def _extract_sequence_no(xml_string: str) -> str:
    import re

    match = re.search(r"<MessageSequenceNo>(\d+)</MessageSequenceNo>", xml_string)
    return match.group(1) if match else "0000"
