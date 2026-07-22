from app.signals.scorer import SignalScorer


def test_strong_signal_scores_above_threshold():
    settings = {
        "scanner": {
            "min_price": 0.5, "max_price": 10, "min_change_percent": 1,
            "max_change_percent": 12, "min_dollar_volume": 1000,
            "min_relative_volume": 2, "min_score": 70,
        },
        "weights": {
            "fresh_positive_news": 30, "relative_volume": 30,
            "early_momentum": 20, "near_session_high": 10,
            "support_reversal": 10,
        },
        "positive_keywords": ["contract"],
        "negative_keywords": ["offering"],
    }
    scorer = SignalScorer(settings)
    quote = {"c": 5.0, "dp": 4.0}
    candles = {
        "v": [100, 100, 100, 100, 100, 100, 400, 500, 600],
        "c": [4.6, 4.62, 4.65, 4.7, 4.75, 4.8, 4.85, 4.92, 5.0],
        "h": [4.7, 4.72, 4.75, 4.8, 4.85, 4.9, 4.95, 5.0, 5.02],
        "l": [4.5, 4.55, 4.6, 4.65, 4.7, 4.75, 4.8, 4.85, 4.9],
    }
    news = [{"headline": "Company wins major contract", "summary": "", "url": "https://example.com"}]
    signal = scorer.score("TEST", quote, candles, news)
    assert signal is not None
    assert signal.score >= 70
