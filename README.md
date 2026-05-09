# Market Risk & Wave Analyzer

Herramienta web local para análisis técnico profesional de activos financieros.
Genera un reporte oscuro de 2 páginas con risk score 0-100, Fibonacci, ondas de Elliott y más.

---

## ¿Qué hace?

- Descarga datos históricos de cualquier activo (acciones, ETFs, crypto, commodities)
- Calcula indicadores técnicos: SMA, EMA, RSI, MACD, ATR, volatilidad, drawdown
- Detecta niveles de Fibonacci (0% a 161.8%)
- Analiza posibles ondas de Elliott (hipótesis probabilística)
- Calcula un Risk Score de 0 a 100
- Genera un reporte visual oscuro profesional con 2 páginas
- Permite copiar el reporte al portapapeles

---

## Tecnologías

**Backend:** Python 3.10+ · FastAPI · uvicorn · pandas · numpy · yfinance · ta · scipy

**Frontend:** HTML5 · CSS3 · JavaScript vanilla · SVG nativo

---

## Instalación paso a paso (Windows)

### Paso 1 — Verifica que tienes Python instalado

Abre PowerShell (busca "PowerShell" en el menú de inicio) y escribe:

```powershell
python --version
```

Debes ver algo como `Python 3.11.x`. Si ves un error, descarga Python en https://www.python.org/downloads/

### Paso 2 — Navega a la carpeta del backend

```powershell
cd "C:\Users\marwi\Desktop\Programar\market-risk-wave-analyzer\backend"
```

### Paso 3 — Crea el entorno virtual

Un entorno virtual es una caja aislada donde se instalan las librerías solo para este proyecto.

```powershell
python -m venv venv
```

Verás que se crea una carpeta llamada `venv`. Eso es correcto.

### Paso 4 — Activa el entorno virtual

```powershell
.\venv\Scripts\activate
```

Sabrás que funcionó porque verás `(venv)` al inicio de la línea en PowerShell.

### Paso 5 — Instala las dependencias

```powershell
pip install -r requirements.txt
```

Esto puede tardar 2-5 minutos dependiendo de tu conexión. Es normal.

### Paso 6 — (Opcional) Configura tus API keys

Si tienes API keys de Alpha Vantage o Finnhub:

1. Ve a la carpeta raíz del proyecto: `C:\Users\marwi\Desktop\Programar\market-risk-wave-analyzer`
2. Copia el archivo `.env.example` y renómbralo a `.env`
3. Abre `.env` con el Bloc de notas
4. Pega tus API keys donde dice `TU_API_KEY_AQUI`

Si no tienes keys, el sistema funciona perfectamente con Yahoo Finance (gratis).

### Paso 7 — Corre el servidor

```powershell
uvicorn main:app --reload
```

Verás algo así en la pantalla:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

El servidor está corriendo. **No cierres esta ventana.**

### Paso 8 — Abre el frontend

Tienes 2 opciones:

**Opción A (más fácil):** Abre el archivo `frontend/index.html` directamente en Chrome o Edge haciendo doble clic.

**Opción B (recomendada):** Instala la extensión "Live Server" en VS Code y abre el archivo con "Open with Live Server".

**Opción C:** Abre otra ventana de PowerShell y ejecuta:
```powershell
cd "C:\Users\marwi\Desktop\Programar\market-risk-wave-analyzer\frontend"
python -m http.server 5500
```
Luego abre http://127.0.0.1:5500 en tu navegador.

---

## Ejemplos de tickers

| Ticker  | Tipo      | Descripción                    |
|---------|-----------|--------------------------------|
| AAPL    | Acción    | Apple Inc.                     |
| NVDA    | Acción    | NVIDIA Corporation             |
| MSFT    | Acción    | Microsoft Corporation          |
| TSLA    | Acción    | Tesla Inc.                     |
| SPY     | ETF       | S&P 500 (SPDR)                 |
| QQQ     | ETF       | Nasdaq 100 (Invesco)           |
| GLD     | ETF       | Oro (SPDR Gold Shares)         |
| USO     | ETF       | Petróleo crudo (US Oil Fund)   |
| BTC-USD | Crypto    | Bitcoin en dólares             |
| ETH-USD | Crypto    | Ethereum en dólares            |
| GC=F    | Commodity | Oro (futuros)                  |
| CL=F    | Commodity | Petróleo WTI (futuros)         |
| XAUUSD  | Forex     | Oro en USD (par de divisas)    |

