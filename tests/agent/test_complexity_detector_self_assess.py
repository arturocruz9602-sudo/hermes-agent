"""Bloque O.2 (Tarea E v2) -- self_assess_response()/should_offer_v2().

Regression coverage for the false-positive fixed on 2026-07-29: a response
that correctly hands a decision back to Arturo (e.g. "reset the session or
keep going?" when the choice is his to make) was being classified as
"resolvi_con_confianza=false" by the self-assessment rubric, triggering a
spurious Tarea E / DeepSeek offer on top of an already-complete answer.
Confirmed live against the real cheap-model call before writing these tests
(see docs/ESTADO.md, 2026-07-29). These tests mock ``_call_cheap_model_json``
so they don't depend on network/API availability, but the JSON payloads used
mirror exactly what the real model returned for each real/representative case.
"""

from __future__ import annotations

from unittest.mock import patch

from agent.complexity_detector import self_assess_response, should_offer_v2


def _assess_with(parsed: dict, user_message: str = "pregunta", response: str = "respuesta") -> dict:
    with patch(
        "agent.complexity_detector._call_cheap_model_json", return_value=parsed
    ):
        return self_assess_response(user_message, response)


def test_correctly_deferred_decision_does_not_offer():
    """The exact real case (2026-07-29): Hermes explained the incident fully
    and asked Arturo whether to /new or keep going -- his call, not Hermes's.
    """
    assessment = _assess_with(
        {"resolvi_con_confianza": True, "multivariable": False, "que_me_falto": None}
    )
    assert should_offer_v2(assessment) is False


def test_genuinely_hedgy_response_still_offers():
    """Real hedging language ("podría ser... prueba con...") must still trigger
    the offer -- the fix must not become permissive across the board."""
    assessment = _assess_with(
        {
            "resolvi_con_confianza": False,
            "multivariable": True,
            "que_me_falto": "investigación y diagnóstico más profundos",
        }
    )
    assert should_offer_v2(assessment) is True


def test_multivariable_with_real_gap_still_offers():
    """multivariable=true + a real unresolved gap must still offer."""
    assessment = _assess_with(
        {
            "resolvi_con_confianza": False,
            "multivariable": True,
            "que_me_falto": "modelar la correlación entre las posiciones",
        }
    )
    assert should_offer_v2(assessment) is True


def test_trivial_confident_answer_does_not_offer():
    assessment = _assess_with(
        {"resolvi_con_confianza": True, "multivariable": False, "que_me_falto": None}
    )
    assert should_offer_v2(assessment) is False


def test_greeting_with_no_real_question_does_not_offer():
    """Regression (2026-07-30): "Hermes" -> "Buenas noches. ¿En qué puedo
    ayudarte?" was classified as resolvi_con_confianza=false ("el usuario
    solo dio una palabra sin contexto") -- a saludo has no question to
    resolve, answering it back is already complete. Confirmed live against
    the real cheap-model call after adding EXCEPCIÓN 2 to
    _SELF_ASSESS_RUBRIC (see docs/ESTADO.md, 2026-07-30): now returns
    resolvi_con_confianza=true. Mocked here the same way as the rest of
    this file so the suite doesn't depend on network/API availability."""
    assessment = _assess_with(
        {"resolvi_con_confianza": True, "multivariable": False, "que_me_falto": None},
        user_message="Hermes",
        response="Buenas noches. ¿En qué puedo ayudarte?",
    )
    assert should_offer_v2(assessment) is False


def test_call_failure_is_fail_safe_default():
    """_call_cheap_model_json returning None (any internal error) must default
    to resolvi_con_confianza=True -- never offer by default on failure."""
    with patch("agent.complexity_detector._call_cheap_model_json", return_value=None):
        assessment = self_assess_response("pregunta", "respuesta")
    assert assessment == {
        "resolvi_con_confianza": True,
        "multivariable": False,
        "que_me_falto": None,
    }
    assert should_offer_v2(assessment) is False
