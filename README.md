# Gold Insights Telegram Bot

Ein Bot, der aktuelle Goldmarktinformationen sammelt, technische Indikatoren berechnet und die Ergebnisse als Nachricht in Telegram veröffentlicht. Der Bot führt **keine Trades** aus, sondern dient ausschließlich der Informationsweitergabe.

## Features

- Abruf von Goldpreisdaten (Standard: Alpha Vantage FX API)
- Abruf relevanter Nachrichten (NewsAPI oder Dummy-Quelle)
- Berechnung zentraler technischer Indikatoren (SMA, EMA, RSI, ATR, Bollinger Bänder)
- Zusammenfassung der Ergebnisse in einer strukturierten Telegram-Nachricht
- Konfigurierbare Ausführung per Scheduler oder einmalige Benachrichtigung

## Projektstruktur

```
.
├── bot
│   ├── config.py          # Konfigurationslogik (JSON/Umgebungsvariablen)
│   ├── data_providers.py  # Schnittstellen zu Preis- und Nachrichtenquellen
│   ├── indicators.py      # Technische Indikatoren und Zusammenfassungen
│   ├── messaging.py       # Erstellung und Versand von Telegram-Nachrichten
│   └── pipeline.py        # Orchestrierung der Datenpipeline
├── run_bot.py             # Kommandozeilen-Einstiegspunkt
├── requirements.txt       # Python-Abhängigkeiten
└── tests                  # Pytest-basiertes Testset
```

## Installation

1. Python 3.11+ vorbereiten (z. B. via `pyenv` oder System-Python).
2. Repository klonen und Abhängigkeiten installieren:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(Die Scheduler-Funktionalität nutzt das `schedule`-Paket. Für wiederkehrende Ausführungen muss dieses installiert sein.)

## Konfiguration

### JSON-Datei

```json
{
  "data": {
    "gold_price_provider": "alpha_vantage",
    "gold_price_options": {"api_key": "YOUR_ALPHA_VANTAGE_KEY"},
    "news_provider": "news_api",
    "news_options": {
      "api_key": "YOUR_NEWS_API_KEY",
      "language": "de"
    }
  },
  "strategy": {
    "lookback_minutes": 240,
    "fast_ma_period": 20,
    "slow_ma_period": 60,
    "rsi_period": 14,
    "atr_period": 14,
    "news_keywords": ["gold", "xau", "usd"],
    "max_news_items": 5
  },
  "telegram": {
    "bot_token": "123456:ABCDEF",
    "chat_id": "-1001234567890"
  },
  "scheduler": {
    "interval_seconds": 900,
    "run_once": false
  }
}
```

Alternativ kann mit `python -m bot.config --dump-config example.json` eine Beispielkonfiguration erzeugt werden (siehe `dump_config_example`).

### Umgebungsvariablen

Wenn keine `--config`-Datei angegeben wird, lädt der Bot Einstellungen aus Umgebungsvariablen mit Präfix `BOT_`. Beispiel:

```bash
export BOT_DATA_GOLD_PRICE_PROVIDER=alpha_vantage
export BOT_DATA_GOLD_PRICE_OPTIONS='{"api_key": "YOUR_ALPHA_VANTAGE_KEY"}'
export BOT_DATA_NEWS_PROVIDER=news_api
export BOT_DATA_NEWS_OPTIONS='{"api_key": "YOUR_NEWS_API_KEY", "language": "de"}'
export BOT_TELEGRAM_BOT_TOKEN=123456:ABCDEF
export BOT_TELEGRAM_CHAT_ID=-1001234567890
export BOT_SCHEDULER_RUN_ONCE=true
```

## Nutzung

### Einmalige Ausführung

```bash
python run_bot.py --config config.json --log-level INFO
```

### Wiederholte Ausführung

In der Konfiguration `"run_once": false` setzen und das `schedule`-Paket installieren. Danach wird der Bot in einer Schleife ausgeführt und versendet regelmäßig Telegram-Nachrichten.

## Tests

```bash
pytest
```

## Sicherheit & Betrieb

- API-Schlüssel nicht im Code ablegen. Stattdessen Umgebungsvariablen oder Secret-Management verwenden.
- Logging auf Dateisystem oder Monitoring-System weiterleiten.
- Der Bot führt **keine** Orders aus. Wer Handel ausführen möchte, muss eine getrennte Order-Engine implementieren.

