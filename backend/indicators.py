"""
indicators.py
=============
Calcula todos los indicadores técnicos sobre los datos históricos de precio.

Librería usada: 'ta' (Technical Analysis Library for Python)
  pip install ta

Indicadores incluidos:
  - SMA 20, 50, 200   (Simple Moving Average)
  - EMA 20            (Exponential Moving Average)
  - RSI 14            (Relative Strength Index)
  - MACD              (Moving Average Convergence Divergence)
  - ATR 14            (Average True Range)
  - Volatilidad anualizada
  - Drawdown máximo
  - Retornos 1M / 3M / 6M / 12M
  - Volumen promedio 20 días
  - Distancia precio vs SMA 200
  - Tendencia general: bullish / neutral / bearish
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import ta


def calculate_indicators(hist: pd.DataFrame, interval: str = "1d") -> Dict[str, Any]:
    """
    Calcula todos los indicadores técnicos sobre el DataFrame de precios.

    Args:
        hist: DataFrame con columnas Open, High, Low, Close, Volume

    Returns:
        Diccionario con todos los indicadores y series para el gráfico SVG

    Raises:
        ValueError: si hay menos de 20 velas (datos insuficientes)
    """
    if len(hist) < 20:
        raise ValueError(
            f"Datos insuficientes: solo {len(hist)} velas disponibles. "
            "Necesito al menos 20 para calcular indicadores. "
            "Prueba con un periodo más largo o un intervalo más corto."
        )

    close: pd.Series = hist["Close"].astype(float)
    high: pd.Series = hist["High"].astype(float)
    low: pd.Series = hist["Low"].astype(float)
    volume: pd.Series = hist.get("Volume", pd.Series(dtype=float)).astype(float)

    # -------------------------------------------------------------------------
    # Medias móviles simples
    # -------------------------------------------------------------------------
    sma_20 = ta.trend.SMAIndicator(close, window=20).sma_indicator()
    sma_50 = (
        ta.trend.SMAIndicator(close, window=50).sma_indicator()
        if len(hist) >= 50
        else pd.Series([np.nan] * len(hist), index=hist.index)
    )
    sma_200 = (
        ta.trend.SMAIndicator(close, window=200).sma_indicator()
        if len(hist) >= 200
        else pd.Series([np.nan] * len(hist), index=hist.index)
    )

    # Media móvil exponencial
    ema_20 = ta.trend.EMAIndicator(close, window=20).ema_indicator()

    # -------------------------------------------------------------------------
    # RSI
    # -------------------------------------------------------------------------
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()

    # -------------------------------------------------------------------------
    # MACD
    # -------------------------------------------------------------------------
    macd_obj = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_obj.macd()
    macd_signal = macd_obj.macd_signal()
    macd_hist = macd_obj.macd_diff()

    # -------------------------------------------------------------------------
    # ATR (Average True Range)
    # -------------------------------------------------------------------------
    atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()

    # -------------------------------------------------------------------------
    # Precio actual
    # -------------------------------------------------------------------------
    current_price = float(close.iloc[-1])

    # -------------------------------------------------------------------------
    # Factor de anualización según el intervalo de tiempo
    # Velas por año: 1d=252, 1wk=52, 1mo=12, 1h=252*6.5, 15m=252*6.5*4, 4h=252*6.5/4
    # -------------------------------------------------------------------------
    bars_per_year = {
        "15m": 252 * 26,   # ~6.5 horas × 4 velas/hora × 252 días
        "1h":  252 * 7,    # ~6.5 horas/día ≈ 7 velas × 252 días
        "4h":  252 * 2,    # ~2 velas de 4h por día × 252 días
        "1d":  252,
        "1wk": 52,
        "1mo": 12,
    }.get(interval, 252)

    # -------------------------------------------------------------------------
    # Volatilidad anualizada
    # -------------------------------------------------------------------------
    daily_returns = close.pct_change().dropna()
    annual_vol = float(daily_returns.std() * np.sqrt(bars_per_year) * 100)  # en %

    # -------------------------------------------------------------------------
    # Drawdown máximo
    # -------------------------------------------------------------------------
    cum_returns = (1 + daily_returns).cumprod()
    rolling_peak = cum_returns.expanding().max()
    drawdown_series = (cum_returns - rolling_peak) / rolling_peak
    max_drawdown = float(drawdown_series.min() * 100)  # en %, negativo

    # -------------------------------------------------------------------------
    # Retornos por periodo (en número de velas según intervalo)
    # -------------------------------------------------------------------------
    bars_1m  = {"15m": 4*26*21, "1h": 7*21, "4h": 2*21, "1d": 21,  "1wk": 4,  "1mo": 1 }.get(interval, 21)
    bars_3m  = {"15m": 4*26*63, "1h": 7*63, "4h": 2*63, "1d": 63,  "1wk": 13, "1mo": 3 }.get(interval, 63)
    bars_6m  = {"15m": 4*26*126,"1h": 7*126,"4h": 2*126,"1d": 126, "1wk": 26, "1mo": 6 }.get(interval, 126)
    bars_12m = {"15m": 4*26*252,"1h": 7*252,"4h": 2*252,"1d": 252, "1wk": 52, "1mo": 12}.get(interval, 252)

    def period_return(n_bars: int) -> Optional[float]:
        if len(close) > n_bars:
            return float((close.iloc[-1] / close.iloc[-n_bars] - 1) * 100)
        return None

    return_1m  = period_return(bars_1m)
    return_3m  = period_return(bars_3m)
    return_6m  = period_return(bars_6m)
    return_12m = period_return(bars_12m)

    # -------------------------------------------------------------------------
    # Volumen promedio 20 días
    # -------------------------------------------------------------------------
    avg_vol_20 = float(volume.tail(20).mean()) if not volume.empty and volume.sum() > 0 else None

    # -------------------------------------------------------------------------
    # Distancia del precio actual vs SMA 200
    # -------------------------------------------------------------------------
    sma200_clean = sma_200.dropna()
    dist_sma200 = None
    if not sma200_clean.empty:
        s200 = float(sma200_clean.iloc[-1])
        dist_sma200 = float((current_price / s200 - 1) * 100)

    # -------------------------------------------------------------------------
    # Tendencia general
    # -------------------------------------------------------------------------
    trend = _determine_trend(close, sma_20, sma_50, sma_200)

    # -------------------------------------------------------------------------
    # Gap reciente y anomalía de volumen
    # -------------------------------------------------------------------------
    recent_gap = _detect_gap(hist)
    volume_anomaly = _detect_volume_anomaly(volume)

    # -------------------------------------------------------------------------
    # Cambio diario
    # -------------------------------------------------------------------------
    price_change = float(close.iloc[-1] - close.iloc[-2]) if len(close) >= 2 else 0.0
    price_change_pct = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) >= 2 else 0.0

    return {
        # Precio
        "current_price": current_price,
        "price_change": price_change,
        "price_change_pct": price_change_pct,

        # Medias móviles (último valor)
        "sma_20": _last(sma_20),
        "sma_50": _last(sma_50),
        "sma_200": _last(sma_200),
        "ema_20": _last(ema_20),

        # RSI
        "rsi": _last(rsi),
        "rsi_signal": _interpret_rsi(_last(rsi)),

        # MACD
        "macd": _last(macd_line),
        "macd_signal_line": _last(macd_signal),
        "macd_histogram": _last(macd_hist),
        "macd_bullish": (_last(macd_hist) or 0) > 0,

        # ATR
        "atr": _last(atr),

        # Volatilidad y drawdown
        "annual_volatility": annual_vol,
        "max_drawdown": max_drawdown,

        # Retornos
        "return_1m": return_1m,
        "return_3m": return_3m,
        "return_6m": return_6m,
        "return_12m": return_12m,

        # Volumen
        "avg_volume_20d": avg_vol_20,

        # SMA 200
        "dist_sma200_pct": dist_sma200,

        # Tendencia
        "trend": trend,

        # Eventos
        "recent_gap": recent_gap,
        "volume_anomaly": volume_anomaly,

        # Series completas para el gráfico SVG
        "price_series": _to_list(close),
        "sma_20_series": _to_list(sma_20),
        "sma_50_series": _to_list(sma_50),
        "sma_200_series": _to_list(sma_200),
        "dates_series": [str(d.date()) for d in hist.index],
        "volume_series": _to_list(volume),
        "rsi_series": _to_list(rsi),
        "macd_series": _to_list(macd_line),
        "macd_signal_series": _to_list(macd_signal),
        "macd_hist_series": _to_list(macd_hist),
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _last(series: pd.Series) -> Optional[float]:
    """Devuelve el último valor no-NaN de una serie, o None."""
    clean = series.dropna()
    return float(clean.iloc[-1]) if not clean.empty else None


def _to_list(series: pd.Series) -> list:
    """Convierte una Serie pandas a lista de floats, None donde hay NaN."""
    return [float(v) if pd.notna(v) else None for v in series]


def _determine_trend(
    close: pd.Series,
    sma_20: pd.Series,
    sma_50: pd.Series,
    sma_200: pd.Series,
) -> str:
    """
    Determina la tendencia general comparando el precio con las medias móviles.
    Lógica: cuántas medias móviles están por debajo del precio actual.
    SMA 200 tiene el doble de peso que SMA 20 y SMA 50.
    """
    price = float(close.iloc[-1])
    bullish = 0
    total = 0

    for sma, weight in [(sma_20, 1), (sma_50, 1), (sma_200, 2)]:
        val = _last(sma)
        if val is not None:
            total += weight
            if price > val:
                bullish += weight

    if total == 0:
        return "neutral"

    ratio = bullish / total
    if ratio >= 0.75:
        return "bullish"
    if ratio <= 0.25:
        return "bearish"
    return "neutral"


def _interpret_rsi(rsi_val: Optional[float]) -> str:
    """Interpreta el valor del RSI en texto simple."""
    if rsi_val is None:
        return "unknown"
    if rsi_val >= 80:
        return "extreme_overbought"
    if rsi_val >= 70:
        return "overbought"
    if rsi_val <= 20:
        return "extreme_oversold"
    if rsi_val <= 30:
        return "oversold"
    if rsi_val >= 55:
        return "bullish"
    if rsi_val <= 45:
        return "bearish"
    return "neutral"


def _detect_gap(hist: pd.DataFrame) -> dict:
    """Detecta si hubo un gap de precio ≥2% en los últimos 5 días."""
    if len(hist) < 2:
        return {"detected": False}

    recent = hist.tail(5)
    for i in range(1, len(recent)):
        prev_close = float(recent["Close"].iloc[i - 1])
        curr_open = float(recent["Open"].iloc[i])
        if prev_close == 0:
            continue
        gap_pct = abs(curr_open - prev_close) / prev_close * 100
        if gap_pct >= 2.0:
            direction = "up" if curr_open > prev_close else "down"
            return {
                "detected": True,
                "gap_pct": round(gap_pct, 2),
                "direction": direction,
                "date": str(recent.index[i].date()),
            }

    return {"detected": False}


def _detect_volume_anomaly(volume: pd.Series) -> dict:
    """Detecta si el volumen del último día es ≥2× el promedio de 20 días."""
    if len(volume) < 20 or volume.sum() == 0:
        return {"detected": False}

    avg = float(volume.tail(20).mean())
    last = float(volume.iloc[-1])

    if avg == 0:
        return {"detected": False}

    ratio = last / avg
    if ratio >= 2.0:
        return {
            "detected": True,
            "ratio": round(ratio, 2),
            "message": f"Volumen {ratio:.1f}× superior al promedio de 20 días",
        }

    return {"detected": False}
