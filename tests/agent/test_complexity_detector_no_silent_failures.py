"""Bloque AG (30 jul 2026): ningun fallo de Tarea E puede ser silencioso.

Tarea E estuvo muerta sin que nadie lo notara porque un `except` devolvia
su default sin loggear -- indistinguible de un mecanismo sano. Estas
pruebas fijan las DOS mitades del contrato en los caminos criticos:

  1. el fail-safe se conserva (nunca lanzar, nunca escalar por defecto), y
  2. el fallo deja rastro en el log.

La mitad (2) es la que faltaba, y es la que convierte "Tarea E lleva horas
apagada" en algo detectable. Ver HAS §F9-L6/L14.
"""

from __future__ import annotations

import logging

import pytest

import agent.complexity_detector as cd

LOGGER = "agent.complexity_detector"


def _romper_strip_accents(monkeypatch):
    monkeypatch.setattr(
        cd, "_strip_accents", lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("boom"))
    )


def test_detect_categories_failure_is_logged(caplog, monkeypatch):
    """Si el detector truena, Tarea E no ve NINGUNA categoria -- queda ciega
    para todo mensaje. El fail-safe (lista vacia) es correcto; el silencio no."""
    _romper_strip_accents(monkeypatch)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert cd.detect_categories("por qué falla el gateway") == []
    assert any("detect_categories" in r.message for r in caplog.records)


def test_parse_yes_no_failure_is_logged(caplog, monkeypatch):
    """Esta es la ruta por la que Arturo autoriza (o niega) un gasto. Un
    fallo mudo aqui convierte su "sí" en ambiguo sin que quede registro."""
    _romper_strip_accents(monkeypatch)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert cd.parse_yes_no("sí") is None
    assert any("parse_yes_no" in r.message for r in caplog.records)


def test_offers_today_count_failure_is_logged(caplog, monkeypatch):
    """Devolver 0 al fallar deja SIN efecto el tope diario anti-spam de
    ofertas -- un fallo persistente de state.db podria destapar el limite
    de gasto sin una sola senal."""
    import sqlite3

    def _explota(*_a, **_kw):
        raise OSError("db bloqueada")

    monkeypatch.setattr(sqlite3, "connect", _explota)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert cd.offers_today_count("sesion-x") == 0
    assert any("offers_today_count" in r.message for r in caplog.records)


@pytest.mark.parametrize(
    "nombre",
    [
        "detect_categories",
        "fetch_context_summary",
        "should_offer",
        "parse_yes_no",
        "check_pending_reply",
        "fetch_coingecko_prices",
        "gather_pre_response_context",
        "offers_today_count",
        "regenerate_in_spanish",
        "_call_cheap_model_json",
    ],
)
def test_critical_handlers_still_mention_their_function(nombre):
    """Guard barato contra la regresion real: que alguien agregue o mueva un
    `except` en estas funciones y se lleve el log de paso. Cada una debe
    seguir nombrandose a si misma en algun _log.* de su cuerpo, para que la
    linea del journal diga QUE se apago, no solo que algo fallo."""
    import inspect

    fuente = inspect.getsource(getattr(cd, nombre))
    assert "_log." in fuente, f"{nombre} ya no loggea ningun fallo"
    assert nombre in fuente.split("_log.", 1)[1][:400] or nombre in fuente, (
        f"el log de {nombre} no lo identifica"
    )
