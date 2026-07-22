from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Secrets:
    finnhub_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str


def load_settings(path: str = "config/settings.yaml") -> dict[str, Any]:
    settings_path = Path(path)
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    with settings_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if "scanner" not in data or "weights" not in data:
        raise ValueError("settings.yaml must contain scanner and weights sections")
    return data


def load_secrets() -> Secrets:
    values = {
        "finnhub_api_key": os.getenv("FINNHUB_API_KEY", "").strip(),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    }
    missing = [name.upper() for name, value in values.items() if not value]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
    return Secrets(**values)
