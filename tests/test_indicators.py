import math

import pytest

from bot import indicators


def test_simple_moving_average_basic():
    values = [1, 2, 3, 4, 5]
    assert indicators.simple_moving_average(values, 3) == pytest.approx(4)


def test_exponential_moving_average_matches_manual():
    values = [10, 11, 12, 13, 14, 15]
    ema = indicators.exponential_moving_average(values, 3)
    # Manual calculation for period 3
    sma = sum(values[:3]) / 3
    multiplier = 2 / (3 + 1)
    ema_manual = sma
    for price in values[3:]:
        ema_manual = (price - ema_manual) * multiplier + ema_manual
    assert ema == pytest.approx(ema_manual)


def test_relative_strength_index_extreme():
    values = [1, 2, 3, 4, 5, 6, 7]
    rsi = indicators.relative_strength_index(values, period=3)
    assert rsi == pytest.approx(100.0)


def test_average_true_range_basic():
    highs = [10, 12, 11, 13]
    lows = [8, 9, 10, 11]
    closes = [9, 11, 10.5, 12]
    atr = indicators.average_true_range(highs, lows, closes, period=2)
    assert atr == pytest.approx(2.25)


def test_price_rate_of_change():
    values = [100, 105, 110, 115]
    roc = indicators.price_rate_of_change(values, period=2)
    assert roc == pytest.approx((115 - 105) / 105)


def test_bollinger_bands_symmetry():
    values = [100 + math.sin(i) for i in range(20)]
    lower, mid, upper = indicators.bollinger_bands(values, period=20)
    assert mid == pytest.approx(sum(values) / 20)
    assert upper - mid == pytest.approx(mid - lower)


def test_summarize_indicators_includes_rsi_and_roc():
    values = [float(i) for i in range(1, 30)]
    summaries = indicators.summarize_indicators(values, [5, 10])
    assert any("RSI" in summary for summary in summaries)
    assert any("RoC" in summary for summary in summaries)

