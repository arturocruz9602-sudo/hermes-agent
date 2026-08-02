#!/usr/bin/env python3
"""loop_orquestador.py -- Orquestador del loop autónomo de Hermes (Bloque AV).

Modo A (confirmado por Arturo 02 ago 2026): el loop procesa una cola de bloques
del proyecto en sesiones VISIBLES de tmux, una ventana por bloque, que Arturo
mira en vivo por SSH desde su MacBook.

DOS STACKS DE MODELOS, NUNCA SE MEZCLAN (DECISIONES 01 ago, r.91):
  - HERMES (runtime, el día a día de Arturo): DeepSeek comanda; la escalera
    gratis (Gemini/Groq/OpenRouter) solo absorbe lo repetitivo. NO se toca aquí.
  - EL LOOP (esto: Claude Code construyendo Hermes): los TRES modelos de Claude
    de la cuenta de Arturo, ruteados por dificultad de la tarea de construcción:
        trivial  -> Haiku 4.5   (mecánico, sin juicio)
        medio    -> Sonnet      (cambio acotado bien especificado)
        complejo -> Opus 4.8    (arquitectura, causa raíz, riesgo, dinero)

CORRECCIÓN 02 ago (Arturo): una versión previa de este archivo clasificaba la
dificultad con Gemini (`_call_cheap_model_json`), arrastrando la decisión del
30 jul que era para el ruteo de HERMES, no para este loop. Teniendo la cuenta de
Claude, el cerebro del loop se queda en Claude: la dificultad la decide HAIKU
(el Claude más barato) vía el CLI `claude -p`. Además la batería probó que Gemini
gratis da HTTP 429 a la 3ª llamada y mandaba TODO a Opus (lo más caro) -- lo
contrario de ahorrar.

Restricciones firmes que este módulo respeta (docs/DECISIONES.md):
  - 22 jul: la dificultad se decide por RÚBRICA evaluada por un modelo que
    devuelve JSON, nunca por una lista de `if` de palabras clave en Python.
  - B10: sin subagentes-que-escriben; el orquestador lanza sesiones `claude`
    completas por bloque (cada una es una sesión real, no un subagente).
  - Cualquier duda de QUÉ construir se resuelve con el CUESTIONARIO_MAESTRO
    (cada bloque de la cola trae sus referencias r.NN).
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass

_log = logging.getLogger("loop_orquestador")

# --- Mapa dificultad -> modelo de Claude Code -------------------------------
# Tres niveles. Alias que el CLI `claude --model` acepta (verificado 02 ago:
# `claude -p ... --model haiku` responde JSON limpio). Un solo lugar para
# cambiarlos.
MODELO_POR_DIFICULTAD = {
    "trivial": "haiku",    # mecánico y sin juicio: correr un comando, un reporte
    "medio": "sonnet",     # cambio acotado bien especificado, 1-2 archivos, docs
    "complejo": "opus",    # arquitectura, causa raíz, multi-archivo, riesgo, dinero
}
NIVELES = tuple(MODELO_POR_DIFICULTAD)  # ("trivial", "medio", "complejo")

# El clasificador (decidir qué tan difícil es un bloque) corre en el Claude más
# barato: Haiku. Es una decisión de una sola llamada, no vale gastar Sonnet/Opus.
MODELO_CLASIFICADOR = "haiku"

# Fail-safe cuando la clasificación no se puede obtener (CLI falla, JSON roto).
# Se elige COMPLEJO->Opus a propósito: en un loop AUTÓNOMO no supervisado, correr
# una tarea compleja con un modelo insuficiente produce trabajo malo difícil de
# detectar; gastar de más en una tarea simple es visible y acotado. El fallback
# SIEMPRE se loguea fuerte (regla 3 / HAS §F9-L6: el silencio no es fallo válido).
DIFICULTAD_FALLBACK = "complejo"


@dataclass
class Clasificacion:
    dificultad: str      # "trivial" | "medio" | "complejo"
    modelo: str          # haiku | sonnet | opus
    razon: str           # explicación corta del modelo (o del fallback)
    es_fallback: bool    # True si se cayó al default por fallo de clasificación


# Criterios compartidos por el clasificador de un bloque y el de lote (no duplicar).
_CRITERIOS = """Hay TRES niveles de dificultad para un BLOQUE de trabajo de ingeniería:

dificultad="trivial" cuando el bloque es puramente MECÁNICO, sin juicio ni riesgo,
y el "cómo" es un solo paso obvio:
  - correr una suite/comando/script que ya existe y reportar el resultado
  - una búsqueda simple, un reporte de estado, listar o contar algo
  - formatear, ordenar imports, un renombrado local sin cambio de comportamiento

dificultad="medio" cuando es ACOTADO pero pide algo de trabajo o cuidado:
  - aplicar un cambio bien especificado en 1-2 archivos
  - actualizar documentación siguiendo un formato existente
  - generar un archivo a partir de una plantilla o de datos ya dados
  - un ajuste con un poco de lógica pero sin decisiones de arquitectura

