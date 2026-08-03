#!/usr/bin/env python3
"""orquestar.py -- Lanzador del loop autónomo de Hermes (Bloque AV, fases 3-5).

Recorre la cola completa del proyecto (loop_cola.COLA) respetando dependencias y,
por cada bloque, en una terminal que Arturo mira en vivo por SSH+tmux:

  1. GATE TÉRMICO (r.103): si la HP pasa 85°C, pausa hasta que baje.
  2. FRENO MANUAL: si existe scripts/.loop_alto, se detiene limpio tras el bloque.
  3. CLASIFICA -> modelo (Haiku, una sola llamada para toda la cola).
  4. CORRE el bloque con `claude -p --model <X>` en STREAMING visible.
  5. MIDE tokens/costo (evento `result` de stream-json) y lo escribe al ledger.
  6. MARCA el bloque hecho en estado persistente (para reanudar tras un corte).

DOS STACKS DE MODELOS (DECISIONES 01 ago, r.91): esto usa SOLO los 3 Claude de la
cuenta de Arturo (Haiku/Sonnet/Opus). La escalera gratis (Gemini/Groq/OpenRouter)
es de HERMES en runtime, no del loop.

PERMISOS (decisión de seguridad de Arturo): los bloques corren con
--permission-mode bypassPermissions para trabajar solos sin trabarse pidiendo
confirmación en cada paso. La RED DE SEGURIDAD es el hook PreToolUse
~/.claude/hooks/hermes-guard.sh (hard-deny de rm -rf, git push --force, DROP SQL,
curl|bash, instalaciones sin versión fija, escritura a credenciales...), que se
dispara SIEMPRE, sin importar el modo de permisos.

Uso:
  python3 scripts/orquestar.py plan        # solo el plan (no ejecuta nada)
  python3 scripts/orquestar.py probar       # prueba inocua del motor (no toca archivos)
  python3 scripts/orquestar.py correr       # corre el loop (respeta estado/freno/temp)
  python3 scripts/orquestar.py correr --max 1   # corre solo el próximo bloque
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import subprocess
import sys
import time

_DIR = pathlib.Path(__file__).resolve().parent
_REPO = _DIR.parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from loop_cola import COLA                       # noqa: E402
from loop_orquestador import clasificar_lote     # noqa: E402

# --- Configuración -----------------------------------------------------------
ESTADO_LOOP = _DIR / ".loop_estado.json"     # progreso persistente (reanudable)
LEDGER = _DIR / "loop_tokens.jsonl"          # gasto por bloque (una línea JSON c/u)
ALTO = _DIR / ".loop_alto"                   # `touch` este archivo para frenar limpio
TEMP_PATH = pathlib.Path("/sys/class/thermal/thermal_zone0/temp")
UMBRAL_TEMP_C = 85                           # r.103: pausa si sube de aquí
PAUSA_TERMICA_S = 30

# Modo de permisos de los bloques. Autonomía total, con hermes-guard como red.
MODO_PERMISOS = "bypassPermissions"

# Techo de vueltas por bloque (freno anti-runaway). Subido 02 ago por orden de
# Arturo: con 30 los bloques medios morían explorando+implementando antes de
# probar/commitear. Ahora alcanza para explorar + implementar + probar + commitear.
MAX_TURNS = {"trivial": 20, "medio": 60, "complejo": 100}


# --- Utilidades de salud/estado ---------------------------------------------
def temp_hp() -> int | None:
    try:
        return int(TEMP_PATH.read_text().strip()) // 1000
    except Exception:
        return None


def gate_termico() -> None:
    while True:
        t = temp_hp()
        if t is None or t < UMBRAL_TEMP_C:
            return
        print(f"  🌡️  HP a {t}°C ≥ {UMBRAL_TEMP_C}°C — pauso {PAUSA_TERMICA_S}s (r.103)...")
        time.sleep(PAUSA_TERMICA_S)


def cargar_estado() -> dict:
    if ESTADO_LOOP.exists():
        try:
            return json.loads(ESTADO_LOOP.read_text())
        except Exception:
            pass
    return {"hechos": []}


def guardar_estado(estado: dict) -> None:
    ESTADO_LOOP.write_text(json.dumps(estado, ensure_ascii=False, indent=2))


def siguiente_bloque(hechos: list, bloqueados: list | None = None) -> dict | None:
    """Primer bloque pendiente (ni hecho ni bloqueado) cuyas dependencias ya
    están todas HECHAS. Un bloque cuya dependencia quedó bloqueada nunca se
    vuelve elegible — el loop simplemente lo salta y termina cuando no hay más."""
    bloqueados = bloqueados or []
    saltar = set(hechos) | set(bloqueados)
    hechos_set = set(hechos)
    for b in COLA:
        if b["id"] in saltar:
            continue
        if all(dep in hechos_set for dep in b.get("depende_de", [])):
            return b
    return None


# --- El prompt de trabajo de un bloque --------------------------------------
def prompt_bloque(bloque: dict) -> str:
    refs = ", ".join(bloque.get("cuestionario", [])) or "(ninguna específica)"
    guia = bloque.get("guia")
    prompt = f"""Eres una sesión del loop autónomo de Hermes trabajando UN SOLO bloque.
