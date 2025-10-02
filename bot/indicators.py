"""Technical indicators used for signal generation."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence


def simple_moving_average(values: Sequence[float], period: int) -> float:
    if period <= 0:
        raise ValueError("Period must be positive")
    if len(values) < period:
        raise ValueError("Not enough values for SMA calculation")
    return sum(values[-period:]) / period


def exponential_moving_average(values: Sequence[float], period: int) -> float:
    if period <= 0:
        raise ValueError("Period must be positive")
    if len(values) < period:
        raise ValueError("Not enough values for EMA calculation")
    multiplier = 2 / (period + 1)
    ema = simple_moving_average(values[:period], period)
    for price in values[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def relative_strength_index(values: Sequence[float], period: int = 14) -> float:
    if period <= 0:
        raise ValueError("Period must be positive")
    if len(values) <= period:
        raise ValueError("Not enough values for RSI calculation")

    gains: List[float] = []
    losses: List[float] = []
    for prev, curr in zip(values[-period - 1 : -1], values[-period:]):
        change = curr - prev
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0
    rs = average_gain / average_loss
    return 100 - (100 / (1 + rs))


def average_true_range(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("High, low and close sequences must be the same length")
    if len(highs) <= period:
        raise ValueError("Not enough values for ATR calculation")

    true_ranges: List[float] = []
    for index in range(1, len(highs)):
        high = highs[index]
        low = lows[index]
        prev_close = closes[index - 1]
        true_range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(true_range)
    if len(true_ranges) < period:
        raise ValueError("Not enough values for ATR calculation")
    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = ((atr * (period - 1)) + tr) / period
    return atr


def price_rate_of_change(values: Sequence[float], period: int = 12) -> float:
    if period <= 0:
        raise ValueError("Period must be positive")
    if len(values) <= period:
        raise ValueError("Not enough values for ROC calculation")
    previous_value = values[-period - 1]
    if previous_value == 0:
        raise ValueError("Cannot compute ROC when previous value is zero")
    return (values[-1] - previous_value) / previous_value


def bollinger_bands(values: Sequence[float], period: int = 20, num_std_dev: float = 2.0) -> Sequence[float]:
    if period <= 1:
        raise ValueError("Period must be greater than one")
    if len(values) < period:
        raise ValueError("Not enough values for Bollinger Bands")
    subset = values[-period:]
    mean = sum(subset) / period
    variance = sum((price - mean) ** 2 for price in subset) / period
    std_dev = math.sqrt(variance)
    return mean - num_std_dev * std_dev, mean, mean + num_std_dev * std_dev


def summarize_indicators(values: Sequence[float], strategy_periods: Iterable[int]) -> List[str]:
    """Generate human-readable indicator summaries."""

    summaries: List[str] = []
    for period in strategy_periods:
        try:
            sma = simple_moving_average(values, period)
            ema = exponential_moving_average(values, period)
        except ValueError:
            continue
        current = values[-1]
        trend = "bullish" if current > ema else "bearish" if current < ema else "neutral"
        summaries.append(
            f"{period}-Period SMA: {sma:.2f}, EMA: {ema:.2f} (Trend: {trend})"
        )
    try:
        rsi = relative_strength_index(values, min(14, len(values) - 1))
        summaries.append(f"RSI: {rsi:.1f}")
    except ValueError:
        pass
    try:
        roc = price_rate_of_change(values, min(12, len(values) - 1))
        summaries.append(f"RoC: {roc * 100:.2f}%")
    except ValueError:
        pass
    return summaries