dificultad="complejo" cuando el bloque exige JUICIO o toca mucho:
  - diseño de arquitectura o decisiones con trade-offs
  - depurar un bug hasta su causa raíz
  - refactor que cruza varios módulos/archivos
  - algo con supuestos sin verificar o que puede romper producción
  - cualquier cosa de seguridad, migraciones de esquema, o dinero real

Ante la duda entre dos niveles, elige SIEMPRE el más alto (trivial<medio<complejo)."""


_RUBRICA_DIFICULTAD = """Eres el enrutador de un loop autónomo de programación.
""" + _CRITERIOS + """
Responde SOLO con JSON válido, sin texto extra, sin markdown, con esta forma exacta:
{{"dificultad": "trivial", "razon": "<una frase>"}}

Título del bloque: {titulo}
Descripción del bloque: {descripcion}"""


_RUBRICA_LOTE = """Eres el enrutador de un loop autónomo de programación. Vas a
clasificar VARIOS bloques de una sola vez.
""" + _CRITERIOS + """
Responde SOLO con un ARRAY JSON válido, sin texto extra, sin markdown: un objeto
por bloque, con esta forma exacta y usando el id EXACTO que se te da:
[{{"id": "<id>", "dificultad": "trivial|medio|complejo", "razon": "<una frase>"}}]

