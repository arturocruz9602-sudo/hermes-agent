"""S4 (HAS Fase 2, Bloque 4): detector de complejidad (Tarea E).

5 mensajes con categoria esperada conocida, ejercitando detect_categories()
real -- no un mock. Confirma, como humo, que la clasificacion de Tarea E
sigue funcionando igual tras el rebase (mismas frases -> mismas categorias).
"""

from __future__ import annotations

import pytest

from agent.complexity_detector import detect_categories


@pytest.mark.parametrize(
    "mensaje,categoria_esperada",
    [
        ("Por favor razona paso a paso antes de responder", "1_razonamiento"),
        ("¿Por qué no funciona este código? ayúdame a depurar", "2_programacion"),
        ("Necesito un diagnóstico de por qué se cayó el gateway anoche", "4_diagnostico"),
        ("optimiza el rendimiento de esta consulta, hay una race condition", "2_programacion"),
    ],
)
def test_known_phrase_maps_to_expected_category(mensaje, categoria_esperada):
    categorias = detect_categories(mensaje)
    assert categoria_esperada in categorias, (
        f"{mensaje!r} deberia incluir {categoria_esperada!r}, "
        f"detectadas: {categorias!r}"
    )


def test_neutral_greeting_has_no_category():
    categorias = detect_categories("hola, ¿cómo estás hoy?")
    assert categorias == [], (
        f"un saludo neutral no deberia disparar ninguna categoria, "
        f"detectadas: {categorias!r}"
    )
