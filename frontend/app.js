/**
 * app.js
 * ======
 * Lógica del frontend:
 *  - Llama al backend (/api/analyze)
 *  - Renderiza el reporte de 2 páginas
 *  - Dibuja el gráfico SVG nativo (precio + SMAs + Fibonacci + Elliott)
 *  - Dibuja el gauge de riesgo SVG
 *  - Maneja los botones de exportar (Copy Report / Copy JSON)
 *
 * El backend debe estar corriendo en http://127.0.0.1:8000
 * Para cambiarlo, modifica la constante API_BASE abajo.
 */

// En localhost usa el backend local; en producción usa la variable global BACKEND_URL
// que se define en index.html antes de cargar este script.
const API_BASE = (typeof BACKEND_URL !== 'undefined' && BACKEND_URL)
  ? BACKEND_URL
  : 'http://127.0.0.1:8000';

// Referencia global al último JSON recibido (para Copy JSON)
let lastReport = null;

// ============================================================
// Navegación entre pantallas
// ============================================================

function showScreen(id) {
  ['search-screen', 'loading', 'error-screen', 'report-screen']
    .forEach(s => {
      const el = document.getElementById(s);
      if (el) el.style.display = s === id ? (s === 'loading' ? 'flex' : 'block') : 'none';
    });
  // La pantalla de loading usa flex
  if (id === 'loading') document.getElementById('loading').style.display = 'flex';
}

function goBack() {
  showScreen('search-screen');
  window.scrollTo(0, 0);
}

function showError(msg) {
  document.getElementById('error-msg').textContent = msg;
  showScreen('error-screen');
}

// ============================================================
// Análisis rápido desde ejemplos
// ============================================================

function quickAnalyze(ticker) {
  document.getElementById('ticker-input').value = ticker;
  runAnalysis();
}

// ============================================================
// Análisis principal
// ============================================================

async function runAnalysis() {
  const ticker   = (document.getElementById('ticker-input').value || '').trim().toUpperCase();
  const period   = document.getElementById('period-select').value;
  const interval = document.getElementById('interval-select').value;

  if (!ticker) {
    document.getElementById('ticker-input').focus();
    return;
  }

  // Loading
  showScreen('loading');
  document.getElementById('loading-ticker').textContent = ticker;

  const steps = [
    'Descargando datos históricos...',
    'Calculando indicadores técnicos...',
    'Analizando niveles de Fibonacci...',
    'Detectando posibles ondas de Elliott...',
    'Calculando risk score...',
    'Generando reporte...',
  ];
  let stepIdx = 0;
  const stepEl = document.getElementById('loading-steps');
  stepEl.textContent = steps[0];
  const stepTimer = setInterval(() => {
    stepIdx = (stepIdx + 1) % steps.length;
    stepEl.textContent = steps[stepIdx];
  }, 1400);

  try {
    const url = `${API_BASE}/api/analyze?ticker=${encodeURIComponent(ticker)}&period=${period}&interval=${interval}`;
    const resp = await fetch(url);

    clearInterval(stepTimer);

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      showError(err.detail || `Error ${resp.status}. Verifica el ticker e intenta de nuevo.`);
      return;
    }

    const data = await resp.json();
    lastReport = data;

    renderReport(data);
    showScreen('report-screen');
    window.scrollTo(0, 0);

  } catch (e) {
    clearInterval(stepTimer);
    showError(
      'No pude conectar con el servidor. ' +
      'Asegúrate de que el backend esté corriendo: uvicorn main:app --reload'
    );
  }
}

// Permitir Enter en el input
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('ticker-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') runAnalysis();
  });
});

// Ajustar opciones de periodo según el intervalo seleccionado
function onIntervalChange() {
  const interval = document.getElementById('interval-select').value;
  const periodSel = document.getElementById('period-select');

  const intraday = {
    '15m': [['5d','5 Días'], ['1mo','1 Mes']],
    '1h':  [['5d','5 Días'], ['1mo','1 Mes'], ['3mo','3 Meses'], ['6mo','6 Meses'], ['1y','1 Año']],
    '4h':  [['5d','5 Días'], ['1mo','1 Mes'], ['3mo','3 Meses'], ['6mo','6 Meses'], ['1y','1 Año']],
  };

  const standard = [
    ['6mo','6 Meses'], ['1y','1 Año'], ['2y','2 Años'], ['5y','5 Años'], ['max','Máximo']
  ];

  const options = intraday[interval] || standard;
  const current = periodSel.value;

  periodSel.innerHTML = options.map(([val, label]) =>
    `<option value="${val}">${label}</option>`
  ).join('');

  // Seleccionar el último disponible por defecto para intradiario
  if (intraday[interval]) {
    periodSel.value = options[options.length - 1][0];
  } else {
    // Intentar mantener la selección anterior
    if ([...periodSel.options].some(o => o.value === current)) {
      periodSel.value = current;
    }
  }
}

