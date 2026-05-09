"""
report_generator.py
===================
Ensambla el JSON final del reporte llamando a todos los módulos de análisis.

Flujo:
  1. data_provider  → descarga OHLCV + info + fundamentales
  2. indicators     → calcula todos los indicadores técnicos
  3. fibonacci      → calcula niveles de retroceso/extensión
  4. elliott        → detecta posibles ondas de Elliott
  5. risk_score     → calcula score 0-100
  6. (finnhub)      → obtiene noticias si hay API key
  7. Ensambla todo en un JSON estructurado para el frontend
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from data_provider import get_market_data, get_finnhub_news
from indicators import calculate_indicators
from fibonacci import calculate_fibonacci
from elliott import analyze_elliott_waves
from risk_score import calculate_risk_score


def generate_report(ticker: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
    """
    Genera el reporte completo de análisis de un activo financiero.

    Args:
        ticker:   símbolo del activo (AAPL, BTC-USD, GC=F, etc.)
        period:   6mo | 1y | 2y | 5y | max
        interval: 1d | 1wk | 1mo

    Returns:
        JSON completo con todos los datos para renderizar el reporte de 2 páginas

    Raises:
        ValueError: si el ticker no existe o no hay datos
    """
    # ------------------------------------------------------------------
    # 1. Datos históricos y fundamentales
    # ------------------------------------------------------------------
    data = get_market_data(ticker, period, interval)
    hist = data["hist"]

    # ------------------------------------------------------------------
    # 2. Indicadores técnicos
    # ------------------------------------------------------------------
    ind = calculate_indicators(hist, interval=interval)

    # ------------------------------------------------------------------
    # 3. Fibonacci
    # ------------------------------------------------------------------
    fib = calculate_fibonacci(hist)

    # ------------------------------------------------------------------
    # 4. Ondas de Elliott
    # ------------------------------------------------------------------
    elliott = analyze_elliott_waves(hist)

    # ------------------------------------------------------------------
    # 5. Risk Score
    # ------------------------------------------------------------------
    risk = calculate_risk_score(ind, data["fundamentals"], data["asset_type"])

    # ------------------------------------------------------------------
    # 6. Noticias (Finnhub, opcional)
    # ------------------------------------------------------------------
    news: List[dict] = []
    try:
        news = get_finnhub_news(ticker)
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 7. Cards de análisis fundamental
    # ------------------------------------------------------------------
    fund = data["fundamentals"]
    atype = data["asset_type"]

    valuation_cards      = _valuation_cards(fund, atype)
    financial_health_cards = _financial_health_cards(fund, atype)
    growth_cards         = _growth_cards(fund, atype)

    # ------------------------------------------------------------------
    # 8. Catalysts y Risks
    # ------------------------------------------------------------------
    catalysts, risks_list = _catalysts_and_risks(ind, fund, atype)

    # ------------------------------------------------------------------
    # 9. Verdict
    # ------------------------------------------------------------------
    verdict = _build_verdict(risk["total"])

    # ------------------------------------------------------------------
    # 10. Soporte y resistencia básicos
    # ------------------------------------------------------------------
    support_resistance = _support_resistance(hist, ind)

    # ------------------------------------------------------------------
    # 11. Tabla trimestral (placeholder estructurado)
    # ------------------------------------------------------------------
    quarterly_table = _quarterly_table(data)

    # ------------------------------------------------------------------
    # Ensamblar JSON final
    # ------------------------------------------------------------------
    return {
        # Info del activo
        "ticker":       data["ticker"],
        "company_name": data["company_name"],
        "currency":     data["currency"],
        "asset_type":   data["asset_type"],
        "provider":     data["provider"],
        "period":       period,
        "interval":     interval,
        "latest_update": datetime.now().strftime("%Y-%m-%d %H:%M"),

        # Precio actual
        "latest_price":         ind["current_price"],
        "price_change":         ind["price_change"],
        "price_change_percent": ind["price_change_pct"],

        # Risk score
        "risk_score":      risk["total"],
        "risk_label":      risk["label"],
        "risk_color":      risk["risk_color"],
        "score_breakdown": risk,

        # Resumen técnico
        "technical_summary": _technical_summary(ind),

        # Indicadores (valores puntuales para KPI strip y cards)
        "indicators": {
            "sma_20":          ind["sma_20"],
            "sma_50":          ind["sma_50"],
            "sma_200":         ind["sma_200"],
            "ema_20":          ind["ema_20"],
            "rsi":             ind["rsi"],
            "rsi_signal":      ind["rsi_signal"],
            "macd":            ind["macd"],
            "macd_signal_line":ind["macd_signal_line"],
            "macd_histogram":  ind["macd_histogram"],
            "macd_bullish":    ind["macd_bullish"],
            "atr":             ind["atr"],
            "annual_volatility": ind["annual_volatility"],
            "max_drawdown":    ind["max_drawdown"],
            "return_1m":       ind["return_1m"],
            "return_3m":       ind["return_3m"],
            "return_6m":       ind["return_6m"],
            "return_12m":      ind["return_12m"],
            "avg_volume_20d":  ind["avg_volume_20d"],
            "dist_sma200_pct": ind["dist_sma200_pct"],
            "trend":           ind["trend"],
        },

        # Series para gráfico SVG (arrays de valores)
        "price_series":      ind["price_series"],
        "sma_20_series":     ind["sma_20_series"],
        "sma_50_series":     ind["sma_50_series"],
        "sma_200_series":    ind["sma_200_series"],
        "dates_series":      ind["dates_series"],
        "volume_series":     ind["volume_series"],

        # Fibonacci
        "fibonacci_levels": fib,

        # Elliott Wave
        "elliott_wave_analysis": elliott,

        # Soporte / Resistencia
        "support_resistance": support_resistance,

        # Cards fundamentales
        "valuation_cards":         valuation_cards,
        "financial_health_cards":  financial_health_cards,
        "growth_cards":            growth_cards,

        # Tabla trimestral
        "quarterly_trend_table": quarterly_table,

        # Earnings info
        "earnings_data": data["earnings_data"],

        # Catalysts y Risks
        "catalysts": catalysts,
        "risks":     risks_list,

        # Verdict
        "verdict": verdict,

        # Noticias recientes
        "recent_news": [
            {"headline": n.get("headline", ""), "source": n.get("source", ""), "url": n.get("url", "")}
            for n in news[:3]
        ],
    }


# ---------------------------------------------------------------------------
# Cards de análisis fundamental
# ---------------------------------------------------------------------------

def _valuation_cards(fund: dict, atype: str) -> List[dict]:
    if atype != "stock":
        names = ["P/E Ratio", "Forward P/E", "Price/Sales", "Price/Book", "EV/EBITDA", "Dividend Yield"]
        return [_na_card(n, f"No aplica para {atype}") for n in names]

    return [
        _card("P/E Ratio",     fund.get("pe_ratio"),
              lambda v: "green" if 8 < v < 25 else "amber" if v <= 40 else "red",
              lambda v: f"{v:.1f}×", "Precio / Beneficio"),
        _card("Forward P/E",   fund.get("forward_pe"),
              lambda v: "green" if 8 < v < 22 else "amber" if v <= 35 else "red",
              lambda v: f"{v:.1f}×", "P/E proyectado"),
        _card("Price/Sales",   fund.get("price_to_sales"),
              lambda v: "green" if v < 5 else "amber" if v < 12 else "red",
              lambda v: f"{v:.1f}×", "Precio / Ingresos"),
        _card("Price/Book",    fund.get("price_to_book"),
              lambda v: "green" if v < 3 else "amber" if v < 7 else "red",
              lambda v: f"{v:.1f}×", "Precio / Valor contable"),
        _card("EV/EBITDA",     fund.get("ev_to_ebitda"),
              lambda v: "green" if v < 12 else "amber" if v < 22 else "red",
              lambda v: f"{v:.1f}×", "Valor empresa / EBITDA"),
        _card("Dividend Yield",fund.get("dividend_yield"),
              lambda v: "green" if v > 0.015 else "amber" if v > 0 else "gray",
              lambda v: f"{v*100:.2f}%", "Rendimiento dividendo"),
    ]


def _financial_health_cards(fund: dict, atype: str) -> List[dict]:
    if atype != "stock":
        names = ["Debt/Equity", "Current Ratio", "Free Cash Flow", "Gross Margin", "Operating Margin", "Net Margin"]
        return [_na_card(n, f"No aplica para {atype}") for n in names]

    return [
        _card("Debt/Equity",     fund.get("debt_to_equity"),
              lambda v: "green" if v < 50 else "amber" if v < 120 else "red",
              lambda v: f"{v:.1f}%", "Nivel de endeudamiento"),
        _card("Current Ratio",   fund.get("current_ratio"),
              lambda v: "green" if v > 1.5 else "amber" if v > 1 else "red",
              lambda v: f"{v:.2f}×", "Liquidez a corto plazo"),
        _card("Free Cash Flow",  fund.get("free_cash_flow"),
              lambda v: "green" if v > 0 else "red",
              lambda v: (f"${v/1e9:.1f}B" if abs(v) >= 1e9 else f"${v/1e6:.0f}M"),
              "Flujo de caja libre"),
        _card("Gross Margin",    fund.get("gross_margin"),
              lambda v: "green" if v > 0.40 else "amber" if v > 0.20 else "red",
              lambda v: f"{v*100:.1f}%", "Margen bruto"),
        _card("Operating Margin",fund.get("operating_margin"),
              lambda v: "green" if v > 0.15 else "amber" if v > 0.05 else "red",
              lambda v: f"{v*100:.1f}%", "Margen operativo"),
        _card("Net Margin",      fund.get("profit_margin"),
              lambda v: "green" if v > 0.10 else "amber" if v > 0 else "red",
              lambda v: f"{v*100:.1f}%", "Margen neto"),
    ]


def _growth_cards(fund: dict, atype: str) -> List[dict]:
    if atype != "stock":
        names = ["Revenue Growth", "EPS Growth", "EBITDA Growth", "FCF Growth", "Guidance", "Earnings Surprise"]
        return [_na_card(n, f"No aplica para {atype}") for n in names]

    return [
        _card("Revenue Growth",   fund.get("revenue_growth"),
              lambda v: "green" if v > 0.08 else "amber" if v > 0 else "red",
              lambda v: f"{v*100:.1f}%", "Crecimiento de ingresos"),
        _card("EPS Growth",       fund.get("earnings_growth"),
              lambda v: "green" if v > 0.08 else "amber" if v > 0 else "red",
              lambda v: f"{v*100:.1f}%", "Crecimiento de EPS"),
        _na_card("EBITDA Growth",     "Requiere proveedor premium"),
        _na_card("FCF Growth",        "Requiere serie histórica de FCF"),
        _na_card("Guidance",          "Requiere Finnhub/Alpha Vantage premium"),
        _na_card("Earnings Surprise", "Requiere datos de consenso"),
    ]


def _card(name: str, value, color_fn, fmt_fn, note: str = "") -> dict:
    """Crea una card de análisis con valor y estado de color."""
    if value is None:
        return _na_card(name, note or "Dato no disponible")
    try:
        color     = color_fn(value)
        formatted = fmt_fn(value)
    except Exception:
        return _na_card(name, note)
    return {"name": name, "value": formatted, "raw_value": value, "status": color, "note": note}


def _na_card(name: str, note: str = "Dato no disponible") -> dict:
    return {"name": name, "value": "N/A", "raw_value": None, "status": "gray", "note": note}


# ---------------------------------------------------------------------------
# Catalysts y Risks
# ---------------------------------------------------------------------------

def _catalysts_and_risks(ind: dict, fund: dict, atype: str):
    catalysts: List[str] = []
    risks: List[str] = []

    trend    = ind.get("trend", "neutral")
    rsi      = ind.get("rsi")
    macd_ok  = ind.get("macd_bullish", False)
    ret1m    = ind.get("return_1m") or 0
    ret3m    = ind.get("return_3m") or 0
    vol      = ind.get("annual_volatility", 0)
    dd       = ind.get("max_drawdown", 0)
    dist200  = ind.get("dist_sma200_pct")

    # --- Catalysts ---
    if trend == "bullish":
        catalysts.append("Tendencia alcista — precio sobre todas las medias móviles clave")
    if macd_ok:
        catalysts.append("MACD positivo — momentum al alza")
    if rsi and 40 <= rsi <= 60:
        catalysts.append(f"RSI neutral ({rsi:.0f}) — espacio para continuar subiendo sin sobrecalentamiento")
    if ret3m and ret3m > 8:
        catalysts.append(f"Retorno positivo de {ret3m:.1f}% en 3 meses")
    if dist200 and dist200 > 5:
        catalysts.append(f"Precio {dist200:.1f}% sobre SMA200 — señal de fortaleza estructural")
    if fund.get("revenue_growth") and fund["revenue_growth"] > 0.08:
        catalysts.append(f"Crecimiento de ingresos del {fund['revenue_growth']*100:.1f}%")
    if fund.get("free_cash_flow") and fund["free_cash_flow"] > 0:
        catalysts.append("Free Cash Flow positivo — generación de caja saludable")
    if fund.get("profit_margin") and fund["profit_margin"] > 0.12:
        catalysts.append(f"Margen neto saludable ({fund['profit_margin']*100:.1f}%)")

    # --- Risks ---
    if trend == "bearish":
        risks.append("Tendencia bajista — precio por debajo de medias móviles clave")
    if not macd_ok:
        risks.append("MACD negativo — momentum bajista")
    if rsi and rsi > 72:
        risks.append(f"RSI sobrecomprado ({rsi:.0f}) — posible corrección próxima")
    if rsi and rsi < 28:
        risks.append(f"RSI sobrevendido ({rsi:.0f}) — alta presión vendedora")
    if ret1m and ret1m < -10:
        risks.append(f"Caída del {ret1m:.1f}% en el último mes")
    if vol > 40:
        risks.append(f"Alta volatilidad anualizada ({vol:.1f}%)")
    if dd < -30:
        risks.append(f"Drawdown máximo elevado ({dd:.1f}%)")
    if dist200 and dist200 < -10:
        risks.append(f"Precio {abs(dist200):.1f}% por debajo de SMA200")
    if fund.get("debt_to_equity") and fund["debt_to_equity"] > 120:
        risks.append(f"Deuda/Equity elevada ({fund['debt_to_equity']:.1f}%)")
    if fund.get("profit_margin") and fund["profit_margin"] < 0:
        risks.append("Empresa reporta pérdidas netas")

    if not catalysts:
        catalysts.append("Sin catalizadores técnicos o fundamentales claros en el periodo analizado")
    if not risks:
        risks.append("Sin factores de riesgo técnico o fundamental inmediatos identificados")

    return catalysts[:7], risks[:7]


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def _build_verdict(score: int) -> dict:
    if score <= 30:
        return {
            "label":       "Favorable / Atractivo",
            "rating":      "BUY ZONE",
            "color":       "#22c55e",
            "explanation": (
                "El activo presenta condiciones técnicas y/o fundamentales favorables. "
                "El riesgo medido es bajo en el periodo analizado."
            ),
        }
    if score <= 50:
        return {
            "label":       "Neutral / En Seguimiento",
            "rating":      "WATCHLIST",
            "color":       "#38bdf8",
            "explanation": (
                "El activo muestra señales mixtas. "
                "No hay urgencia de acción pero merece seguimiento activo."
            ),
        }
    if score <= 70:
        return {
            "label":       "Riesgoso / Con Precaución",
            "rating":      "CAUTION",
            "color":       "#f59e0b",
            "explanation": (
                "El activo presenta factores de riesgo relevantes. "
                "Si decides operar, aplica gestión de riesgo estricta."
            ),
        }
    return {
        "label":       "Alto Riesgo / Especulativo",
        "rating":      "HIGH RISK",
        "color":       "#ef4444",
        "explanation": (
            "El activo presenta múltiples señales de riesgo elevado. "
            "Solo apto para traders con alta tolerancia al riesgo y gestión de posición muy estricta."
        ),
    }


# ---------------------------------------------------------------------------
# Soporte y resistencia
# ---------------------------------------------------------------------------

def _support_resistance(hist, ind: dict) -> dict:
    close = hist["Close"].astype(float)
    high  = hist["High"].astype(float)
    low   = hist["Low"].astype(float)

    s20  = float(low.tail(20).min())
    s50  = float(low.tail(50).min()) if len(low) >= 50 else None
    r20  = float(high.tail(20).max())
    r50  = float(high.tail(50).max()) if len(high) >= 50 else None

    return {
        "support_20":    round(s20, 4),
        "support_50":    round(s50, 4) if s50 else None,
        "resistance_20": round(r20, 4),
        "resistance_50": round(r50, 4) if r50 else None,
        "sma_20":        ind.get("sma_20"),
        "sma_50":        ind.get("sma_50"),
        "sma_200":       ind.get("sma_200"),
    }


# ---------------------------------------------------------------------------
# Resumen técnico en texto
# ---------------------------------------------------------------------------

def _technical_summary(ind: dict) -> str:
    trend_map = {"bullish": "alcista", "bearish": "bajista", "neutral": "neutral"}
    trend_es  = trend_map.get(ind.get("trend", "neutral"), "neutral")
    rsi_val   = ind.get("rsi")
    macd_ok   = ind.get("macd_bullish", False)
    vol       = ind.get("annual_volatility", 0)

    rsi_str = ""
    if rsi_val:
        if rsi_val > 70:
            rsi_str = f"RSI sobrecomprado ({rsi_val:.0f})"
        elif rsi_val < 30:
            rsi_str = f"RSI sobrevendido ({rsi_val:.0f})"
        else:
            rsi_str = f"RSI neutral ({rsi_val:.0f})"

    macd_str = "MACD positivo (momentum alcista)" if macd_ok else "MACD negativo (momentum bajista)"

    parts = [f"Tendencia {trend_es}"]
    if rsi_str:
        parts.append(rsi_str)
    parts.append(macd_str)
    parts.append(f"Volatilidad anualizada {vol:.1f}%")
    parts.append(f"Drawdown máximo {ind.get('max_drawdown', 0):.1f}%")

    return ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# Tabla trimestral
# ---------------------------------------------------------------------------

def _quarterly_table(data: dict) -> List[dict]:
    """
    Devuelve tabla de datos trimestrales.
    Yahoo Finance provee ciertos datos trimestrales — si no están disponibles,
    devuelve un placeholder claro.
    Para datos trimestrales completos se recomienda Alpha Vantage o Finnhub premium.
    """
    if data["asset_type"] != "stock":
        return []

    try:
        yf_ticker_obj = None
        # Intentar obtener datos trimestrales reales
        import yfinance as yf
        yf_ticker_obj = yf.Ticker(data["ticker"])
        qf = yf_ticker_obj.quarterly_financials

        if qf is not None and not qf.empty:
            rows = []
            for col in qf.columns[:4]:  # últimos 4 trimestres
                quarter = str(col.date()) if hasattr(col, "date") else str(col)
                revenue_key = next((k for k in qf.index if "Revenue" in str(k) or "Total Revenue" in str(k)), None)
                income_key  = next((k for k in qf.index if "Net Income" in str(k)), None)
                revenue = _fmt_millions(qf.loc[revenue_key, col]) if revenue_key else "N/A"
                net_inc = _fmt_millions(qf.loc[income_key,  col]) if income_key  else "N/A"
                rows.append({
                    "quarter": quarter, "revenue": revenue, "eps": "N/A",
                    "margin": "N/A", "fcf": "N/A", "debt": "N/A",
                    "notes": net_inc,
                })
            return rows
    except Exception:
        pass

    return [{
        "quarter": "N/A", "revenue": "N/A", "eps": "N/A",
        "margin": "N/A", "fcf": "N/A", "debt": "N/A",
        "notes": "Datos trimestrales detallados requieren proveedor premium (Alpha Vantage, Finnhub)",
    }]


def _fmt_millions(value) -> str:
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        return f"${v/1e6:.1f}M"
    except Exception:
        return "N/A"
