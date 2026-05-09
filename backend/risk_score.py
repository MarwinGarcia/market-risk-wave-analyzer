"""
risk_score.py
=============
Calcula el risk score del activo en una escala de 0 a 100.

Composición del score:
  35% → Riesgo técnico      (tendencia, RSI, MACD, volatilidad, drawdown)
  35% → Riesgo financiero   (fundamentales: deuda, márgenes, crecimiento)
  30% → Riesgo momentum     (retornos recientes, gaps, volumen anormal)

Para activos sin fundamentales (crypto, commodities, ETFs, forex):
  El peso financiero (35%) se redistribuye:
    50% técnico + 50% momentum

Interpretación del score total:
   0 -  30  → Riesgo Bajo     (verde)
  31 -  60  → Riesgo Medio    (ámbar)
  61 -  80  → Riesgo Alto     (rojo)
  81 - 100  → Riesgo Extremo  (rojo oscuro)
"""

from typing import Dict, Any, Optional, Tuple


def calculate_risk_score(
    indicators: Dict[str, Any],
    fundamentals: Dict[str, Any],
    asset_type: str,
) -> Dict[str, Any]:
    """
    Calcula el risk score total del activo.

    Args:
        indicators:  resultado de indicators.calculate_indicators()
        fundamentals: datos fundamentales de data_provider._extract_fundamentals()
        asset_type:  "stock" | "etf" | "crypto" | "commodity" | "forex"

    Returns:
        Diccionario con score total, label, color y breakdown por categoría
    """
    ind = indicators
    has_fundamentals = (asset_type == "stock") and bool(fundamentals)

    # --- Calcular cada componente ---
    tech_score, tech_exp = _technical_risk(ind)
    fin_score,  fin_exp  = _financial_risk(fundamentals, has_fundamentals)
    mom_score,  mom_exp  = _momentum_risk(ind, asset_type)

    # --- Calcular total según disponibilidad de fundamentales ---
    if has_fundamentals:
        total = tech_score * 0.35 + fin_score * 0.35 + mom_score * 0.30
        tech_weight = 35
        fin_weight  = 35
        mom_weight  = 30
    else:
        # Sin fundamentales: redistribuimos el 35% entre técnico y momentum
        total = tech_score * 0.50 + mom_score * 0.50
        tech_weight = 50
        fin_weight  = 0
        mom_weight  = 50
        fin_exp = (
            f"Datos fundamentales no disponibles para activos tipo '{asset_type}'. "
            "El peso financiero (35%) se redistribuye en riesgo técnico y momentum."
        )

    total = int(min(100, max(0, round(total))))

    return {
        "technical": {
            "score":       int(round(tech_score)),
            "weight":      tech_weight,
            "explanation": tech_exp,
        },
        "financial": {
            "score":       int(round(fin_score)) if has_fundamentals else None,
            "weight":      fin_weight,
            "explanation": fin_exp,
            "available":   has_fundamentals,
        },
        "momentum_events": {
            "score":       int(round(mom_score)),
            "weight":      mom_weight,
            "explanation": mom_exp,
        },
        "total":      total,
        "label":      _risk_label(total),
        "risk_color": _risk_color(total),
    }


# ---------------------------------------------------------------------------
# Componente 1: Riesgo Técnico (0-100)
# ---------------------------------------------------------------------------

