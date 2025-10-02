"""Telegram messaging helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

import requests

from .data_providers import GoldPriceSnapshot, NewsArticle

LOGGER = logging.getLogger(__name__)


@dataclass
class MessageBuilder:
    """Compose human-readable Telegram messages."""

    def build_report(
        self,
        *,
        price_snapshot: GoldPriceSnapshot,
        price_change: Optional[float],
        indicator_summaries: Iterable[str],
        news: Iterable[NewsArticle],
    ) -> str:
        lines = [
            "\u2728 **Goldmarkt-Update**",
            f"Preis: {price_snapshot.price:.2f} {price_snapshot.currency} ({price_snapshot.timestamp:%Y-%m-%d %H:%M UTC})",
        ]
        if price_change is not None:
            lines.append(f"Veränderung (letzte Periode): {price_change:+.2f}%")
        lines.append("\nTechnische Indikatoren:")
        for summary in indicator_summaries:
            lines.append(f"- {summary}")
        headlines_added = False
        for index, article in enumerate(news, start=1):
            if not headlines_added:
                lines.append("\nWichtige Schlagzeilen:")
                headlines_added = True
            lines.append(f"{index}. [{article.title}]({article.url}) ({article.source}, {article.published_at:%H:%M UTC})")
        if not headlines_added:
            lines.append("\nKeine aktuellen Schlagzeilen gefunden.")
        lines.append("\nHinweis: Dieser Bot informiert nur und führt **keine** Trades aus.")
        return "\n".join(lines)


class TelegramNotifier:
    """Send formatted messages to Telegram chats."""

    TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, *, bot_token: str, chat_id: str, thread_id: Optional[int] = None) -> None:
        if not bot_token or not chat_id:
            raise ValueError("bot_token and chat_id are required for TelegramNotifier")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.thread_id = thread_id

    def send_message(self, text: str, *, parse_mode: str = "Markdown", disable_web_page_preview: bool = True) -> None:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if self.thread_id is not None:
            payload["message_thread_id"] = self.thread_id
        url = self.TELEGRAM_API.format(token=self.bot_token)
        response = requests.post(url, json=payload, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            LOGGER.error("Failed to send Telegram message: %s", exc)
            raise

