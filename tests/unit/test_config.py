"""Unit tests for app/config.py."""

import os
from unittest.mock import patch
from app.config import Config, load_config


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("OWNER_ID", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("ALERT_CHECK_INTERVAL", raising=False)
    monkeypatch.delenv("ALERT_WORKER_INITIAL_DELAY", raising=False)

    cfg = load_config()
    assert cfg.BOT_TOKEN == ""
    assert cfg.OWNER_ID == 0
    assert cfg.ALERT_CHECK_INTERVAL == 300
    assert cfg.ALERT_WORKER_INITIAL_DELAY == 10
    assert cfg.VERSION == "v2.2 (Alerts & Notifications)"
    assert "github.com" in cfg.REPO_URL


def test_load_config_custom_values(monkeypatch, tmp_path):
    custom_db = str(tmp_path / "custom.db")
    monkeypatch.setenv("BOT_TOKEN", "12345:TEST_TOKEN")
    monkeypatch.setenv("OWNER_ID", "987654321")
    monkeypatch.setenv("DB_PATH", custom_db)
    monkeypatch.setenv("ALERT_CHECK_INTERVAL", "120")
    monkeypatch.setenv("ALERT_WORKER_INITIAL_DELAY", "5")

    cfg = load_config()
    assert cfg.BOT_TOKEN == "12345:TEST_TOKEN"
    assert cfg.OWNER_ID == 987654321
    assert cfg.DB_PATH == custom_db
    assert cfg.ALERT_CHECK_INTERVAL == 120
    assert cfg.ALERT_WORKER_INITIAL_DELAY == 5


def test_load_config_invalid_ints(monkeypatch):
    monkeypatch.setenv("OWNER_ID", "invalid_id")
    monkeypatch.setenv("ALERT_CHECK_INTERVAL", "invalid_interval")
    monkeypatch.setenv("ALERT_WORKER_INITIAL_DELAY", "invalid_delay")

    cfg = load_config()
    assert cfg.OWNER_ID == 0
    assert cfg.ALERT_CHECK_INTERVAL == 300
    assert cfg.ALERT_WORKER_INITIAL_DELAY == 10


def test_load_config_docker_dir(monkeypatch):
    monkeypatch.setenv("DOCKER", "1")
    monkeypatch.delenv("DB_PATH", raising=False)
    cfg = load_config()
    assert cfg.DB_DIR == "/data"
    assert cfg.DB_PATH == "/data/database.db"


def test_load_config_makedirs_oserror(monkeypatch):
    monkeypatch.delenv("DOCKER", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)
    with patch("os.path.exists", side_effect=[False, False]):
        with patch("os.makedirs", side_effect=OSError("Read only filesystem")):
            cfg = load_config()
            assert cfg.DB_DIR == "./data"

