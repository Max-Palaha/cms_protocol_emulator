# tests/utils/test_registry_tools.py

import pytest
from utils import registry_tools


class DummyProtocol:
    async def run(self):
        pass


def test_register_and_get_protocol():
    # Register
    name = "dummy_proto"
    decorator = registry_tools.register_protocol(name)
    decorated_class = decorator(DummyProtocol)

    # Ensure correct class returned
    assert decorated_class is DummyProtocol

    # Get from registry
    retrieved = registry_tools.get_protocol_handler(name)
    assert retrieved is DummyProtocol


def test_register_existing_protocol_raises():
    name = "duplicate_proto"
    registry_tools.register_protocol(name)(DummyProtocol)

    with pytest.raises(ValueError, match="already registered"):
        registry_tools.register_protocol(name)(DummyProtocol)


def test_get_unregistered_protocol_raises():
    with pytest.raises(ValueError, match="is not registered"):
        registry_tools.get_protocol_handler("nonexistent_proto")
