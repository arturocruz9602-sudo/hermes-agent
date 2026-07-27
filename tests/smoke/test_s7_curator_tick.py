"""S7 (HAS Fase 2, Bloque 4): tick de curator (dry).

Ejercita should_run_now()/maybe_run_curator() real -- las compuertas que
deciden si el curator corre, sin invocar nunca la revision real por LLM
(el "dry" del escenario: se prueba la logica de la compuerta, no el
review costoso). HERMES_HOME aislado via el fixture compartido.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import agent.curator as curator


def test_fresh_install_defers_first_run_and_seeds_state(isolated_hermes_home):
    assert curator.load_state()["last_run_at"] is None

    result = curator.should_run_now()

    assert result is False, (
        "una instalacion fresca (sin last_run_at) no debe correr de "
        "inmediato -- debe diferir un intervalo completo"
    )
    state = curator.load_state()
    assert state["last_run_at"] is not None, "should_run_now() debe sembrar last_run_at en la primera observacion"


def test_paused_never_runs_even_with_old_last_run(isolated_hermes_home):
    old = datetime.now(timezone.utc) - timedelta(days=30)
    curator.save_state({**curator._default_state(), "last_run_at": old.isoformat()})
    curator.set_paused(True)

    assert curator.should_run_now() is False


def test_runs_after_interval_elapsed_since_last_run(isolated_hermes_home):
    old = datetime.now(timezone.utc) - timedelta(days=30)
    curator.save_state({**curator._default_state(), "last_run_at": old.isoformat()})

    assert curator.should_run_now() is True


def test_maybe_run_curator_is_noop_when_gated_off(isolated_hermes_home, monkeypatch):
    curator.set_paused(True)

    def _boom(**_kwargs):
        raise AssertionError("run_curator_review no debe llamarse si el tick esta gateado")

    monkeypatch.setattr(curator, "run_curator_review", _boom)

    result = curator.maybe_run_curator()
    assert result is None
