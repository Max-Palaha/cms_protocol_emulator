import pytest
from utils.mode_manager import ModeManager


@pytest.fixture
def fresh_mode_manager():
    """
    Provides a fresh ModeManager instance for testing.
    """
    return ModeManager()


@pytest.fixture
def example_sia_message():
    return 'D350003A"SIA-DCS"0003L0#55555[#55555|Nri1/PH0]_12:00:00,01-01-2025'


@pytest.fixture
def example_masxml_heartbeat():
    return """<?xml version='1.0' encoding='UTF-8'?>
    <XMLMessageClass>
        <MessageType>HEARTBEAT</MessageType>
        <SourceID>5</SourceID>
        <MessageSequenceNo>100</MessageSequenceNo>
    </XMLMessageClass>"""


@pytest.fixture
def example_masxml_ajax():
    return """<?xml version='1.0' encoding='UTF-8'?>
    <XMLMessageClass>
        <MessageType>AJAX</MessageType>
        <SourceID>5</SourceID>
        <MessageSequenceNo>101</MessageSequenceNo>
        <KeyValuePair><Key>Account</Key><Value>ABCDEF1234</Value></KeyValuePair>
        <KeyValuePair><Key>EventCode</Key><Value>E120</Value></KeyValuePair>
        <KeyValuePair><Key>Area</Key><Value>1</Value></KeyValuePair>
        <KeyValuePair><Key>User</Key><Value>0</Value></KeyValuePair>
    </XMLMessageClass>"""
