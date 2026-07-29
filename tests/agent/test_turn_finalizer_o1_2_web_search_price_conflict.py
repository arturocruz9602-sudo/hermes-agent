"""Bloque O.1.2 (29 Jul 2026) -- cierra el hueco arquitectónico de O.1 vs
web_search nativo (docs/ESTADO.md, item 3 del backlog auditado del 22 Jul).

O.1 (agent/turn_context.py) solo reconciliaba precios contra Brave/
CoinGecko inyectados ANTES del turno por el propio código -- no veía
datos que el modelo obtiene por su cuenta llamando a web_search DURANTE
el turno. Bug real confirmado: ETH $1,917-1,929 vs $1,736.63 real
presentados sin aviso (mensaje 15885), conflicto originado en 3 llamadas
nativas a web_search. Este bloque corre POST-respuesta (mismo patrón que
O.6.1) usando la misma fetch_coingecko_prices/_PRICE_MENTION_RE que O.1
ya usaba para el caso Brave.

Mocks CoinGecko (real network call) -- no se testea contra la red real
aquí, solo la lógica de detección/comparación/aviso.
"""

from __future__ import annotations

from unittest.mock import patch

from agent.turn_finalizer import finalize_turn
from tests.agent.test_turn_finalizer_bloque_af import _StubAgent


def _finalize(messages, final_response, current_turn_user_idx=0):
    agent = _StubAgent()
    return finalize_turn(
        agent,
        final_response=final_response,
        api_call_count=1,
        interrupted=False,
        failed=False,
        messages=messages,
        conversation_history=None,
        effective_task_id="task-1",
        turn_id="turn-1",
        user_message="cual es el precio de ethereum",
        original_user_message="cual es el precio de ethereum",
        _should_review_memory=False,
        _turn_exit_reason="text_response(finish_reason=stop)",
        current_turn_user_idx=current_turn_user_idx,
    ), agent


def _messages_with_web_search_call():
    return [
        {"role": "user", "content": "cual es el precio de ethereum"},
        {
            "role": "assistant", "content": "",
            "tool_calls": [{"id": "c1", "function": {"name": "web_search", "arguments": "{}"}}],
        },
        {
            "role": "tool", "name": "web_search", "tool_name": "web_search",
            "tool_call_id": "c1", "content": "ETH esta en $1,929.40 segun noticias recientes",
        },
    ]


def test_conflicting_price_after_web_search_gets_flagged():
    messages = _messages_with_web_search_call()
    with patch(
        "agent.complexity_detector.fetch_coingecko_prices",
        return_value={"ethereum": 1736.63},
    ):
        result, agent = _finalize(
            messages, "El precio actual de ETH es $1,929.40, segun mi busqueda.",
        )
    assert "⚠️" in result["final_response"]
    assert "1,736.63" in result["final_response"] or "1736.63" in result["final_response"]


def test_no_web_search_call_never_checks_price():
    """Sin web_search en el turno, O.1.2 no debe tocar nada -- el caso
    Brave/CoinGecko pre-inyectado ya lo cubre O.1, no este bloque."""
    messages = [{"role": "user", "content": "cual es el precio de ethereum"}]
    with patch("agent.complexity_detector.fetch_coingecko_prices") as mock_fetch:
        result, agent = _finalize(messages, "El precio de ETH es $1,929.40.")
    mock_fetch.assert_not_called()
    assert "⚠️" not in result["final_response"]


def test_web_search_called_but_price_matches_real_no_warning():
    messages = _messages_with_web_search_call()
    with patch(
        "agent.complexity_detector.fetch_coingecko_prices",
        return_value={"ethereum": 1929.40},
    ):
        result, agent = _finalize(messages, "El precio actual de ETH es $1,929.40.")
    assert "⚠️" not in result["final_response"]


def test_web_search_called_but_no_known_coin_no_crash():
    messages = _messages_with_web_search_call()
    with patch("agent.complexity_detector.fetch_coingecko_prices", return_value=None):
        result, agent = _finalize(messages, "No encontre informacion util.")
    assert "⚠️" not in result["final_response"]


def test_fetch_failure_is_fail_safe_never_raises():
    messages = _messages_with_web_search_call()
    with patch(
        "agent.complexity_detector.fetch_coingecko_prices",
        side_effect=RuntimeError("network down"),
    ):
        result, agent = _finalize(messages, "El precio de ETH es $1,929.40.")
    # No lanza, y la respuesta original sigue intacta (fail-safe real).
    assert result["final_response"] == "El precio de ETH es $1,929.40."


def test_missing_current_turn_user_idx_skips_check():
    messages = _messages_with_web_search_call()
    with patch("agent.complexity_detector.fetch_coingecko_prices") as mock_fetch:
        result, agent = _finalize(
            messages, "El precio de ETH es $1,929.40.", current_turn_user_idx=None,
        )
    mock_fetch.assert_not_called()
