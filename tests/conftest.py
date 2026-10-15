"""Pytest configuration, shared fixtures and test utilities."""

import os
from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.database import init_db


@pytest.fixture
def tmp_db_path(tmp_path):
    """Provide a path to a temporary SQLite database initialized with schema."""
    db_file = str(tmp_path / "test_bot.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def mock_bot():
    """Mock Aiogram Bot object with async methods."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.delete_webhook = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot


@pytest.fixture
def mock_fsm_context():
    """Provide real FSMContext with in-memory storage for realistic state testing."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=123456, chat_id=111111, user_id=111111)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
def sample_quota_data():
    """Sample quota and subscription data returned by Z.ai API."""
    return {
        "level": "PRO",
        "plan_title": "GLM Coding Plan - Pro (v3)",
        "subscription_end": 1780000000000,
        "auto_renew": True,
        "limits": [
            {
                "type": "CREDIT_LIMIT",
                "unit": 3,
                "number": 5,
                "percentage": 42.5,
                "currentValue": 425,
                "usage": 1000,
                "nextResetTime": 1780000000000,
            },
            {
                "type": "CREDIT_LIMIT",
                "unit": 6,
                "number": 1,
                "percentage": 15.0,
                "currentValue": 1500,
                "usage": 10000,
                "nextResetTime": 1780500000000,
            },
            {
                "type": "TIME_LIMIT",
                "unit": 1,
                "percentage": 20.0,
                "remaining": 8,
                "usage": 10,
                "nextResetTime": 1780100000000,
                "usageDetails": [
                    {"modelCode": "search-prime", "usage": 2},
                    {"modelCode": "web-reader", "usage": 0},
                ],
            },
        ],
    }
