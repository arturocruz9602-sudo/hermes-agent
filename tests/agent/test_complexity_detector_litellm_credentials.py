"""Regression (2026-07-30): _resolve_litellm_credentials() only knew how to
read ``custom_providers['LiteLLM']``.

That morning ``config.yaml.known-good`` (4 Jul) was restored over
``~/.hermes/config.yaml``. That file carries the very same LiteLLM
credentials, but under the ``model:`` section instead of a
``custom_providers`` entry. The lookup raised, ``_call_cheap_model_json``
swallowed it with a bare ``except: return None``, and every caller fell
back to its fail-safe default -- so the whole of Tarea E's self-assessment
went dead while looking exactly like "the model said everything's fine".
Confirmed live: 8 probe cases (greeting, emoji, one-word real question,
multivariable financial question) all returned the byte-identical default
``{"resolvi_con_confianza": true, "multivariable": false, "que_me_falto": null}``
before the fix, and 8/8 discriminating answers after it.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from agent.complexity_detector import _call_cheap_model_json, _resolve_litellm_credentials

_KEY = "sk-real-master-key"


def _resolve_with(cfg: dict) -> "tuple[str, str]":
    with patch("hermes_cli.config.load_config", return_value=cfg), patch(
        "hermes_cli.env_loader.load_hermes_dotenv"
    ), patch.dict("os.environ", {"LITELLM_MASTER_KEY": _KEY}):
        return _resolve_litellm_credentials()


def test_reads_custom_providers_entry():
    """Historic form: entry named 'LiteLLM' under custom_providers."""
    base_url, api_key = _resolve_with(
        {
            "custom_providers": [
                {
                    "name": "LiteLLM",
                    "base_url": "http://localhost:4000/v1",
                    "api_key": "${LITELLM_MASTER_KEY}",
                }
            ]
        }
    )
    assert (base_url, api_key) == ("http://localhost:4000/v1", _KEY)


def test_falls_back_to_model_section():
    """The shape that broke production: same credentials, no custom_providers
    entry -- exactly what config.yaml.known-good (4 Jul) looks like."""
    base_url, api_key = _resolve_with(
        {
            "model": {
                "default": "chat-primary",
                "provider": "custom",
                "base_url": "http://localhost:4000/v1",
                "api_key": "${LITELLM_MASTER_KEY}",
            },
            "custom_providers": [
                {"name": "Local (localhost:11434)", "base_url": "http://localhost:11434/v1"}
            ],
        }
    )
    assert (base_url, api_key) == ("http://localhost:4000/v1", _KEY)


def test_incomplete_custom_providers_entry_falls_through_to_model():
    """A LiteLLM entry missing its api_key must not shadow a usable model:
    section -- otherwise the partial entry silently wins and we're back to
    the fail-safe default."""
    base_url, api_key = _resolve_with(
        {
            "custom_providers": [{"name": "LiteLLM", "base_url": "http://localhost:4000/v1"}],
            "model": {
                "base_url": "http://localhost:4000/v1",
                "api_key": "${LITELLM_MASTER_KEY}",
            },
        }
    )
    assert (base_url, api_key) == ("http://localhost:4000/v1", _KEY)


def test_raises_when_neither_form_is_present():
    """No usable credentials anywhere: must raise loudly, naming both places
    it looked, rather than returning empty strings."""
    with pytest.raises(RuntimeError, match="custom_providers|model:"):
        _resolve_with({"custom_providers": [{"name": "Local", "base_url": "http://x/v1"}]})


def test_call_failure_is_logged_not_silent(caplog):
    """HAS §F9-L6/L14: the silence itself was the bug. A failing cheap-model
    call still returns None (fail-safe preserved), but must leave a log line
    so a dead Tarea E is distinguishable from a healthy one."""
    with patch(
        "agent.complexity_detector._resolve_litellm_credentials",
        side_effect=RuntimeError("credenciales de LiteLLM no encontradas"),
    ), caplog.at_level(logging.WARNING, logger="agent.complexity_detector"):
        assert _call_cheap_model_json("cualquier prompt") is None

    assert any(
        "modelo barato" in r.message for r in caplog.records
    ), f"no se registro el fallo: {[r.message for r in caplog.records]}"
