#!/usr/bin/env python3
"""
brief_matutino.py — El "panorama del día" de las 6:30 que Arturo puso como su
prioridad #1 (cuestionario r.98: *"Reportes y un panorama general de lo que va
a suceder y voy a realizar en el día"*; r.86: clima cruzado con la agenda +
noticias de trading + todo lo que deba saber).

Qué hace, y qué NO:
    SÍ arma el brief con datos REALES de su vida (la libreta) + clima (Open-Meteo,
    sin llave) + noticias de trading (best-effort) y lo empuja UNA vez a Telegram
    (reutiliza enviar.py, igual que cierre_del_dia.py y vigilar_correo_escuela.py).
    NO usa modelos de pago: todo es determinista o APIs gratis. Cada sección
    degrada con gracia: si el clima o las noticias fallan, el brief sale igual con
    lo demás (HAS L6/L14 — nunca fallar en silencio, pero tampoco caerse entero).

Reloj: usa el reloj de la libreta (real, o el virtual HERMES_FECHA_SIMULADA en
simulación) — por eso se puede probar un lunes de gym con lluvia sin esperar al
lunes. Entorno via HERMES_ENTORNO (real por defecto).

USO:
    python3 brief_matutino.py               # arma y envía a Telegram
    python3 brief_matutino.py --print       # solo imprime (no envía) — para probar
    python3 brief_matutino.py --forzar      # reenvía aunque ya se mandó hoy
    HERMES_ENTORNO=simulacion HERMES_FECHA_SIMULADA=2026-09-14T06:30 \
        python3 brief_matutino.py --print   # simular un día concreto
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import Libreta, entorno_activo  # noqa: E402

HOME = Path.home()
LOG = HOME / ".hermes/logs/brief_matutino.log"
ESTADO = HOME / ".hermes/state/brief_matutino.json"
ENVIAR = HOME / ".hermes/scripts/enviar.py"
PYTHON = HOME / ".hermes/hermes-agent/venv/bin/python"

# Iguala de la Independencia, Guerrero (r.116). Zona America/Mexico_City.
LAT, LON = 18.3446, -99.5405
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


# ── clima (Open-Meteo, gratis, sin llave) ────────────────────────────────
def _clima(fecha: str) -> dict | None:
    """Devuelve {'max','min','prob_lluvia','hora_lluvia'} o None si falla."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&hourly=precipitation_probability"
        "&timezone=America%2FMexico_City"
        f"&start_date={fecha}&end_date={fecha}"
    )
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            d = json.load(r)
        daily = d["daily"]
        prob = daily["precipitation_probability_max"][0]
        hora_lluvia = None
        if prob and prob >= 50:
            horas = d["hourly"]["time"]
            probs = d["hourly"]["precipitation_probability"]
            pico = max(range(len(probs)), key=lambda i: probs[i] or 0)
            hora_lluvia = horas[pico][11:16]  # 'HH:MM'
        return {
            "max": daily["temperature_2m_max"][0],
            "min": daily["temperature_2m_min"][0],
            "prob_lluvia": prob,
            "hora_lluvia": hora_lluvia,
        }
    except Exception as e:  # noqa: BLE001 — best-effort, el brief sale sin clima
        log(f"⚠️  clima no disponible ({type(e).__name__}: {e}) — sigo sin él")
        return None


def _seccion_clima(lib: Libreta, fecha: str, dia_semana: int) -> str:
    c = _clima(fecha)
    if not c:
        return ""
    linea = f"🌤️ Clima: {round(c['min'])}–{round(c['max'])}°C"
    if c["prob_lluvia"] and c["prob_lluvia"] >= 50:
        linea += f", {c['prob_lluvia']}% de lluvia"
        if c["hora_lluvia"]:
            linea += f" (pico ~{c['hora_lluvia']})"
        # cruzar con la agenda: ¿hay gym/trabajo a esa hora hoy?
        bloques = lib.con.execute(
            "SELECT actividad, hora_inicio, hora_fin FROM horario "
            "WHERE dia_semana = ? AND activo = 1 ORDER BY hora_inicio",
            (dia_semana,),
        ).fetchall()
        for b in bloques:
            act = (b["actividad"] or "").lower()
            if c["hora_lluvia"] and b["hora_inicio"] and b["hora_fin"]:
                if b["hora_inicio"] <= c["hora_lluvia"] <= b["hora_fin"] and (
                    "gym" in act or "trabaj" in act or "graba" in act
                ):
                    linea += f" — ojo, se cruza con «{b['actividad']}» ({b['hora_inicio']}–{b['hora_fin']})"
                    break
    return linea


