"""Orchestrates the flow between data providers, indicators and messaging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Sequence

from .config import BotConfig
from .data_providers import (
    GoldPriceProvider,
    GoldPriceSnapshot,
    NewsArticle,
    NewsProvider,
    build_gold_price_provider,
    build_news_provider,
)
from .indicators import summarize_indicators
from .messaging import MessageBuilder, TelegramNotifier

LOGGER = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for pipeline outputs used in testing and logging."""

    message: str
    price_snapshot: GoldPriceSnapshot
    indicator_summaries: Sequence[str]
    news: Sequence[NewsArticle]


class GoldInsightPipeline:
    """Run the end-to-end flow to produce Telegram updates."""

    def __init__(
        self,
        config: BotConfig,
        *,
        price_provider: GoldPriceProvider | None = None,
        news_provider: NewsProvider | None = None,
        notifier: TelegramNotifier | None = None,
        message_builder: MessageBuilder | None = None,
    ) -> None:
        self.config = config
        self.price_provider = price_provider or build_gold_price_provider(
            config.data.gold_price_provider,
            config.data.gold_price_options,
        )
        self.news_provider = news_provider or build_news_provider(
            config.data.news_provider,
            config.data.news_options,
        )
        self.notifier = notifier or TelegramNotifier(
            bot_token=config.telegram.bot_token,
            chat_id=config.telegram.chat_id,
            thread_id=config.telegram.thread_id,
        )
        self.message_builder = message_builder or MessageBuilder()

    def run_once(self) -> PipelineResult:
        LOGGER.info("Fetching gold price snapshots")
        lookback = self.config.strategy.lookback_minutes
        interval = max(1, min(self.config.strategy.fast_ma_period, self.config.strategy.slow_ma_period))
        time_series = self.price_provider.fetch_time_series(
            lookback_minutes=lookback,
            interval_minutes=interval,
        )
        if not time_series:
            raise RuntimeError("No price data received from provider")
        LOGGER.debug("Fetched %s price points", len(time_series))
        price_snapshot = time_series[-1]
        prices = [snapshot.price for snapshot in time_series]
        indicator_summaries = summarize_indicators(
            prices,
            [
                self.config.strategy.fast_ma_period,
                self.config.strategy.slow_ma_period,
            ],
        )
        price_change = None
        if len(prices) >= 2:
            previous = prices[-2]
            if previous:
                price_change = (prices[-1] - previous) / previous * 100
        LOGGER.info("Fetching news articles")
        news = self.news_provider.fetch_latest(
            keywords=self.config.strategy.news_keywords,
            max_items=self.config.strategy.max_news_items,
        )
        message = self.message_builder.build_report(
            price_snapshot=price_snapshot,
            price_change=price_change,
            indicator_summaries=indicator_summaries,
            news=news,
        )
        LOGGER.info("Sending Telegram notification")
        self.notifier.send_message(message)
        return PipelineResult(
            message=message,
            price_snapshot=price_snapshot,
            indicator_summaries=tuple(indicator_summaries),
            news=tuple(news),
        )

    def schedule(self, *, scheduler) -> None:
        """Run the pipeline using a scheduler object with an ``every`` interface."""

        interval_seconds = self.config.scheduler.interval_seconds
        LOGGER.info("Scheduling pipeline every %s seconds", interval_seconds)
        job = scheduler.every(interval_seconds).seconds

        def _job() -> None:
            try:
                self.run_once()
            except Exception as exc:  # pragma: no cover - scheduler integration
                LOGGER.exception("Pipeline execution failed: %s", exc)

        job.do(_job)
        if self.config.scheduler.run_once:
            LOGGER.info("Running once as requested by configuration")
            _job()
        else:
            LOGGER.info("Entering scheduler loop")
            while True:
                scheduler.run_pending()
                time.sleep(1)

