"""
test_risk_score.py
==================
Tests para el módulo de risk score.
Ejecutar con: pytest tests/test_risk_score.py -v
"""

import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk_score import calculate_risk_score, _risk_label, _risk_color


def make_ind(trend="bullish", rsi=50.0, vol=20.0, dd=-10.0, macd_ok=True, ret1m=2.0):
    return {
        "trend": trend,
        "rsi": rsi,
        "macd_bullish": macd_ok,
        "macd_histogram": 0.5 if macd_ok else -0.5,
        "annual_volatility": vol,
        "max_drawdown": dd,
        "return_1m": ret1m,
        "return_3m": 5.0,
        "return_6m": 8.0,
        "dist_sma200_pct": 10.0,
        "recent_gap": {"detected": False},
        "volume_anomaly": {"detected": False},
    }


# ---------------------------------------------------------------------------
# Tests de calculate_risk_score
# ---------------------------------------------------------------------------

def test_total_in_range():
    result = calculate_risk_score(make_ind(), {}, "stock")
    assert 0 <= result["total"] <= 100


def test_has_all_breakdown_keys():
    result = calculate_risk_score(make_ind(), {}, "stock")
    assert "technical" in result
    assert "financial" in result
    assert "momentum_events" in result
    assert "total" in result
    assert "label" in result
    assert "risk_color" in result


def test_bearish_higher_than_bullish():
    bullish = calculate_risk_score(make_ind(trend="bullish"), {}, "stock")
    bearish = calculate_risk_score(make_ind(trend="bearish"), {}, "stock")
    assert bearish["total"] > bullish["total"]


def test_high_volatility_raises_score():
    low_vol  = calculate_risk_score(make_ind(vol=10),  {}, "stock")
    high_vol = calculate_risk_score(make_ind(vol=100), {}, "stock")
    assert high_vol["total"] > low_vol["total"]


def test_crypto_no_fundamentals():
    result = calculate_risk_score(make_ind(vol=80), {}, "crypto")
    assert result["financial"]["available"] == False
    assert 0 <= result["total"] <= 100


def test_commodity_no_fundamentals():
    result = calculate_risk_score(make_ind(), {}, "commodity")
    assert result["financial"]["available"] == False


def test_overbought_rsi_raises_score():
    normal = calculate_risk_score(make_ind(rsi=50), {}, "stock")
    overbought = calculate_risk_score(make_ind(rsi=82), {}, "stock")
    assert overbought["total"] > normal["total"]


def test_severe_drawdown_raises_score():
    mild   = calculate_risk_score(make_ind(dd=-5),  {}, "stock")
    severe = calculate_risk_score(make_ind(dd=-55), {}, "stock")
    assert severe["total"] > mild["total"]


# ---------------------------------------------------------------------------
# Tests de _risk_label
# ---------------------------------------------------------------------------

def test_label_low():    assert _risk_label(20) == "Riesgo Bajo"
def test_label_medium(): assert _risk_label(50) == "Riesgo Medio"
def test_label_high():   assert _risk_label(70) == "Riesgo Alto"
def test_label_extreme():assert _risk_label(90) == "Riesgo Extremo"


# ---------------------------------------------------------------------------
# Tests de _risk_color
# ---------------------------------------------------------------------------

def test_color_green():   assert _risk_color(15) == "#22c55e"
def test_color_amber():   assert _risk_color(45) == "#f59e0b"
def test_color_red():     assert _risk_color(75) == "#ef4444"
def test_color_darkred(): assert _risk_color(90) == "#7f1d1d"