// ============================================================
// Render principal del reporte
// ============================================================

function renderReport(d) {
  renderHeader(d);
  renderGauge(d.risk_score, d.risk_color, d.risk_label, d.technical_summary);
  renderKpiStrip(d);
  renderChart(d);
  renderCards('valuation-cards',       d.valuation_cards);
  renderCards('financial-health-cards', d.financial_health_cards);
  renderCards('growth-cards',           d.growth_cards);
  renderScoreBreakdown(d.score_breakdown);
  renderQuarterlyTable(d.quarterly_trend_table);
  renderElliott(d.elliott_wave_analysis);
  renderFibonacci(d.fibonacci_levels);
  renderCatalystsRisks(d.catalysts, d.risks);
  renderBottomLine(d.verdict, d.risk_score);
}

// ============================================================
// Header
// ============================================================

function renderHeader(d) {
  document.getElementById('r-ticker').textContent = d.ticker;
  document.getElementById('r-name').textContent   = d.company_name;

  const priceEl  = document.getElementById('r-price');
  priceEl.textContent = fmt(d.latest_price, 2, d.currency);

  const changeEl = document.getElementById('r-change');
  const chg  = d.price_change ?? 0;
  const sign = chg >= 0 ? '+' : '';
  changeEl.textContent = `${sign}${chg.toFixed(2)} (${sign}${(d.price_change_percent ?? 0).toFixed(2)}%)`;
  changeEl.className   = `price-change mono ${chg >= 0 ? 'up' : 'down'}`;

  const intervalLabel = {
    '15m': '15 Minutos', '1h': '1 Hora', '4h': '4 Horas',
    '1d': 'Diario', '1wk': 'Semanal', '1mo': 'Mensual'
  }[d.interval] || d.interval;

  document.getElementById('r-meta').textContent =
    `Datos al ${d.latest_update}  |  Proveedor: ${d.provider}  |  Periodo: ${d.period}  |  Timeframe: ${intervalLabel}`;

  const badge = document.getElementById('r-asset-badge');
  badge.textContent = capitalize(d.asset_type);
  badge.className   = `asset-badge ${d.asset_type}`;
}

// ============================================================
// Risk Gauge (SVG semicircular)
// ============================================================