def _technical_risk(ind: Dict[str, Any]) -> Tuple[float, str]:
    """
    Evalúa el riesgo basándose en indicadores técnicos.

    Factores (máx 100 puntos):
      Tendencia vs SMA200  → hasta 25 pts
      Distancia SMA200     → hasta 10 pts
      RSI extremo          → hasta 15 pts
      MACD negativo        → hasta 10 pts
      Volatilidad          → hasta 15 pts
      Drawdown máximo      → hasta 15 pts
    """
    risk = 0.0
    factors: list = []

    # ---- Tendencia general ----
    trend = ind.get("trend", "neutral")
    if trend == "bearish":
        risk += 25
        factors.append("Tendencia bajista (precio bajo medias móviles clave)")
    elif trend == "neutral":
        risk += 12
        factors.append("Tendencia neutral (señales mixtas)")
    else:
        factors.append("Tendencia alcista (precio sobre medias móviles clave)")

    # ---- Distancia vs SMA 200 ----
    dist = ind.get("dist_sma200_pct")
    if dist is not None:
        if dist < -20:
            risk += 10
            factors.append(f"Precio muy por debajo de SMA200 ({dist:.1f}%)")
        elif dist < -8:
            risk += 5
            factors.append(f"Precio por debajo de SMA200 ({dist:.1f}%)")
        elif dist > 30:
            risk += 5  # Sobreextensión al alza también es riesgo
            factors.append(f"Precio muy extendido sobre SMA200 (+{dist:.1f}%)")

    # ---- RSI ----
    rsi = ind.get("rsi")
    if rsi is not None:
        if rsi >= 80:
            risk += 15
            factors.append(f"RSI extremadamente sobrecomprado ({rsi:.1f})")
        elif rsi >= 70:
            risk += 8
            factors.append(f"RSI sobrecomprado ({rsi:.1f})")
        elif rsi <= 20:
            risk += 15
            factors.append(f"RSI en pánico extremo ({rsi:.1f})")
        elif rsi <= 30:
            risk += 6
            factors.append(f"RSI sobrevendido ({rsi:.1f})")

    # ---- MACD ----
    if not ind.get("macd_bullish", True):
        risk += 10
        factors.append("MACD en zona negativa (momentum bajista)")

    # ---- Volatilidad anualizada ----
    vol = ind.get("annual_volatility", 0)
    if vol > 80:
        risk += 15
        factors.append(f"Volatilidad anualizada extrema ({vol:.1f}%)")
    elif vol > 50:
        risk += 10
        factors.append(f"Volatilidad anualizada muy alta ({vol:.1f}%)")
    elif vol > 30:
        risk += 5
        factors.append(f"Volatilidad anualizada elevada ({vol:.1f}%)")

    # ---- Drawdown máximo ----
    dd = ind.get("max_drawdown", 0)
    if dd < -50:
        risk += 15
        factors.append(f"Drawdown máximo severo ({dd:.1f}%)")
    elif dd < -30:
        risk += 10
        factors.append(f"Drawdown máximo alto ({dd:.1f}%)")
    elif dd < -15:
        risk += 4
        factors.append(f"Drawdown máximo moderado ({dd:.1f}%)")

    risk = min(100.0, risk)
    exp = f"Score técnico: {int(risk)}/100. " + " | ".join(factors)
    return risk, exp


# ---------------------------------------------------------------------------
# Componente 2: Riesgo Financiero (0-100)
# ---------------------------------------------------------------------------

def _financial_risk(fund: Dict[str, Any], has_fundamentals: bool) -> Tuple[float, str]:
    """
    Evalúa el riesgo basándose en métricas fundamentales.
    Solo aplica a acciones con datos disponibles.
    """
    if not has_fundamentals:
        return 50.0, "Sin datos fundamentales disponibles."

    risk = 20.0  # base neutra
    factors: list = []

    # ---- Deuda / Equity ----
    de = fund.get("debt_to_equity")
    if de is not None:
        if de > 200:
            risk += 25
            factors.append(f"Deuda/Equity muy alta ({de:.1f}%)")
        elif de > 100:
            risk += 15
            factors.append(f"Deuda/Equity elevada ({de:.1f}%)")
        elif de > 50:
            risk += 5
            factors.append(f"Deuda/Equity moderada ({de:.1f}%)")
        else:
            risk -= 5
            factors.append(f"Deuda/Equity baja ({de:.1f}%)")

    # ---- Margen neto ----
    pm = fund.get("profit_margin")
    if pm is not None:
        if pm < 0:
            risk += 20
            factors.append(f"Pérdidas netas (margen neto: {pm*100:.1f}%)")
        elif pm < 0.03:
            risk += 10
            factors.append(f"Margen neto muy bajo ({pm*100:.1f}%)")
        elif pm > 0.20:
            risk -= 10
            factors.append(f"Margen neto saludable ({pm*100:.1f}%)")

    # ---- Crecimiento de ingresos ----
    rg = fund.get("revenue_growth")
    if rg is not None:
        if rg < -0.15:
            risk += 15
            factors.append(f"Ingresos cayendo fuerte ({rg*100:.1f}%)")
        elif rg < -0.05:
            risk += 8
            factors.append(f"Ingresos en caída ({rg*100:.1f}%)")
        elif rg > 0.20:
            risk -= 8
            factors.append(f"Crecimiento de ingresos fuerte ({rg*100:.1f}%)")

    # ---- P/E ----
    pe = fund.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe > 150:
            risk += 15
            factors.append(f"P/E extremadamente alto ({pe:.1f}x) — valoración especulativa")
        elif pe > 60:
            risk += 8
            factors.append(f"P/E elevado ({pe:.1f}x)")
        elif pe < 8:
            risk += 5
            factors.append(f"P/E muy bajo ({pe:.1f}x) — posible trampa de valor")

    # ---- Free Cash Flow ----
    fcf = fund.get("free_cash_flow")
    if fcf is not None:
        if fcf < 0:
            risk += 10
            factors.append("Free Cash Flow negativo")
        else:
            risk -= 5
            factors.append("Free Cash Flow positivo")

    risk = min(100.0, max(0.0, risk))
    exp = f"Score financiero: {int(risk)}/100. " + (" | ".join(factors) if factors else "Datos limitados.")
    return risk, exp


