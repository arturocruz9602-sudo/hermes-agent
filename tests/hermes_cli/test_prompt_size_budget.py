"""Bloque P2 -- presupuesto de contexto como regresion del arnes.

Ancla: docs/DECISIONES.md "01 ago - Presupuesto de contexto como prueba
permanente del arnes". Techo de tokens de prompt por bloque: si un
bloque vuelve a viajar a su tamano crudo, esta suite debe reportarlo en
rojo, igual que un bug funcional -- no es optimizacion opcional.

Motivo real (no hipotetico), encontrado y corregido en esta misma
sesion: el 30 jul se midio MEMORY.md completo viajando en cada vuelta
(102,597 chars = ~25,650 tokens) y se agrego `_memoria_como_indice`
(Bloque AK), extendida despues a USER.md (Bloque AL, commit dcfc55dd9,
formato "§" separado por entradas). Pero el call site real en
`agent/system_prompt.py` (linea ~566) nunca quedo conectado a esa
funcion para USER.md -- el bloque prometia el ahorro (5,480 -> 2,387
tokens) y nunca se aplico. Corregido en esta sesion (ver
`agent/system_prompt.py`); estas pruebas miden el prompt REAL de punta
a punta (`build_system_prompt`, la misma funcion que arma cada vuelta
en produccion) para que esa regresion exacta -- o cualquier otra que
deje de aplicar el indice -- se note aqui, no en la cuota de Gemini.

No se fija un techo sobre el `system_prompt` de produccion (19.1k
tokens/vuelta, medido en Telegram): los toolsets reales se recortan en
`config.yaml`, fuera de este repo (Bloque AL punto 2), y el perfil
"cli" que arma `_build_inspection_agent` trae otro juego de
herramientas. El techo de abajo es relativo a ESTA fixture (memoria y
perfil a escala real, sin depender de que config.yaml exista) -- sirve
para detectar que el indice de memoria/perfil se rompio, no para
replicar el numero exacto de produccion.
"""

from __future__ import annotations

import pytest

from agent.system_prompt import build_system_prompt
from hermes_cli.prompt_size import _build_inspection_agent, compute_prompt_breakdown

# Con el indice funcionando (medido en esta sesion, ver commit del fix):
#   full system prompt ~24,245 chars (~6,061 tokens) con esta fixture.
# Si el call site de USER.md deja de indexar (la regresion real que se
# encontro y corrigio aqui), sube a ~38,537 chars (~9,634 tokens).
# Techo con margen holgado sobre el numero sano, muy por debajo del roto:
_TECHO_PROMPT_TOTAL_TOKENS = 7_500
_TECHO_MEMORIA_TOKENS = 1_200  # baseline real documentado: 848 tokens
_TECHO_PERFIL_TOKENS = 3_200  # baseline real documentado: 2,387 tokens
_MUESTRAS = 3  # "una llamada no es una medicion" -- leccion del 30 jul


def _seed_memory_a_escala_real(hermes_home):
    """MEMORY.md >12,000 chars con encabezados '##' (dispara el indice)."""
    mem_dir = hermes_home / "memories"
    mem_dir.mkdir(parents=True, exist_ok=True)
    partes = ["Memoria persistente de Hermes.\n"]
    i = 0
    while sum(len(p) for p in partes) < 102_000:
        partes.append(
            f"## SECCION {i} -- HARDWARE Y CONFIGURACION\n"
            + ("dato relevante de Arturo repetido varias veces. " * 45)
        )
        i += 1
    memory_text = "\n".join(partes)
    (mem_dir / "MEMORY.md").write_text(memory_text, encoding="utf-8")
    return memory_text


def _seed_user_a_escala_real(hermes_home):
    """USER.md >12,000 chars, 81 entradas separadas por '§' (formato real
    de memory_tool.py), cada una larga como una entrada de perfil real --
    no una frase corta, para que la truncacion a 110 chars del indice
    produzca una reduccion medible (si las entradas ya son cortas, el
    indice y el crudo casi coinciden y la prueba no detecta nada)."""
    mem_dir = hermes_home / "memories"
    mem_dir.mkdir(parents=True, exist_ok=True)
    relleno = (
        "dato de perfil de Arturo, contexto relevante sobre su vida diaria y "
        "preferencias personales, rutina semanal completa, horarios de trabajo "
        "en la taqueria y de la escuela, metas financieras del riel de ahorro, "
        "y decisiones recientes que Hermes debe recordar siempre -- entrada "
        "de ejemplo numero "
    )
    entradas = [relleno + str(i) for i in range(81)]
    user_text = "§".join(entradas)
    (mem_dir / "USER.md").write_text(user_text, encoding="utf-8")
    return user_text