Ya leíste CLAUDE.md, MANDATO y ESTADO al arrancar (hook). Respétalos al pie.

BLOQUE {bloque['id']}: {bloque['titulo']}
Descripción: {bloque['descripcion']}
Ancla en el HAS: {bloque.get('has', '-')}
Respuestas del cuestionario que lo gobiernan: {refs}

Reglas de este bloque:
- Cualquier duda de ALCANCE se resuelve con docs/CUESTIONARIO_MAESTRO.md; donde un
  doc viejo lo contradiga, gana el cuestionario. Consulta docs/DECISIONES.md antes
  de tocar arquitectura.
- Regla de simulación (r.20): nada real fuera del laboratorio Docker; en producción,
  captura espontánea = preguntar antes de crear.
- B10: la escritura ocurre en esta sesión; los subagentes son solo de lectura.
- Si necesitas una decisión de Arturo que NO está en los documentos, NO la inventes:
  déjala anotada en ESTADO.md como pendiente y avanza con lo que SÍ puedas cerrar.
- COMMIT INCREMENTAL (importante): haz `git commit` de avance WIP DESPUÉS DE CADA PASO
  con sentido — cada archivo que escribas, cada prueba que pase. NO lo dejes para el
  final. Si te quedas sin vueltas, lo ya commiteado se conserva y el loop reanuda desde
  ahí. Entregable mínimo: trabajo hecho + pruebas con evidencia. No declares cerrado lo
  que no probaste (regla 2).
- CONSULTA INTERNET AL FALLAR (orden de Arturo, 02 ago): si algo te falla, te atascas o
  un error no es obvio (bug, API que no responde como esperas, comportamiento raro de una
  herramienta), NO reintentes a ciegas ni te rindas: busca en internet la solución —
  foros (Stack Overflow, GitHub Issues), documentación oficial y páginas especializadas —
  copiando el mensaje de error EXACTO en la búsqueda. PRIORIZA fuentes con fechas
  recientes/actuales (últimos ~6 meses) sobre las antiguas: las APIs y herramientas
  cambian rápido y una respuesta vieja puede estar obsoleta. Aplica esta regla en el
  intento 1 y también en el reintento (intento 2): antes de fallar dos veces, investiga
  en la web y ataca la causa real.

