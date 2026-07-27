"""S5 (HAS Fase 2, Bloque 4): guardias de permisos.

Un intento de `rm -rf /` simulado debe quedar denegado por el piso
"hardline" real de tools/approval.py -- el mismo guardia que protege
produccion. Confirma, como humo, que tras el rebase la capa de
seguridad mas estricta sigue bloqueando incondicionalmente.
"""

from __future__ import annotations

import pytest

from tools.approval import (
    check_all_command_guards,
    disable_session_yolo,
    reset_current_session_key,
    set_current_session_key,
)


@pytest.fixture
def clean_session(monkeypatch):
    monkeypatch.delenv("HERMES_YOLO_MODE", raising=False)
    monkeypatch.delenv("HERMES_INTERACTIVE", raising=False)
    monkeypatch.delenv("HERMES_GATEWAY_SESSION", raising=False)
    monkeypatch.delenv("HERMES_CRON_SESSION", raising=False)
    monkeypatch.delenv("HERMES_EXEC_ASK", raising=False)
    token = set_current_session_key("smoke_s5")
    try:
        disable_session_yolo("smoke_s5")
        yield
    finally:
        disable_session_yolo("smoke_s5")
        reset_current_session_key(token)


def test_rm_rf_root_is_blocked_hardline(clean_session):
    result = check_all_command_guards("rm -rf /", "local")
    assert result["approved"] is False
    assert result.get("hardline") is True
    assert "BLOCKED (hardline)" in result["message"]


def test_yolo_mode_cannot_bypass_hardline(clean_session, monkeypatch):
    monkeypatch.setenv("HERMES_YOLO_MODE", "1")
    result = check_all_command_guards("rm -rf /", "local")
    assert result["approved"] is False
    assert result.get("hardline") is True