function renderGauge(score, color, label, summary) {
  const svg    = document.getElementById('gauge-svg');
  const W = 200, H = 110, R = 88, cx = 100, cy = 100;
  const startAngle = 180, endAngle = 0; // semicírculo superior

  function polarToXY(deg, radius) {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy - radius * Math.sin(rad) };
  }

  function arcPath(startDeg, endDeg, r) {
    const s = polarToXY(startDeg, r);
    const e = polarToXY(endDeg, r);
    const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 0 ${e.x} ${e.y}`;
  }

  // El gauge va de 180° (izq) a 0° (der) — score 0→100 mapea a 180→0
  const scoreAngle = 180 - (score / 100) * 180;

  // Zonas de color (fondo)
  const zones = [
    { from: 180, to: 126, color: '#22c55e' },  // 0-30: verde
    { from: 126, to:  54, color: '#f59e0b' },  // 31-60: ámbar
    { from:  54, to:  18, color: '#ef4444' },  // 61-80: rojo
    { from:  18, to:   0, color: '#7f1d1d' },  // 81-100: rojo oscuro
  ];

  let svgHtml = '';

  // Track de fondo
  svgHtml += `<path d="${arcPath(180, 0, R)}" fill="none" stroke="#242838" stroke-width="16" stroke-linecap="round"/>`;

  // Zonas coloreadas
  zones.forEach(z => {
    const to = Math.max(z.to, scoreAngle); // solo hasta el ángulo actual
    if (z.from > scoreAngle) {
      svgHtml += `<path d="${arcPath(z.from, Math.max(z.to, scoreAngle), R)}" fill="none" stroke="${z.color}" stroke-width="16" stroke-linecap="butt" opacity="0.25"/>`;
    }
  });

  // Arco activo (del score)
  svgHtml += `<path d="${arcPath(180, scoreAngle, R)}" fill="none" stroke="${color}" stroke-width="16" stroke-linecap="round"/>`;

  // Aguja
  const needle = polarToXY(scoreAngle, R - 8);
  svgHtml += `<circle cx="${needle.x}" cy="${needle.y}" r="8" fill="${color}" />`;
  svgHtml += `<circle cx="${needle.x}" cy="${needle.y}" r="4" fill="#08090d" />`;

  // Etiquetas 0 y 100
  svgHtml += `<text x="8"   y="108" fill="#6b7280" font-size="10" font-family="JetBrains Mono">0</text>`;
  svgHtml += `<text x="182" y="108" fill="#6b7280" font-size="10" font-family="JetBrains Mono">100</text>`;

  svg.innerHTML = svgHtml;

  document.getElementById('gauge-number').textContent = score;
  document.getElementById('gauge-number').style.color = color;
  document.getElementById('gauge-risk-label').textContent = label;
  document.getElementById('gauge-risk-label').style.color  = color;
  document.getElementById('gauge-summary').textContent    = summary || '';
}

// ============================================================
// KPI Strip
// ============================================================

function renderKpiStrip(d) {
  const ind = d.indicators || {};

  const kpis = [
    { label: 'Precio',       value: fmt(d.latest_price, 2, d.currency),          sub: d.currency, color: null },
    { label: 'Retorno 1M',   value: fmtPct(ind.return_1m),                        sub: '1 mes',    color: signColor(ind.return_1m) },
    { label: 'Retorno 3M',   value: fmtPct(ind.return_3m),                        sub: '3 meses',  color: signColor(ind.return_3m) },
    { label: 'Retorno 12M',  value: fmtPct(ind.return_12m),                       sub: '12 meses', color: signColor(ind.return_12m) },
    { label: 'Volatilidad',  value: ind.annual_volatility != null ? `${ind.annual_volatility.toFixed(1)}%` : 'N/A', sub: 'anualizada', color: null },
    { label: 'Drawdown Max', value: ind.max_drawdown != null ? `${ind.max_drawdown.toFixed(1)}%` : 'N/A', sub: 'máximo',     color: '#ef4444' },
    { label: 'RSI',          value: ind.rsi != null ? ind.rsi.toFixed(1) : 'N/A',  sub: rsiLabel(ind.rsi), color: rsiColor(ind.rsi) },
    { label: 'vs SMA200',    value: ind.dist_sma200_pct != null ? `${ind.dist_sma200_pct > 0 ? '+' : ''}${ind.dist_sma200_pct.toFixed(1)}%` : 'N/A', sub: 'distancia', color: signColor(ind.dist_sma200_pct) },
  ];

  document.getElementById('kpi-strip').innerHTML = kpis.map(k => `
    <div class="kpi-item">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value mono" style="${k.color ? `color:${k.color}` : ''}">${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join('');
}

// ============================================================
// Gráfico SVG principal
// ============================================================