@pytest.fixture
def isolated_home_escala_real(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.chdir(tmp_path)
    memory_text = _seed_memory_a_escala_real(hermes_home)
    user_text = _seed_user_a_escala_real(hermes_home)
    return hermes_home, memory_text, user_text


def _prompt_real_de_punta_a_punta() -> str:
    """El mismo camino que produccion: arma un agente offline y construye
    el system prompt completo via `agent.system_prompt.build_system_prompt`
    -- no una recomputacion aparte que pueda desincronizarse del call site
    real (eso fue exactamente lo que ocultaba la regresion de USER.md)."""
    agent = _build_inspection_agent("cli")
    return build_system_prompt(agent)


def test_prompt_completo_no_regresa_al_tamano_crudo(isolated_home_escala_real):
    """Guarda de punta a punta: si `agent/system_prompt.py` deja de aplicar
    `_memoria_como_indice` a memoria o a USER.md (la regresion real
    encontrada y corregida en este bloque), el prompt completo casi se
    duplica -- este techo debe ponerse rojo antes de que llegue a Telegram."""
    full = _prompt_real_de_punta_a_punta()
    tokens = len(full) // 4
    assert tokens <= _TECHO_PROMPT_TOTAL_TOKENS, (
        f"prompt completo: ~{tokens} tokens con memoria/perfil a escala real, "
        f"techo {_TECHO_PROMPT_TOTAL_TOKENS} -- revisa si algun bloque dejo de indexarse"
    )


def test_memoria_indexada_no_regresa_al_tamano_crudo(isolated_home_escala_real):
    _, memory_text, _ = isolated_home_escala_real
    data = compute_prompt_breakdown("cli")
    memoria_chars = data["memory"]["chars"]
    assert memoria_chars < len(memory_text) / 5, (
        "el bloque de memoria no se esta indexando -- viaja casi crudo"
    )
    assert memoria_chars // 4 <= _TECHO_MEMORIA_TOKENS, (
        f"memoria en el prompt: ~{memoria_chars // 4} tokens, techo {_TECHO_MEMORIA_TOKENS}"
    )


def test_perfil_usuario_indexado_no_regresa_al_tamano_crudo(isolated_home_escala_real):
    """Regresion real corregida en este bloque: USER.md no pasaba por
    `_memoria_como_indice` en el call site de `agent/system_prompt.py`,
    pese a que Bloque AL (dcfc55dd9) prometia esa reduccion."""
    _, _, user_text = isolated_home_escala_real
    data = compute_prompt_breakdown("cli")
    perfil_chars = data["user_profile"]["chars"]
    assert perfil_chars < len(user_text) / 2, (
        "USER.md viaja casi sin indexar -- misma regresion que Bloque AL prometio cerrar"
    )
    assert perfil_chars // 4 <= _TECHO_PERFIL_TOKENS, (
        f"perfil de usuario en el prompt: ~{perfil_chars // 4} tokens, techo {_TECHO_PERFIL_TOKENS}"
    )


def test_presupuesto_estable_en_tres_muestras(isolated_home_escala_real):
    """>=3 muestras por corrida (regla del bloque P2): una sola llamada no
    es una medicion confiable -- se exige consistencia entre corridas,
    midiendo el prompt real de punta a punta cada vez."""
    muestras_tokens = [len(_prompt_real_de_punta_a_punta()) // 4 for _ in range(_MUESTRAS)]

    assert len(muestras_tokens) >= _MUESTRAS
    assert max(muestras_tokens) <= _TECHO_PROMPT_TOTAL_TOKENS, muestras_tokens
    # Sin fuentes de aleatoriedad reales en este calculo: las muestras deben
    # coincidir. Si no coinciden, algo no determinista se coló en el prompt
    # (p. ej. un timestamp con precision de segundo en vez de dia).
    assert len(set(muestras_tokens)) == 1, "medicion del prompt inestable entre muestras"
