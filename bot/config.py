"""Configuration loading utilities for the gold insights bot."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional


@dataclass
class DataProviderConfig:
    """Configuration options for external market and news providers."""

    gold_price_provider: str
    gold_price_options: Dict[str, Any] = field(default_factory=dict)
    news_provider: str = ""
    news_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """Parameters that drive signal generation and reporting."""

    lookback_minutes: int = 240
    fast_ma_period: int = 20
    slow_ma_period: int = 60
    rsi_period: int = 14
    atr_period: int = 14
    news_keywords: List[str] = field(default_factory=lambda: ["gold", "xau", "usd"])
    max_news_items: int = 5


@dataclass
class TelegramConfig:
    """Telegram bot related configuration."""

    bot_token: str
    chat_id: str
    thread_id: Optional[int] = None


@dataclass
class SchedulerConfig:
    """Runtime options for the pipeline scheduler."""

    interval_seconds: int = 900
    run_once: bool = False


@dataclass
class BotConfig:
    """Top level configuration."""

    data: DataProviderConfig
    strategy: StrategyConfig
    telegram: TelegramConfig
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)


class ConfigError(RuntimeError):
    """Raised when the configuration cannot be loaded."""


def _coerce_bool(value: str) -> bool:
    """Parse a boolean from an environment variable string."""

    value_lower = value.strip().lower()
    if value_lower in {"1", "true", "yes", "on"}:
        return True
    if value_lower in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"Invalid boolean value: {value}")


def _load_from_mapping(mapping: Mapping[str, Any]) -> BotConfig:
    """Construct a :class:`BotConfig` from a nested mapping."""

    try:
        data_mapping = mapping["data"]
        strategy_mapping = mapping.get("strategy", {})
        telegram_mapping = mapping["telegram"]
        scheduler_mapping = mapping.get("scheduler", {})
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise ConfigError(f"Missing configuration section: {exc.args[0]}") from exc

    data_config = DataProviderConfig(
        gold_price_provider=data_mapping["gold_price_provider"],
        gold_price_options=dict(data_mapping.get("gold_price_options", {})),
        news_provider=data_mapping.get("news_provider", ""),
        news_options=dict(data_mapping.get("news_options", {})),
    )

    strategy_config = StrategyConfig(
        lookback_minutes=int(strategy_mapping.get("lookback_minutes", StrategyConfig.lookback_minutes)),
        fast_ma_period=int(strategy_mapping.get("fast_ma_period", StrategyConfig.fast_ma_period)),
        slow_ma_period=int(strategy_mapping.get("slow_ma_period", StrategyConfig.slow_ma_period)),
        rsi_period=int(strategy_mapping.get("rsi_period", StrategyConfig.rsi_period)),
        atr_period=int(strategy_mapping.get("atr_period", StrategyConfig.atr_period)),
        news_keywords=list(strategy_mapping.get("news_keywords", StrategyConfig().news_keywords)),
        max_news_items=int(strategy_mapping.get("max_news_items", StrategyConfig.max_news_items)),
    )

    telegram_config = TelegramConfig(
        bot_token=str(telegram_mapping["bot_token"]),
        chat_id=str(telegram_mapping["chat_id"]),
        thread_id=(
            int(telegram_mapping["thread_id"])
            if telegram_mapping.get("thread_id") is not None
            else None
        ),
    )

    scheduler_config = SchedulerConfig(
        interval_seconds=int(scheduler_mapping.get("interval_seconds", SchedulerConfig.interval_seconds)),
        run_once=bool(scheduler_mapping.get("run_once", SchedulerConfig.run_once)),
    )

    return BotConfig(
        data=data_config,
        strategy=strategy_config,
        telegram=telegram_config,
        scheduler=scheduler_config,
    )


def _load_json_config(path: Path) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in configuration file {path}: {exc}") from exc


def _load_from_env(prefix: str = "BOT_") -> Mapping[str, Any]:
    """Load configuration from environment variables.

    The environment variables use the following structure::

        BOT_DATA_GOLD_PRICE_PROVIDER=alpha_vantage
        BOT_DATA_GOLD_PRICE_OPTIONS={"api_key": "..."}
        BOT_STRATEGY_LOOKBACK_MINUTES=120

    Nested dictionaries are provided as JSON strings to keep the format simple.
    """

    def _pop_json(mapping: MutableMapping[str, str], key: str, default: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        raw_value = mapping.pop(key, None)
        if raw_value is None:
            return dict(default or {})
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON for {key}: {exc}") from exc

    env: Dict[str, str] = {
        key[len(prefix) :]: value
        for key, value in os.environ.items()
        if key.startswith(prefix)
    }

    if not env:
        raise ConfigError("Environment variables with prefix BOT_ were not found.")

    data_section: Dict[str, Any] = {}
    if "DATA_GOLD_PRICE_PROVIDER" in env:
        data_section["gold_price_provider"] = env.pop("DATA_GOLD_PRICE_PROVIDER")
    else:
        raise ConfigError("BOT_DATA_GOLD_PRICE_PROVIDER is required")
    data_section["gold_price_options"] = _pop_json(env, "DATA_GOLD_PRICE_OPTIONS")

    news_provider = env.pop("DATA_NEWS_PROVIDER", "")
    if news_provider:
        data_section["news_provider"] = news_provider
    data_section["news_options"] = _pop_json(env, "DATA_NEWS_OPTIONS")

    strategy_section: Dict[str, Any] = {}
    for option in ("LOOKBACK_MINUTES", "FAST_MA_PERIOD", "SLOW_MA_PERIOD", "RSI_PERIOD", "ATR_PERIOD", "MAX_NEWS_ITEMS"):
        key = f"STRATEGY_{option}"
        if key in env:
            strategy_section[option.lower()] = int(env.pop(key))

    if "STRATEGY_NEWS_KEYWORDS" in env:
        keywords = json.loads(env.pop("STRATEGY_NEWS_KEYWORDS"))
        if not isinstance(keywords, list):  # pragma: no cover - sanity guard
            raise ConfigError("STRATEGY_NEWS_KEYWORDS must be a JSON list")
        strategy_section["news_keywords"] = [str(keyword) for keyword in keywords]

    telegram_section = {
        "bot_token": env.pop("TELEGRAM_BOT_TOKEN"),
        "chat_id": env.pop("TELEGRAM_CHAT_ID"),
    }
    thread = env.pop("TELEGRAM_THREAD_ID", None)
    if thread is not None:
        telegram_section["thread_id"] = int(thread)

    scheduler_section: Dict[str, Any] = {}
    if "SCHEDULER_INTERVAL_SECONDS" in env:
        scheduler_section["interval_seconds"] = int(env.pop("SCHEDULER_INTERVAL_SECONDS"))
    if "SCHEDULER_RUN_ONCE" in env:
        scheduler_section["run_once"] = _coerce_bool(env.pop("SCHEDULER_RUN_ONCE"))

    if env:
        unknown = ", ".join(sorted(env))
        raise ConfigError(f"Unsupported configuration keys: {unknown}")

    return {
        "data": data_section,
        "strategy": strategy_section,
        "telegram": telegram_section,
        "scheduler": scheduler_section,
    }


def load_config(config_path: Optional[Path] = None, *, env_prefix: str = "BOT_") -> BotConfig:
    """Load a :class:`BotConfig` from a JSON file or environment variables."""

    if config_path is not None:
        mapping = _load_json_config(config_path)
    else:
        mapping = _load_from_env(env_prefix)

    return _load_from_mapping(mapping)


def dump_config_example(path: Path, *, keywords: Optional[Iterable[str]] = None) -> None:
    """Write an example configuration to *path*."""

    example = {
        "data": {
            "gold_price_provider": "alpha_vantage",
            "gold_price_options": {"api_key": "YOUR_ALPHA_VANTAGE_KEY"},
            "news_provider": "news_api",
            "news_options": {
                "api_key": "YOUR_NEWS_API_KEY",
                "language": "de",
            },
        },
        "strategy": {
            "lookback_minutes": 240,
            "fast_ma_period": 20,
            "slow_ma_period": 60,
            "rsi_period": 14,
            "atr_period": 14,
            "news_keywords": list(keywords or ["gold", "xau", "usd"]),
            "max_news_items": 5,
        },
        "telegram": {
            "bot_token": "123456:ABCDEF",
            "chat_id": "-1001234567890",
        },
        "scheduler": {
            "interval_seconds": 900,
            "run_once": False,
        },
    }
    path.write_text(json.dumps(example, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Konfigurationswerkzeuge für den Gold-Bot")
    parser.add_argument(
        "--dump-config",
        type=Path,
        help="Pfad für eine Beispielkonfiguration im JSON-Format",
    )
    parser.add_argument(
        "--env-prefix",
        default="BOT_",
        help="Präfix für Umgebungsvariablen beim Laden der Konfiguration",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Geladene Konfiguration auf STDOUT ausgeben",
    )
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        help="Pfad zu einer bestehenden Konfiguration",
    )
    return parser.parse_args()


def _main() -> int:
    args = _parse_args()
    if args.dump_config:
        dump_config_example(args.dump_config)
        print(f"Beispielkonfiguration gespeichert in {args.dump_config}")
        return 0
    config_path: Optional[Path] = args.config
    try:
        config = load_config(config_path, env_prefix=args.env_prefix)
    except ConfigError as exc:
        print(f"Fehler beim Laden der Konfiguration: {exc}")
        return 1
    if args.print:
        print(config)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI utility
    raise SystemExit(_main())

