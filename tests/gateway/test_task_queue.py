"""Tests para Cola v2 (HAS §E5, OT-5 Bloque 3, gateway/task_queue.py).

Cubre la escalera de reintentos (process_task_ladder, con proveedores
mockeados -- no se llama a ningun LLM real aqui) y el ciclo completo del
watcher (reclamar -> procesar -> notificar) contra una SessionDB real
(tmp_path) y un adapter falso en memoria.

Incluye la verificación E2E que pide HAS §OT-5 (Fase 5 del plan): 15
tareas sintéticas con el proveedor primario deshabilitado, las 15 deben
terminar en 'notificada' con su mensaje entregado, cero pérdidas.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from gateway.config import Platform
from gateway.task_queue import (
    GatewayTaskQueueMixin,
    TaskLadderExhausted,
    process_task_ladder,
)
from hermes_state import AsyncSessionDB, SessionDB


# ---------------------------------------------------------------------------
# process_task_ladder -- escalera de reintentos en aislamiento
# ---------------------------------------------------------------------------

def test_ladder_succeeds_on_first_provider_first_attempt():
    with patch("gateway.task_queue._call_provider", return_value="resultado ok") as mock_call:
        resultado, proveedor, intentos = process_task_ladder('{"prompt": "hola"}')
    assert resultado == "resultado ok"
    assert proveedor == "chat-fallback"  # Groq, el primero de la escalera
    assert intentos == 1
    mock_call.assert_called_once_with("chat-fallback", "hola")


def test_ladder_falls_through_to_second_provider(monkeypatch):
    calls = []

    def fake_call(model, prompt, timeout=30):
        calls.append(model)
        if model == "chat-fallback":
            raise RuntimeError("Groq caido")
        return f"resultado de {model}"

    with patch("gateway.task_queue._call_provider", side_effect=fake_call):
        resultado, proveedor, intentos = process_task_ladder('{"prompt": "hola"}')

    assert proveedor == "chat-primary"  # Gemini, segundo de la escalera
    assert resultado == "resultado de chat-primary"
    # 5 intentos agotados en chat-fallback + 1 exitoso en chat-primary.
    assert intentos == 6
    assert calls.count("chat-fallback") == 5


def test_ladder_exhausts_all_three_providers_and_raises():
    with patch("gateway.task_queue._call_provider", side_effect=RuntimeError("todo caido")):
        with pytest.raises(TaskLadderExhausted) as exc_info:
            process_task_ladder('{"prompt": "hola"}')
    # 5 intentos x 3 proveedores = 15 intentos totales antes de rendirse.
    assert exc_info.value.intentos == 15


def test_ladder_uses_raw_payload_as_prompt_if_not_json():
    with patch("gateway.task_queue._call_provider", return_value="ok") as mock_call:
        process_task_ladder("no es json valido")
    mock_call.assert_called_once_with("chat-fallback", "no es json valido")


# ---------------------------------------------------------------------------
# Ciclo completo del watcher contra una SessionDB real + adapter falso
# ---------------------------------------------------------------------------

class _FakeAdapter:
    """Adapter falso en memoria -- puede configurarse para fallar N veces
    antes de entregar, simulando una caida transitoria de Telegram."""

    def __init__(self, fail_times: int = 0):
        self.sent: list[tuple[str, str]] = []
        self.fail_times = fail_times
        self._fail_count = 0

    async def send(self, chat_id, message, metadata=None):
        if self._fail_count < self.fail_times:
            self._fail_count += 1
            raise RuntimeError("fallo simulado de envio")
        self.sent.append((chat_id, message))
        from types import SimpleNamespace
        return SimpleNamespace(success=True)


class _FakeGateway(GatewayTaskQueueMixin):
    def __init__(self, db_path: Path, adapter: _FakeAdapter):
        self._running = True
        self._session_db = AsyncSessionDB(SessionDB(db_path))
        self.adapters = {Platform.TELEGRAM: adapter}


@pytest.mark.asyncio
async def test_full_cycle_resolves_and_notifies(tmp_path):
    adapter = _FakeAdapter()
    gw = _FakeGateway(tmp_path / "state.db", adapter)
    task_id = gw._session_db._db.enqueue_task("prueba", '{"prompt": "hola"}', chat_id="c1")

    with patch("gateway.task_queue.process_task_ladder", return_value=("resultado real", "chat-fallback", 1)):
        await gw._task_queue_process_one_tick()

    assert len(adapter.sent) == 1
    chat_id, msg = adapter.sent[0]
    assert chat_id == "c1"
    assert "resultado real" in msg
    assert f"#{task_id}" in msg

    row = gw._session_db._db.get_unnotified_tasks()
    assert row == []  # ya quedo 'notificada'


@pytest.mark.asyncio
async def test_stuck_task_still_gets_notified(tmp_path):
    adapter = _FakeAdapter()
    gw = _FakeGateway(tmp_path / "state.db", adapter)
    gw._session_db._db.enqueue_task("tarea imposible", '{"prompt": "x"}', chat_id="c1")

    with patch(
        "gateway.task_queue.process_task_ladder",
        side_effect=TaskLadderExhausted("boom", 15),
    ):
        await gw._task_queue_process_one_tick()

    assert len(adapter.sent) == 1
    assert "necesito ayuda" in adapter.sent[0][1]


@pytest.mark.asyncio
async def test_notification_retries_until_adapter_recovers(tmp_path):
    """GARANTIA (HAS §E5): si Telegram falla, la fila NO se marca
    notificada -- el siguiente tick reintenta hasta que se entregue."""
    adapter = _FakeAdapter(fail_times=2)
    gw = _FakeGateway(tmp_path / "state.db", adapter)
    gw._session_db._db.enqueue_task("x", '{"prompt": "hola"}', chat_id="c1")

    with patch("gateway.task_queue.process_task_ladder", return_value=("r", "chat-fallback", 1)):
        await gw._task_queue_process_one_tick()  # resuelve, notificacion falla (intento 1)
        assert adapter.sent == []
        assert len(gw._session_db._db.get_unnotified_tasks()) == 1

        await gw._task_queue_process_one_tick()  # reintenta notificacion (intento 2), falla
        assert adapter.sent == []

        await gw._task_queue_process_one_tick()  # reintenta notificacion (intento 3), exito
        assert len(adapter.sent) == 1
        assert gw._session_db._db.get_unnotified_tasks() == []


@pytest.mark.asyncio
async def test_watchdog_reclaims_orphaned_task(tmp_path):
    adapter = _FakeAdapter()
    gw = _FakeGateway(tmp_path / "state.db", adapter)
    task_id = gw._session_db._db.enqueue_task("x", "{}", chat_id="c1")
    gw._session_db._db.claim_next_task()  # queda en_proceso, nunca se resuelve (simula worker muerto)

    with patch.object(
        gw._session_db._db, "get_orphaned_processing_tasks",
        return_value=[{"id": task_id}],
    ):
        await gw._task_queue_watchdog_tick()

    # Ya se puede volver a reclamar -- el watchdog la re-encoló.
    reclaimed = gw._session_db._db.claim_next_task()
    assert reclaimed["id"] == task_id


# ---------------------------------------------------------------------------
# Verificación E2E real pedida por HAS §OT-5 (Fase 5 del plan): 15 tareas
# sintéticas con el proveedor primario deshabilitado, cero pérdidas.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_15_synthetic_tasks_primary_provider_disabled_zero_losses(tmp_path):
    adapter = _FakeAdapter()
    gw = _FakeGateway(tmp_path / "state.db", adapter)

    task_ids = [
        gw._session_db._db.enqueue_task(f"tarea sintetica {i}", f'{{"prompt": "tarea {i}"}}', chat_id="c1")
        for i in range(15)
    ]

    def fake_call(model, prompt, timeout=30):
        # "proveedor primario deshabilitado a propósito" -- chat-fallback
        # (Groq, primero de la escalera) siempre falla; Gemini responde.
        if model == "chat-fallback":
            raise RuntimeError("proveedor primario deshabilitado (prueba)")
        return f"resultado real para: {prompt}"

    with patch("gateway.task_queue._call_provider", side_effect=fake_call):
        # Un tick procesa UNA tarea nueva -- 15 ticks para las 15 encoladas,
        # mas margen por si alguna notificacion necesitara un tick extra.
        for _ in range(20):
            await gw._task_queue_process_one_tick()

    assert len(adapter.sent) == 15, (
        f"se perdieron {15 - len(adapter.sent)} de 15 tareas -- "
        f"entregadas: {[m for _, m in adapter.sent]}"
    )
    sent_task_numbers = {int(msg.split("#")[1].split(":")[0]) for _, msg in adapter.sent}
    assert sent_task_numbers == set(task_ids)
    assert gw._session_db._db.get_unnotified_tasks() == []
    for tid in task_ids:
        assert not any(t["id"] == tid for t in gw._session_db._db.get_orphaned_processing_tasks(0))
