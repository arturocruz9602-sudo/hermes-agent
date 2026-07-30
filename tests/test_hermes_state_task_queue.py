"""Tests para la capa de datos de Cola v2 (HAS §E5, hermes_state.py).

Cubre la máquina de estados (encolada -> en_proceso -> resuelta ->
notificada, con 'atorada' como salida alterna) y las garantías de
compare-and-swap que la hacen segura contra workers concurrentes/zombies
-- no la escalera de reintentos ni la notificación real (eso vive en
gateway/task_queue.py, con sus propios tests).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_state import SessionDB


@pytest.fixture
def db(tmp_path: Path) -> SessionDB:
    return SessionDB(tmp_path / "state.db")


def test_enqueue_and_claim_roundtrip(db):
    task_id = db.enqueue_task("prueba", '{"prompt": "hola"}', chat_id="c1")
    assert task_id > 0
    claimed = db.claim_next_task()
    assert claimed["id"] == task_id
    assert claimed["estado"] == "en_proceso"
    assert claimed["started_at"] is not None


def test_claim_returns_none_when_queue_empty(db):
    assert db.claim_next_task() is None


def test_claim_picks_oldest_first(db):
    id1 = db.enqueue_task("primera", "{}", chat_id="c1")
    id2 = db.enqueue_task("segunda", "{}", chat_id="c1")
    first_claimed = db.claim_next_task()
    assert first_claimed["id"] == id1
    second_claimed = db.claim_next_task()
    assert second_claimed["id"] == id2


def test_claim_is_compare_and_swap_not_double_claimable(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    # Nada más que reclamar -- ya está en_proceso, no debe volver a salir.
    assert db.claim_next_task() is None


def test_mark_resolved_transitions_from_en_proceso(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    ok = db.mark_task_resolved(task_id, "resultado real", "hash1", 3, proveedor="chat-fallback")
    assert ok is True
    row = db.get_unnotified_tasks()[0]
    assert row["estado"] == "resuelta"
    assert row["resultado"] == "resultado real"
    assert row["intentos"] == 3
    assert row["proveedor_actual"] == "chat-fallback"


def test_mark_resolved_fails_if_not_en_proceso(db):
    """Sin haber reclamado (claim_next_task) primero, la fila sigue
    'encolada' -- mark_task_resolved no debe transicionarla (CAS real)."""
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    ok = db.mark_task_resolved(task_id, "resultado", "hash1", 1)
    assert ok is False


def test_mark_resolved_is_noop_if_already_reclaimed_by_watchdog(db):
    """Simula el caso zombie: el watchdog re-encoló la tarea (volvió a
    'encolada') antes de que el worker original terminara -- el
    resultado tardío no debe pisar el estado."""
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    db.reclaim_orphaned_task(task_id)  # simula el watchdog re-encolando
    ok = db.mark_task_resolved(task_id, "resultado tardio", "hash1", 1)
    assert ok is False


def test_mark_task_notified_transitions_resuelta_to_notificada(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    db.mark_task_resolved(task_id, "r", "h", 1)
    ok = db.mark_task_notified(task_id)
    assert ok is True
    assert db.get_unnotified_tasks() == []


def test_mark_task_notified_requires_resuelta_first(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    ok = db.mark_task_notified(task_id)
    assert ok is False


def test_mark_task_stuck_transitions_from_en_proceso(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    ok = db.mark_task_stuck(task_id, 15)
    assert ok is True


def test_stuck_task_appears_in_unnotified_until_notified_keep_stuck(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    db.mark_task_stuck(task_id, 15)
    unnotified = db.get_unnotified_tasks()
    assert len(unnotified) == 1
    assert unnotified[0]["estado"] == "atorada"

    ok = db.mark_task_notified(task_id, keep_stuck=True)
    assert ok is True
    assert db.get_unnotified_tasks() == []

    # La fila se queda en 'atorada' -- no hay un estado "atorada-notificada".
    row = db.claim_next_task()
    assert row is None  # no hay nada en 'encolada'


def test_orphaned_processing_task_detected_after_threshold(db, monkeypatch):
    import time as time_mod

    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    # started_at ya quedó en el pasado real (ahorita) -- usamos un
    # max_age_seconds de 0 para simular "ya pasaron 2 horas" sin mockear
    # el reloj del sistema completo.
    orphaned = db.get_orphaned_processing_tasks(max_age_seconds=0)
    assert len(orphaned) == 1
    assert orphaned[0]["id"] == task_id


def test_fresh_task_not_orphaned_before_threshold(db):
    db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    orphaned = db.get_orphaned_processing_tasks(max_age_seconds=7200)
    assert orphaned == []


def test_reclaim_orphaned_task_returns_to_encolada(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    ok = db.reclaim_orphaned_task(task_id)
    assert ok is True
    # Ya se puede volver a reclamar.
    reclaimed = db.claim_next_task()
    assert reclaimed["id"] == task_id
    assert reclaimed["started_at"] is not None


def test_reclaim_is_noop_if_task_already_resolved(db):
    """El worker 'zombie' en realidad seguia vivo y ya resolvio la tarea
    justo antes de que el watchdog la reclamara -- el watchdog no debe
    pisar un resultado real."""
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    db.claim_next_task()
    db.mark_task_resolved(task_id, "resultado real", "hash1", 1)
    ok = db.reclaim_orphaned_task(task_id)
    assert ok is False


def test_enqueue_defaults_platform_to_telegram(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1")
    row = db.claim_next_task()
    assert row["platform"] == "telegram"


def test_enqueue_custom_platform(db):
    task_id = db.enqueue_task("x", "{}", chat_id="c1", platform="discord")
    row = db.claim_next_task()
    assert row["platform"] == "discord"