Al terminar, resume en máximo 5 líneas: qué hiciste, qué probaste (con números), y
qué queda pendiente."""
    if guia:
        prompt += (
            "\n\nGUÍA DE REUSO (verificada por Hermes el 02 ago; úsala, no la re-explores):\n"
            + guia
        )
    if bloque.get("entorno") == "docker_qa":
        prompt += (
            "\n\n⚠ CANDADO DE SEGURIDAD (r.119, GANA sobre cualquier otra instrucción): este "
            "bloque es docker_qa, PERO esta sesión corre en el HOST con credenciales de "
            "PRODUCCIÓN y NO hay canal QA de Telegram configurado en ~/.hermes/.env (solo el "
            "real TELEGRAM_HOME_CHANNEL). Por lo tanto: NO envíes NINGÚN tráfico de prueba a "
            "Telegram ni a ningún canal/servicio real. Genera y VERIFICA LOCAL (que el .ogg "
            "exista y sea Opus válido); deja el envío en vivo (sendVoice) como PENDIENTE "
            "documentado en ESTADO.md hasta que exista un canal QA. Cierra el bloque cableando "
            "el código + commit WIP; eso cuenta como entregable."
        )
    return prompt


# --- Ejecutar un bloque en streaming visible --------------------------------
def _resumen_tool(name: str, inp: dict) -> str:
    for k in ("command", "file_path", "pattern", "path", "url", "prompt"):
        if isinstance(inp, dict) and inp.get(k):
            return f"{name}: {str(inp[k])[:80]}"
    return name


def correr_bloque(prompt: str, modelo: str, max_turns: int,
                  permisos: str = MODO_PERMISOS) -> dict:
    """Corre `claude -p` en streaming, imprime el trabajo en vivo y devuelve el
    gasto medido del evento `result`. Nunca lanza."""
    cmd = [
        "claude", "-p", prompt,
        "--model", modelo,
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", permisos,
        "--max-turns", str(max_turns),
    ]
    res = {"usage": {}, "cost": None, "num_turns": None, "is_error": None,
           "final": "", "rc": None}
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
    except Exception as e:
        print(f"  ✖ no se pudo lanzar claude: {e}")
        return res

    for ln in proc.stdout:  # type: ignore[union-attr]
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except Exception:
            continue
        t = o.get("type")
        if t == "assistant":
            for c in (o.get("message", {}).get("content") or []):
                if c.get("type") == "text" and c.get("text", "").strip():
                    print("  " + c["text"].strip())
                elif c.get("type") == "tool_use":
                    print(f"  🔧 {_resumen_tool(c.get('name', '?'), c.get('input', {}))}")
        elif t == "rate_limit_event":
            print("  ⏳ límite de tasa — la sesión espera...")
        elif t == "result":
            res["usage"] = o.get("usage", {}) or {}
            res["cost"] = o.get("total_cost_usd")
            res["num_turns"] = o.get("num_turns")
            res["is_error"] = o.get("is_error", False)
            res["final"] = o.get("result", "")
    proc.wait()
    res["rc"] = proc.returncode
    return res


def registrar(bloque: dict, clasif, res: dict, intento: int = 1) -> None:
    u = res.get("usage", {}) or {}
    fila = {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "bloque": bloque["id"],
        "intento": intento,
        "dificultad": clasif.dificultad,
        "modelo": clasif.modelo,
        "input_tokens": u.get("input_tokens"),
        "output_tokens": u.get("output_tokens"),
        "cache_read": u.get("cache_read_input_tokens"),
        "cache_creation": u.get("cache_creation_input_tokens"),
        "cost_usd": res.get("cost"),
        "num_turns": res.get("num_turns"),
        "is_error": res.get("is_error"),
        "rc": res.get("rc"),
    }
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    print(f"  💰 tokens in/out: {fila['input_tokens']}/{fila['output_tokens']}  ·  "
          f"cache_read {fila['cache_read']}  ·  costo ${fila['cost_usd']}  ·  "
          f"{fila['num_turns']} vueltas")


# --- Bucle principal ---------------------------------------------------------
def _fallo(res: dict) -> bool:
    return bool(res.get("is_error")) or res.get("rc") not in (0, None)


def correr(max_bloques: int | None) -> None:
    clasifs = clasificar_lote(COLA)
    estado = cargar_estado()
    hechos = estado.setdefault("hechos", [])
    bloqueados = estado.setdefault("bloqueados", [])
    corridos = 0
    costo_total = 0.0

    while True:
        if max_bloques is not None and corridos >= max_bloques:
            print(f"\n■ Alcancé el máximo de {max_bloques} bloque(s) de esta corrida.")
            break
        if ALTO.exists():
            print("\n■ Freno manual (.loop_alto) — me detengo limpio. Borra el archivo para seguir.")
            break
        bloque = siguiente_bloque(hechos, bloqueados)
        if bloque is None:
            print("\n✔ No quedan bloques con dependencias listas. Loop al día.")
            break

        clasif = clasifs[bloque["id"]]
        # Orden de Arturo (02 ago): un bloque que falla NO detiene el loop. Se
        # reintenta UNA vez con el techo de vueltas nuevo; si vuelve a fallar se
        # marca BLOQUEADO y se sigue con el siguiente. El avance WIP se conserva
        # porque cada bloque commitea incrementalmente.
        exito = False
        for intento in (1, 2):
            gate_termico()
            print(f"\n{'='*90}")
            print(f"▶ BLOQUE {bloque['id']} · {bloque['titulo']}  (intento {intento}/2)")
            print(f"  dificultad={clasif.dificultad} → modelo={clasif.modelo} · "
                  f"HAS {bloque.get('has','-')} · temp {temp_hp()}°C · "
                  f"máx {MAX_TURNS.get(clasif.dificultad, 60)} vueltas")
            print(f"{'='*90}")

            res = correr_bloque(prompt_bloque(bloque), clasif.modelo,
                                MAX_TURNS.get(clasif.dificultad, 60))
            registrar(bloque, clasif, res, intento)
            if res.get("cost"):
                costo_total += res["cost"]

            if not _fallo(res):
                exito = True
                break
            if intento == 1:
                print(f"  ✖ intento 1 de {bloque['id']} falló (agotó vueltas o error) — "
                      "reintento UNA vez con el techo nuevo (orden de Arturo).")
                time.sleep(2)

        if exito:
            hechos.append(bloque["id"])
            print(f"  ✔ {bloque['id']} marcado HECHO.")
        else:
            bloqueados.append(bloque["id"])
            print(f"  ✖✖ {bloque['id']} falló 2 veces — lo marco BLOQUEADO y SIGO con el "
                  "siguiente (el loop no se detiene, orden de Arturo). Su avance WIP quedó "
                  "commiteado; revisar después.")
        guardar_estado(estado)
        corridos += 1
        time.sleep(2)

    print(f"\n{'─'*90}")
    print(f"Resumen: {corridos} bloque(s) procesados · hechos={len(hechos)} · "
          f"bloqueados={len(bloqueados)} · costo acumulado ${costo_total:.4f}")
    if bloqueados:
        print(f"  ⚠ bloqueados (revisar): {', '.join(bloqueados)}")
    print(f"  ledger: {LEDGER}")


def probar() -> None:
    """Prueba INOCUA del motor: una llamada a Haiku que no toca archivos, para
    verificar el streaming visible y la captura de tokens de punta a punta."""
    print("Prueba inocua del motor (no toca archivos, no usa herramientas):\n")
    prompt = ("Sin usar NINGUNA herramienta y sin tocar archivos, responde en 3 "
              "líneas cómo abordarías el bloque 'AS-2: cierre nocturno en audio'.")
    res = correr_bloque(prompt, "haiku", max_turns=1, permisos="acceptEdits")
    print()
    from loop_orquestador import Clasificacion
    registrar({"id": "PRUEBA"}, Clasificacion("trivial", "haiku", "prueba", False), res)


def main() -> int:
    ap = argparse.ArgumentParser(description="Loop autónomo de Hermes")
    ap.add_argument("modo", choices=["plan", "probar", "correr"], help="qué hacer")
    ap.add_argument("--max", type=int, default=None, help="máx bloques a correr")
    args = ap.parse_args()

    if args.modo == "plan":
        from loop_orquestador import planificar
        planificar()
    elif args.modo == "probar":
        probar()
    elif args.modo == "correr":
        correr(args.max)
    return 0


if __name__ == "__main__":
    sys.exit(main())
