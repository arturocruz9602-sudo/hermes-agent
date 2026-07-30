"""Bloque AI (30 jul 2026) -- recorte de herramientas en turnos triviales.

Medicion real que lo motiva (cuenta de Arturo, Telegram): "Hola Hermes"
con respuesta de voz costo 219,930 tokens = 88% del limite por minuto de
la cuota gratuita, repartido en 3 iteraciones de ~70k. De cada iteracion,
~20,150 tokens son las 44 definiciones de herramientas -- remandadas
integras en cada vuelta. El costo no se paga por mensaje: por ITERACION.

El riesgo de este recorte NO es simetrico: gastar tokens de mas es
molesto, pero quitarle a Hermes una herramienta que si necesitaba le
rompe la tarea a Arturo. Por eso todo aqui se inclina a NO recortar.
"""

from __future__ import annotations

import pytest

from agent.complexity_detector import is_trivial_turn, select_tools_for_turn

TRIVIALES = [
    "Hola Hermes", "hola", "buenos dias", "Buenas noches", "gracias",
    "ok", "Hermes", "listo", "perfecto", "que tal", "sale", "entendido",
]

# Mensajes que EMPIEZAN como saludo pero traen una peticion real: el caso
# peligroso. Si alguno recortara, Arturo se queda sin la herramienta.
CON_PETICION = [
    "hola, y de paso mandame el reporte de ayer",
    "buenos dias, ponme una alarma para las 7",
    "hermes revisa el correo",
    "que tal quedo el guion?",
    "gracias, ahora busca el precio del bitcoin",
    "hola necesito ayuda con la tarea de la escuela",
    "te voy a mandar 45 fotos de la boda",
    "ok, entonces crea la nota en obsidian",
    "listo, ahora ejecuta las pruebas",
]


@pytest.mark.parametrize("msg", TRIVIALES)
def test_saludo_puro_es_trivial(msg):
    assert is_trivial_turn(msg) is True, f"no lo detecto trivial: {msg!r}"


@pytest.mark.parametrize("msg", CON_PETICION)
def test_saludo_con_peticion_no_es_trivial(msg):
    """El fallo caro: recortar herramientas en un mensaje que SI pedia algo."""
    assert is_trivial_turn(msg) is False, f"lo recortaria y romperia la tarea: {msg!r}"


def test_mensaje_vacio_no_recorta():
    assert is_trivial_turn("") is False
    assert is_trivial_turn(None) is False


def test_mensaje_largo_no_es_trivial():
    """Tope de palabras: un texto largo no es un saludo aunque empiece como uno."""
    assert is_trivial_turn("hola hola hola hola hola hola hola hola") is False


def _tool(nombre):
    return {"type": "function", "function": {"name": nombre, "description": "x" * 300}}


def test_select_conserva_el_nucleo():
    """Voz y memoria SI se conservan: Arturo usa respuesta por voz a diario
    (verificado en el turno real: el saludo genero audio TTS)."""
    tools = [_tool(n) for n in
             ("text_to_speech", "memory", "memory_search", "clarify",
              "terminal", "browser_click", "kanban_create", "computer_use")]
    rec = select_tools_for_turn("Hola Hermes", tools)
    nombres = {(t["function"]["name"]) for t in rec}
    assert "text_to_speech" in nombres
    assert "memory" in nombres
    assert "terminal" not in nombres
    assert "kanban_create" not in nombres
    assert len(rec) < len(tools)


def test_select_no_recorta_si_hay_peticion():
    tools = [_tool(n) for n in ("text_to_speech", "terminal", "memory")]
    assert select_tools_for_turn("hola, revisa el correo", tools) is None


def test_select_sin_tools_no_falla():
    assert select_tools_for_turn("hola", None) is None
    assert select_tools_for_turn("hola", []) is None


def test_select_no_recorta_si_el_nucleo_no_esta_presente():
    """Si ninguna herramienta del nucleo esta disponible, recortar dejaria
    la lista vacia -- eso cambia el comportamiento del turno sin que nadie
    lo haya pedido. Mejor no tocar nada."""
    tools = [_tool(n) for n in ("terminal", "browser_click", "kanban_create")]
    assert select_tools_for_turn("hola", tools) is None