function renderChart(d) {
  const svg  = document.getElementById('main-chart');
  const W    = 900, H = 320;
  const PAD  = { top: 20, right: 20, bottom: 30, left: 60 };
  const iW   = W - PAD.left - PAD.right;
  const iH   = H - PAD.top  - PAD.bottom;

  const prices     = d.price_series   || [];
  const sma50      = d.sma_50_series  || [];
  const sma200     = d.sma_200_series || [];
  const dates      = d.dates_series   || [];
  const fibLvls    = d.fibonacci_levels?.levels;
  const waveGroups = d.elliott_wave_analysis?.wave_groups || [];

  if (!prices.length) { svg.innerHTML = '<text x="50%" y="50%" fill="#6b7280" text-anchor="middle">Sin datos de precio</text>'; return; }

  // Determinar rango Y incluyendo SMAs y Fibonacci
  const allVals = [...prices.filter(v => v != null)];
  if (fibLvls) Object.values(fibLvls).forEach(v => allVals.push(v));

  const minY = Math.min(...allVals) * 0.995;
  const maxY = Math.max(...allVals) * 1.005;
  const rangeY = maxY - minY;

  const n = prices.length;

  function scaleX(i) { return PAD.left + (i / (n - 1)) * iW; }
  function scaleY(v) { return PAD.top + iH - ((v - minY) / rangeY) * iH; }

  function makeLine(arr, color, sw = 1.5, dash = '') {
    let d_ = '', first = true;
    arr.forEach((v, i) => {
      if (v == null) { first = true; return; }
      const x = scaleX(i), y = scaleY(v);
      d_ += first ? `M${x},${y}` : `L${x},${y}`;
      first = false;
    });
    return d_ ? `<path d="${d_}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-dasharray="${dash}" vector-effect="non-scaling-stroke"/>` : '';
  }

  let html = '';

  // Fondo
  html += `<rect x="${PAD.left}" y="${PAD.top}" width="${iW}" height="${iH}" fill="#0d0f18" rx="8"/>`;

  // Líneas de cuadrícula horizontales
  for (let i = 0; i <= 4; i++) {
    const y = PAD.top + (iH / 4) * i;
    const v = maxY - (rangeY / 4) * i;
    html += `<line x1="${PAD.left}" y1="${y}" x2="${PAD.left + iW}" y2="${y}" stroke="#242838" stroke-width="1"/>`;
    html += `<text x="${PAD.left - 6}" y="${y + 4}" fill="#6b7280" font-size="10" text-anchor="end" font-family="JetBrains Mono">${v.toFixed(2)}</text>`;
  }

  // Etiquetas del eje X (4 fechas)
  const xLabels = [0, Math.floor(n * 0.25), Math.floor(n * 0.5), Math.floor(n * 0.75), n - 1];
  xLabels.forEach(i => {
    if (!dates[i]) return;
    const x = scaleX(i);
    html += `<text x="${x}" y="${H - 8}" fill="#6b7280" font-size="10" text-anchor="middle" font-family="JetBrains Mono">${dates[i]}</text>`;
  });

  // Área bajo el precio
  if (prices.filter(v => v != null).length > 1) {
    let areaPath = '';
    let first = true;
    prices.forEach((v, i) => {
      if (v == null) return;
      const x = scaleX(i), y = scaleY(v);
      areaPath += first ? `M${x},${y}` : `L${x},${y}`;
      first = false;
    });
    // Cerrar el área
    const lastIdx = prices.map((v, i) => v != null ? i : -1).filter(i => i >= 0).pop();
    areaPath += `L${scaleX(lastIdx)},${PAD.top + iH} L${scaleX(0)},${PAD.top + iH} Z`;
    html += `<path d="${areaPath}" fill="url(#price-grad)" opacity="0.15"/>`;
    html += `<defs><linearGradient id="price-grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#38bdf8" stop-opacity="0.8"/><stop offset="100%" stop-color="#38bdf8" stop-opacity="0"/></linearGradient></defs>`;
  }

  // Niveles de Fibonacci (líneas horizontales punteadas)
  if (fibLvls) {
    const fibColors = {
      '38.2%': '#a78bfa', '50%': '#a78bfa', '61.8%': '#a78bfa',
      '23.6%': '#6b7280', '78.6%': '#6b7280',
    };
    Object.entries(fibLvls).forEach(([name, price]) => {
      if (price < minY || price > maxY) return;
      const y = scaleY(price);
      const col = fibColors[name] || '#3e4a6a';
      html += `<line x1="${PAD.left}" y1="${y}" x2="${PAD.left + iW}" y2="${y}" stroke="${col}" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>`;
      html += `<text x="${PAD.left + iW + 3}" y="${y + 4}" fill="${col}" font-size="9" font-family="JetBrains Mono" opacity="0.8">${name}</text>`;
    });
  }

  // SMA 50
  html += makeLine(sma50,  '#38bdf8', 1.5);
  // SMA 200
  html += makeLine(sma200, '#f59e0b', 1.5);
  // Precio
  html += makeLine(prices, '#f5f7fa', 2);

  // Ondas de Elliott — un grupo por grado, cada uno con su color
  // Primario (oro, I-V): ondas del ciclo mayor
  // Intermedio (violeta, 1-5): sub-ondas del ciclo actual
  const WAVE_CFG = {
    primary:      { r: 7, textSize: 13, dash: '6,3', sw: 2.0 },
    intermediate: { r: 5, textSize: 10, dash: '4,4', sw: 1.5 },
  };

  waveGroups.forEach(group => {
    const cfg   = WAVE_CFG[group.degree] || WAVE_CFG.intermediate;
    const color = group.color || '#a78bfa';
    const pts   = group.labeled_pivots || [];

    // Línea conectora entre los pivotes del patrón
    if (pts.length >= 2) {
      let linePath = '';
      let first = true;
      pts.forEach(p => {
        if (p.position < 0 || p.position >= n) return;
        const x = scaleX(p.position), y = scaleY(p.price);
        linePath += first ? `M${x},${y}` : `L${x},${y}`;
        first = false;
      });
      if (linePath) {
        html += `<path d="${linePath}" fill="none" stroke="${color}" stroke-width="${cfg.sw}" stroke-dasharray="${cfg.dash}" opacity="0.75"/>`;
      }
    }

    // Puntos y etiquetas
    pts.forEach(p => {
      if (p.position < 0 || p.position >= n) return;
      const px = scaleX(p.position);
      const py = scaleY(p.price);
      // Anillo exterior + relleno oscuro para legibilidad
      html += `<circle cx="${px}" cy="${py}" r="${cfg.r}" fill="${color}" opacity="0.9"/>`;
      html += `<circle cx="${px}" cy="${py}" r="${cfg.r - 2}" fill="#08090d"/>`;
      // Etiqueta arriba de los highs, abajo de los lows
      const labelY = p.type === 'high'
        ? py - cfg.r - 4
        : py + cfg.r + cfg.textSize;
      html += `<text x="${px}" y="${labelY}" fill="${color}" font-size="${cfg.textSize}" text-anchor="middle" font-family="JetBrains Mono" font-weight="700">${p.label}</text>`;
    });
  });

  // Precio actual (línea horizontal)
  if (prices.length) {
    const lastPrice = prices.filter(v => v != null).pop();
    if (lastPrice) {
      const y = scaleY(lastPrice);
      html += `<line x1="${PAD.left}" y1="${y}" x2="${PAD.left + iW}" y2="${y}" stroke="#f5f7fa" stroke-width="1" stroke-dasharray="3,3" opacity="0.4"/>`;
    }
  }

  svg.innerHTML = html;

  // Tooltip con mousemove
  const wrapper = svg.parentElement;
  svg.addEventListener('mousemove', e => {
    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const ratio   = (mouseX - PAD.left * (rect.width / W)) / (iW * (rect.width / W));
    const idx     = Math.round(ratio * (n - 1));
    if (idx < 0 || idx >= n) return;
    const v = prices[idx];
    if (v == null) return;
    const tip = document.getElementById('chart-tooltip');
    tip.style.display = 'block';
    tip.style.left    = `${e.clientX - rect.left + 10}px`;
    tip.style.top     = `${e.clientY - rect.top - 30}px`;
    document.getElementById('tip-date').textContent = dates[idx] || '';
    document.getElementById('tip-val').textContent  = `$${v.toFixed(2)}`;
  });
  svg.addEventListener('mouseleave', () => {
    document.getElementById('chart-tooltip').style.display = 'none';
  });
}

