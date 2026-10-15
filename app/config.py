"""Configuration management for Z.ai Usage Telegram Bot."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    BOT_TOKEN: str
    OWNER_ID: int
    DB_DIR: str
    DB_PATH: str
    ALERT_CHECK_INTERVAL: int = 300
    ALERT_WORKER_INITIAL_DELAY: int = 10
    VERSION: str = "v2.2 (Alerts & Notifications)"
    REPO_URL: str = "https://github.com/theillarion/z-ai-usage-tg-bot"


def load_config() -> Config:
    """Load configuration from environment variables."""
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    try:
        owner_id = int(os.getenv("OWNER_ID", "0"))
    except ValueError:
        owner_id = 0

    # DB Directory resolution
    db_dir = "/data"
    if not os.path.exists(db_dir) and not os.environ.get("DOCKER"):
        db_dir = "./data"
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError:
                pass

    db_path = os.getenv("DB_PATH")
    if not db_path:
        db_path = os.path.join(db_dir, "database.db")

    try:
        check_interval = int(os.getenv("ALERT_CHECK_INTERVAL", "300"))
    except ValueError:
        check_interval = 300

    try:
        initial_delay = int(os.getenv("ALERT_WORKER_INITIAL_DELAY", "10"))
    except ValueError:
        initial_delay = 10

    return Config(
        BOT_TOKEN=bot_token,
        OWNER_ID=owner_id,
        DB_DIR=db_dir,
        DB_PATH=db_path,
        ALERT_CHECK_INTERVAL=check_interval,
        ALERT_WORKER_INITIAL_DELAY=initial_delay,
    )


# Default config singleton
config = load_config()
