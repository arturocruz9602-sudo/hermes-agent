#!/usr/bin/env python3
"""
cierre_del_dia_audio.py — Resumen nocturno EN AUDIO (r.90: *"de preferencia
ahí SÍ que use audio, y que sea cuando yo vaya a descansar"*).

Qué hace, y qué NO:
    SÍ arma un resumen breve del día (saldo, gastos por categoría, pagos
    cerca, tareas de mañana) con datos REALES de la libreta, lo convierte a
    voz reutilizando tools.tts_tool.text_to_speech_tool (el mismo TTS que ya
    usa el resto de Hermes -- NO se crea un motor nuevo) y guarda el .ogg
    (Opus) listo para nota de voz de Telegram.
    NO lo envía a Telegram todavía. Candado r.119: esta sesión corre en el
    HOST con credenciales de PRODUCCIÓN y no existe un canal QA de Telegram
    configurado en ~/.hermes/.env. enviar_voz() ya está cableada en
    enviar.py, pero el envío en vivo (sendVoice) queda PENDIENTE hasta que
    exista un canal QA o Arturo apruebe mandarlo a producción directamente
    (ver docs/ESTADO.md).
    NO interpreta ni escribe nada nuevo en la libreta -- solo lee (mismo
    patrón de solo_lectura=True que brief_matutino.py).

Reloj: usa el reloj de la libreta (real, o el virtual HERMES_FECHA_SIMULADA
en simulación) — igual que brief_matutino.py, así se puede probar un día
concreto sin esperar a que llegue.

USO:
    python3 cierre_del_dia_audio.py --print      # solo el texto (no genera audio)
    python3 cierre_del_dia_audio.py --generar    # genera el .ogg y lo VERIFICA local (no envía)
    python3 cierre_del_dia_audio.py --generar --forzar   # aunque ya se haya generado hoy
    HERMES_ENTORNO=simulacion HERMES_FECHA_SIMULADA=2026-09-14T22:45 \
        python3 cierre_del_dia_audio.py --print   # simular un día concreto
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import Libreta, entorno_activo  # noqa: E402

HOME = Path.home()
LOG = HOME / ".hermes/logs/cierre_del_dia_audio.log"
ESTADO = HOME / ".hermes/state/cierre_del_dia_audio.json"
AUDIO_DIR = HOME / ".hermes/cache/audio/cierre_del_dia"

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def construir_resumen(entorno: str | None = None) -> str:
    """Arma el texto hablado del resumen nocturno con datos reales de la libreta."""
    ent = entorno_activo(entorno)
    with Libreta(ent, solo_lectura=True) as lib:
        ahora = lib.ahora()
        fecha = lib.hoy()
        balance = lib.balance(desde=fecha, hasta=fecha)
        categorias = lib.gastos_por_categoria(desde=fecha, hasta=fecha)
        pagos = [p for p in lib.pagos_recurrentes_por_vencer(dentro_de_dias=3)
                 if p["proximo_pago"] is not None]
        tareas = lib.tareas_pendientes(dentro_de_dias=1)

    partes = [f"Buenas noches, jefe. Resumen de hoy, {ahora.day} de {MESES_ES[ahora.month - 1]}."]

    if balance["ingresos"] or balance["gastos"]:
        partes.append(
            f"Ingresos: {balance['ingresos']:.0f} pesos. "
            f"Gastos: {balance['gastos']:.0f} pesos. "
            f"Saldo del día: {balance['saldo']:.0f} pesos."
        )
        if categorias:
            top = ", ".join(f"{c['categoria']} {c['total']:.0f} pesos" for c in categorias[:3])
            partes.append(f"Lo más fuerte: {top}.")
    else:
        partes.append("No registré gastos ni ingresos hoy.")

    if pagos:
        cerca = ", ".join(f"{p['nombre']} el {p['proximo_pago']}" for p in pagos)
        partes.append(f"Pagos cerca: {cerca}.")

    if tareas:
        pendientes = ", ".join(t["titulo"] for t in tareas)
        partes.append(f"Para mañana en la escuela: {pendientes}.")

    partes.append("Eso es todo. Que descanses.")
    return " ".join(partes)


def _ya_se_genero_hoy() -> bool:
    if not ESTADO.exists():
        return False
    try:
        return json.loads(ESTADO.read_text()).get("ultimo_audio") == datetime.date.today().isoformat()
    except Exception as e:  # noqa: BLE001
        log(f"⚠️  no pude leer el estado ({e}) — genero de todos modos, "
            f"mejor repetir que quedarme callado")
        return False


def _marcar_generado(ruta: str) -> None:
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "ultimo_audio": datetime.date.today().isoformat(),
        "archivo": ruta,
    }))
    os.replace(tmp, ESTADO)


def _verificar_ogg_opus(ruta: str) -> bool:
    """Confirma EN DISCO (no de fe) que el archivo existe y es Opus válido.

    HAS regla 1: nada de auto-reportes. "El TTS no tiró error" no es
    verificación -- correr ffprobe sobre el archivo real sí lo es.
    """
    if not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
        log(f"🔴 el .ogg no existe o está vacío: {ruta}")
        return False
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of",
             "default=noprint_wrappers=1:nokey=1", ruta],
            capture_output=True, text=True, timeout=15,
        )
    except Exception as e:  # noqa: BLE001
        log(f"🔴 ffprobe falló al verificar {ruta}: {e}")
        return False
    codec = r.stdout.strip()
    if codec != "opus":
        log(f"🔴 codec inesperado en {ruta}: '{codec}' (se esperaba 'opus')")
        return False
    return True


def generar_audio(entorno: str | None = None) -> str | None:
    """Genera el .ogg del resumen y lo VERIFICA localmente. NUNCA lo envía."""
    from tools.tts_tool import text_to_speech_tool

    texto = construir_resumen(entorno)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    salida = AUDIO_DIR / f"cierre_{timestamp}.ogg"

    resultado_raw = text_to_speech_tool(texto, output_path=str(salida))
    try:
        resultado = json.loads(resultado_raw)
    except json.JSONDecodeError:
        log(f"🔴 TTS devolvió algo no-JSON: {resultado_raw[:200]}")
        return None

    if not resultado.get("success"):
        log(f"🔴 TTS falló: {resultado.get('error', 'sin detalle')}")
        return None

    archivo = resultado["file_path"]
    if not _verificar_ogg_opus(archivo):
        return None

    tam = os.path.getsize(archivo)
    log(f"✅ audio del cierre generado y verificado: {archivo} ({tam:,} bytes, opus ok)")
    return archivo


def main() -> None:
    if "--print" in sys.argv:
        print("\n" + construir_resumen() + "\n")
        return

    if "--generar" not in sys.argv:
        print("USO:")
        print("  python3 cierre_del_dia_audio.py --print              → solo el texto")
        print("  python3 cierre_del_dia_audio.py --generar             → genera y verifica el .ogg (NO envía)")
        print("  python3 cierre_del_dia_audio.py --generar --forzar    → aunque ya se haya generado hoy")
        sys.exit(1)

    if _ya_se_genero_hoy() and "--forzar" not in sys.argv:
        log("✅ ya se generó el audio del cierre hoy, no repito (usa --forzar)")
        return

    archivo = generar_audio()
    if not archivo:
        sys.exit(1)

    _marcar_generado(archivo)
    log(
        "⏸️  ENVÍO PENDIENTE (candado r.119): no hay canal QA de Telegram "
        "configurado y esta sesión corre con credenciales de producción. "
        "enviar_voz() ya está cableada en enviar.py -- falta activarla "
        "cuando exista canal QA o Arturo apruebe producción. Ver ESTADO.md."
    )


if __name__ == "__main__":
    main()
