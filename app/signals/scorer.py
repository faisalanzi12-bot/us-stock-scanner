from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Signal:
    symbol: str
    price: float
    change_percent: float
    score: int
    relative_volume: float
    dollar_volume: float
    reasons: list[str]
    news_headline: str | None = None
    news_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SignalScorer:
    def __init__(self, settings: dict[str, Any]):
        self.cfg = settings["scanner"]
        self.weights = settings["weights"]
        self.positive = [x.lower() for x in settings.get("positive_keywords", [])]
        self.negative = [x.lower() for x in settings.get("negative_keywords", [])]

    def score(self, symbol: str, quote: dict[str, Any], candles: dict[str, Any], news: list[dict[str, Any]]) -> Signal | None:
        price = float(quote.get("c") or 0)
        change = float(quote.get("dp") or 0)
        if not (self.cfg["min_price"] <= price <= self.cfg["max_price"]):
            return None
        if change < self.cfg["min_change_percent"] or change > self.cfg["max_change_percent"]:
            return None

        volumes = [float(v) for v in candles.get("v", [])]
        closes = [float(v) for v in candles.get("c", [])]
        highs = [float(v) for v in candles.get("h", [])]
        lows = [float(v) for v in candles.get("l", [])]
        if len(volumes) < 8 or len(closes) < 8:
            return None

        recent_volume = sum(volumes[-3:])
        baseline_chunks = [sum(volumes[i:i+3]) for i in range(0, max(0, len(volumes)-3), 3)]
        baseline = sum(baseline_chunks) / len(baseline_chunks) if baseline_chunks else 0
        relative_volume = recent_volume / baseline if baseline > 0 else 0
        dollar_volume = sum(volumes) * price
        if dollar_volume < self.cfg["min_dollar_volume"]:
            return None

        score = 0
        reasons: list[str] = []
        if relative_volume >= self.cfg["min_relative_volume"]:
            score += int(self.weights["relative_volume"])
            reasons.append(f"حجم نسبي مرتفع {relative_volume:.1f}×")

        recent_return = ((closes[-1] / closes[-4]) - 1) * 100 if closes[-4] else 0
        if 0.5 <= recent_return <= 6.0:
            score += int(self.weights["early_momentum"])
            reasons.append(f"زخم مبكر +{recent_return:.1f}%")

        session_high = max(highs)
        if session_high and price >= session_high * 0.985:
            score += int(self.weights["near_session_high"])
            reasons.append("قريب من أعلى الجلسة")

        recent_low = min(lows[-6:])
        if recent_low and closes[-1] > closes[-2] > recent_low * 1.01:
            score += int(self.weights["support_reversal"])
            reasons.append("ارتداد محتمل من دعم قصير")

        chosen_news = None
        for item in news:
            text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
            if any(word in text for word in self.negative):
                continue
            if any(word in text for word in self.positive):
                chosen_news = item
                score += int(self.weights["fresh_positive_news"])
                reasons.append("محفز خبري إيجابي حديث")
                break

        if score < self.cfg["min_score"]:
            return None
        return Signal(
            symbol=symbol,
            price=price,
            change_percent=change,
            score=min(score, 100),
            relative_volume=relative_volume,
            dollar_volume=dollar_volume,
            reasons=reasons,
            news_headline=(chosen_news or {}).get("headline"),
            news_url=(chosen_news or {}).get("url"),
        )
