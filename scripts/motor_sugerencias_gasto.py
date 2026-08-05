#!/usr/bin/env python3
"""
motor_sugerencias_gasto.py — Motor de sugerencias de gasto (Bloque F8-1, Fase 7 / E10).

Evalúa los gastos reales de libreta.db y le SUGIERE a Arturo -- nunca decide
por él -- apenas detecta un patrón (r.25: "sí, que me haga sugerencias") y
en un consolidado los domingos. Todos los gastos cuentan sin excepción
(r.24), ninguna categoría es intocable (r.26: "acepto sus sugerencias"), y
el método de pago no importa (r.27) porque libreta.db no lo distingue: todo
entra a `gastos` por igual, así que este motor nunca filtra por categoría
ni por forma de pago.

Reglas locales sobre números ya en disco, sin mandar nada a una API externa
(r.91). Nunca promete ni actúa: cada aviso cierra preguntando qué quiere
hacer Arturo (mismo formato que vigilar_correo_escuela.py /
vigilar_correo_personal.py).

No duplica el reporte semanal financiero (F7-3,
scripts/reporte_rieles_semanales.py): ese reporta NÚMEROS (balance,
ingresos, meta de ahorro); este solo dice cuándo un número se sale de lo
normal y pregunta qué hacer. Conviven: F7-3 puede correr aparte, o el
consolidado dominical puede mandarse justo después.

USO
  python3 motor_sugerencias_gasto.py --evaluar    -> revisa gastos nuevos desde la
                                                       última corrida, avisa los atípicos
  python3 motor_sugerencias_gasto.py --dominical  -> consolidado semanal de patrones
                                                       (pensado para el domingo AM, r.25)
  python3 motor_sugerencias_gasto.py --probar     -> imprime sin avisar ni tocar estado
                                                       (combínalo con --evaluar/--dominical)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from libreta import Libreta

HOME = os.path.expanduser("~")
ESTADO = os.path.join(HOME, ".hermes/state/sugerencias_gasto_vistos.json")
LOG = os.path.join(HOME, ".hermes/logs/sugerencias_gasto.log")
ENVIAR = os.path.join(HOME, ".hermes/scripts/enviar.py")
PYTHON = os.path.join(HOME, ".hermes/hermes-agent/venv/bin/python")

# ── umbrales (reglas locales; r.26: nada intocable, todas las categorías se
# evalúan igual, ninguna lista de exclusión) ────────────────────────────────
# Gasto individual atípico: cuántas veces el promedio histórico de ESA
# categoría hace falta para avisar de inmediato. Con piso en pesos para que
# una categoría de gasto chico (ej. "cafe") no dispare por unos pesos de más.
MULTIPLICADOR_ATIPICO = 2.5
PISO_ATIPICO_MXN = 150.0
# Categoría disparada en la semana: variación mínima vs. el promedio de las
# semanas anteriores, con piso para no reaccionar a categorías marginales.
UMBRAL_CATEGORIA_PCT = 0.5
PISO_CATEGORIA_MXN = 100.0
SEMANAS_HISTORICO_CATEGORIA = 4
# Mínimo de gastos previos en la categoría para confiar en el promedio; con
# menos, cualquier número "parece" atípico solo por falta de historial.
MIN_HISTORICO = 3
DIAS_HISTORICO_ATIPICO = 90


def log(mensaje):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} | {mensaje}\n")
    print(mensaje)


def avisar(mensaje):
    try:
        r = subprocess.run([PYTHON, ENVIAR, "--mensaje", mensaje],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            log(f"🔴 FALLO al avisar por Telegram (rc={r.returncode}): "
                f"{r.stderr.strip()[:200]}")
            return False
        return True
    except Exception as e:
        log(f"🔴 FALLO al avisar por Telegram: {e}")
        return False


def cargar_ultimo_id():
    """None = estado ilegible: el caller debe tratarlo como 'parte de lo más
    nuevo que exista ahora', igual que vigilar_correo_escuela.py trata un
    estado roto como primera corrida -- nunca reavisa el histórico completo
    por un archivo de estado dañado."""
    if not os.path.exists(ESTADO):
        return 0
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return int(json.load(f).get("ultimo_id", 0))
    except Exception as e:
        log(f"⚠️  No pude leer el estado ({e}) — evalúo desde el gasto más nuevo, "
            f"no desde 0, para no reavisar todo el histórico")
        return None


def guardar_ultimo_id(ultimo_id):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ultimo_id": ultimo_id,
                   "actualizado": datetime.now().isoformat()}, f)
    os.replace(tmp, ESTADO)


def fecha_hace_n_dias(n, desde_fecha=None):
    d = (datetime.fromisoformat(desde_fecha).date() if desde_fecha
         else datetime.now().date())
    return str(d - timedelta(days=n))


# ── detección: gasto individual atípico (apenas se detecta, r.25) ──────────

def _promedio_historico_categoria(lib, categoria, excluir_id, hasta_fecha):
    desde = fecha_hace_n_dias(DIAS_HISTORICO_ATIPICO, hasta_fecha)
    row = lib.con.execute(
        "SELECT AVG(monto_mxn), COUNT(*) FROM gastos "
        "WHERE categoria = ? AND id != ? AND fecha BETWEEN ? AND ?",
        (categoria, excluir_id, desde, hasta_fecha),
    ).fetchone()
    return row[0] or 0.0, row[1]


def detectar_atipico(lib, gasto):
    """Un gasto es atípico si es varias veces el promedio histórico de su
    categoría (con piso en pesos e historial mínimo, ver umbrales arriba).
    Devuelve None si no aplica -- nunca fuerza un hallazgo."""
    promedio, n = _promedio_historico_categoria(
        lib, gasto["categoria"], gasto["id"], gasto["fecha"])
    if n < MIN_HISTORICO or promedio <= 0:
        return None
    if gasto["monto_mxn"] < PISO_ATIPICO_MXN:
        return None
    veces = gasto["monto_mxn"] / promedio
    if veces < MULTIPLICADOR_ATIPICO:
        return None
    return {
        "tipo": "atipico", "id": gasto["id"], "categoria": gasto["categoria"],
        "monto": gasto["monto_mxn"], "descripcion": gasto["descripcion"],
        "fecha": gasto["fecha"], "promedio_historico": promedio,
        "veces": veces, "n_historico": n,
    }


def construir_mensaje_atipico(h):
    desc = f" ({h['descripcion']})" if h["descripcion"] else ""
    return (
        f"Arturo, un gasto de ${h['monto']:.2f} en '{h['categoria']}'{desc} "
        f"({h['fecha']}) es {h['veces']:.1f}x tu promedio en esa categoría "
        f"(~${h['promedio_historico']:.2f}, sobre {h['n_historico']} gastos "
        f"anteriores). ¿Fue algo puntual o quieres que le ponga ojo?"
    )


def evaluar_inmediato(lib, *, avisar_fn=avisar, marcar_estado=True):
    """Revisa los gastos registrados desde la última corrida y avisa los
    atípicos apenas se detectan (r.25). Devuelve los hallazgos avisados."""
    ultimo_id = cargar_ultimo_id()
    if ultimo_id is None:
        ultimo_id = lib.con.execute(
            "SELECT COALESCE(MAX(id),0) FROM gastos").fetchone()[0]
    nuevos = lib.con.execute(
        "SELECT * FROM gastos WHERE id > ? ORDER BY id", (ultimo_id,)
    ).fetchall()
    if not nuevos:
        log("✅ Sin gastos nuevos que evaluar")
        return []

    avisados = []
    max_id = ultimo_id
    for g in nuevos:
        max_id = max(max_id, g["id"])
        hallazgo = detectar_atipico(lib, g)
        if hallazgo is None:
            continue
        msg = construir_mensaje_atipico(hallazgo)
        if avisar_fn(msg):
            log(f"✅ Avisado atípico [{hallazgo['categoria']}]: ${hallazgo['monto']:.2f}")
            avisados.append(hallazgo)
        else:
            log(f"🔴 NO se pudo avisar del gasto atípico id={g['id']}")
    if marcar_estado:
        guardar_ultimo_id(max_id)
    return avisados


# ── detección: categoría disparada en la semana (consolidado dominical) ────

def _total_categoria_periodo(lib, categoria, desde, hasta):
    row = lib.con.execute(
        "SELECT COALESCE(SUM(monto_mxn),0), COUNT(*) FROM gastos "
        "WHERE categoria = ? AND fecha BETWEEN ? AND ?",
        (categoria, desde, hasta),
    ).fetchone()
    return row[0], row[1]


def _categorias_activas(lib, desde, hasta):
    rows = lib.con.execute(
        "SELECT DISTINCT categoria FROM gastos WHERE fecha BETWEEN ? AND ?",
        (desde, hasta),
    ).fetchall()
    return [r[0] for r in rows]


def detectar_categorias_disparadas(lib, hoy_str=None):
    """Categorías cuyo gasto de la semana actual se salió del patrón de las
    `SEMANAS_HISTORICO_CATEGORIA` semanas anteriores. Una categoría sin
    historial previo (nueva esta semana) no cuenta como "disparada" -- no
    hay base para comparar, solo es gasto nuevo."""
    hoy_str = hoy_str or lib.hoy()
    semana_actual_desde = fecha_hace_n_dias(6, hoy_str)
    ventana_desde = fecha_hace_n_dias(6 + 7 * SEMANAS_HISTORICO_CATEGORIA, hoy_str)
    categorias = sorted(set(_categorias_activas(lib, ventana_desde, hoy_str)))

    hallazgos = []
    for categoria in categorias:
        total_actual, n_actual = _total_categoria_periodo(
            lib, categoria, semana_actual_desde, hoy_str)
        if total_actual < PISO_CATEGORIA_MXN:
            continue
        totales_previos = []
        for semana in range(1, SEMANAS_HISTORICO_CATEGORIA + 1):
            hasta_prev = fecha_hace_n_dias(7 * semana, hoy_str)
            desde_prev = fecha_hace_n_dias(7 * semana + 6, hoy_str)
            total_prev, _ = _total_categoria_periodo(lib, categoria, desde_prev, hasta_prev)
            totales_previos.append(total_prev)
        promedio_historico = sum(totales_previos) / len(totales_previos)
        if promedio_historico <= 0:
            continue
        variacion = (total_actual - promedio_historico) / promedio_historico
        if variacion < UMBRAL_CATEGORIA_PCT:
            continue
        hallazgos.append({
            "tipo": "categoria_disparada", "categoria": categoria,
            "total_actual": total_actual, "n_actual": n_actual,
            "promedio_historico": promedio_historico,
            "variacion_pct": variacion * 100,
        })
    return hallazgos


def construir_mensaje_categoria(h):
    return (
        f"• {h['categoria']}: ${h['total_actual']:.2f} esta semana "
        f"({h['n_actual']} gastos) — {h['variacion_pct']:.0f}% más que tu "
        f"promedio de las últimas {SEMANAS_HISTORICO_CATEGORIA} semanas "
        f"(${h['promedio_historico']:.2f})"
    )


def construir_consolidado_dominical(lib, hoy_str=None):
    hoy_str = hoy_str or lib.hoy()
    disparadas = detectar_categorias_disparadas(lib, hoy_str)
    lineas = [
        f"Arturo, resumen de patrones de gasto de la semana "
        f"({fecha_hace_n_dias(6, hoy_str)} a {hoy_str}):"
    ]
    if not disparadas:
        lineas.append("Sin categorías fuera de lo normal esta semana — todo "
                       "dentro de tu patrón habitual.")
    else:
        lineas.append("Categorías que se salieron de tu patrón habitual:")
        lineas.extend(construir_mensaje_categoria(h) for h in disparadas)
        lineas.append("¿Alguna de estas fue intencional o quieres que le ponga ojo?")
    return "\n".join(lineas)


def evaluar_dominical(lib, *, avisar_fn=avisar):
    msg = construir_consolidado_dominical(lib)
    if avisar_fn(msg):
        log("✅ Consolidado dominical enviado")
        return True
    log("🔴 NO se pudo enviar el consolidado dominical")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--evaluar", action="store_true",
                        help="revisa gastos nuevos y avisa los atípicos")
    parser.add_argument("--dominical", action="store_true",
                        help="consolidado semanal de patrones (domingo AM, r.25)")
    parser.add_argument("--probar", action="store_true",
                        help="imprime sin avisar ni tocar estado")
    parser.add_argument("--entorno", choices=["real", "simulacion"], default="real")
    args = parser.parse_args()

    if not (args.evaluar or args.dominical):
        parser.error("usa --evaluar y/o --dominical (opcionalmente con --probar)")

    with Libreta(args.entorno, solo_lectura=args.probar) as lib:
        if args.evaluar:
            if args.probar:
                ultimo_id = cargar_ultimo_id() or 0
                nuevos = lib.con.execute(
                    "SELECT * FROM gastos WHERE id > ? ORDER BY id", (ultimo_id,)
                ).fetchall()
                hallazgos = [h for g in nuevos
                            for h in [detectar_atipico(lib, g)] if h is not None]
                for h in hallazgos:
                    print(construir_mensaje_atipico(h))
                print(f"\n{len(nuevos)} gastos nuevos evaluados, {len(hallazgos)} "
                      f"atípicos (--probar: sin avisar, sin tocar estado)")
            else:
                evaluar_inmediato(lib)
        if args.dominical:
            if args.probar:
                print(construir_consolidado_dominical(lib))
            else:
                evaluar_dominical(lib)


if __name__ == "__main__":
    main()