// ============================================================
// Cards de análisis (Valuación / Salud / Crecimiento)
// ============================================================

function renderCards(containerId, cards) {
  if (!cards || !cards.length) return;
  document.getElementById(containerId).innerHTML = cards.map(c => `
    <div class="analysis-card ${c.status}">
      <div class="card-name">${c.name}</div>
      <div class="card-value mono">${c.value}</div>
      <div class="card-note">${c.note || ''}</div>
    </div>
  `).join('');
}

// ============================================================
// Score Breakdown Bars
// ============================================================

function renderScoreBreakdown(sb) {
  if (!sb) return;

  const rows = [
    { key: 'technical',        label: 'Riesgo Técnico',      sub: `Peso: ${sb.technical?.weight || 35}%` },
    { key: 'financial',        label: 'Riesgo Financiero',   sub: `Peso: ${sb.financial?.weight  || 35}%` },
    { key: 'momentum_events',  label: 'Momentum / Eventos',  sub: `Peso: ${sb.momentum_events?.weight || 30}%` },
  ];

  document.getElementById('score-breakdown').innerHTML = rows.map(r => {
    const comp  = sb[r.key];
    const score = comp?.score != null ? comp.score : '—';
    const pct   = comp?.score != null ? comp.score : 0;
    const color = scoreToColor(pct);
    const exp   = comp?.explanation || '';
    return `
      <div class="breakdown-row">
        <div>
          <div class="breakdown-label">${r.label}</div>
          <div class="breakdown-sublabel">${r.sub}</div>
        </div>
        <div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${pct}%; background:${color};"></div>
          </div>
          <div style="font-size:11px; color:var(--text3); margin-top:4px; line-height:1.5">${exp}</div>
        </div>
        <div class="breakdown-score" style="color:${color}">${score}</div>
      </div>
    `;
  }).join('');
}

// ============================================================
// Tabla trimestral
// ============================================================

function renderQuarterlyTable(rows) {
  const table = document.getElementById('quarterly-table');
  const headers = ['Quarter', 'Revenue', 'EPS', 'Margen', 'FCF', 'Deuda', 'Notas'];

  table.innerHTML = `
    <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
    <tbody>
      ${(rows || []).map(r => `
        <tr>
          <td class="mono">${r.quarter || 'N/A'}</td>
          <td class="mono">${r.revenue || 'N/A'}</td>
          <td class="mono">${r.eps     || 'N/A'}</td>
          <td class="mono">${r.margin  || 'N/A'}</td>
          <td class="mono">${r.fcf     || 'N/A'}</td>
          <td class="mono">${r.debt    || 'N/A'}</td>
          <td style="font-family:var(--font-sans); color:var(--text3)">${r.notes || ''}</td>
        </tr>
      `).join('')}
    </tbody>
  `;
}

// ============================================================
// Elliott Wave
// ============================================================

