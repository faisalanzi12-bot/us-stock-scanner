from __future__ import annotations

import html
import requests

from app.signals.scorer import Signal


class TelegramSender:
    def __init__(self, token: str, chat_id: str, timeout: int = 20):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, text: str) -> None:
        response = requests.post(
            self.url,
            json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram error: {payload}")

    def send_signal(self, signal: Signal) -> None:
        reasons = "\n".join(f"✅ {html.escape(reason)}" for reason in signal.reasons)
        message = (
            "🚨 <b>فرصة مبكرة محتملة</b>\n\n"
            f"السهم: <b>{html.escape(signal.symbol)}</b>\n"
            f"السعر: <b>${signal.price:.2f}</b>\n"
            f"التغير: <b>{signal.change_percent:+.2f}%</b>\n"
            f"التقييم: <b>{signal.score}/100</b>\n"
            f"الحجم النسبي: <b>{signal.relative_volume:.1f}×</b>\n\n"
            f"<b>الأسباب:</b>\n{reasons}"
        )
        if signal.news_headline:
            message += f"\n\n📰 {html.escape(signal.news_headline[:300])}"
            if signal.news_url:
                safe_url = html.escape(signal.news_url, quote=True)
                message += f'\n<a href="{safe_url}">فتح الخبر</a>'
        message += "\n\n⚠️ ليست توصية شراء. راقب إدارة المخاطر وتجنب مطاردة السهم."
        self.send(message)
