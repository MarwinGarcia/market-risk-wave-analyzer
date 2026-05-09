"""
data_provider.py
================
Capa unificada de datos financieros.

Proveedores disponibles:
  1. Yahoo Finance  — default, gratis, sin API key
  2. Alpha Vantage  — gratis con key (25 llamadas/día)
  3. Finnhub        — gratis con key (60 llamadas/minuto)

Para CAMBIAR de proveedor en el futuro:
  - Agrega tu clase nueva siguiendo el patrón de _get_yahoo_data()
  - Llámala desde get_market_data() en el orden que prefieras
  - El resto del sistema NO necesita cambios

Para AGREGAR TradingView u otro proveedor:
  - Crea _get_tradingview_data(ticker, period, interval) -> dict
  - Devuelve el mismo formato que _get_yahoo_data()
  - Úsala como primera opción en get_market_data()
"""

import os
import json
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import yfinance as yf
from datetime import date, timedelta
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

# ---------------------------------------------------------------------------
# API Keys (se leen del archivo .env)
# ---------------------------------------------------------------------------
ALPHA_VANTAGE_KEY: str = os.getenv("ALPHA_VANTAGE_KEY", "")
FINNHUB_KEY: str = os.getenv("FINNHUB_KEY", "")


# ---------------------------------------------------------------------------
# Función principal — punto de entrada
# ---------------------------------------------------------------------------

