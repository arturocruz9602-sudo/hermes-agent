"""S6 (HAS Fase 2, Bloque 4): cola de mensajes pendientes (Tarea C/D).

Ejercita el ciclo de vida real de mensajes_pendientes en un SessionDB
aislado (tmp_path/state.db, no el real): encolar -> leer -> reclamar ->
marcar procesado. Confirma, como humo, que la cola durable de mensajes
(la que reintenta cuando la cuota del proveedor se agota) sigue
funcionando igual tras el rebase.
"""

from __future__ import annotations

import pytest

from hermes_state import SessionDB


@pytest.fixture
def db(tmp_path):
    return SessionDB(tmp_path / "state.db")


def test_insert_then_read_pending_message(db):
    msg_id = db.insert_pending_message("hola, ¿sigues ahí?", canal="telegram", chat_id="12345")
    pending = db.get_pending_messages(estado="pendiente")
    assert len(pending) == 1
    assert pending[0]["id"] == msg_id
    assert pending[0]["contenido"] == "hola, ¿sigues ahí?"
    assert pending[0]["chat_id"] == "12345"


def test_claim_then_mark_processed_removes_from_pending(db):
    msg_id = db.insert_pending_message("segundo mensaje", canal="telegram", chat_id="12345")

    claimed = db.claim_pending(msg_id, via="smoke_test")
    assert claimed is True

    db.mark_pending_processed(msg_id)
    pending = db.get_pending_messages(estado="pendiente")
    assert pending == []


def test_double_claim_is_rejected(db):
    msg_id = db.insert_pending_message("tercer mensaje", canal="telegram", chat_id="12345")
    first = db.claim_pending(msg_id, via="watcher_a")
    second = db.claim_pending(msg_id, via="watcher_b")
    assert first is True
    assert second is False, (
        "un mensaje ya reclamado no debe poder reclamarse dos veces -- "
        "evita procesar la misma fila por dos caminos (auto-watcher + "
        "autorizacion manual de DeepSeek)"
    )
