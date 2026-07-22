from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.providers.finnhub import FinnhubError, FinnhubProvider
from app.signals.scorer import Signal, SignalScorer
from app.storage.json_store import JsonStore


class StockScanner:
    def __init__(self, provider: FinnhubProvider, scorer: SignalScorer, store: JsonStore, settings: dict[str, Any]):
        self.provider = provider
        self.scorer = scorer
        self.store = store
        self.cfg = settings["scanner"]

    def _refresh_universe(self, state: dict[str, Any]) -> None:
        updated_raw = state.get("universe_updated_at")
        should_refresh = not state.get("universe")
        if updated_raw:
            try:
                updated = datetime.fromisoformat(updated_raw)
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                should_refresh = datetime.now(timezone.utc) - updated > timedelta(hours=self.cfg["universe_refresh_hours"])
            except ValueError:
                should_refresh = True
        if not should_refresh:
            return
        symbols = self.provider.stock_symbols("US")
        universe = sorted({
            item.get("symbol", "").strip()
            for item in symbols
            if item.get("symbol")
            and item.get("type") in {"Common Stock", "ADR"}
            and "." not in item.get("symbol", "")
        })
        state["universe"] = universe
        state["universe_updated_at"] = datetime.now(timezone.utc).isoformat()
        state["cursor"] = 0

    def run(self) -> tuple[list[Signal], dict[str, Any]]:
        state = self.store.load_state()
        self._refresh_universe(state)
        universe = state.get("universe", [])
        if not universe:
            raise RuntimeError("Finnhub returned an empty US stock universe")

        batch_size = int(self.cfg["max_symbols_per_run"])
        cursor = int(state.get("cursor", 0)) % len(universe)
        batch = [universe[(cursor + i) % len(universe)] for i in range(min(batch_size, len(universe)))]
        state["cursor"] = (cursor + len(batch)) % len(universe)

        now = datetime.now(timezone.utc)
        end_ts = int(now.timestamp())
        start_ts = int((now - timedelta(minutes=self.cfg["candle_lookback_minutes"])).timestamp())
        signals: list[Signal] = []
        errors: list[str] = []

        for symbol in batch:
            if self.store.in_cooldown(state, symbol, int(self.cfg["cooldown_hours"])):
                continue
            try:
                quote = self.provider.quote(symbol)
                price = float(quote.get("c") or 0)
                if not (self.cfg["min_price"] <= price <= self.cfg["max_price"]):
                    continue
                candles = self.provider.candles(symbol, str(self.cfg["candle_resolution"]), start_ts, end_ts)
                if candles.get("s") != "ok":
                    continue
                news = self.provider.company_news(symbol, int(self.cfg["news_lookback_hours"]))
                signal = self.scorer.score(symbol, quote, candles, news)
                if signal:
                    signals.append(signal)
            except FinnhubError as exc:
                errors.append(f"{symbol}: {exc}")
                if "limit" in str(exc).lower():
                    break

        signals.sort(key=lambda item: (item.score, item.relative_volume), reverse=True)
        signals = signals[: int(self.cfg["max_alerts_per_run"])]
        state["last_run_at"] = now.isoformat()
        state["last_batch"] = batch
        state["last_errors"] = errors[-10:]
        return signals, state
