#!/usr/bin/env python3
"""
cierre_del_dia.py — El cuestionario nocturno que Arturo pidio el 31 jul 2026:
*"prefiero obviamente que el cuestionario me lo haga Hermes al final del dia"*.

Que hace este script, y que NO hace:
    SI empuja la pregunta a Telegram una vez por dia (reutiliza enviar.py,
    igual que vigilar_correo_escuela.py).
    NO interpreta la respuesta de Arturo ni escribe en la libreta -- eso
    pasa en la conversacion normal de Telegram con el Hermes en vivo, que ya
    tiene el toolset 'terminal'/'code_execution' encendido y sabe usar
    libreta.py (ver skills/finanzas/SKILL.md, seccion 3). Un cron no puede
    "escuchar" la respuesta; la conversacion si.

Hora por defecto 22:45, porque su bloque de trabajo real termina ~22:30 casi
todos los dias (ver docs/DISENO_INTERFACES.md) -- es una referencia visual
"por confirmar", no un dato duro, asi que si a Arturo le cae mal la hora, se
ajusta el timer sin tocar este script.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys

HOME = os.path.expanduser("~")
ESTADO = os.path.join(HOME, ".hermes/state/cierre_del_dia.json")
LOG = os.path.join(HOME, ".hermes/logs/cierre_del_dia.log")
ENVIAR = os.path.join(HOME, ".hermes/scripts/enviar.py")
PYTHON = os.path.join(HOME, ".hermes/hermes-agent/venv/bin/python")

PREGUNTA = (
    "🌙 Cierre del día\n\n"
    "¿Trabajaste hoy en la taquería? ¿Cuánto ganaste?\n"
    "¿Vendiste refrescos? ¿Cuántos?\n"
    "¿Algún gasto que anotar (gasolina, comida, algo extra)?\n\n"
    "Contéstame como quieras, yo lo registro."
)


def log(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def ya_se_pregunto_hoy() -> bool:
    hoy = datetime.date.today().isoformat()
    if not os.path.exists(ESTADO):
        return False
    try:
        import json
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f).get("ultima_pregunta") == hoy
    except Exception as e:
        log(f"⚠️  No pude leer el estado ({e}) — pregunto de todos modos, "
            f"mejor repetir que quedarme callado")
        return False


def marcar_preguntado() -> None:
    import json
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ultima_pregunta": datetime.date.today().isoformat()}, f)
    os.replace(tmp, ESTADO)


def main() -> None:
    if ya_se_pregunto_hoy() and "--forzar" not in sys.argv:
        log("✅ ya se pregunto hoy, no repito (usa --forzar para saltarlo)")
        return

    r = subprocess.run([PYTHON, ENVIAR, "--mensaje", PREGUNTA],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log(f"🔴 FALLO al mandar el cierre del dia: {r.stderr.strip()[:200]}")
        sys.exit(1)

    marcar_preguntado()
    log("✅ pregunta de cierre del dia enviada")


if __name__ == "__main__":
    main()
