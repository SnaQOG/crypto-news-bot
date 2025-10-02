"""Market and news data provider abstractions."""

from __future__ import annotations

import abc
import datetime as dt
import logging
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableMapping, Optional, Sequence

import requests

LOGGER = logging.getLogger(__name__)


@dataclass
class GoldPriceSnapshot:
    """Representation of a single gold price observation."""

    timestamp: dt.datetime
    price: float
    currency: str = "USD"


class GoldPriceProvider(abc.ABC):
    """Abstract interface for classes that provide gold prices."""

    @abc.abstractmethod
    def fetch_latest(self) -> GoldPriceSnapshot:
        """Fetch the most recent price."""

    @abc.abstractmethod
    def fetch_time_series(self, *, lookback_minutes: int, interval_minutes: int) -> Sequence[GoldPriceSnapshot]:
        """Fetch a time-series of gold prices for signal generation."""


class AlphaVantageGoldPriceProvider(GoldPriceProvider):
    """Fetch gold prices from the Alpha Vantage FX API."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, *, api_key: str, from_symbol: str = "XAU", to_symbol: str = "USD") -> None:
        if not api_key:
            raise ValueError("AlphaVantageGoldPriceProvider requires an api_key")
        self.api_key = api_key
        self.from_symbol = from_symbol
        self.to_symbol = to_symbol

    def _request(self, params: Mapping[str, str]) -> Mapping[str, Mapping[str, str]]:
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def fetch_latest(self) -> GoldPriceSnapshot:
        payload = self._request(
            {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": self.from_symbol,
                "to_currency": self.to_symbol,
                "apikey": self.api_key,
            }
        )
        raw_rate = payload.get("Realtime Currency Exchange Rate", {})
        price = float(raw_rate["5. Exchange Rate"])
        timestamp = dt.datetime.fromisoformat(raw_rate["6. Last Refreshed"])  # type: ignore[arg-type]
        return GoldPriceSnapshot(timestamp=timestamp, price=price, currency=self.to_symbol)

    def fetch_time_series(self, *, lookback_minutes: int, interval_minutes: int) -> Sequence[GoldPriceSnapshot]:
        payload = self._request(
            {
                "function": "FX_INTRADAY",
                "from_symbol": self.from_symbol,
                "to_symbol": self.to_symbol,
                "interval": f"{interval_minutes}min",
                "apikey": self.api_key,
                "outputsize": "full",
            }
        )
        time_series = payload.get(f"Time Series FX ({interval_minutes}min)", {})
        snapshots = [
            GoldPriceSnapshot(
                timestamp=dt.datetime.fromisoformat(timestamp),
                price=float(values["4. close"]),
                currency=self.to_symbol,
            )
            for timestamp, values in time_series.items()
        ]
        limit = max(1, int(lookback_minutes / interval_minutes) + 1)
        snapshots.sort(key=lambda snap: snap.timestamp)
        return snapshots[-limit:]


@dataclass
class NewsArticle:
    """Simplified representation of a news article."""

    title: str
    url: str
    published_at: dt.datetime
    source: str


class NewsProvider(abc.ABC):
    """Interface for fetching news items."""

    @abc.abstractmethod
    def fetch_latest(self, *, keywords: Iterable[str], max_items: int = 5) -> List[NewsArticle]:
        """Return a list of news articles."""


class NewsApiProvider(NewsProvider):
    """Fetch news using the newsapi.org endpoint."""

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, *, api_key: str, language: str = "en", sort_by: str = "publishedAt") -> None:
        if not api_key:
            raise ValueError("NewsApiProvider requires an api_key")
        self.api_key = api_key
        self.language = language
        self.sort_by = sort_by

    def fetch_latest(self, *, keywords: Iterable[str], max_items: int = 5) -> List[NewsArticle]:
        query = " OR ".join(keywords)
        params = {
            "q": query,
            "apiKey": self.api_key,
            "language": self.language,
            "sortBy": self.sort_by,
            "pageSize": max_items,
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        articles = []
        for article in payload.get("articles", []):
            published = article.get("publishedAt")
            try:
                published_at = dt.datetime.fromisoformat(published.replace("Z", "+00:00")) if published else dt.datetime.utcnow()
            except ValueError:  # pragma: no cover - fallback path
                LOGGER.warning("Failed to parse news timestamp %s", published)
                published_at = dt.datetime.utcnow()
            articles.append(
                NewsArticle(
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    published_at=published_at,
                    source=(article.get("source") or {}).get("name", ""),
                )
            )
        return articles


class DummyNewsProvider(NewsProvider):
    """A deterministic provider used when no API credentials are configured."""

    def __init__(self, *, headlines: Optional[Sequence[str]] = None) -> None:
        self.headlines = list(headlines or [])

    def fetch_latest(self, *, keywords: Iterable[str], max_items: int = 5) -> List[NewsArticle]:
        now = dt.datetime.utcnow()
        items = self.headlines or [
            "Gold prices consolidate as traders await Fed signals",
            "Mining sector sees renewed investment amid safe-haven demand",
            "ETF inflows point to bullish sentiment in precious metals",
        ]
        return [
            NewsArticle(
                title=headline,
                url="https://example.com/gold-news",
                published_at=now - dt.timedelta(minutes=index * 5),
                source="DummyWire",
            )
            for index, headline in enumerate(items[:max_items])
        ]


def build_gold_price_provider(name: str, options: Optional[MutableMapping[str, str]]) -> GoldPriceProvider:
    """Factory for gold price providers."""

    options = options or {}
    if name == "alpha_vantage":
        return AlphaVantageGoldPriceProvider(api_key=str(options.get("api_key", "")))
    raise ValueError(f"Unsupported gold price provider: {name}")


def build_news_provider(name: str, options: Optional[MutableMapping[str, str]]) -> NewsProvider:
    """Factory for news providers."""

    options = options or {}
    if not name:
        return DummyNewsProvider()
    if name == "news_api":
        return NewsApiProvider(
            api_key=str(options.get("api_key", "")),
            language=str(options.get("language", "en")),
            sort_by=str(options.get("sort_by", "publishedAt")),
        )
    if name == "dummy":
        return DummyNewsProvider(headlines=options.get("headlines"))
    raise ValueError(f"Unsupported news provider: {name}")

