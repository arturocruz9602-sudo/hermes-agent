#!/usr/bin/env python3
"""
motor_sugerencias_gasto.py — Motor de sugerencias de gasto (Bloques F8-1/F8-2, Fase 7 / E10).

Evalúa los gastos reales de libreta.db y le SUGIERE a Arturo -- nunca decide
por él -- apenas detecta un patrón (r.25: "sí, que me haga sugerencias") y
en un consolidado los domingos. Todos los gastos cuentan sin excepción
(r.24), ninguna categoría es intocable (r.26: "acepto sus sugerencias"), y
el método de pago no importa (r.27) porque libreta.db no lo distingue: todo
entra a `gastos` por igual, así que este motor nunca filtra por categoría
ni por forma de pago.

F8-2 amplía el consolidado dominical más allá de `gastos` solo (esa tabla
hoy casi no tiene historial): también cruza `pagos_recurrentes` (¿un fijo
como gym/deepseek/colegiatura no se registró este ciclo?) y
`negocio_compras`/`negocio_ventas` (¿la reja subió de precio, cayó el ritmo
de venta, o el negocio no está recuperando lo invertido?), usando
margen_negocio() de Libreta. Mismas reglas: sin historial previo no hay
patrón que romper, así que no avisa desde el día uno.

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

# ── pagos recurrentes (F8-2): lo esperado vs. lo realmente registrado ──────
# Ventana del ciclo en dias, aproximada a 30 por mes -- el motor no persigue
# el calendario exacto (dia_del_mes), solo si el patron se rompio.
DIAS_POR_MES_APROX = 30

# ── negocio (F8-2): reventa de refrescos, negocio_compras/negocio_ventas ───
NEGOCIO_PRODUCTO_DEFAULT = "refresco"
SEMANAS_HISTORICO_NEGOCIO = 4
# El ritmo actual de ventas cae esto o mas vs. su promedio historico -> avisar.
UMBRAL_RITMO_VENTAS_PCT = 0.5
# Piso de unidades vendidas en el periodo historico para confiar en su
# promedio (mismo espiritu que MIN_HISTORICO arriba).
MIN_UNIDADES_HISTORICO_RITMO = 5
# Dias desde la ultima compra antes de esperar que las ventas ya la hayan
# cubierto -- comprar una reja y no recuperarla en 2 dias es normal, no una
# desviacion; una semana y media es un piso conservador para no meter ruido.
DIAS_GRACIA_RECUPERAR_REJA = 10


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


def evaluar_inmediato(lib, *, avisar_fn=None, marcar_estado=True):
    """Revisa los gastos registrados desde la última corrida y avisa los
    atípicos apenas se detectan (r.25). Devuelve los hallazgos avisados.

    avisar_fn=None (default) resuelve avisar() en el momento de la llamada,
    no al definir la función -- así un monkeypatch de pruebas sobre el
    nombre del módulo sí se respeta (si quedara ligado al valor por default
    de la firma, quedaría congelado a la función original desde el import)."""
    if avisar_fn is None:
        avisar_fn = avisar
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


# ── detección: pagos recurrentes sin registrar (consolidado dominical) ─────

def detectar_pagos_recurrentes_sin_registrar(lib, hoy_str=None):
    """Fijos (`pagos_recurrentes`) cuyo ciclo mas reciente no tiene un gasto
    correspondiente en `gastos` (categoria = nombre del fijo, ej. 'gym',
    'deepseek', 'colegiatura').

    Solo avisa si YA hubo al menos un gasto de ese fijo ANTES del ciclo
    actual -- sin eso es "nunca confirmado", no una desviacion de un patron
    (mismo criterio que brief_matutino.py trata `ultimo_pago IS NULL`: falta
    de dato no es alarma). Evita que un fijo recien dado de alta, o uno que
    Arturo simplemente no ha empezado a registrar todavia, dispare cada
    domingo desde el dia uno."""
    hoy_str = hoy_str or lib.hoy()
    hallazgos = []
    pagos = lib.con.execute(
        "SELECT * FROM pagos_recurrentes WHERE activo = 1"
    ).fetchall()
    for p in pagos:
        desde_ciclo = fecha_hace_n_dias(DIAS_POR_MES_APROX * p["frecuencia_meses"], hoy_str)
        hubo_antes = lib.con.execute(
            "SELECT 1 FROM gastos WHERE categoria = ? AND fecha < ? LIMIT 1",
            (p["nombre"], desde_ciclo),
        ).fetchone()
        if not hubo_antes:
            continue
        total_ciclo, _ = _total_categoria_periodo(lib, p["nombre"], desde_ciclo, hoy_str)
        if total_ciclo > 0:
            continue
        hallazgos.append({
            "tipo": "recurrente_sin_registrar", "nombre": p["nombre"],
            "monto_esperado": p["monto_mxn"], "frecuencia_meses": p["frecuencia_meses"],
            "desde": desde_ciclo, "hasta": hoy_str,
        })
    return hallazgos


def construir_mensaje_recurrente_sin_registrar(h):
    return (
        f"• {h['nombre']}: esperaba ~${h['monto_esperado']:.2f} (cada "
        f"{h['frecuencia_meses']} mes(es)) y no veo nada registrado en "
        f"gastos desde {h['desde']} — ¿lo registraste o no aplicó?"
    )


# ── detección: negocio de reventa de refrescos ──────────────────────────────

def detectar_reja_mas_cara(lib, producto=NEGOCIO_PRODUCTO_DEFAULT):
    """La compra mas reciente cuesta mas que la compra inmediata anterior.
    Comparacion directa contra la ultima, no un promedio -- con pocas
    compras historicas un promedio no dice nada todavia."""
    compras = lib.con.execute(
        "SELECT * FROM negocio_compras WHERE producto = ? "
        "ORDER BY fecha DESC, id DESC LIMIT 2",
        (producto,),
    ).fetchall()
    if len(compras) < 2:
        return None
    ultima, anterior = compras[0], compras[1]
    if ultima["costo_mxn"] <= anterior["costo_mxn"]:
        return None
    return {
        "tipo": "reja_mas_cara", "producto": producto,
        "costo_actual": ultima["costo_mxn"], "costo_anterior": anterior["costo_mxn"],
        "fecha": ultima["fecha"],
    }


def construir_mensaje_reja_mas_cara(h):
    return (
        f"• {h['producto']}: la última reja costó ${h['costo_actual']:.2f} "
        f"({h['fecha']}), más que la compra anterior (${h['costo_anterior']:.2f}) "
        f"— ¿subió el precio o fue otra cosa?"
    )


def _unidades_por_dia(lib, producto, desde, hasta):
    total = lib.con.execute(
        "SELECT COALESCE(SUM(unidades),0) FROM negocio_ventas "
        "WHERE producto = ? AND fecha BETWEEN ? AND ?",
        (producto, desde, hasta),
    ).fetchone()[0]
    dias = (datetime.fromisoformat(hasta).date()
            - datetime.fromisoformat(desde).date()).days + 1
    return (total / dias if dias > 0 else 0.0), total


def detectar_ritmo_ventas_bajo(lib, producto=NEGOCIO_PRODUCTO_DEFAULT, hoy_str=None):
    """Piezas/dia de la semana actual vs. el promedio de las
    SEMANAS_HISTORICO_NEGOCIO semanas previas -- mismo patron que
    detectar_categorias_disparadas, pero mirando hacia abajo (ritmo que cae)
    en vez de hacia arriba (categoria que se dispara)."""
    hoy_str = hoy_str or lib.hoy()
    semana_actual_desde = fecha_hace_n_dias(6, hoy_str)
    hasta_previo = fecha_hace_n_dias(7, hoy_str)
    desde_previo = fecha_hace_n_dias(7 + 7 * SEMANAS_HISTORICO_NEGOCIO - 1, hoy_str)
    ritmo_previo, total_previo = _unidades_por_dia(lib, producto, desde_previo, hasta_previo)
    if total_previo < MIN_UNIDADES_HISTORICO_RITMO or ritmo_previo <= 0:
        return None
    ritmo_actual, total_actual = _unidades_por_dia(lib, producto, semana_actual_desde, hoy_str)
    variacion = (ritmo_actual - ritmo_previo) / ritmo_previo
    if variacion > -UMBRAL_RITMO_VENTAS_PCT:
        return None
    return {
        "tipo": "ritmo_ventas_bajo", "producto": producto,
        "ritmo_actual": ritmo_actual, "ritmo_previo": ritmo_previo,
        "total_actual": total_actual, "variacion_pct": variacion * 100,
    }


def construir_mensaje_ritmo_ventas_bajo(h):
    return (
        f"• {h['producto']}: vendiste ~{h['ritmo_actual']:.1f} piezas/día "
        f"esta semana, {abs(h['variacion_pct']):.0f}% menos que tu ritmo "
        f"habitual (~{h['ritmo_previo']:.1f} piezas/día) — ¿bajaron las "
        f"ventas o falta registrar algo?"
    )


def detectar_negocio_no_recupera_reja(lib, producto=NEGOCIO_PRODUCTO_DEFAULT, hoy_str=None):
    """Desde la ultima compra, ¿las ventas ya cubrieron lo invertido
    (margen_negocio())? Solo avisa si ya pasaron DIAS_GRACIA_RECUPERAR_REJA
    dias -- recien comprar y no haber recuperado todavia es normal."""
    hoy_str = hoy_str or lib.hoy()
    ultima_compra = lib.con.execute(
        "SELECT * FROM negocio_compras WHERE producto = ? "
        "ORDER BY fecha DESC, id DESC LIMIT 1",
        (producto,),
    ).fetchone()
    if ultima_compra is None:
        return None
    dias_desde_compra = (datetime.fromisoformat(hoy_str).date()
                         - datetime.fromisoformat(ultima_compra["fecha"]).date()).days
    if dias_desde_compra < DIAS_GRACIA_RECUPERAR_REJA:
        return None
    m = lib.margen_negocio(producto, desde=ultima_compra["fecha"], hasta=hoy_str)
    if m["ganancia"] >= 0:
        return None
    return {"tipo": "negocio_no_recupera", "producto": producto,
            "dias_desde_compra": dias_desde_compra, **m}


def construir_mensaje_negocio_no_recupera(h):
    return (
        f"• {h['producto']}: pasaron {h['dias_desde_compra']} días desde la "
        f"última reja (${h['invertido']:.2f}) y las ventas solo han traído "
        f"${h['ingreso']:.2f} ({h['unidades_vendidas']} piezas) — no se ha "
        f"recuperado. ¿bajó el ritmo o falta registrar ventas?"
    )


def construir_consolidado_dominical(lib, hoy_str=None):
    hoy_str = hoy_str or lib.hoy()
    disparadas = detectar_categorias_disparadas(lib, hoy_str)
    fijos_faltantes = detectar_pagos_recurrentes_sin_registrar(lib, hoy_str)
    negocio_hallazgos = [h for h in (
        detectar_reja_mas_cara(lib),
        detectar_ritmo_ventas_bajo(lib, hoy_str=hoy_str),
        detectar_negocio_no_recupera_reja(lib, hoy_str=hoy_str),
    ) if h is not None]
    constructores_negocio = {
        "reja_mas_cara": construir_mensaje_reja_mas_cara,
        "ritmo_ventas_bajo": construir_mensaje_ritmo_ventas_bajo,
        "negocio_no_recupera": construir_mensaje_negocio_no_recupera,
    }

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

    if fijos_faltantes:
        lineas.append("\nFijos que no veo registrados este ciclo:")
        lineas.extend(construir_mensaje_recurrente_sin_registrar(h) for h in fijos_faltantes)

    if negocio_hallazgos:
        lineas.append("\nNegocio (refrescos):")
        lineas.extend(constructores_negocio[h["tipo"]](h) for h in negocio_hallazgos)

    if disparadas or fijos_faltantes or negocio_hallazgos:
        lineas.append("\n¿Alguna de estas fue intencional o quieres que le ponga ojo?")
    return "\n".join(lineas)


def evaluar_dominical(lib, *, avisar_fn=None):
    if avisar_fn is None:
        avisar_fn = avisar
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
