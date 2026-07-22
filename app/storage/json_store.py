from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / "state.json"
        self.signals_path = self.data_dir / "signals.json"

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    @staticmethod
    def _write(path: Path, data: Any) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def load_state(self) -> dict[str, Any]:
        return self._read(self.state_path, {"cursor": 0, "universe": [], "universe_updated_at": None, "alerts": {}})

    def save_state(self, state: dict[str, Any]) -> None:
        self._write(self.state_path, state)

    def append_signal(self, signal: dict[str, Any]) -> None:
        signals = self._read(self.signals_path, [])
        signals.append(signal)
        self._write(self.signals_path, signals[-2000:])

    def in_cooldown(self, state: dict[str, Any], symbol: str, cooldown_hours: int) -> bool:
        raw = state.get("alerts", {}).get(symbol)
        if not raw:
            return False
        try:
            sent_at = datetime.fromisoformat(raw)
        except ValueError:
            return False
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - sent_at < timedelta(hours=cooldown_hours)
