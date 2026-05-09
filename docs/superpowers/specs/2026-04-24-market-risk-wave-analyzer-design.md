# Market Risk & Wave Analyzer — Design Spec
**Date:** 2026-04-24  
**Status:** Approved by user  
**Project location:** `C:\Users\marwi\Desktop\Programar\market-risk-wave-analyzer`

---

## 1. Overview

A local web tool for analyzing financial assets (stocks, ETFs, commodities, crypto, forex) that generates a 2-page dark HTML risk report with technical analysis, Fibonacci levels, Elliott Wave hypothesis, and a 0-100 risk score. Built for personal use to research assets before trading.

---

## 2. Architecture

**Pattern:** Backend + Frontend separated (Option B)

```
market-risk-wave-analyzer/
│
├── backend/
│   ├── main.py              ← FastAPI server + /api/analyze endpoint
│   ├── data_provider.py     ← Unified data layer (Yahoo / Alpha Vantage / Finnhub)
│   ├── indicators.py        ← Technical indicators (SMA, EMA, RSI, MACD, ATR, etc.)
│   ├── fibonacci.py         ← Swing detection + Fibonacci levels 0%-161.8%
│   ├── elliott.py           ← Probabilistic Elliott Wave detection
│   ├── risk_score.py        ← 0-100 risk score (35/35/30 weighting)
│   ├── report_generator.py  ← Assembles final JSON report
│   └── requirements.txt     ← Python dependencies
│
├── frontend/
│   ├── index.html           ← Search screen + 2-page dark report
│   ├── styles.css           ← Dark professional theme (#08090d)
│   └── app.js               ← Fetch API, SVG rendering, clipboard export
│
├── .env.example             ← API key template
└── README.md                ← Step-by-step guide for beginners
```

**Data flow:**
```
User types AAPL
  → app.js: GET /api/analyze?ticker=AAPL&period=1y&interval=1d
  → data_provider.py: download OHLCV + fundamentals
  → indicators.py: compute all technicals
  → fibonacci.py: detect swing high/low, compute levels
  → elliott.py: detect pivots, label wave hypothesis
  → risk_score.py: compute 0-100 score
  → report_generator.py: assemble JSON
  → app.js: render dark 2-page HTML report
```

---

## 3. Data Layer (`data_provider.py`)

**Priority order:**
1. **Yahoo Finance** (`yfinance`) — default, free, no key, OHLCV + partial fundamentals
2. **Alpha Vantage** — if API key in `.env`, better fundamentals + earnings
3. **Finnhub** — if API key in `.env`, news + earnings calendar
4. **Graceful fallback** — clear error message to user if all fail

**Data by source:**

| Data | Yahoo Finance | Alpha Vantage | Finnhub |
|---|---|---|---|
| Historical OHLCV | ✅ | ✅ | ✅ |
| Name, currency | ✅ | ✅ | ✅ |
| Fundamentals (P/E, debt) | ✅ partial | ✅ better | ❌ |
| Earnings / news | ❌ | ✅ | ✅ |
| Crypto (BTC-USD) | ✅ | ✅ | ✅ |
| Commodities (GC=F, CL=F) | ✅ | ❌ | ❌ |

**Extensibility:** Adding TradingView or any new provider requires only adding a new class in `data_provider.py` following the same interface. Nothing else changes.

**API keys:** Stored in `.env` file (never committed). Template in `.env.example`.

---

## 4. Analysis Modules

### `indicators.py`
- SMA 20, SMA 50, SMA 200
- EMA 20
- RSI 14
- MACD + signal line + histogram
- ATR (Average True Range)
- Annualized volatility
- Maximum drawdown
- Returns: 1M, 3M, 6M, 12M
- Average volume (20 days)
- Distance from price to SMA 200
- Overall trend: bullish / neutral / bearish

### `fibonacci.py`
- Detects swing high and swing low for selected period
- Computes levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%, 127.2%, 161.8%
- Interprets where current price sits relative to levels in plain language

### `elliott.py`
- Detects pivots (local highs/lows) using scipy
- Simplifies price series into major swings
- Attempts to label 1-2-3-4-5 impulse or A-B-C correction
- Validates 3 basic Elliott rules:
  - Wave 2 must not retrace more than 100% of wave 1
  - Wave 3 must not be the shortest
  - Wave 4 must not strongly overlap wave 1
- Returns confidence: high / medium / low
- Uses prudent language: "could", "possible", "probable zone", "invalidation level"
- Includes disclaimer: "This is not financial advice"

**Output:**
```json
{
  "wave_count_candidate": "1-2-3-4-5",
  "current_possible_wave": "4",
  "confidence": "medium",
  "invalidation_level": 185.40,
  "explanation_simple": "Posible estructura impulsiva en desarrollo...",
  "pivots": [...],
  "warnings": ["Wave 4 not yet confirmed"]
}
```

### `risk_score.py`
- **35% Technical:** trend vs SMA200, volatility, drawdown, extreme RSI, negative MACD, broken supports
- **35% Financial:** revenue growth, profit margin, debt/equity, FCF, EPS trend — marked "N/A" if unavailable, weight redistributed
- **30% Momentum/Events:** recent returns, volume anomaly, gap detection, proximity to earnings