function renderElliott(ew) {
  const el = document.getElementById('elliott-box');
  if (!ew) { el.innerHTML = '<p class="text2">Datos de Elliott no disponibles.</p>'; return; }

  if (!ew.available) {
    el.innerHTML = `
      <p class="text2" style="margin-bottom:0.75rem">${ew.message || 'Análisis no disponible.'}</p>
      <p class="elliott-disclaimer">${ew.disclaimer || ''}</p>
    `;
    return;
  }

  const groups = ew.wave_groups || [];

  // Leyenda de colores por grado
  const legendHtml = groups.map(g => {
    const degLabel = g.degree === 'primary' ? 'Primario' : 'Intermedio';
    const notation = g.pattern === 'impulse'
      ? (g.degree === 'primary' ? 'I – II – III – IV – V' : '1 – 2 – 3 – 4 – 5')
      : (g.degree === 'primary' ? 'A – B – C'            : 'a – b – c');
    return `
      <div style="display:flex; align-items:center; gap:0.5rem; padding:0.5rem 0.75rem;
                  background:rgba(255,255,255,0.03); border-radius:6px;
                  border-left:3px solid ${g.color}">
        <span style="width:10px; height:10px; border-radius:50%; background:${g.color}; flex-shrink:0"></span>
        <div>
          <div style="font-size:11px; color:var(--text3); margin-bottom:1px">${degLabel}</div>
          <div class="mono" style="font-size:12px; color:${g.color}; font-weight:700">${notation}</div>
        </div>
        <div style="margin-left:auto; text-align:right">
          <div style="font-size:10px; color:var(--text3)">Onda actual</div>
          <div class="mono" style="font-size:13px; color:${g.color}; font-weight:700">${g.current_possible_wave || '?'}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:10px; color:var(--text3)">Confianza</div>
          <div class="mono" style="font-size:12px; color:var(--text2)">${g.confidence}</div>
        </div>
      </div>
    `;
  }).join('');

  // Panel del grupo principal (texto de análisis)
  const main = groups.find(g => g.degree === 'primary') || groups[0];
  const confClass = (main?.confidence || 'baja').toLowerCase();
  const warnings  = (main?.warnings || []).map(w => `<li>${w}</li>`).join('');

  el.innerHTML = `
    <div class="elliott-header">
      <span class="elliott-pattern">${main?.wave_count_candidate || '—'}</span>
      <span class="confidence-badge ${confClass}">Confianza: ${main?.confidence || 'baja'}</span>
    </div>

    <div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1rem">
      ${legendHtml}
    </div>

    <div class="elliott-grid">
      <div class="elliott-item">
        <div class="elliott-item-label">Onda Actual (Primario)</div>
        <div class="elliott-item-value mono" style="color:#f59e0b">${main?.current_possible_wave || '?'}</div>
      </div>
      <div class="elliott-item">
        <div class="elliott-item-label">Nivel de Invalidación</div>
        <div class="elliott-item-value mono" style="color:var(--red)">${main?.invalidation_level != null ? '$' + main.invalidation_level.toFixed(2) : 'N/A'}</div>
      </div>
      <div class="elliott-item">
        <div class="elliott-item-label">Patrón Candidato</div>
        <div class="elliott-item-value mono">${main?.pattern === 'impulse' ? 'Impulsivo' : main?.pattern === 'corrective' ? 'Correctivo' : 'No determinado'}</div>
      </div>
      <div class="elliott-item">
        <div class="elliott-item-label">Score de Confianza</div>
        <div class="elliott-item-value mono">${main?.score != null ? (main.score * 100).toFixed(0) + '/100' : '—'}</div>
      </div>
    </div>

    <div class="elliott-explanation">${main?.explanation_simple || ''}</div>
    ${warnings ? `<ul class="cr-list" style="margin-bottom:0.75rem">${warnings}</ul>` : ''}
    <p class="elliott-disclaimer">${ew.disclaimer || ''}</p>
  `;
}

// ============================================================
// Fibonacci
// ============================================================

