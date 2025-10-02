import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List

import pytest

from bot.config import BotConfig, DataProviderConfig, SchedulerConfig, StrategyConfig, TelegramConfig
from bot.data_providers import GoldPriceProvider, GoldPriceSnapshot, NewsArticle, NewsProvider
from bot.messaging import TelegramNotifier
from bot.pipeline import GoldInsightPipeline


@dataclass
class StubPriceProvider(GoldPriceProvider):
    snapshots: List[GoldPriceSnapshot]

    def fetch_latest(self) -> GoldPriceSnapshot:
        return self.snapshots[-1]

    def fetch_time_series(self, *, lookback_minutes: int, interval_minutes: int):
        return self.snapshots


@dataclass
class StubNewsProvider(NewsProvider):
    articles: List[NewsArticle]

    def fetch_latest(self, *, keywords: Iterable[str], max_items: int = 5) -> List[NewsArticle]:
        return self.articles[:max_items]


@dataclass
class StubNotifier(TelegramNotifier):
    sent_messages: List[str]

    def __init__(self) -> None:  # type: ignore[override]
        self.sent_messages = []

    def send_message(self, text: str, *, parse_mode: str = "Markdown", disable_web_page_preview: bool = True) -> None:  # type: ignore[override]
        self.sent_messages.append(text)


@pytest.fixture
def pipeline_config() -> BotConfig:
    return BotConfig(
        data=DataProviderConfig(
            gold_price_provider="stub",
            gold_price_options={},
            news_provider="stub",
        ),
        strategy=StrategyConfig(
            lookback_minutes=60,
            fast_ma_period=5,
            slow_ma_period=15,
            news_keywords=["gold"],
            max_news_items=3,
        ),
        telegram=TelegramConfig(bot_token="dummy", chat_id="dummy"),
        scheduler=SchedulerConfig(run_once=True),
    )


def make_snapshots(start_price: float = 1900.0) -> List[GoldPriceSnapshot]:
    base = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    return [
        GoldPriceSnapshot(timestamp=base + dt.timedelta(minutes=i * 5), price=start_price + i)
        for i in range(20)
    ]


def make_articles() -> List[NewsArticle]:
    base = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    return [
        NewsArticle(
            title=f"Gold headline {i}",
            url=f"https://example.com/{i}",
            published_at=base + dt.timedelta(minutes=i),
            source="UnitTestWire",
        )
        for i in range(5)
    ]


def test_pipeline_run_once(pipeline_config):
    price_provider = StubPriceProvider(snapshots=make_snapshots())
    news_provider = StubNewsProvider(articles=make_articles())
    notifier = StubNotifier()

    pipeline = GoldInsightPipeline(
        pipeline_config,
        price_provider=price_provider,
        news_provider=news_provider,
        notifier=notifier,
    )

    result = pipeline.run_once()

    assert notifier.sent_messages, "Expected a message to be sent"
    message = notifier.sent_messages[0]
    assert "Goldmarkt-Update" in message
    assert "Hinweis" in message
    assert result.price_snapshot == price_provider.snapshots[-1]
    assert result.news
    assert any("RSI" in summary for summary in result.indicator_summaries)


def test_pipeline_requires_price_data(pipeline_config):
    pipeline = GoldInsightPipeline(
        pipeline_config,
        price_provider=StubPriceProvider(snapshots=[]),
        news_provider=StubNewsProvider(articles=[]),
        notifier=StubNotifier(),
    )

    with pytest.raises(RuntimeError):
        pipeline.run_once()

