#!/usr/bin/env python3
"""ventana_mantenimiento.py -- Ventana de mantenimiento nocturna (HAS §E14).

Corre SOLO entre 2:00 y 5:00 (hora local de la HP). No confundir con "ventana
de mantenimiento" de E9 regla 7 (esa es el ciclo de suscripción de Claude Pro,
~cada 4 meses -- HAS E14 lo aclara explícito). Si un mantenimiento invade
horario de servicio -- Hermes respondiéndole a Arturo con latencia degradada
por una tarea de fondo -- es bug, no característica.

Gate térmico (r.103): mientras la HP esté a >=85°C, pausa antes de seguir.

PERSISTENCIA: reusa `cola_v2.ColaTareas` (HAS §E5, F5-2 -- de ahí la
dependencia declarada en `loop_cola.py`) en vez de inventar una cola nueva.
La garantía dura de F5-2 (toda tarea termina en `notificada` o `atorada`+aviso,
nada se pierde en silencio, todo intento queda en `task_queue_log`) YA cubre
el requisito de "ejecutar con evidencia" de este bloque -- no hay que
reconstruirla aquí.

FUENTES DE CANDIDATOS
  - conectada hoy: skills `stale` -- HAS §F5/§E3, `last_verified` > 180 días
    sobre skills `status: active` en `~/.hermes/skills`.
  - documentadas, SIN conectar todavía (el subsistema real no existe aún --
    no se inventa aquí, queda anotado en ESTADO.md como pendiente):
      * bugs con logs (necesita un canal real de reporte de errores).
      * propuestas del barrido semanal (F3/F4 -- el barrido semanal en sí
        todavía no corre).

Lo que este módulo NO hace: reparar skills. Detectar y dejar evidencia
accionable es el mantenimiento de esta ventana; aplicar el arreglo pasa por
la compuerta F2v2 (respaldo -> investigar -> staging -> probar vieja Y nueva),
un mecanismo aparte.

Uso:
    python3 scripts/ventana_mantenimiento.py acumular         # detecta y encola candidatos nuevos
    python3 scripts/ventana_mantenimiento.py correr           # ejecuta la cola (respeta ventana+temp)
    python3 scripts/ventana_mantenimiento.py correr --forzar  # ignora el horario (pruebas/diagnóstico)
    python3 scripts/ventana_mantenimiento.py estado           # cuenta por estado + evidencia reciente
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yaml

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from cola_v2 import ATORADA, ENCOLADA, EN_PROCESO, NOTIFICADA, ColaTareas, SolverError  # noqa: E402

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILLS_DIR = HERMES_HOME / "skills"

HORA_INICIO = 2
HORA_FIN = 5
TEMP_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
UMBRAL_TEMP_C = 85            # r.103
PAUSA_TERMICA_S = 30
UMBRAL_STALE_DIAS = 180       # HAS §F5/§E3
CHAT_ID_MANTENIMIENTO = "ventana_mantenimiento"


# --- Ventana horaria + gate térmico ------------------------------------------
def en_ventana(ahora: datetime | None = None) -> bool:
    """True solo entre las 2:00 y las 5:00 (HAS §E14)."""
    h = (ahora or datetime.now()).hour
    return HORA_INICIO <= h < HORA_FIN


def temp_hp() -> int | None:
    try:
        return int(TEMP_PATH.read_text().strip()) // 1000
    except Exception:
        return None


def gate_termico(*, lector=temp_hp, dormir=time.sleep, umbral: int = UMBRAL_TEMP_C,
                  pausa_s: int = PAUSA_TERMICA_S, avisar=print) -> None:
    """Pausa mientras la HP esté >= umbral (r.103). `lector`/`dormir`
    inyectables para que las pruebas nunca duerman ni lean /sys de verdad."""
    while True:
        t = lector()
        if t is None or t < umbral:
            return
        avisar(f"  \U0001f321️  HP a {t}°C >= {umbral}°C -- pauso {pausa_s}s (r.103)...")
        dormir(pausa_s)


# --- Fuente: skills stale (HAS §F5/§E3) --------------------------------------
def _leer_frontmatter(skill_md: Path) -> dict:
    texto = skill_md.read_text(encoding="utf-8", errors="replace")
    if not texto.startswith("---"):
        return {}
    fin = texto.find("\n---", 3)
    if fin == -1:
        return {}
    try:
        datos = yaml.safe_load(texto[3:fin])
    except yaml.YAMLError:
        return {}
    return datos if isinstance(datos, dict) else {}


def _a_fecha(valor) -> date | None:
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            return None
    return None


def detectar_skills_stale(skills_dir: Path = SKILLS_DIR, *,
                           umbral_dias: int = UMBRAL_STALE_DIAS,
                           hoy: date | None = None) -> list[dict]:
    """Skill `status: active` con `last_verified` > umbral_dias -> stale
    (HAS §F5). Skills sin el campo (aún sin clasificar por F2v2 v1.5 pt.3) no
    cuentan aquí -- es un problema distinto ("sin clasificar", no "vencida")."""
    hoy = hoy or date.today()
    hallazgos = []
    if not skills_dir.exists():
        return hallazgos
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        fm = _leer_frontmatter(skill_md)
        if fm.get("status") != "active":
            continue
        lv = _a_fecha(fm.get("last_verified"))
        if lv is None:
            continue
        dias = (hoy - lv).days
        if dias > umbral_dias:
            hallazgos.append({
                "tipo": "skill_stale",
                "skill": fm.get("name", skill_md.parent.name),
                "ruta": str(skill_md),
                "last_verified": lv.isoformat(),
                "dias_de_atraso": dias,
            })
    return hallazgos


def _huella(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def acumular(cola: ColaTareas, *, skills_dir: Path = SKILLS_DIR,
             hoy: date | None = None) -> int:
    """Encola candidatos nuevos detectados en esta pasada (dedup contra lo que
    ya sigue activo -- `encolada`/`en_proceso` -- para no duplicar; una vez
    resuelta y notificada, si sigue stale la próxima noche, se vuelve a
    encolar). Devuelve cuántos se encolaron."""
    activos = set()
    for f in cola.con.execute(
            "SELECT payload FROM task_queue WHERE estado IN (?, ?)",
            (ENCOLADA, EN_PROCESO)):
        try:
            activos.add(_huella(json.loads(f["payload"])))
        except (json.JSONDecodeError, TypeError):
            continue

    encolados = 0
    for hallazgo in detectar_skills_stale(skills_dir, hoy=hoy):
        if _huella(hallazgo) in activos:
            continue
        cola.encolar(
            f"mantenimiento: skill stale -- {hallazgo['skill']} "
            f"({hallazgo['dias_de_atraso']}d, umbral {UMBRAL_STALE_DIAS}d)",
            hallazgo, chat_id=CHAT_ID_MANTENIMIENTO,
        )
        encolados += 1
    return encolados


# --- Ejecución de la cola -----------------------------------------------------
def solver_mantenimiento(payload: dict, proveedor: str) -> str:
    """Re-verifica el hallazgo AL EJECUTAR (pudo arreglarse entre `acumular` y
    `correr`) y devuelve la evidencia. No repara nada -- eso pasa por F2v2."""
    tipo = payload.get("tipo")
    if tipo != "skill_stale":
        raise SolverError(f"tipo de mantenimiento sin manejador: {tipo!r}")

    ruta = Path(payload["ruta"])
    if not ruta.exists():
        return json.dumps(
            {"skill": payload.get("skill"), "evidencia": "la skill ya no existe (borrada/movida)"},
            ensure_ascii=False)

    fm = _leer_frontmatter(ruta)
    lv = _a_fecha(fm.get("last_verified"))
    if lv is not None and (date.today() - lv).days <= UMBRAL_STALE_DIAS:
        return json.dumps({
            "skill": payload.get("skill"),
            "evidencia": f"ya no está stale: last_verified={lv.isoformat()}",
        }, ensure_ascii=False)

    return json.dumps({
        "skill": payload.get("skill"),
        "evidencia": f"sigue stale: last_verified={lv.isoformat() if lv else None}, "
                      f"umbral={UMBRAL_STALE_DIAS}d",
        "accion_sugerida": "correr F2v2 (respaldo->investigar->staging->probar "
                            "vieja y nueva) o clasificar nivel_riesgo=critico si aplica",
    }, ensure_ascii=False)


def notificador_mantenimiento(chat_id: str, texto: str) -> None:
    """De noche no se despierta a Arturo por esto (E14: la ventana es para no
    competir con el servicio, no para generar ruido nuevo). La garantía dura
    de F5-2 ya deja la evidencia en `task_queue`/`task_queue_log`; enganchar
    un resumen al brief matutino es trabajo aparte, anotado como pendiente."""
    return None


def correr(cola: ColaTareas, *, forzar: bool = False, ahora: datetime | None = None,
           gate=gate_termico, dormir=time.sleep, limite: int | None = None) -> dict:
    if not forzar and not en_ventana(ahora):
        return {"corrido": False, "razon": "fuera de ventana 2:00-5:00 (HAS E14)",
                "resueltas": 0, "atoradas": 0}
    gate()
    resultado = cola.procesar_pendientes(
        solver=solver_mantenimiento,
        notificador=notificador_mantenimiento,
        dormir=dormir,
        limite=limite,
    )
    return {"corrido": True, **resultado}


def contar_por_estado_mantenimiento(cola: ColaTareas) -> dict[str, int]:
    """`cola.contar_por_estado()` cuenta TODA `task_queue` -- la tabla es
    compartida con otros usos reales de cola_v2 (ej. la prueba con chat_id de
    QA). Aquí se filtra a lo que encoló esta ventana (`chat_id` fijo)."""
    filas = cola.con.execute(
        "SELECT estado, COUNT(*) n FROM task_queue WHERE chat_id = ? GROUP BY estado",
        (CHAT_ID_MANTENIMIENTO,)).fetchall()
    return {f["estado"]: f["n"] for f in filas}


def reporte_evidencia(cola: ColaTareas, *, limite: int = 20) -> list[dict]:
    """Evidencia legible de las últimas tareas de mantenimiento tocadas
    (resultado real del solver, tal como quedó en `task_queue`)."""
    filas = cola.con.execute(
        "SELECT id, descripcion, estado, resultado, resolved_at "
        "FROM task_queue WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (CHAT_ID_MANTENIMIENTO, limite)).fetchall()
    return [dict(f) for f in filas]


# --- CLI ----------------------------------------------------------------------
def _main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entorno", default=None, help="real (default) o simulacion")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("acumular")
    p_correr = sub.add_parser("correr")
    p_correr.add_argument("--forzar", action="store_true")
    p_correr.add_argument("--limite", type=int, default=None)
    sub.add_parser("estado")
    args = ap.parse_args()

    with ColaTareas(entorno=args.entorno) as cola:
        if args.cmd == "acumular":
            n = acumular(cola)
            print(f"encolados: {n}")
        elif args.cmd == "correr":
            r = correr(cola, forzar=args.forzar, limite=args.limite)
            print(json.dumps(r, ensure_ascii=False))
        elif args.cmd == "estado":
            print(json.dumps(contar_por_estado_mantenimiento(cola), ensure_ascii=False))
            for fila in reporte_evidencia(cola):
                print(json.dumps(fila, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
