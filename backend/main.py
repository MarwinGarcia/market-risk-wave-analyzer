"""
main.py
========
Punto de entrada del servidor. FastAPI recibe peticiones del frontend
y devuelve el análisis completo en formato JSON.

Para correr el servidor:
  uvicorn main:app --reload

El servidor queda disponible en: http://127.0.0.1:8000
Documentación automática en:    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from report_generator import generate_report

# ---------------------------------------------------------------------------
# Crear la aplicación FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Market Risk & Wave Analyzer API",
    description="Análisis técnico, Fibonacci, ondas de Elliott y risk score 0-100",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS: permite que el archivo HTML pueda llamar al backend
# Sin esto el navegador bloquea las peticiones
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # En producción: cambia por tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """
    Endpoint de verificación.
    Abre http://127.0.0.1:8000 en el navegador — si ves este mensaje, el servidor funciona.
    """
    return {
        "status": "ok",
        "message": "Market Risk & Wave Analyzer API funcionando correctamente ✓",
        "uso": "GET /api/analyze?ticker=AAPL&period=1y&interval=1d",
        "docs": "http://127.0.0.1:8000/docs",
    }


@app.get("/api/analyze")
def analyze(
    ticker: str = Query(..., description="Símbolo del activo: AAPL, BTC-USD, GC=F, SPY…"),
    period: str = Query("1y", description="Periodo: 6mo | 1y | 2y | 5y | max"),
    interval: str = Query("1d", description="Intervalo: 1d | 1wk | 1mo"),
):
    """
    Analiza un activo financiero y devuelve el reporte completo.

    Ejemplos de uso:
    - /api/analyze?ticker=AAPL
    - /api/analyze?ticker=BTC-USD&period=2y
    - /api/analyze?ticker=GC=F&period=1y&interval=1d
    - /api/analyze?ticker=SPY&period=5y&interval=1wk
    """
    ticker = ticker.strip().upper()

    if not ticker:
        raise HTTPException(status_code=400, detail="El ticker no puede estar vacío.")

    valid_intervals = ["15m", "1h", "4h", "1d", "1wk", "1mo"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Intervalo inválido '{interval}'. Usa uno de: {', '.join(valid_intervals)}",
        )

    # Limitar periodos según el intervalo (yfinance tiene límites para intradiario)
    # 15m → máximo 60 días | 1h/4h → máximo 2 años
    intraday_max = {"15m": "1mo", "1h": "1y", "4h": "1y"}
    if interval in intraday_max:
        intraday_valid = {
            "15m": ["5d", "1mo"],
            "1h":  ["5d", "1mo", "3mo", "6mo", "1y"],
            "4h":  ["5d", "1mo", "3mo", "6mo", "1y"],
        }
        valid_periods = intraday_valid[interval]
        if period not in valid_periods:
            # Auto-ajustar al máximo permitido
            period = intraday_max[interval]
    else:
        valid_periods = ["6mo", "1y", "2y", "5y", "max"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Periodo inválido '{period}'. Usa uno de: {', '.join(valid_periods)}",
            )

    try:
        report = generate_report(ticker, period, interval)
        return JSONResponse(content=report)

    except ValueError as e:
        # Error controlado: ticker inválido, sin datos, etc.
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Error inesperado: loguear y devolver mensaje amigable
        print(f"\n[ERROR] Analizando {ticker}:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error interno al analizar '{ticker}'. "
                "Verifica que el ticker sea válido e intenta de nuevo. "
                "Ejemplos válidos: AAPL, NVDA, SPY, GLD, BTC-USD, GC=F, CL=F"
            ),
        )
