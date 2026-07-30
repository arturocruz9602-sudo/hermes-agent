"""Bloque AK (30 jul 2026) -- MEMORY.md va como INDICE, no completa.

Medicion real (cuenta de Arturo, Telegram):
  MEMORY.md              102,597 chars (~25,650 tokens)
  system prompt completo 156,281 chars (~39,070 tokens)
  seccion mas pesada     "LAPTOP WINDOWS - ESPECIFICACIONES TECNICAS",
                         ~13,843 tokens, viajando en CADA vuelta del
                         agente aunque el mensaje fuera "hola".

Con Gemini free tier (250,000 tokens/minuto) eso agota la cuota en 3-4
mensajes, y el 429 cae a mitad de stream -- donde el fallback de LiteLLM
ya no puede saltar a Groq/OpenRouter.

Seguro porque la memoria NO se pierde: memoria_indexador.py la indexa por
secciones (source='memory_md') y la busqueda las recupera con score alto
(verificado: 0.868 / 0.875 / 0.883 en consultas reales).
"""

from __future__ import annotations

from agent.system_prompt import _memoria_como_indice


def _memoria_grande(n_secciones=40, relleno=600):
    partes = ["Memoria persistente de Hermes.\n"]
    for i in range(n_secciones):
        partes.append(f"## SECCION {i}\n" + ("dato relevante. " * relleno))
    return "\n".join(partes)


def test_memoria_grande_se_vuelve_indice():
    grande = _memoria_grande()
    idx = _memoria_como_indice(grande)
    assert len(idx) < len(grande) / 10, "el indice deberia ser una fraccion del original"
    assert "SECCION 0" in idx and "SECCION 39" in idx, "deben listarse todos los titulos"
    assert "dato relevante" not in idx, "el CONTENIDO no debe viajar, solo los titulos"


def test_el_indice_dice_como_recuperar_el_detalle():
    """Sin esto el modelo creeria que perdio la memoria y responderia
    'no recuerdo' -- peor que gastar los tokens."""
    idx = _memoria_como_indice(_memoria_grande())
    assert "memory_search" in idx
    assert "NUNCA digas que no recuerdas" in idx


def test_memoria_chica_se_manda_completa():
    """Por debajo del umbral no compensa: mandar el indice y ademas tener
    que buscar sale mas caro que mandar la memoria entera."""
    chica = "## A\ndato\n\n## B\notro dato\n"
    assert _memoria_como_indice(chica) == chica


def test_sin_secciones_reconocibles_no_se_toca():
    """Prosa larga sin encabezados '##': no hay indice que construir, y un
    resumen inventado seria peor que el original."""
    prosa = "texto sin encabezados. " * 2000
    assert _memoria_como_indice(prosa) == prosa


def test_entrada_vacia_o_none_no_revienta():
    assert _memoria_como_indice("") == ""
    assert _memoria_como_indice(None) is None


def test_memoria_real_de_arturo_si_esta_disponible():
    """Contra el archivo real, si existe en esta maquina."""
    import os
    ruta = os.path.expanduser("~/.hermes/memories/MEMORY.md")
    if not os.path.isfile(ruta):
        return
    original = open(ruta, encoding="utf-8").read()
    if len(original) <= 12_000:
        return
    idx = _memoria_como_indice(original)
    assert len(idx) < len(original) / 5
    assert "memory_search" in idx
