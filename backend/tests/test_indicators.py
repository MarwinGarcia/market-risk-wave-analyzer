"""
test_indicators.py
==================
Tests para el módulo de indicadores técnicos.
Ejecutar con: pytest tests/test_indicators.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators import calculate_indicators, _interpret_rsi, _determine_trend


# ---------------------------------------------------------------------------
# Fixture: crear DataFrames de prueba
# ---------------------------------------------------------------------------

def make_hist(n=250, start=100.0, direction="up"):
    """Crea un DataFrame de precios de prueba."""
    dates = pd.date_range(end=datetime.now(), periods=n, freq="B")  # días hábiles
    np.random.seed(42)

    if direction == "up":
        prices = [start + i * 0.5 + np.random.normal(0, 0.8) for i in range(n)]
    elif direction == "down":
        prices = [start + 100 - i * 0.5 + np.random.normal(0, 0.8) for i in range(n)]
    else:
        prices = [start + np.random.normal(0, 2) for _ in range(n)]

    prices = [max(1.0, p) for p in prices]

    return pd.DataFrame({
        "Open":   [p * 0.995 for p in prices],
        "High":   [p * 1.015 for p in prices],
        "Low":    [p * 0.985 for p in prices],
        "Close":  prices,
        "Volume": [int(1_000_000 + np.random.randint(0, 500_000)) for _ in range(n)],
    }, index=dates)


# ---------------------------------------------------------------------------
# Tests de calculate_indicators
# ---------------------------------------------------------------------------

def test_returns_all_required_keys():
    """Verifica que el resultado contiene todas las claves esperadas."""
    hist = make_hist(250)
    result = calculate_indicators(hist)

    required = [
        "current_price", "price_change", "price_change_pct",
        "sma_20", "sma_50", "sma_200", "ema_20",
        "rsi", "rsi_signal", "macd", "macd_bullish",
        "annual_volatility", "max_drawdown",
        "return_1m", "return_3m",
        "trend", "price_series", "dates_series",
    ]
    for key in required:
        assert key in result, f"Falta la clave: {key}"


def test_current_price_equals_last_close():
    hist = make_hist(100)
    result = calculate_indicators(hist)
    assert abs(result["current_price"] - hist["Close"].iloc[-1]) < 0.001


def test_annual_volatility_positive():
    hist = make_hist(100)
    result = calculate_indicators(hist)
    assert result["annual_volatility"] > 0


def test_max_drawdown_nonpositive():
    hist = make_hist(100)
    result = calculate_indicators(hist)
    assert result["max_drawdown"] <= 0


def test_price_series_length_matches_hist():
    hist = make_hist(150)
    result = calculate_indicators(hist)
    assert len(result["price_series"]) == len(hist)


def test_dates_series_length_matches_hist():
    hist = make_hist(150)
    result = calculate_indicators(hist)
    assert len(result["dates_series"]) == len(hist)


def test_sma_200_none_when_insufficient_data():
    """SMA 200 debe ser None cuando hay menos de 200 velas."""
    hist = make_hist(50)
    result = calculate_indicators(hist)
    assert result["sma_200"] is None


def test_raises_on_insufficient_data():
    hist = make_hist(10)
    with pytest.raises(ValueError, match="suficientes|insuficiente"):
        calculate_indicators(hist)


def test_uptrend_detected():
    hist = make_hist(250, direction="up")
    result = calculate_indicators(hist)
    # Con 250 velas en tendencia alcista, debe detectar bullish o neutral
    assert result["trend"] in ("bullish", "neutral")


def test_downtrend_detected():
    hist = make_hist(250, direction="down")
    result = calculate_indicators(hist)
    assert result["trend"] in ("bearish", "neutral")


# ---------------------------------------------------------------------------
# Tests de _interpret_rsi
# ---------------------------------------------------------------------------

def test_rsi_overbought():
    assert _interpret_rsi(75) == "overbought"

def test_rsi_extreme_overbought():
    assert _interpret_rsi(82) == "extreme_overbought"

def test_rsi_oversold():
    assert _interpret_rsi(25) == "oversold"

def test_rsi_extreme_oversold():
    assert _interpret_rsi(18) == "extreme_oversold"

def test_rsi_neutral():
    assert _interpret_rsi(50) == "neutral"

def test_rsi_none():
    assert _interpret_rsi(None) == "unknown"
