from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class FinnhubError(RuntimeError):
    pass


class FinnhubProvider:
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str, request_delay: float = 1.05, timeout: int = 20):
        self.api_key = api_key
        self.request_delay = max(0.0, request_delay)
        self.timeout = timeout
        self.session = requests.Session()
        self._last_request_at = 0.0

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        query = dict(params or {})
        query["token"] = self.api_key
        try:
            response = self.session.get(
                f"{self.BASE_URL}/{endpoint}", params=query, timeout=self.timeout
            )
            self._last_request_at = time.monotonic()
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise FinnhubError(f"Finnhub request failed for {endpoint}: {exc}") from exc
        if isinstance(payload, dict) and payload.get("error"):
            raise FinnhubError(str(payload["error"]))
        return payload

    def stock_symbols(self, exchange: str = "US") -> list[dict[str, Any]]:
        payload = self._get("stock/symbol", {"exchange": exchange})
        return payload if isinstance(payload, list) else []

    def quote(self, symbol: str) -> dict[str, Any]:
        payload = self._get("quote", {"symbol": symbol})
        return payload if isinstance(payload, dict) else {}

    def candles(self, symbol: str, resolution: str, start_ts: int, end_ts: int) -> dict[str, Any]:
        payload = self._get(
            "stock/candle",
            {"symbol": symbol, "resolution": resolution, "from": start_ts, "to": end_ts},
        )
        return payload if isinstance(payload, dict) else {}

    def company_news(self, symbol: str, lookback_hours: int) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=lookback_hours)
        payload = self._get(
            "company-news",
            {"symbol": symbol, "from": start.date().isoformat(), "to": now.date().isoformat()},
        )
        if not isinstance(payload, list):
            return []
        cutoff = int(start.timestamp())
        return [item for item in payload if int(item.get("datetime") or 0) >= cutoff]