BLOQUES A CLASIFICAR:
{bloques}"""


def _claude_texto(prompt: str, modelo: str, *, timeout: int = 180) -> str | None:
    """Corre `claude -p` headless con el modelo dado y devuelve su stdout crudo,
    o None ante cualquier fallo (nunca lanza).

    Se usa para el clasificador (Haiku). NO llama a ningún modelo de pago de
    Hermes: usa la cuenta de Claude de Arturo, que es justo el stack del loop.
    """
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", modelo],
            capture_output=True, text=True, timeout=timeout,
        )
    except Exception:
        _log.warning("no se pudo ejecutar `claude -p --model %s`", modelo, exc_info=True)
        return None
    if proc.returncode != 0:
        _log.warning(
            "`claude -p --model %s` salió con código %s: %s",
            modelo, proc.returncode, (proc.stderr or "").strip()[:300],
        )
        return None
    return proc.stdout or ""


def _extraer_json(raw: str, tipo: type):
    """Extrae un objeto ({}) o arreglo ([]) JSON de la salida cruda del modelo,
    tolerando cercas ```json y prosa alrededor. Devuelve None si no hay uno del
    `tipo` pedido (dict o list)."""
    if raw is None:
        return None
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s).strip()
    try:
        parsed = json.loads(s)
        if isinstance(parsed, tipo):
            return parsed
    except Exception:
        pass
    abre, cierra = ("[", "]") if tipo is list else ("{", "}")
    ini, fin = s.find(abre), s.rfind(cierra)
    if ini != -1 and fin > ini:
        try:
            parsed = json.loads(s[ini:fin + 1])
            if isinstance(parsed, tipo):
                return parsed
        except Exception:
            pass
    _log.warning("no se pudo extraer JSON %s de: %r", tipo.__name__, s[:200])
    return None


def _claude_json(prompt: str, modelo: str, *, timeout: int = 90) -> dict | None:
    """Igual, pero devuelve el dict JSON de la respuesta (clasificación de UN bloque)."""
    return _extraer_json(_claude_texto(prompt, modelo, timeout=timeout), dict)


def clasificar_dificultad(titulo: str, descripcion: str = "") -> Clasificacion:
    """Clasifica un bloque de trabajo como trivial/medio/complejo vía rúbrica
    evaluada por Haiku, y lo mapea al modelo de Claude Code. Nunca lanza: ante
    cualquier fallo cae al fallback (COMPLEJO->Opus) y lo marca/loguea.
    """
    prompt = _RUBRICA_DIFICULTAD.format(
        titulo=(titulo or "").strip(),
        descripcion=(descripcion or "").strip() or "(sin descripción)",
    )
    parsed = _claude_json(prompt, MODELO_CLASIFICADOR)

    if parsed is None:
        _log.warning(
            "clasificación de dificultad FALLÓ para %r -- fallback a %s (%s). "
            "Revisar el CLI de Claude: un fallback silencioso rutea mal todo el loop.",
            titulo, DIFICULTAD_FALLBACK, _modelo_de(DIFICULTAD_FALLBACK),
        )
        return Clasificacion(
            dificultad=DIFICULTAD_FALLBACK,
            modelo=_modelo_de(DIFICULTAD_FALLBACK),
            razon="fallback: la clasificación no devolvió JSON usable",
            es_fallback=True,
        )

    dificultad = str(parsed.get("dificultad", "")).strip().lower()
    if dificultad not in NIVELES:
        _log.warning(
            "dificultad inesperada %r del modelo para %r -- fallback a %s",
            dificultad, titulo, DIFICULTAD_FALLBACK,
        )
        return Clasificacion(
            dificultad=DIFICULTAD_FALLBACK,
            modelo=_modelo_de(DIFICULTAD_FALLBACK),
            razon=f"fallback: dificultad no reconocida ({dificultad!r})",
            es_fallback=True,
        )

    razon = str(parsed.get("razon", "")).strip() or "(sin razón)"
    return Clasificacion(
        dificultad=dificultad,
        modelo=_modelo_de(dificultad),
        razon=razon,
        es_fallback=False,
    )


def _modelo_de(dificultad: str) -> str:
    # Cualquier valor no reconocido cae al modelo del fallback (Opus), coherente
    # con DIFICULTAD_FALLBACK: nunca sub-dimensionar un bloque sin querer.
    return MODELO_POR_DIFICULTAD.get(dificultad, MODELO_POR_DIFICULTAD[DIFICULTAD_FALLBACK])


def _clasif_fallback(razon: str) -> Clasificacion:
    return Clasificacion(
        dificultad=DIFICULTAD_FALLBACK, modelo=_modelo_de(DIFICULTAD_FALLBACK),
        razon=razon, es_fallback=True,
    )


def clasificar_lote(bloques: list) -> dict:
    """Clasifica MUCHOS bloques en UNA sola llamada a Haiku (una sesión, no una
    por bloque). Es lo que usa el planificador para no gastar 20 arranques de
    `claude`. Devuelve {id: Clasificacion}. Cualquier bloque que el modelo no
    devuelva o devuelva mal cae al fallback (COMPLEJO->Opus), logueado.
    """
    lineas = []
    for b in bloques:
        desc = (b.get("descripcion", "") or "").strip().replace("\n", " ")
        lineas.append(f'- id="{b["id"]}" | título: {b["titulo"]} | descripción: {desc}')
    prompt = _RUBRICA_LOTE.format(bloques="\n".join(lineas))

    # Un solo bloque de trabajo grande: damos más tiempo que una clasificación suelta.
    arr = _extraer_json(_claude_texto(prompt, MODELO_CLASIFICADOR, timeout=300), list)

    por_id: dict = {}
    if arr:
        for item in arr:
            if isinstance(item, dict) and item.get("id"):
                por_id[str(item["id"])] = item

    resultado: dict = {}
    for b in bloques:
        item = por_id.get(b["id"])
        if item is None:
            _log.warning("el lote no devolvió el bloque %r -- fallback a %s",
                         b["id"], DIFICULTAD_FALLBACK)
            resultado[b["id"]] = _clasif_fallback("fallback: el lote no clasificó este bloque")
            continue
        dif = str(item.get("dificultad", "")).strip().lower()
        if dif not in NIVELES:
            _log.warning("dificultad inesperada %r para %r -- fallback", dif, b["id"])
            resultado[b["id"]] = _clasif_fallback(f"fallback: dificultad no reconocida ({dif!r})")
            continue
        razon = str(item.get("razon", "")).strip() or "(sin razón)"
        resultado[b["id"]] = Clasificacion(dif, _modelo_de(dif), razon, es_fallback=False)
    return resultado


# --- Planificación de la cola ------------------------------------------------
def planificar(imprimir: bool = True) -> list:
    """Clasifica TODA la cola de bloques y devuelve el plan (bloque -> modelo).
    Es lo que Arturo ve primero: qué va a correr, con qué modelo, y por qué,
    ANTES de que el loop toque nada. Importa la cola aquí para no acoplar el
    módulo si aún no existe.
    """
    from loop_cola import COLA  # mismo directorio

    clasifs = clasificar_lote(COLA)  # UNA sola llamada a Haiku para toda la cola

    plan = []
    if imprimir:
        print(f"{'#':>2}  {'bloque':34} {'dific.':9} {'modelo':7} {'HAS':22} depende")
        print("-" * 100)
    conteo = {"trivial": 0, "medio": 0, "complejo": 0}
    for i, bloque in enumerate(COLA, 1):
        c = clasifs[bloque["id"]]
        plan.append((bloque, c))
        conteo[c.dificultad] = conteo.get(c.dificultad, 0) + 1
        if imprimir:
            has = (bloque.get("has", "") or "-")[:22]
            dep = ", ".join(bloque.get("depende_de", [])) or "-"
            marca = " ⚠fb" if c.es_fallback else ""
            etiqueta = f"{bloque['id']} {bloque['titulo']}"[:34]
            print(f"{i:>2}  {etiqueta:34} {c.dificultad:9} {c.modelo:7} {has:22} {dep}{marca}")
            if c.es_fallback:
                print(f"     └─ {c.razon}")
    if imprimir:
        print("-" * 100)
        print(f"total: {len(COLA)} bloques  ·  "
              f"trivial→haiku: {conteo['trivial']}  ·  "
              f"medio→sonnet: {conteo['medio']}  ·  "
              f"complejo→opus: {conteo['complejo']}")
    return plan


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "plan":
        planificar()
    else:
        # Uso manual rápido:  python3 scripts/loop_orquestador.py "título" "descripción"
        titulo = sys.argv[1] if len(sys.argv) > 1 else "correr la suite de tests y reportar"
        descripcion = sys.argv[2] if len(sys.argv) > 2 else ""
        c = clasificar_dificultad(titulo, descripcion)
        print(f"dificultad={c.dificultad}  modelo={c.modelo}  fallback={c.es_fallback}")
        print(f"razón: {c.razon}")