# ── noticias de trading (best-effort, Brave si hay llave) ────────────────
def _seccion_trading() -> str:
    key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not key:
        # buscar en .env sin exponer nada
        envf = HOME / ".hermes/hermes-agent/.env"
        if envf.exists():
            for ln in envf.read_text(errors="ignore").splitlines():
                if ln.startswith("BRAVE_SEARCH_API_KEY="):
                    key = ln.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        return ""
    try:
        req = urllib.request.Request(
            "https://api.search.brave.com/res/v1/news/search?q=bitcoin+ethereum+cripto+hoy&count=3&freshness=pd&search_lang=es",
            headers={"Accept": "application/json", "X-Subscription-Token": key},
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.load(r)
        items = (d.get("results") or [])[:3]
        if not items:
            return ""
        líneas = ["📈 Trading (titulares de hoy):"]
        for it in items:
            líneas.append(f"  • {it.get('title', '').strip()[:90]}")
        return "\n".join(líneas)
    except Exception as e:  # noqa: BLE001
        log(f"⚠️  noticias de trading no disponibles ({type(e).__name__}) — sigo sin ellas")
        return ""


# ── el brief ─────────────────────────────────────────────────────────────
def construir_brief(entorno: str | None = None) -> str:
    ent = entorno_activo(entorno)
    with Libreta(ent, solo_lectura=True) as lib:
        ahora = lib.ahora()
        fecha = lib.hoy()
        dia_semana = ahora.isoweekday()  # 1=lunes
        partes: list[str] = [f"☀️ Buenos días, jefe. {DIAS_ES[dia_semana - 1].capitalize()} {ahora.strftime('%d/%m')}."]

        clima = _seccion_clima(lib, fecha, dia_semana)
        if clima:
            partes.append("")
            partes.append(clima)

        # agenda del día: horario + citas
        bloques = lib.con.execute(
            "SELECT actividad, hora_inicio, hora_fin FROM horario "
            "WHERE dia_semana = ? AND activo = 1 ORDER BY hora_inicio",
            (dia_semana,),
        ).fetchall()
        citas_hoy = lib.con.execute(
            "SELECT titulo, fecha_hora, lugar FROM citas "
            "WHERE date(fecha_hora) = ? ORDER BY fecha_hora",
            (fecha,),
        ).fetchall()
        if bloques or citas_hoy:
            partes.append("\n🗓️ Tu día:")
            for b in bloques:
                fin = f"–{b['hora_fin']}" if b["hora_fin"] else ""
                partes.append(f"  • {b['hora_inicio']}{fin} {b['actividad']}")
            for c in citas_hoy:
                hora = c["fecha_hora"][11:16] if len(c["fecha_hora"]) >= 16 else ""
                lugar = f" ({c['lugar']})" if c["lugar"] else ""
                partes.append(f"  • {hora} {c['titulo']}{lugar}")

        # pagos por vencer (avisar con anticipación, r.81). SOLO los realmente
        # próximos (con fecha calculable): un pago sin ultimo_pago registrado no
        # es "cerca", es "sin confirmar" — no se grita como alarma cada mañana.
        pagos = [p for p in lib.pagos_recurrentes_por_vencer(dentro_de_dias=3)
                 if p["proximo_pago"] is not None]
        if pagos:
            partes.append("\n💸 Pagos cerca:")
            for p in pagos:
                partes.append(f"  • {p['nombre']}: ${p['monto_mxn']:.0f} (≈{p['proximo_pago']})")

        # tareas escolares con entrega cercana
        tareas = lib.tareas_pendientes(dentro_de_dias=3)
        if tareas:
            partes.append("\n📚 Escuela (entrega cerca):")
            for t in tareas:
                ent_txt = f" — entrega {t['fecha_entrega']}" if t["fecha_entrega"] else ""
                partes.append(f"  • {t['titulo']}{ent_txt}")

        # avance de la meta capital
        try:
            m = lib.meta_ahorro("capital_principal")
            if m:
                falta = m["objetivo_mxn"] - m["acumulado_mxn"]
                pct = (m["acumulado_mxn"] / m["objetivo_mxn"] * 100) if m["objetivo_mxn"] else 0
                partes.append(
                    f"\n🎯 Capital: ${m['acumulado_mxn']:,.0f} / ${m['objetivo_mxn']:,.0f} "
                    f"({pct:.0f}%) — faltan ${falta:,.0f}"
                )
        except Exception as e:  # noqa: BLE001
            log(f"⚠️  meta capital no leída ({e})")

    # noticias de trading (fuera del 'with': no toca la libreta)
    trading = _seccion_trading()
    if trading:
        partes.append("\n" + trading)

    return "\n".join(partes)


# ── envío (mismo patrón que cierre_del_dia.py) ───────────────────────────
def _ya_se_envio_hoy() -> bool:
    if not ESTADO.exists():
        return False
    try:
        return json.loads(ESTADO.read_text()).get("ultimo_envio") == datetime.date.today().isoformat()
    except Exception as e:  # noqa: BLE001
        log(f"⚠️  no pude leer estado ({e}) — envío de todos modos")
        return False


def _marcar_enviado() -> None:
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps({"ultimo_envio": datetime.date.today().isoformat()}))
    os.replace(tmp, ESTADO)


def main() -> None:
    solo_print = "--print" in sys.argv
    brief = construir_brief()

    if solo_print:
        print("\n" + brief + "\n")
        return

    if _ya_se_envio_hoy() and "--forzar" not in sys.argv:
        log("✅ ya se envió el brief hoy, no repito (usa --forzar)")
        return

    r = subprocess.run([str(PYTHON), str(ENVIAR), "--mensaje", brief],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log(f"🔴 FALLO al enviar el brief: {r.stderr.strip()[:200]}")
        sys.exit(1)
    _marcar_enviado()
    log("✅ brief matutino enviado")


if __name__ == "__main__":
    main()
