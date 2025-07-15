# tests/utils/test_config_loader.py

import pytest
from utils import config_loader

TEST_YAML = """
environment:
  ports:
    sia-dcs: 1234
    masxml: 5678
logging:
  level: DEBUG
"""


@pytest.fixture(autouse=True)
def reset_config(monkeypatch):
    monkeypatch.setattr(config_loader, "CONFIG", None)
    monkeypatch.setattr(config_loader, "PORTS", {})
    yield


def test_load_config(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(TEST_YAML)

    monkeypatch.setattr(config_loader, "CONFIG_PATH", config_file)
    loaded = config_loader.load_config(force_reload=True)

    assert isinstance(loaded, dict)
    assert loaded.get("environment", {}).get("ports", {}).get("sia-dcs") == 1234


def test_get_port_by_key(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(TEST_YAML)

    monkeypatch.setattr(config_loader, "CONFIG_PATH", config_file)
    config_loader.CONFIG = None
    config_loader.load_config(force_reload=True)

    assert config_loader.get_port_by_key("sia_dcs") == 1234
    assert config_loader.get_port_by_key("masxml") == 5678