function renderFibonacci(fib) {
  const el = document.getElementById('fib-box');
  if (!fib || fib.error) {
    el.innerHTML = `<p class="text2">${fib?.error || 'Datos de Fibonacci no disponibles.'}</p>`;
    return;
  }

  const price = fib.current_price;
  const supp  = fib.nearest_support;
  const res   = fib.nearest_resistance;

  // Renderizar niveles
  const levelsHtml = (fib.sorted_levels || []).map(l => {
    const isNearSupport    = supp?.name === l.name;
    const isNearResistance = res?.name  === l.name;
    const diff = price && l.price ? ((price - l.price) / l.price * 100).toFixed(1) : null;
    let cls = '';
    if (isNearSupport)    cls = 'support';
    if (isNearResistance) cls = 'resistance';
    if (diff !== null && Math.abs(parseFloat(diff)) < 0.5) cls = 'current';
    return `
      <div class="fib-level ${cls}">
        <span class="fib-level-name">${l.name}</span>
        <span class="fib-level-price mono">$${l.price?.toFixed(2) || 'N/A'}</span>
      </div>
    `;
  }).join('');

  el.innerHTML = `
    <div class="fib-header">
      <div class="fib-stat">
        <div class="fib-stat-label">Swing High</div>
        <div class="fib-stat-val mono" style="color:var(--red)">$${fib.swing_high?.toFixed(2)} <span style="font-size:10px;color:var(--text3)">${fib.swing_high_date}</span></div>
      </div>
      <div class="fib-stat">
        <div class="fib-stat-label">Precio Actual</div>
        <div class="fib-stat-val mono" style="color:var(--blue)">$${price?.toFixed(2)}</div>
      </div>
      <div class="fib-stat">
        <div class="fib-stat-label">Swing Low</div>
        <div class="fib-stat-val mono" style="color:var(--green)">$${fib.swing_low?.toFixed(2)} <span style="font-size:10px;color:var(--text3)">${fib.swing_low_date}</span></div>
      </div>
    </div>
    <div class="fib-levels">${levelsHtml}</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-bottom:1rem">
      <div style="padding:0.6rem 0.8rem; background:var(--green-bg); border-radius:6px; border:1px solid rgba(34,197,94,0.2)">
        <div style="font-size:11px; color:var(--text3); margin-bottom:2px">Soporte más cercano</div>
        <div class="mono" style="color:var(--green); font-weight:700">${supp?.name || 'N/A'} — $${supp?.price?.toFixed(2) || 'N/A'} (${supp?.distance_pct?.toFixed(1) || '—'}% abajo)</div>
      </div>
      <div style="padding:0.6rem 0.8rem; background:var(--red-bg); border-radius:6px; border:1px solid rgba(239,68,68,0.2)">
        <div style="font-size:11px; color:var(--text3); margin-bottom:2px">Resistencia más cercana</div>
        <div class="mono" style="color:var(--red); font-weight:700">${res?.name || 'N/A'} — $${res?.price?.toFixed(2) || 'N/A'} (${res?.distance_pct?.toFixed(1) || '—'}% arriba)</div>
      </div>
    </div>
    <div class="fib-interpretation">${fib.interpretation || ''}</div>
  `;
}

// ============================================================
// Catalysts vs Risks
// ============================================================

function renderCatalystsRisks(catalysts, risks) {
  const el = document.getElementById('catalysts-risks-grid');
  el.innerHTML = `
    <div class="cr-box catalysts">
      <div class="cr-title catalysts">✦ Catalizadores</div>
      <ul class="cr-list">${(catalysts||[]).map(c => `<li>${c}</li>`).join('')}</ul>
    </div>
    <div class="cr-box risks">
      <div class="cr-title risks">⚠ Riesgos</div>
      <ul class="cr-list">${(risks||[]).map(r => `<li>${r}</li>`).join('')}</ul>
    </div>
  `;
}

// ============================================================
// Bottom Line / Verdict
// ============================================================

function renderBottomLine(verdict, score) {
  const el = document.getElementById('bottom-line');
  if (!verdict) { el.innerHTML = ''; return; }

  const pct = `${score}%`;

  el.innerHTML = `
    <div class="verdict-header">
      <div class="verdict-rating mono" style="color:${verdict.color}">${verdict.rating}</div>
      <div class="verdict-label">${verdict.label}</div>
    </div>
    <div class="rating-bar-track">
      <div class="rating-needle" style="left:${pct}"></div>
    </div>
    <div class="verdict-explanation">${verdict.explanation}</div>
    <div class="disclaimer-box">
      ⚠ Este reporte es únicamente para fines educativos e informativos. No constituye asesoría financiera,
      recomendación de inversión ni señal de compra/venta. El análisis de ondas de Elliott es una hipótesis
      probabilística. Siempre haz tu propia investigación (DYOR).
    </div>
  `;
}

// ============================================================
// Copy Report (texto legible)
// ============================================================

