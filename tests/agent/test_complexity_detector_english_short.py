"""Bloque O.4 -- deteccion de respuestas cortas en ingles (30 jul 2026).

Reportado por Arturo en vivo: le escribio "hola" por Telegram y Hermes le
contesto en ingles. El enforcement de español de Bloque O.4 ni se entero
-- no habia una sola linea en el journal porque
``response_looks_like_english`` devolvia False y ``regenerate_in_spanish``
nunca llego a llamarse.

Causa: el heuristico exigia >=20 palabras Y >=5 stopwords inglesas, asi
que TODA respuesta breve pasaba sin filtro -- justo las que Arturo ve a
diario. Verificado antes del fix: 6 de 6 respuestas cortas en ingles
pasaban, incluida una de 19 palabras.
"""

from __future__ import annotations

import pytest

from agent.complexity_detector import response_looks_like_english

INGLES_CORTO = [
    "Hello! How can I help you today?",
    "Good morning, sir. How may I assist you?",
    "Hi there! What can I do for you?",
    "I'm here. What do you need?",
    # 15 y 19 palabras: por debajo del piso viejo de 20, y ademas traen
    # "me" -- que es stopword en AMBOS idiomas y rompia una version
    # anterior del fix que exigia cero stopwords españolas.
    "Okay, the user is asking about the weather. Let me check that for you now.",
    "Sure! I can help you with that. Just let me know what you need and I will do it.",
]

ESPANOL = [
    "Buenos días, jefe. ¿En qué puedo ayudarle?",
    "Claro que sí, ahorita le reviso el pendiente que me dejó ayer por la tarde.",
    "Son las 6 de la mañana, tiene 35 minutos para alistarse.",
    "Le puse un recordatorio para las 7, señor.",
    "Ya mandé el reporte, no hubo error en el commit.",
    # Español con anglicismos tecnicos: el caso que la regla NO debe morder.
    "Listo, ya quedó el deploy del backend.",
    "Ok, checando el status del servidor.",
    # El aviso de fallback del propio Bloque O.4 -- si esto se detectara
    # como ingles se regeneraria en bucle.
    "⚠️ Tuve un problema generando una respuesta clara para esto. Intenta de nuevo, por favor.",
]


@pytest.mark.parametrize("texto", INGLES_CORTO)
def test_detecta_ingles_corto(texto):
    assert response_looks_like_english(texto) is True, f"paso sin detectar: {texto!r}"


@pytest.mark.parametrize("texto", ESPANOL)
def test_no_falso_positivo_en_espanol(texto):
    assert response_looks_like_english(texto) is False, f"falso positivo: {texto!r}"


def test_textos_muy_cortos_no_disparan():
    """Menos de 4 palabras no alcanza para decidir idioma: "Hecho.",
    "OK", un nombre de archivo. Regenerar eso seria peor que dejarlo."""
    for t in ("Hecho.", "OK", "Listo", "sí", "config.yaml"):
        assert response_looks_like_english(t) is False


def test_ingles_largo_sigue_detectandose():
    """La regla vieja (>=20 palabras) no se toco -- sigue cubriendo el
    caso original de Bloque O.4: razonamiento interno crudo en ingles."""
    largo = (
        "Okay, the user is asking me to check the weather for tomorrow. "
        "I should look at the forecast and then tell them what I found, "
        "but first I need to verify that the location is correct and that "
        "the service is actually available right now."
    )
    assert response_looks_like_english(largo) is True