# ---------------------------------------------------------------------------
# Componente 3: Riesgo Momentum / Eventos (0-100)
# ---------------------------------------------------------------------------

def _momentum_risk(ind: Dict[str, Any], asset_type: str) -> Tuple[float, str]:
    """
    Evalúa el riesgo basándose en momentum reciente, gaps y volumen anormal.
    """
    risk = 15.0  # base
    factors: list = []

    # ---- Retorno 1 mes ----
    ret1m = ind.get("return_1m")
    if ret1m is not None:
        if ret1m < -25:
            risk += 30
            factors.append(f"Caída del {ret1m:.1f}% en 1 mes — posible pánico")
        elif ret1m < -15:
            risk += 20
            factors.append(f"Caída del {ret1m:.1f}% en 1 mes")
        elif ret1m < -7:
            risk += 10
            factors.append(f"Caída del {ret1m:.1f}% en 1 mes")
        elif ret1m > 35:
            risk += 15
            factors.append(f"Subida del {ret1m:.1f}% en 1 mes — posible sobreextensión")
        elif ret1m > 20:
            risk += 7
            factors.append(f"Subida del {ret1m:.1f}% en 1 mes")

    # ---- Retorno 3 meses ----
    ret3m = ind.get("return_3m")
    if ret3m is not None and ret3m < -20:
        risk += 10
        factors.append(f"Retorno negativo de {ret3m:.1f}% en 3 meses")

    # ---- Gap reciente ----
    gap = ind.get("recent_gap") or {}
    if gap.get("detected"):
        gap_pct = gap.get("gap_pct", 0)
        direction = gap.get("direction", "")
        if gap_pct >= 5:
            risk += 20
            factors.append(f"Gap {direction} del {gap_pct:.1f}% en los últimos 5 días")
        else:
            risk += 10
            factors.append(f"Gap {direction} del {gap_pct:.1f}% reciente")

    # ---- Volumen anormal ----
    vol_anom = ind.get("volume_anomaly") or {}
    if vol_anom.get("detected"):
        ratio = vol_anom.get("ratio", 1)
        if ratio >= 3:
            risk += 15
            factors.append(f"Volumen {ratio:.1f}× el promedio — actividad inusual")
        else:
            risk += 7
            factors.append(f"Volumen elevado ({ratio:.1f}× promedio)")

    # ---- Ajuste por tipo de activo ----
    if asset_type == "crypto":
        vol = ind.get("annual_volatility", 0)
        if vol > 100:
            risk += 15
            factors.append(f"Volatilidad cripto extrema ({vol:.0f}%)")
        elif vol > 60:
            risk += 7
            factors.append(f"Volatilidad cripto alta ({vol:.0f}%)")

    if asset_type in ("commodity", "forex") and not factors:
        factors.append("Sin eventos de momentum destacables en el periodo")

    risk = min(100.0, max(0.0, risk))
    exp = f"Score momentum: {int(risk)}/100. " + (" | ".join(factors) if factors else "Sin anomalías detectadas.")
    return risk, exp


# ---------------------------------------------------------------------------
# Helpers de interpretación
# ---------------------------------------------------------------------------

def _risk_label(score: int) -> str:
    if score <= 30:
        return "Riesgo Bajo"
    if score <= 60:
        return "Riesgo Medio"
    if score <= 80:
        return "Riesgo Alto"
    return "Riesgo Extremo"


def _risk_color(score: int) -> str:
    if score <= 30:
        return "#22c55e"   # verde
    if score <= 60:
        return "#f59e0b"   # ámbar
    if score <= 80:
        return "#ef4444"   # rojo
    return "#7f1d1d"       # rojo oscuro
