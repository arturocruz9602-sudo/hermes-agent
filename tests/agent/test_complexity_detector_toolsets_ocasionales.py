"""Bloque AM (30 jul 2026) -- toolsets ocasionales solo cuando se piden.

Peso real en Telegram vs uso real de Arturo (1,125 llamadas en state.db):
    kanban          5,028 tok    24 usos  (2% de las llamadas, 33% del peso)
    session_search  1,796 tok     8 usos
    skills          1,401 tok    42 usos
    obsidian_note     473 tok     2 usos
Contra los esenciales que NUNCA se tocan: terminal 527 usos, file 362.

kanban NO se elimina: el HAS lo contempla como pieza central de Fase 5
("Notion = tablero de operacion, kanban espejo"). Se carga cuando el
mensaje lo pide, que es distinto de quitarlo.

Riesgo ASIMETRICO: gastar tokens de mas es molesto; dejar a Hermes sin la
herramienta que necesitaba le rompe la tarea a Arturo. Los disparadores
son generosos a proposito y ante duda se manda todo.
"""

from __future__ import annotations

import pytest

from agent.complexity_detector import select_toolsets_for_turn

_TS = {
    "kanban_show": "kanban", "kanban_create": "kanban",
    "session_search": "session_search",
    "skill_view": "skills", "skills_list": "skills",
    "obsidian_note": "obsidian_note",
    "terminal": "terminal", "read_file": "file", "memory": "memory",
    "text_to_speech": "tts", "web_search": "web",
}


@pytest.fixture(autouse=True)
def _fake_toolset_map(monkeypatch):
    import model_tools
    monkeypatch.setattr(model_tools, "get_toolset_for_tool", lambda n: _TS.get(n))


def _tools():
    return [{"type": "function", "function": {"name": n, "description": "x" * 200}}
            for n in _TS]


def _nombres(res):
    return {t["function"]["name"] for t in res}


@pytest.mark.parametrize("msg", [
    "muestrame el kanban",
    "que tareas tengo pendientes hoy",
    "agrega una tarea al tablero",
    "que hay en el board",
    "esos pendientes ya estan bloqueados?",
])
def test_kanban_se_carga_cuando_se_pide(msg):
    """Si falla, Arturo pide su tablero y Hermes no puede darselo."""
    res = select_toolsets_for_turn(msg, _tools())
    if res is None:
        return  # mandar todo tambien es correcto
    assert "kanban_show" in _nombres(res), f"kanban ausente para {msg!r}"


@pytest.mark.parametrize("msg,tool", [
    ("que dijimos ayer sobre el guion", "session_search"),
    ("busca en mi historial cuando hablamos del mac mini", "session_search"),
    ("guarda esta idea como nota", "obsidian_note"),
    ("que skills tienes instaladas", "skill_view"),
    ("que sabes hacer", "skill_view"),
])
def test_ocasionales_se_cargan_cuando_se_piden(msg, tool):
    res = select_toolsets_for_turn(msg, _tools())
    if res is None:
        return
    assert tool in _nombres(res), f"{tool} ausente para {msg!r}"


@pytest.mark.parametrize("msg", [
    "revisa el correo y dime que hay",
    "ponme una alarma para las 7",
    "resume estas fotos de la clase",
])
def test_mensaje_normal_recorta_los_ocasionales(msg):
    res = select_toolsets_for_turn(msg, _tools())
    assert res is not None, "deberia recortar en un mensaje que no los pide"
    n = _nombres(res)
    assert "kanban_show" not in n and "session_search" not in n


def test_esenciales_nunca_se_tocan():
    """terminal/file/memory/tts/web son el 95% del uso real: si alguno se
    cae, Hermes deja de poder hacer su trabajo diario."""
    res = select_toolsets_for_turn("revisa el correo", _tools())
    n = _nombres(res)
    for imprescindible in ("terminal", "read_file", "memory", "text_to_speech", "web_search"):
        assert imprescindible in n, f"se perdio {imprescindible}"


def test_mensaje_largo_manda_todo():
    """Tarea compleja (>60 palabras) = no arriesgarse a recortar.

    El umbral vive en select_toolsets_for_turn; aqui se fija el contrato:
    pasado ese largo, se mandan TODAS las herramientas aunque el texto no
    nombre ningun toolset ocasional.
    """
    largo = "necesito que " + "hagas muchas cosas distintas y variadas hoy " * 10
    assert len(largo.split()) > 60, "el caso de prueba debe superar el umbral real"
    assert select_toolsets_for_turn(largo, _tools()) is None


def test_entradas_vacias_no_revientan():
    assert select_toolsets_for_turn("", _tools()) is None
    assert select_toolsets_for_turn("hola", None) is None