def get_market_data(ticker: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
    """
    Descarga datos históricos y fundamentales del activo.

    Orden de prioridad:
      1. Yahoo Finance (siempre disponible, sin key)
      2. Alpha Vantage (si hay ALPHA_VANTAGE_KEY en .env)

    Args:
        ticker:   símbolo del activo (AAPL, BTC-USD, GC=F, etc.)
        period:   6mo | 1y | 2y | 5y | max
        interval: 1d | 1wk | 1mo

    Returns:
        Diccionario con hist (DataFrame), info, fundamentals, asset_type, etc.

    Raises:
        ValueError: si no hay datos para el ticker
    """
    try:
        return _get_yahoo_data(ticker, period, interval)
    except ValueError:
        raise
    except Exception as e:
        # Si Yahoo falla y hay Alpha Vantage key, intentamos Alpha Vantage
        if ALPHA_VANTAGE_KEY:
            try:
                return _get_alpha_vantage_data(ticker, period, interval)
            except Exception as e2:
                raise ValueError(
                    f"No encontré datos para '{ticker}'. "
                    "Verifica que el ticker sea correcto. "
                    "Ejemplos válidos: AAPL, SPY, GLD, BTC-USD, GC=F, CL=F"
                ) from e2
        raise ValueError(
            f"No encontré datos para '{ticker}'. "
            "Verifica que el ticker sea correcto. "
            "Ejemplos válidos: AAPL, SPY, GLD, BTC-USD, GC=F, CL=F"
        ) from e


# ---------------------------------------------------------------------------
# Proveedor 1: Yahoo Finance
# ---------------------------------------------------------------------------

def _get_yahoo_data(ticker: str, period: str, interval: str) -> Dict[str, Any]:
    """
    Descarga datos de Yahoo Finance usando la librería yfinance.

    Soporta: acciones US, ETFs, crypto (BTC-USD), commodities (GC=F, CL=F), forex.

    Para cambiar a otro proveedor como default:
      Reemplaza esta llamada en get_market_data() por _get_alpha_vantage_data()
      o por tu nueva función de proveedor.
    """
    yf_ticker = yf.Ticker(ticker)

    # --- 4h no existe en yfinance: descargamos 1h y resampleamos ---
    fetch_interval = "1h" if interval == "4h" else interval

    # --- Descargar historial de precios OHLCV ---
    hist = yf_ticker.history(period=period, interval=fetch_interval, auto_adjust=True)

    if hist is None or hist.empty:
        raise ValueError(
            f"No encontré datos históricos para '{ticker}'. "
            "Prueba con otro ticker o periodo más corto."
        )

    # Limpiar el índice (eliminar timezone para serialización JSON)
    hist.index = hist.index.tz_localize(None) if hist.index.tz is not None else hist.index

    # --- Resamplear 1h → 4h si fue solicitado ---
    if interval == "4h":
        hist = hist.resample("4h").agg({
            "Open":   "first",
            "High":   "max",
            "Low":    "min",
            "Close":  "last",
            "Volume": "sum",
        }).dropna()

    # --- Información del activo ---
    info: dict = {}
    try:
        info = yf_ticker.info or {}
    except Exception:
        pass

    # --- Tipo de activo ---
    asset_type = _detect_asset_type(ticker, info)

    # --- Fundamentales (solo para acciones) ---
    fundamentals: dict = {}
    if asset_type == "stock":
        fundamentals = _extract_fundamentals(info)

    # --- Datos de earnings ---
    earnings_data: dict = {}
    if asset_type == "stock":
        earnings_data = _extract_earnings(yf_ticker, info)

    return {
        "ticker": ticker.upper(),
        "company_name": info.get("longName") or info.get("shortName") or ticker.upper(),
        "currency": info.get("currency", "USD"),
        "asset_type": asset_type,
        "provider": "Yahoo Finance",
        "hist": hist,
        "info": info,
        "fundamentals": fundamentals,
        "earnings_data": earnings_data,
    }


def _detect_asset_type(ticker: str, info: dict) -> str:
    """Detecta el tipo de activo basándose en la info de Yahoo y el formato del ticker."""
    quote_type = (info.get("quoteType") or "").lower()

    if quote_type == "equity":
        return "stock"
    if quote_type == "etf":
        return "etf"
    if quote_type == "cryptocurrency":
        return "crypto"
    if quote_type == "future":
        return "commodity"
    if quote_type in ("currency", "forex"):
        return "forex"

    # Detección por formato del ticker cuando Yahoo no informa el tipo
    t = ticker.upper()
    if "-USD" in t or "-EUR" in t or "-BTC" in t:
        return "crypto"
    if t.endswith("=F"):
        return "commodity"
    if len(t) == 6 and t.isalpha():
        return "forex"

    return "stock"  # default


def _extract_fundamentals(info: dict) -> dict:
    """Extrae métricas fundamentales del diccionario info de Yahoo Finance."""

    def safe(key):
        val = info.get(key)
        return val if val not in (None, "N/A", "None", float("inf"), float("-inf")) else None

    return {
        "pe_ratio": safe("trailingPE"),
        "forward_pe": safe("forwardPE"),
        "price_to_sales": safe("priceToSalesTrailing12Months"),
        "price_to_book": safe("priceToBook"),
        "ev_to_ebitda": safe("enterpriseToEbitda"),
        "dividend_yield": safe("dividendYield"),
        "debt_to_equity": safe("debtToEquity"),
        "current_ratio": safe("currentRatio"),
        "free_cash_flow": safe("freeCashflow"),
        "gross_margin": safe("grossMargins"),
        "operating_margin": safe("operatingMargins"),
        "profit_margin": safe("profitMargins"),
        "revenue_growth": safe("revenueGrowth"),
        "earnings_growth": safe("earningsGrowth"),
        "total_debt": safe("totalDebt"),
        "total_cash": safe("totalCash"),
        "market_cap": safe("marketCap"),
        "beta": safe("beta"),
        "week_52_high": safe("fiftyTwoWeekHigh"),
        "week_52_low": safe("fiftyTwoWeekLow"),
        "sector": safe("sector"),
        "industry": safe("industry"),
    }


def _extract_earnings(yf_ticker: yf.Ticker, info: dict) -> dict:
    """Extrae información de earnings disponible en Yahoo Finance."""
    result: dict = {"has_quarterly": False, "next_earnings_date": None}

    try:
        earnings_dates = info.get("earningsDate")
        if isinstance(earnings_dates, list) and earnings_dates:
            result["next_earnings_date"] = str(earnings_dates[0])
        elif isinstance(earnings_dates, (int, float)):
            from datetime import datetime
            result["next_earnings_date"] = str(datetime.fromtimestamp(earnings_dates).date())
    except Exception:
        pass

    try:
        qf = yf_ticker.quarterly_financials
        result["has_quarterly"] = qf is not None and not qf.empty
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Proveedor 2: Alpha Vantage
# ---------------------------------------------------------------------------

def _get_alpha_vantage_data(ticker: str, period: str, interval: str) -> Dict[str, Any]:
    """
    [PROVEEDOR ALTERNATIVO — Alpha Vantage]

    Para usar como proveedor principal:
      1. Agrega ALPHA_VANTAGE_KEY en tu archivo .env
      2. En get_market_data(), cambia el orden de llamadas:
         return _get_alpha_vantage_data(ticker, period, interval)

    Documentación: https://www.alphavantage.co/documentation/
    Límite gratuito: 25 llamadas/día
    """
    if not ALPHA_VANTAGE_KEY:
        raise ValueError("Alpha Vantage API key no configurada. Agrega ALPHA_VANTAGE_KEY en .env")

    interval_map = {"1d": "DAILY_ADJUSTED", "1wk": "WEEKLY_ADJUSTED", "1mo": "MONTHLY_ADJUSTED"}
    av_function = f"TIME_SERIES_{interval_map.get(interval, 'DAILY_ADJUSTED')}"

    url = "https://www.alphavantage.co/query"
    params = {
        "function": av_function,
        "symbol": ticker,
        "apikey": ALPHA_VANTAGE_KEY,
        "outputsize": "full",
        "datatype": "json",
    }

    full_url = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full_url, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    # Detectar error en respuesta
    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage no reconoce el ticker '{ticker}'")
    if "Note" in data:
        raise ValueError("Límite de llamadas de Alpha Vantage alcanzado. Espera un minuto e intenta de nuevo.")

    # Buscar la clave de la serie temporal en la respuesta
    ts_key = next((k for k in data if "Time Series" in k), None)
    if not ts_key:
        raise ValueError(f"Alpha Vantage no devolvió datos para '{ticker}'")

    ts = data[ts_key]
    records = []
    for date_str, vals in ts.items():
        # Alpha Vantage usa claves como "1. open", "2. high", etc.
        keys = list(vals.keys())
        records.append({
            "Date": pd.to_datetime(date_str),
            "Open": float(vals.get(keys[0], 0)),
            "High": float(vals.get(keys[1], 0)),
            "Low": float(vals.get(keys[2], 0)),
            "Close": float(vals.get(keys[3], 0)),
            "Volume": float(vals.get(keys[4], 0)) if len(keys) > 4 else 0.0,
        })

    hist = pd.DataFrame(records).set_index("Date").sort_index()
    hist = _filter_by_period(hist, period)

    if hist.empty:
        raise ValueError(f"Sin datos para '{ticker}' con el periodo '{period}' en Alpha Vantage")

    return {
        "ticker": ticker.upper(),
        "company_name": ticker.upper(),
        "currency": "USD",
        "asset_type": "stock",
        "provider": "Alpha Vantage",
        "hist": hist,
        "info": {},
        "fundamentals": {},
        "earnings_data": {"has_quarterly": False},
    }


def _filter_by_period(hist: pd.DataFrame, period: str) -> pd.DataFrame:
    """Filtra el DataFrame por periodo cuando Alpha Vantage devuelve datos completos."""
    period_days = {"6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 99999}
    days = period_days.get(period, 365)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return hist[hist.index >= cutoff]


# ---------------------------------------------------------------------------
# Proveedor 3: Finnhub (solo noticias y earnings calendar)
# ---------------------------------------------------------------------------

def get_finnhub_news(ticker: str) -> list:
    """
    [PROVEEDOR ADICIONAL — Finnhub]

    Obtiene noticias recientes del activo. Solo se usa si hay FINNHUB_KEY en .env.
    Documentación: https://finnhub.io/docs/api
    Límite gratuito: 60 llamadas/minuto

    Para activar: agrega FINNHUB_KEY=tu_key en el archivo .env
    """
    if not FINNHUB_KEY:
        return []

    today = date.today()
    from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    url = "https://finnhub.io/api/v1/company-news"
    params = {"symbol": ticker, "from": from_date, "to": to_date, "token": FINNHUB_KEY}

    try:
        full_url = url + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(full_url, timeout=10) as resp:
            news = json.loads(resp.read().decode())
        return news[:5] if isinstance(news, list) else []
    except Exception:
        return []
