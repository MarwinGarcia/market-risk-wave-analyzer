"""
elliott.py
==========
Detección probabilística de posibles ondas de Elliott.

IMPORTANTE — Limitaciones y uso correcto:
  - Las ondas de Elliott son SUBJETIVAS e interpretativas
  - Este módulo genera HIPÓTESIS, NO predicciones
  - El lenguaje de todas las respuestas es deliberadamente prudente:
    "podría", "posible", "zona probable", "nivel de invalidación"
  - Los resultados NO son asesoría financiera

Proceso técnico:
  1. Detectar pivotes locales (máximos y mínimos) usando scipy.signal
  2. Asegurar alternancia high/low entre pivotes
  3. Intentar encajar en patrón impulsivo 1-2-3-4-5
  4. Intentar encajar en patrón correctivo A-B-C
  5. Validar reglas básicas de Elliott
  6. Devolver el patrón con mayor puntuación y su nivel de confianza
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from typing import Dict, Any, List, Tuple, Optional


def analyze_elliott_waves(hist: pd.DataFrame) -> Dict[str, Any]:
    """
    Analiza ondas de Elliott en dos grados de magnitud:
      - Primario   (order grande): ondas principales del ciclo mayor — color oro
      - Intermedio (order normal): sub-ondas dentro del ciclo — color violeta

    Retorna 'wave_groups' con cada grado detectado, más los campos del grupo
    principal para compatibilidad con el texto de análisis.
    """
    if len(hist) < 30:
        return {
            "available": False,
            "wave_groups": [],
            "labeled_pivots": [],
            "pivots": [],
            "message": (
                "Datos insuficientes para análisis de ondas de Elliott. "
                "Necesito al menos 30 velas. Prueba con un periodo más largo."
            ),
            "warnings": ["Datos insuficientes"],
            "disclaimer": _disclaimer(),
        }

    close = hist["Close"].astype(float).values
    try:
        dates = [str(d) for d in hist.index]
    except Exception:
        dates = [str(i) for i in range(len(close))]

    n = len(close)

    # Dos escalas de análisis:
    #   Primario    → pivotes grandes (tendencia mayor)
    #   Intermedio  → pivotes medianos (sub-ciclo actual)
    degree_configs = [
        ("primary",      max(6, n // 8),  "#f59e0b"),   # oro
        ("intermediate", max(3, n // 25), "#a78bfa"),   # violeta
    ]

    wave_groups: List[Dict] = []
    primary_pivots: List = []

    for degree, order, color in degree_configs:
        pivots = _detect_pivots(close, order=order)

        if degree == "primary":
            primary_pivots = pivots

        if len(pivots) < 4:
            continue

        impulse    = _try_impulse(pivots, close)
        corrective = _try_corrective(pivots, close)
        best = impulse if impulse["score"] >= corrective["score"] else corrective

        window = best.pop("_window", None)
        if not window or best["score"] < 0.20:
            continue

        labeled = _make_labeled_pivots(window, dates, best["pattern"], degree)

        wave_groups.append({
            "degree":               degree,
            "color":                color,
            "pattern":              best["pattern"],
            "wave_count_candidate": best["wave_count_candidate"],
            "confidence":           best["confidence"],
            "score":                best["score"],
            "current_possible_wave":best["current_possible_wave"],
            "invalidation_level":   best["invalidation_level"],
            "labeled_pivots":       labeled,
            "explanation_simple":   best["explanation_simple"],
            "warnings":             best["warnings"],
        })

    if not wave_groups:
        return {
            "available": False,
            "wave_groups": [],
            "labeled_pivots": [],
            "pivots": _format_pivots(primary_pivots, dates),
            "message": (
                "No se detectaron estructuras de onda claras en el periodo analizado. "
                "Prueba con un periodo más largo o un intervalo diferente."
            ),
            "warnings": ["Sin patrones detectados con confianza suficiente"],
            "disclaimer": _disclaimer(),
        }

    # El grupo primario (o el de mayor score) representa el análisis principal
    main = next((g for g in wave_groups if g["degree"] == "primary"), wave_groups[0])

    return {
        "available":            True,
        "wave_groups":          wave_groups,
        "pivots":               _format_pivots(primary_pivots, dates),
        "labeled_pivots":       main["labeled_pivots"],  # compatibilidad
        # Campos del grupo principal (para el panel de texto)
        "pattern":              main["pattern"],
        "confidence":           main["confidence"],
        "score":                main["score"],
        "wave_count_candidate": main["wave_count_candidate"],
        "current_possible_wave":main["current_possible_wave"],
        "invalidation_level":   main["invalidation_level"],
        "explanation_simple":   main["explanation_simple"],
        "warnings":             main["warnings"],
        "disclaimer":           _disclaimer(),
    }


# ---------------------------------------------------------------------------
# Detección de pivotes
# ---------------------------------------------------------------------------

def _detect_pivots(close: np.ndarray, order: int = 5) -> List[Tuple[int, float, str]]:
    """
    Detecta máximos y mínimos locales usando scipy.

    Args:
        close: array de precios de cierre
        order: cuántas velas a cada lado para considerar un pivote

    Returns:
        Lista de (posición, precio, tipo) ordenada temporalmente, con alternancia garantizada
    """
    highs = set(argrelextrema(close, np.greater_equal, order=order)[0])
    lows  = set(argrelextrema(close, np.less_equal,   order=order)[0])

    pivots = []
    for i in sorted(highs | lows):
        if i in highs and i in lows:
            # Índice que es tanto high como low — usar el contexto para decidir
            pivots.append((i, float(close[i]), "high"))
        elif i in highs:
            pivots.append((i, float(close[i]), "high"))
        else:
            pivots.append((i, float(close[i]), "low"))

    # Filtrar pivotes muy cercanos (< order/2 de distancia)
    pivots = _merge_close(pivots, min_gap=max(2, order // 2))

    # Garantizar alternancia high ↔ low
    pivots = _alternate(pivots)

    return pivots


def _merge_close(pivots: List[Tuple], min_gap: int) -> List[Tuple]:
    """Fusiona pivotes adyacentes del mismo tipo que están demasiado cerca."""
    if not pivots:
        return []
    result = [pivots[0]]
    for p in pivots[1:]:
        if p[0] - result[-1][0] < min_gap:
            # Mismo tipo — conservar el más extremo
            if p[2] == result[-1][2]:
                if (p[2] == "high" and p[1] > result[-1][1]) or \
                   (p[2] == "low"  and p[1] < result[-1][1]):
                    result[-1] = p
        else:
            result.append(p)
    return result


def _alternate(pivots: List[Tuple]) -> List[Tuple]:
    """Asegura que los pivotes alternen entre high y low, conservando el más extremo."""
    if not pivots:
        return []
    result = [pivots[0]]
    for p in pivots[1:]:
        if p[2] != result[-1][2]:
            result.append(p)
        else:
            # Mismo tipo consecutivo: conservar el más extremo
            if (p[2] == "high" and p[1] > result[-1][1]) or \
               (p[2] == "low"  and p[1] < result[-1][1]):
                result[-1] = p
    return result


# ---------------------------------------------------------------------------
# Patrón impulsivo 1-2-3-4-5
# ---------------------------------------------------------------------------

def _try_impulse(
    pivots: List[Tuple], close: np.ndarray
) -> Dict[str, Any]:
    """
    Intenta encajar los pivotes en un patrón impulsivo 1-2-3-4-5.
    Evalúa múltiples ventanas de 6 pivotes y devuelve la mejor.
    """
    best_score = 0.0
    best: Optional[Dict] = None

    # Evaluar ventanas de 6 pivotes consecutivos
    for start in range(max(0, len(pivots) - 9), len(pivots) - 4):
        window = pivots[start: start + 6]
        if len(window) < 5:
            continue
        score, violations = _score_impulse(window)
        if score > best_score:
            best_score = score
            best = {"window": window, "violations": violations}

    if best is None or best_score < 0.25:
        return {
            "pattern": "impulse",
            "score": best_score,
            "confidence": "low",
            "wave_count_candidate": "1-2-3-4-5 (no claro)",
            "current_possible_wave": "?",
            "invalidation_level": None,
            "labeled_pivots": [],
            "explanation_simple": (
                "No se detectó una estructura impulsiva 1-2-3-4-5 clara en el periodo. "
                "Posible consolidación, tendencia lineal o estructura compleja. "
                "Considera analizar en un timeframe diferente."
            ),
            "warnings": ["Patrón impulsivo no encontrado con confianza suficiente"],
        }

    window = best["window"]
    violations = best["violations"]
    confidence = _confidence_label(best_score)
    current_wave = _current_wave_impulse(window, close)
    invalidation = _invalidation_impulse(window)

    return {
        "pattern": "impulse",
        "score": round(best_score, 2),
        "confidence": confidence,
        "wave_count_candidate": "1-2-3-4-5",
        "current_possible_wave": current_wave,
        "invalidation_level": invalidation,
        "_window": window,   # retirado por el caller, no llega al frontend
        "explanation_simple": _explain_impulse(current_wave, confidence, invalidation, violations),
        "warnings": violations or ["Sin violaciones detectadas de las reglas básicas de Elliott"],
    }


def _score_impulse(window: List[Tuple]) -> Tuple[float, List[str]]:
    """
    Puntúa qué tan bien encajan los pivotes en un patrón impulsivo.

    Retorna (score 0-1, lista de violaciones).
    """
    if len(window) < 5:
        return 0.0, ["Pivotes insuficientes"]

    prices = [p[1] for p in window]
    types  = [p[2] for p in window]
    score  = 1.0
    violations: List[str] = []

    # Para patrón alcista: high-low-high-low-high (5 puntos)
    # Para patrón bajista: low-high-low-high-low
    is_bullish = types[0] == "low" and types[1] == "high"  # W1 sube

    if is_bullish:
        p0, p1, p2, p3, p4 = prices[:5]
        w1 = p1 - p0
        w2 = p1 - p2
        w3 = p3 - p2
        w4 = p3 - p4 if len(prices) > 4 else 0
        w5 = prices[5] - p4 if len(prices) > 5 else 0

        # Regla 1: Onda 2 no retrocede >100% de Onda 1
        if w1 > 0 and w2 / w1 > 1.0:
            violations.append("Onda 2 retrocede más del 100% de Onda 1")
            score -= 0.35

        # Regla 2: Onda 3 no es la más corta (entre W1, W3, W5)
        waves = [w for w in [w1, w3, w5] if w > 0]
        if waves and w3 == min(waves) and len(waves) == 3:
            violations.append("Onda 3 es la más corta (violación de Elliott)")
            score -= 0.30

        # Regla 3: Onda 4 no solapa territorio de Onda 1
        if len(prices) > 4 and p4 < p1:
            violations.append("Onda 4 solapa el techo de Onda 1")
            score -= 0.20

        # Bonus: Onda 3 es la más larga
        if waves and w3 == max(waves):
            score += 0.15

        # Bonus: dirección correcta de cada onda
        if p1 > p0 and p2 < p1 and p3 > p2:
            score += 0.10
    else:
        # Patrón bajista — validación simétrica
        if len(prices) >= 5:
            p0, p1, p2, p3, p4 = prices[:5]
            w1 = p0 - p1
            w2 = p2 - p1
            if w1 > 0 and w2 / w1 > 1.0:
                violations.append("Onda 2 retrocede más del 100% de Onda 1")
                score -= 0.35

    score = max(0.0, min(1.0, score))
    return score, violations


def _current_wave_impulse(window: List[Tuple], close: np.ndarray) -> str:
    """Estima en qué onda podría estar el precio actualmente."""
    n = len(window)
    # Después del último pivote detectado, el precio está "entre ondas"
    if n >= 6:
        return "5 o corrección post-impulso"
    wave_map = {5: "5", 4: "4 o 5", 3: "3 o 4", 2: "2 o 3"}
    return wave_map.get(n, "?")


def _invalidation_impulse(window: List[Tuple]) -> Optional[float]:
    """
    Calcula el nivel de invalidación del patrón impulsivo.
    Nivel de invalidación básico: precio del inicio de Onda 2 (segundo pivote).
    """
    if len(window) >= 2:
        return round(float(window[1][1]), 4)
    return None


def _explain_impulse(
    current_wave: str,
    confidence: str,
    invalidation: Optional[float],
    violations: List[str],
) -> str:
    base = (
        f"Posible estructura impulsiva 1-2-3-4-5 detectada en el periodo analizado. "
        f"El precio podría estar en la onda {current_wave}. "
    )
    if invalidation:
        base += f"Nivel de invalidación del escenario: {invalidation:.2f}. "
    base += f"Confianza del análisis: {confidence}. "
    if violations:
        base += f"Advertencias técnicas: {'; '.join(violations)}. "
    base += (
        "Este es un escenario hipotético basado en patrones históricos. "
        "No es una predicción ni asesoría financiera."
    )
    return base


# ---------------------------------------------------------------------------
# Patrón correctivo A-B-C
# ---------------------------------------------------------------------------

def _try_corrective(
    pivots: List[Tuple], close: np.ndarray
) -> Dict[str, Any]:
    """Intenta encajar los últimos pivotes en un patrón correctivo A-B-C."""
    if len(pivots) < 4:
        return {"pattern": "corrective", "score": 0.0, "confidence": "low",
                "wave_count_candidate": "A-B-C (insuficiente)", "current_possible_wave": "?",
                "invalidation_level": None, "labeled_pivots": [],
                "explanation_simple": "Pivotes insuficientes para A-B-C.",
                "warnings": ["Pivotes insuficientes"]}

    window = pivots[-4:]
    prices = [p[1] for p in window]
    score  = 0.4  # base
    violations: List[str] = []

    # A-B-C bajista: A baja, B sube parcialmente, C baja
    a_down = prices[1] < prices[0]
    if a_down and len(prices) >= 4:
        a = prices[0] - prices[1]
        b = prices[2] - prices[1]
        c = prices[2] - prices[3]

        # B no debe superar inicio de A
        if prices[2] > prices[0]:
            violations.append("Onda B supera el inicio de A (estructura irregular)")
            score -= 0.15

        # C idealmente similar a A en magnitud (ratio 0.618 a 1.618)
        if a > 0 and c > 0:
            ratio = c / a
            if 0.618 <= ratio <= 1.618:
                score += 0.25
            else:
                violations.append(f"Onda C/A ratio fuera de rango típico ({ratio:.2f})")
                score -= 0.10

        # Dirección correcta
        if prices[1] < prices[0] and prices[2] > prices[1] and prices[3] < prices[2]:
            score += 0.15

    score = max(0.0, min(1.0, score))
    confidence = _confidence_label(score)
    invalidation = round(float(window[0][1]), 4)

    current_wave = "C" if len(window) >= 4 else "B"

    return {
        "pattern": "corrective",
        "score": round(score, 2),
        "confidence": confidence,
        "wave_count_candidate": "A-B-C",
        "current_possible_wave": current_wave,
        "invalidation_level": invalidation,
        "_window": window,   # retirado por el caller, no llega al frontend
        "explanation_simple": (
            f"Posible corrección A-B-C en desarrollo. "
            f"El precio podría estar en la onda {current_wave}. "
            f"Nivel de invalidación: {invalidation:.2f}. "
            f"Confianza: {confidence}. "
            + (f"Advertencias: {'; '.join(violations)}. " if violations else "")
            + "Escenario hipotético — no es asesoría financiera."
        ),
        "warnings": violations or ["Sin violaciones en las reglas básicas A-B-C"],
    }


# ---------------------------------------------------------------------------
# Helpers comunes
# ---------------------------------------------------------------------------

def _confidence_label(score: float) -> str:
    if score >= 0.70:
        return "alta"
    if score >= 0.45:
        return "media"
    return "baja"


def _format_pivots(pivots: List[Tuple], dates: List[str]) -> List[Dict]:
    """Formatea los pivotes para el JSON de respuesta."""
    formatted = []
    for pos, price, ptype in pivots:
        date_str = dates[pos] if 0 <= pos < len(dates) else str(pos)
        formatted.append({
            "position": int(pos),
            "price": round(float(price), 4),
            "type": ptype,
            "date": date_str,
        })
    return formatted


def _make_labeled_pivots(
    window: List[Tuple], dates: List[str], pattern: str, degree: str = "intermediate"
) -> List[Dict]:
    """
    Devuelve solo los pivotes del patrón detectado con etiquetas correctas.

    Notación estándar de Elliott por grado:
      primary     impulso   → I  II  III  IV  V
      primary     correctivo→ A  B  C
      intermediate impulso  → 1  2  3  4  5
      intermediate correctivo→ a  b  c
    """
    if pattern == "impulse":
        labels = ["I", "II", "III", "IV", "V"] if degree == "primary" else ["1", "2", "3", "4", "5"]
    else:
        labels = ["A", "B", "C"] if degree == "primary" else ["a", "b", "c"]

    result = []
    for i, (pos, price, ptype) in enumerate(window):
        if i >= len(labels):
            break
        date_str = dates[pos] if 0 <= pos < len(dates) else str(pos)
        result.append({
            "position": int(pos),
            "price":    round(float(price), 4),
            "type":     ptype,
            "date":     date_str,
            "label":    labels[i],
        })
    return result


def _disclaimer() -> str:
    return (
        "IMPORTANTE: El análisis de ondas de Elliott es una hipótesis probabilística "
        "basada en patrones históricos de precio. No garantiza resultados futuros. "
        "Este análisis NO constituye asesoría financiera."
    )
