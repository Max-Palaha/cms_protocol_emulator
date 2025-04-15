# tests/utils/test_mode_manager.py

import pytest
from datetime import datetime
from utils.mode_manager import EmulationMode, TimeModeDuration


def test_default_mode(fresh_mode_manager):
    protocol_mode = fresh_mode_manager.get("test_proto")
    assert protocol_mode.mode == EmulationMode.ACK


def test_switch_to_nak_then_back(fresh_mode_manager):
    protocol_mode = fresh_mode_manager.get("test_proto")
    protocol_mode.set_mode(EmulationMode.NAK, count=2, next_mode=EmulationMode.ONLY_PING)

    assert protocol_mode.mode == EmulationMode.NAK
    protocol_mode.consume_packet()
    assert protocol_mode.mode == EmulationMode.NAK
    protocol_mode.consume_packet()
    assert protocol_mode.mode == EmulationMode.ONLY_PING


def test_drop_mode(fresh_mode_manager):
    protocol_mode = fresh_mode_manager.get("drop_proto")
    protocol_mode.set_drop(3)

    assert protocol_mode.mode == EmulationMode.DROP_N
    assert protocol_mode.drop_count == 3

    protocol_mode.drop_count -= 1
    assert protocol_mode.drop_count == 2


def test_time_custom_mode_once(fresh_mode_manager):
    protocol_mode = fresh_mode_manager.get("time_proto")
    custom_time = datetime.strptime("2024-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
    protocol_mode.set_time(custom_time, TimeModeDuration.ONCE)

    assert protocol_mode.mode == EmulationMode.TIME_CUSTOM
    timestamp = protocol_mode.get_response_timestamp()
    assert timestamp.startswith("00:00:00,01-01-2024")
    # After consuming once, timestamp override should clear
    assert protocol_mode.get_response_timestamp() != timestamp
