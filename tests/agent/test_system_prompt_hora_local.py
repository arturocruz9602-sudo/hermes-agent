"""Bloque AJ (30 jul 2026) -- la hora local va en el system prompt.

El prompt inyectaba solo la FECHA ("Thursday, July 30, 2026"), a proposito,
para mantenerlo byte-estable todo el dia y no invalidar el cache de
prefijos. El comentario de upstream asumia que "el modelo puede consultar
la hora exacta con herramientas cuando la necesite" -- pero en esta
instalacion NO existe ninguna herramienta de tiempo (verificado contra el
registro real de herramientas), asi que Hermes no tenia NINGUNA via para
saber la hora, y la adivinaba mal.

Casos reales del 30 jul en la cuenta de Arturo:
  11:47 AM -> "Buenas noches. ¿En qué puedo ayudarte?"
  14:38    -> "Buenas noches, Arturo"

Importa para el uso real: despertador, "son las 6, tiene 35 minutos para
alistarse", ventanas de estudio, horarios de trabajo.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.system_prompt import build_system_prompt_parts


def _make_agent(**overrides):
    base = dict(
        load_soul_identity=False,
        skip_context_files=True,
        valid_tool_names=[],
        _task_completion_guidance=False,
        _tool_use_enforcement=False,
        _environment_probe=False,
        _kanban_worker_guidance="",
        _memory_store=None,
        _memory_manager=None,
        model="",
        provider="",
        platform="",
        pass_session_id=False,
        session_id="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _volatile_a_las(hora: int) -> str:
    momento = datetime.datetime(2026, 7, 30, hora, 38, tzinfo=datetime.timezone.utc)
    with (
        patch("run_agent.load_soul_md", return_value=""),
        patch("run_agent.build_nous_subscription_prompt", return_value=""),
        patch("run_agent.build_environment_hints", return_value=""),
        patch("run_agent.build_context_files_prompt", return_value=""),
        patch("hermes_time.now", return_value=momento),
    ):
        partes = build_system_prompt_parts(_make_agent())
    return partes["volatile"]


def test_incluye_la_hora_local():
    vol = _volatile_a_las(14)
    assert "Hora local actual" in vol
    assert "14:38" in vol


@pytest.mark.parametrize(
    "hora,saludo_esperado",
    [
        (3, "buenas noches"),    # madrugada
        (8, "buenos días"),
        (11, "buenos días"),
        (14, "buenas tardes"),   # el caso que fallaba en vivo
        (19, "buenas noches"),
        (23, "buenas noches"),
    ],
)
def test_saludo_correcto_por_franja(hora, saludo_esperado):
    vol = _volatile_a_las(hora)
    assert saludo_esperado in vol, f"a las {hora}:38 deberia sugerir {saludo_esperado!r}"


def test_no_dice_buenas_noches_a_media_tarde():
    """Regresion directa del bug que reporto Arturo: 14:38 -> 'Buenas noches'."""
    vol = _volatile_a_las(14)
    assert "buenas noches" not in vol


def test_la_fecha_original_sigue_presente():
    """No se rompio el formato historico: la fecha sigue tal cual estaba."""
    vol = _volatile_a_las(14)
    assert "Conversation started:" in vol
    assert "July 30, 2026" in vol