function copyReport() {
  if (!lastReport) return;
  const d  = lastReport;
  const ind = d.indicators;

  const text = [
    `╔══════════════════════════════════════════════════╗`,
    `  MARKET RISK & WAVE ANALYZER — ${d.ticker}`,
    `  ${d.company_name}`,
    `╚══════════════════════════════════════════════════╝`,
    ``,
    `PRECIO:     ${fmt(d.latest_price, 2, d.currency)}  (${d.price_change >= 0 ? '+' : ''}${d.price_change_percent?.toFixed(2)}%)`,
    `RIESGO:     ${d.risk_score}/100 — ${d.risk_label}`,
    `TENDENCIA:  ${(ind.trend || 'N/A').toUpperCase()}`,
    ``,
    `── INDICADORES ─────────────────────────────────────`,
    `RSI (14):   ${ind.rsi?.toFixed(1) || 'N/A'}  [${ind.rsi_signal || ''}]`,
    `MACD:       ${ind.macd_bullish ? 'POSITIVO (alcista)' : 'NEGATIVO (bajista)'}`,
    `Volatilidad:${ind.annual_volatility?.toFixed(1) || 'N/A'}% anualizada`,
    `Drawdown:   ${ind.max_drawdown?.toFixed(1) || 'N/A'}%`,
    `vs SMA200:  ${ind.dist_sma200_pct != null ? `${ind.dist_sma200_pct > 0 ? '+' : ''}${ind.dist_sma200_pct.toFixed(1)}%` : 'N/A'}`,
    `Retorno 1M: ${fmtPct(ind.return_1m)}`,
    `Retorno 3M: ${fmtPct(ind.return_3m)}`,
    ``,
    `── FIBONACCI ────────────────────────────────────────`,
    `Swing High: $${d.fibonacci_levels?.swing_high?.toFixed(2) || 'N/A'}`,
    `Swing Low:  $${d.fibonacci_levels?.swing_low?.toFixed(2)  || 'N/A'}`,
    `Soporte +cercano:    ${d.fibonacci_levels?.nearest_support?.name || 'N/A'} ($${d.fibonacci_levels?.nearest_support?.price?.toFixed(2) || 'N/A'})`,
    `Resistencia +cercana:${d.fibonacci_levels?.nearest_resistance?.name || 'N/A'} ($${d.fibonacci_levels?.nearest_resistance?.price?.toFixed(2) || 'N/A'})`,
    ``,
    `── ELLIOTT WAVE ──────────────────────────────────────`,
    `Patrón:     ${d.elliott_wave_analysis?.wave_count_candidate || 'No determinado'}`,
    `Onda actual:${d.elliott_wave_analysis?.current_possible_wave || '?'}`,
    `Confianza:  ${d.elliott_wave_analysis?.confidence || 'N/A'}`,
    `Invalidación: $${d.elliott_wave_analysis?.invalidation_level?.toFixed(2) || 'N/A'}`,
    ``,
    `── CATALIZADORES ────────────────────────────────────`,
    ...(d.catalysts || []).map(c => `  + ${c}`),
    ``,
    `── RIESGOS ───────────────────────────────────────────`,
    ...(d.risks || []).map(r => `  ⚠ ${r}`),
    ``,
    `── CONCLUSIÓN ────────────────────────────────────────`,
    `Rating:  ${d.verdict?.rating || 'N/A'} — ${d.verdict?.label || ''}`,
    `${d.verdict?.explanation || ''}`,
    ``,
    `Generado: ${d.latest_update}  |  Proveedor: ${d.provider}`,
    `⚠ Solo para fines educativos. No es asesoría financiera.`,
  ].join('\n');

  copyToClipboard(text, 'btn-copy-report');
}

// ============================================================
// Copy JSON
// ============================================================

function copyJSON() {
  if (!lastReport) return;
  copyToClipboard(JSON.stringify(lastReport, null, 2), 'btn-copy-json');
}

// ============================================================
// Helpers de formato y utilidades
// ============================================================

function fmt(v, decimals = 2, currency = '') {
  if (v == null) return 'N/A';
  const prefix = currency && currency !== 'USD' ? currency + ' ' : '$';
  return prefix + Number(v).toFixed(decimals);
}

function fmtPct(v) {
  if (v == null) return 'N/A';
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

function signColor(v) {
  if (v == null) return null;
  return v >= 0 ? '#22c55e' : '#ef4444';
}

function rsiColor(rsi) {
  if (rsi == null) return null;
  if (rsi >= 70) return '#ef4444';
  if (rsi <= 30) return '#22c55e';
  return '#38bdf8';
}

function rsiLabel(rsi) {
  if (rsi == null) return '—';
  if (rsi >= 80) return 'Extremo OB';
  if (rsi >= 70) return 'Sobrecomprado';
  if (rsi <= 20) return 'Extremo OS';
  if (rsi <= 30) return 'Sobrevendido';
  return 'Neutral';
}

function scoreToColor(v) {
  if (v <= 30) return '#22c55e';
  if (v <= 60) return '#f59e0b';
  if (v <= 80) return '#ef4444';
  return '#7f1d1d';
}

function capitalize(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function copyToClipboard(text, btnId) {
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById(btnId);
    if (btn) { btn.classList.add('copied'); setTimeout(() => btn.classList.remove('copied'), 2000); }
    showToast();
  }).catch(() => {
    // Fallback para navegadores sin clipboard API
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity  = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast();
  });
}

function showToast() {
  const toast = document.getElementById('toast');
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}
