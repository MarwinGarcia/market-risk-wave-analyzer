"""
fibonacci.py
============
Calcula niveles de retroceso y extensión de Fibonacci.

Proceso:
  1. Detecta el swing high (precio máximo) y swing low (precio mínimo) del periodo
  2. Calcula los 9 niveles de Fibonacci: 0% → 161.8%
  3. Interpreta la posición actual del precio en texto simple

Niveles calculados:
  Retrocesos:  0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
  Extensiones: 127.2%, 161.8%
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# Ratios de Fibonacci y sus nombres
FIBO_RATIOS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
FIBO_NAMES  = ["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%", "127.2%", "161.8%"]


def calculate_fibonacci(hist: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula niveles de Fibonacci para el periodo dado.

    Args:
        hist: DataFrame con columnas High, Low, Close

    Returns:
        Diccionario con swing_high, swing_low, niveles y la interpretación del precio actual
    """
    if len(hist) < 10:
        return {"error": "Datos insuficientes para Fibonacci (mínimo 10 velas)"}

    high_series = hist["High"].astype(float)
    low_series  = hist["Low"].astype(float)
    close       = hist["Close"].astype(float)

    swing_high = float(high_series.max())
    swing_low  = float(low_series.min())
    swing_high_date = str(high_series.idxmax().date())
    swing_low_date  = str(low_series.idxmin().date())

    current_price = float(close.iloc[-1])
    price_range   = swing_high - swing_low

    if price_range == 0:
        return {"error": "El rango de precio es cero — no se pueden calcular niveles"}

    # Determinar si el movimiento dominante es alcista o bajista
    # (si el swing_high viene después del swing_low → tendencia alcista en el periodo)
    idx_high = hist.index.get_loc(high_series.idxmax())
    idx_low  = hist.index.get_loc(low_series.idxmin())
    uptrend  = idx_high > idx_low

    # Calcular niveles
    levels: Dict[str, float] = {}
    for ratio, name in zip(FIBO_RATIOS, FIBO_NAMES):
        if uptrend:
            # Retroceso alcista: 0% = swing_high (soporte arriba), 100% = swing_low
            level = swing_high - price_range * ratio
        else:
            # Retroceso bajista: 0% = swing_low (resistencia abajo), 100% = swing_high
            level = swing_low + price_range * ratio
        levels[name] = round(level, 4)

    # Niveles ordenados de menor a mayor para encontrar soporte/resistencia
    sorted_levels = sorted(levels.items(), key=lambda x: x[1])

    nearest_support    = _find_nearest(current_price, sorted_levels, direction="below")
    nearest_resistance = _find_nearest(current_price, sorted_levels, direction="above")

    interpretation = _interpret_position(current_price, levels, uptrend, sorted_levels)

    return {
        "swing_high": round(swing_high, 4),
        "swing_low":  round(swing_low, 4),
        "swing_high_date": swing_high_date,
        "swing_low_date":  swing_low_date,
        "uptrend":       uptrend,
        "current_price": round(current_price, 4),
        "price_range":   round(price_range, 4),
        "levels":        levels,
        "sorted_levels": [{"name": n, "price": p} for n, p in sorted_levels],
        "nearest_support":    nearest_support,
        "nearest_resistance": nearest_resistance,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _find_nearest(
    price: float,
    sorted_levels: list,
    direction: str,
) -> Dict[str, Any]:
    """Encuentra el nivel de Fibonacci más cercano en la dirección indicada."""
    candidates = []
    for name, lvl in sorted_levels:
        if direction == "below" and lvl < price:
            candidates.append((name, lvl, abs(price - lvl) / price * 100))
        elif direction == "above" and lvl > price:
            candidates.append((name, lvl, abs(lvl - price) / price * 100))

    if not candidates:
        return {"name": "N/A", "price": None, "distance_pct": None}

    best = min(candidates, key=lambda x: x[2])
    return {"name": best[0], "price": best[1], "distance_pct": round(best[2], 2)}


def _interpret_position(
    price: float,
    levels: Dict[str, float],
    uptrend: bool,
    sorted_levels: list,
) -> str:
    """
    Devuelve una interpretación en español del precio actual vs los niveles de Fibonacci.
    Usa lenguaje prudente: 'podría', 'posible', 'zona probable'.
    """
    trend_word = "alcista" if uptrend else "bajista"

    # Determinar entre qué dos niveles está el precio
    below = [(n, p) for n, p in sorted_levels if p <= price]
    above = [(n, p) for n, p in sorted_levels if p > price]

    if not below and above:
        return (
            f"El precio ({price:.2f}) está por debajo de todos los niveles de Fibonacci del periodo. "
            "Posible zona de sobreventa extrema o nuevo mínimo histórico en el rango analizado."
        )

    if below and not above:
        return (
            f"El precio ({price:.2f}) está por encima de todos los niveles de Fibonacci del periodo. "
            "Posible extensión o nuevo máximo en el rango analizado."
        )

    lower_name, lower_price = below[-1]
    upper_name, upper_price = above[0]

    # Mensajes específicos para niveles clave
    key_messages = {
        "61.8%": (
            f"El precio está cerca del nivel 61.8% de Fibonacci — la 'zona áurea'. "
            f"Es uno de los niveles de retroceso más respetados en tendencias {trend_word}s. "
            f"Podría actuar como {'soporte' if uptrend else 'resistencia'} importante."
        ),
        "50%": (
            f"El precio está cerca del nivel 50% de Fibonacci — zona de equilibrio. "
            f"Un {'rebote' if uptrend else 'rechazo'} en este nivel tendría significado técnico relevante."
        ),
        "38.2%": (
            f"El precio está cerca del nivel 38.2% de Fibonacci. "
            f"Retroceso moderado — posible {'soporte' if uptrend else 'resistencia'} en tendencia {trend_word}."
        ),
        "78.6%": (
            f"El precio está cerca del nivel 78.6% de Fibonacci — retroceso profundo. "
            f"Si este nivel no sostiene el precio, es posible que el movimiento previo se invalide."
        ),
        "23.6%": (
            f"El precio está cerca del nivel 23.6% de Fibonacci — retroceso superficial. "
            f"Indica una tendencia {trend_word} fuerte con poca corrección."
        ),
    }

    # Nivel más cercano al precio
    all_close = sorted(
        [(n, p) for n, p in sorted_levels],
        key=lambda x: abs(x[1] - price)
    )
    closest_name = all_close[0][0] if all_close else ""

    if closest_name in key_messages and abs(levels[closest_name] - price) / price < 0.02:
        return key_messages[closest_name]

    return (
        f"El precio ({price:.2f}) se encuentra entre los niveles "
        f"{lower_name} ({lower_price:.2f}) y {upper_name} ({upper_price:.2f}) de Fibonacci. "
        f"Observa la reacción del precio en los niveles más cercanos como posible "
        f"{'soporte' if uptrend else 'resistencia'} en la tendencia {trend_word}."
    )
