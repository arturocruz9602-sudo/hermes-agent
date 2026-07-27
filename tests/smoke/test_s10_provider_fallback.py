"""S10 (HAS Fase 2, Bloque 4): fallback de proveedores (mock).

Con un error de API simulado (mock, no una llamada real) para cada
escenario real de la escalera Gemini->Groq->OpenRouter->DeepSeek,
confirma que classify_api_error() -- la funcion real que decide si el
bucle de reintentos debe rotar a otro proveedor -- clasifica correcto.
No dispara ninguna llamada real a un proveedor.
"""

from __future__ import annotations

from agent.error_classifier import FailoverReason, classify_api_error


class MockAPIError(Exception):
    def __init__(self, message, status_code=None, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def test_rate_limit_triggers_fallback_to_next_provider():
    err = MockAPIError("rate limit exceeded", status_code=429)
    result = classify_api_error(err, provider="gemini", model="gemini-2.5-pro")
    assert result.reason in {FailoverReason.rate_limit, FailoverReason.upstream_rate_limit}
    assert result.should_fallback is True, (
        "un 429 debe marcar should_fallback -- es la senal real que hace "
        "que el bucle de reintentos rote de Gemini al siguiente proveedor"
    )


def test_billing_exhaustion_triggers_fallback():
    err = MockAPIError("insufficient_quota: you have run out of credits", status_code=402)
    result = classify_api_error(err, provider="groq", model="llama-3.3-70b")
    assert result.reason == FailoverReason.billing
    assert result.should_fallback is True


def test_server_overload_is_retryable_not_immediate_fallback():
    err = MockAPIError("service overloaded, try again", status_code=503)
    result = classify_api_error(err, provider="openrouter", model="nemotron-3-super-120b")
    assert result.reason == FailoverReason.overloaded
    assert result.retryable is True
