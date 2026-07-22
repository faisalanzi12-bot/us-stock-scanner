from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import load_secrets, load_settings
from app.notifications.telegram import TelegramSender
from app.providers.finnhub import FinnhubProvider
from app.scanner.scanner import StockScanner
from app.signals.scorer import SignalScorer
from app.storage.json_store import JsonStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("stock-scanner")


def main() -> None:
    settings = load_settings()
    secrets = load_secrets()
    store = JsonStore()
    provider = FinnhubProvider(
        secrets.finnhub_api_key,
        request_delay=float(settings["scanner"]["request_delay_seconds"]),
    
    scorer = SignalScorer(settings)
    scanner = StockScanner(provider, scorer, store, settings)
telegram = TelegramSender(secrets.telegram_bot_token, secrets.telegram_chat_id)
telegram.send("✅ اختبار: US Stock Scanner مربوط بتيليجرام ويعمل")
    signals, state = scanner.run()
    logger.info("Found %d qualifying signals", len(signals))
    for signal in signals:
        telegram.send_signal(signal)
        sent_at = datetime.now(timezone.utc).isoformat()
        state.setdefault("alerts", {})[signal.symbol] = sent_at
        record = signal.to_dict() | {"sent_at": sent_at}
        store.append_signal(record)
        logger.info("Alert sent: %s score=%s", signal.symbol, signal.score)
    store.save_state(state)


if __name__ == "__main__":
    main()