**Output:**
```json
{
  "technical": {"score": 22, "weight": 35, "explanation": "..."},
  "financial": {"score": 18, "weight": 35, "explanation": "..."},
  "momentum_events": {"score": 20, "weight": 30, "explanation": "..."},
  "total": 60
}
```

**Interpretation:**
- 0-30: Low risk (green)
- 31-60: Medium risk (amber)
- 61-80: High risk (red)
- 81-100: Extreme risk (dark red)

---

## 5. Frontend Design

### Search Screen
- Ticker input field
- Period selector: 6m / 1y / 2y / 5y / max
- Interval selector: 1d / 1wk / 1mo
- "Analyze" button

### Page 1
- **A. Header:** ticker, name, price, daily change, currency, last update, data provider
- **B. Risk Gauge:** circular/semicircular SVG gauge 0-100 with color zones
- **C. KPI Strip:** 8 metrics in one row (price, 1M/3M/12M return, volatility, drawdown, RSI, distance vs SMA200)
- **D. SVG Price Chart:** price line + SMA50 + SMA200 + Fibonacci markers + Elliott pivot points + basic tooltip
- **E. Analysis Cards:** 3 grids × 6 cards each:
  - Valuation: P/E, Forward P/E, P/S, P/B, EV/EBITDA, Dividend Yield
  - Financial Health: Debt/Equity, Current Ratio, FCF, Gross Margin, Operating Margin, Net Margin
  - Growth: Revenue Growth, EPS Growth, EBITDA Growth, FCF Growth, Guidance, Earnings Surprise
  - Card states: green (beats), red (misses), amber (caution), gray (unavailable)
- **F. Score Breakdown Bars:** Technical 35% / Financial 35% / Momentum 30%

### Page 2
- **A. Quarterly Trend Table:** Quarter, Revenue, EPS, Margin, FCF, Debt, Notes
- **B. Latest Earnings Update:** text summary, "unavailable" message if no data
- **C. Elliott Wave Analysis:** candidate structure, current wave, confidence, invalidation, explanation
- **D. Fibonacci Analysis:** table of levels vs current price, support/resistance interpretation
- **E. Catalysts vs Risks:** two-column layout
- **F. Bottom Line:** rating bar + verdict label + short explanation + disclaimer

### Export Buttons
- **"Copy Report"** → clipboard: text summary (asset, score, trend, Elliott, Fibonacci, catalysts, risks, verdict)
- **"Copy JSON"** → clipboard: full raw JSON response

### Visual Design
- Background: `#08090d`
- Cards: `#11131a`
- Borders: `#242838`
- Primary text: `#f5f7fa`
- Secondary text: `#9ca3af`
- Green: `#22c55e` | Red: `#ef4444` | Amber: `#f59e0b` | Blue: `#38bdf8` | Purple: `#a78bfa`
- Fonts: DM Sans (body) + JetBrains Mono (numbers)

---

## 6. Error Handling

### Asset type behavior

| Type | Example | Fundamentals | Earnings | Behavior |
|---|---|---|---|---|
| US Stock | AAPL, NVDA | ✅ full | ✅ | Full report |
| ETF | SPY, QQQ, GLD | ⚠️ partial | ❌ | Cards show N/A where needed |
| Commodity futures | CL=F, GC=F | ❌ | ❌ | Technical-only report |
| Crypto | BTC-USD | ❌ | ❌ | Technical-only report |
| Forex | XAUUSD | ⚠️ limited | ❌ | Technical-only report |

### Error messages (plain language)
- Invalid ticker → "No encontré datos para 'XYZ'. Prueba con AAPL, SPY o BTC-USD."
- No historical data → warning shown, chart skipped
- Missing fundamentals → card shows gray "N/A" state
- No internet → clear connection error message
- Invalid API key → warns which provider failed, uses next available

---

## 7. Test Tickers

| Ticker | Type | Expected |
|---|---|---|
| AAPL | Stock | Full report |
| NVDA | Stock | Full report |
| SPY | ETF | Partial fundamentals |
| GLD | ETF | Technical only |
| USO | ETF | Technical only |
| BTC-USD | Crypto | Technical only |
| CL=F | Commodity | Technical only |
| GC=F | Commodity | Technical only |

---

## 8. Technology Stack

**Backend:**
- Python 3.10+
- FastAPI
- uvicorn
- pandas + numpy
- yfinance
- pandas-ta (technical indicators)
- scipy (pivot detection for Elliott)
- python-dotenv (API key management)
- httpx (Alpha Vantage + Finnhub HTTP calls)

**Frontend:**
- HTML5 + CSS3 + Vanilla JavaScript
- SVG (native, no chart library)
- Google Fonts: DM Sans + JetBrains Mono

---

## 9. Constraints & Limitations

- Elliott Wave is a probabilistic hypothesis, not a prediction
- Yahoo Finance free tier: rate limits apply with high usage
- Alpha Vantage free tier: 25 calls/day
- Finnhub free tier: 60 calls/minute
- Commodities and crypto have no fundamental data — technical-only analysis
- No real-time data — uses end-of-day or delayed data depending on provider
- This tool is for educational purposes only, not financial advice

---

## 10. Future Extensions (not in scope for v1)

- TradingView integration (when/if official API becomes available)
- Polygon.io, Twelve Data, Tiingo, Nasdaq Data Link
- Real-time streaming prices
- Portfolio-level risk analysis
- Alert system for risk threshold breaches
- React/Vue frontend upgrade
