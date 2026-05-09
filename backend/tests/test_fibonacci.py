"""
test_fibonacci.py
=================
Tests para el módulo de Fibonacci.
Ejecutar con: pytest tests/test_fibonacci.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fibonacci import calculate_fibonacci, FIBO_NAMES


def make_trending_hist(n=100, low=100.0, high=200.0):
    """Crea un DataFrame con tendencia clara de low a high."""
    dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
    prices = [low + (high - low) * i / (n - 1) for i in range(n)]
    return pd.DataFrame({
        "Open":   [p * 0.998 for p in prices],
        "High":   [p * 1.010 for p in prices],
        "Low":    [p * 0.990 for p in prices],
        "Close":  prices,
        "Volume": [1_000_000] * n,
    }, index=dates)


def make_small_hist(n=5):
    dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
    return pd.DataFrame({
        "Open": [100] * n, "High": [105] * n,
        "Low":  [95]  * n, "Close": [100] * n,
        "Volume": [1000] * n,
    }, index=dates)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_returns_all_fibo_names():
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    for name in FIBO_NAMES:
        assert name in result["levels"], f"Falta nivel: {name}"


def test_swing_high_above_swing_low():
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    assert result["swing_high"] > result["swing_low"]


def test_retracement_levels_in_range():
    """Los niveles 0%-100% deben estar entre swing_low y swing_high."""
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    lo = result["swing_low"]
    hi = result["swing_high"]
    for name in ["23.6%", "38.2%", "50%", "61.8%", "78.6%"]:
        lvl = result["levels"][name]
        assert lo <= lvl <= hi, f"Nivel {name}={lvl} fuera de rango [{lo}, {hi}]"


def test_insufficient_data_returns_error():
    hist = make_small_hist(5)
    result = calculate_fibonacci(hist)
    assert "error" in result


def test_current_price_present():
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    assert "current_price" in result
    assert result["current_price"] > 0


def test_nearest_support_below_price():
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    supp = result["nearest_support"]
    if supp["price"] is not None:
        assert supp["price"] <= result["current_price"]


def test_nearest_resistance_above_price():
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    res = result["nearest_resistance"]
    if res["price"] is not None:
        assert res["price"] >= result["current_price"]


def test_interpretation_is_string():
    hist = make_trending_hist()
    result = calculate_fibonacci(hist)
    assert isinstance(result["interpretation"], str)
    assert len(result["interpretation"]) > 10
