"""Command-line entry point for the gold insight bot."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from bot import GoldInsightPipeline, load_config
from bot.config import ConfigError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Goldmarkt-Telegram-Bot")
    parser.add_argument(
        "--config",
        type=Path,
        help="Pfad zu einer JSON-Konfigurationsdatei. Wenn nicht angegeben, werden Umgebungsvariablen verwendet.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging-Level",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        logging.getLogger(__name__).error("Konfiguration konnte nicht geladen werden: %s", exc)
        return 1
    pipeline = GoldInsightPipeline(config)
    if config.scheduler.run_once:
        pipeline.run_once()
    else:
        try:
            import schedule
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            logging.getLogger(__name__).error(
                "Das schedule-Paket ist erforderlich für wiederkehrende Ausführungen: %s",
                exc,
            )
            return 2
        pipeline.schedule(scheduler=schedule)
    return 0


if __name__ == "__main__":
    sys.exit(main())