---

## Correr los tests

Con el entorno virtual activado, desde la carpeta `backend`:

```powershell
pytest tests/ -v
```

---

## Solución de problemas comunes

### Error: "uvicorn no se reconoce como comando"
El entorno virtual no está activado. Ejecuta:
```powershell
.\venv\Scripts\activate
```
Luego intenta de nuevo.

### Error: "No module named 'fastapi'"
Las dependencias no se instalaron. Ejecuta:
```powershell
pip install -r requirements.txt
```

### El frontend dice "No pude conectar con el servidor"
El backend no está corriendo. Abre PowerShell y ejecuta:
```powershell
cd "C:\Users\marwi\Desktop\Programar\market-risk-wave-analyzer\backend"
.\venv\Scripts\activate
uvicorn main:app --reload
```

### Error: "No encontré datos para 'XYZ'"
- Verifica que el ticker esté bien escrito
- Algunos tickers requieren formato especial: `BTC-USD`, `GC=F`, `CL=F`
- Yahoo Finance puede tener restricciones temporales. Espera unos minutos e intenta de nuevo.

### La pantalla se queda en "Cargando..."
Abre las herramientas de desarrollador del navegador (F12) y ve a la pestaña "Console".
Si ves un error CORS, asegúrate de que el backend esté corriendo y que la URL sea `http://127.0.0.1:8000`.

### pip install falla con errores de compilación
Actualiza pip primero:
```powershell
python -m pip install --upgrade pip
```
Luego intenta instalar de nuevo.

---

## Limitaciones importantes

### Elliott Wave
- Las ondas de Elliott son **subjetivas e interpretativas**
- El análisis del sistema es una **hipótesis probabilística**, no una predicción
- La confianza puede ser baja o media — esto es normal
- No tomes decisiones financieras basadas solo en este análisis

### Datos gratuitos (Yahoo Finance)
- Los datos son de cierre del día anterior (no tiempo real)
- Yahoo Finance puede tener limitaciones de velocidad con uso intensivo
- Algunos fundamentales pueden no estar disponibles para todos los activos
- Crypto, commodities y ETFs no tienen datos fundamentales (P/E, EPS, etc.)

### Alpha Vantage (plan gratuito)
- 25 llamadas por día
- Algunos activos no están disponibles (commodities, crypto limitado)

### Finnhub (plan gratuito)
- 60 llamadas por minuto
- Solo se usa para noticias recientes en esta versión

---

## Cómo conectar una API paga en el futuro

1. Abre `backend/data_provider.py`
2. Crea una nueva función siguiendo el patrón de `_get_yahoo_data()`:
   ```python
   def _get_polygon_data(ticker, period, interval):
       # Tu código aquí
       return { "ticker": ..., "hist": ..., ... }
   ```
3. En `get_market_data()`, añade tu función como primera opción:
   ```python
   def get_market_data(ticker, period, interval):
       return _get_polygon_data(ticker, period, interval)  # Nueva primera opción
       # ... resto del código
   ```
4. El resto del sistema (indicators, fibonacci, elliott, risk_score) no necesita cambios.

---

## Próximos pasos recomendados

- [ ] Conectar Alpha Vantage para fundamentales más completos
- [ ] Agregar datos trimestrales reales (necesita Alpha Vantage o Finnhub premium)
- [ ] Implementar alertas de riesgo por email
- [ ] Agregar análisis de portfolio (múltiples activos)
- [ ] Integrar Polygon.io para datos en tiempo real
- [ ] Mejorar la detección de ondas de Elliott con algoritmos más sofisticados
- [ ] Agregar backtesting básico de señales

---

## Descargo de responsabilidad

Esta herramienta es **únicamente para fines educativos e informativos**.
No constituye asesoría financiera, recomendación de inversión, ni señal de compra o venta.
Siempre haz tu propia investigación (DYOR) antes de tomar decisiones financieras.
