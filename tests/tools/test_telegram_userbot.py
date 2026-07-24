"""Unit tests for tools/telegram_userbot.py (HAS OT-QA prep, Bloque AF).

Never touches the real vault or the network -- ``vault_get`` is
monkeypatched in every case. The point of this module today is that it
refuses to connect (L13NotClosedError) until a real session string
exists; these tests pin exactly that contract.
"""

import pytest

from tools.vault_tool import VaultAuthError
import tools.telegram_userbot as userbot


def test_missing_session_string_raises_l13_not_closed(monkeypatch):
    monkeypatch.setattr(
        userbot, "vault_get",
        lambda servicio, passphrase: {
            "success": False,
            "error": f"No hay ninguna entrada guardada para '{servicio}'.",
        },
    )
    with pytest.raises(userbot.L13NotClosedError):
        userbot.TelegramUserbot(api_id=1, api_hash="x", vault_passphrase="whatever")


def test_wrong_passphrase_raises_vault_auth_error_not_l13(monkeypatch):
    """A wrong passphrase must never be silently read as 'not configured
    yet' -- that would mask a real auth problem as an unrelated gating
    state."""
    monkeypatch.setattr(
        userbot, "vault_get",
        lambda servicio, passphrase: {
            "success": False,
            "error": "passphrase incorrecta o bóveda dañada.",
        },
    )
    with pytest.raises(VaultAuthError):
        userbot.TelegramUserbot(api_id=1, api_hash="x", vault_passphrase="wrong")


def test_valid_session_string_constructs_client(monkeypatch):
    # A real, validly-encoded StringSession (fake DC/auth-key bytes, never
    # touches the network) -- Telethon validates the format at
    # construction time AND an unauthenticated empty session serializes
    # to "" (falsy), so a made-up placeholder or a bare StringSession()
    # aren't usable fixtures here; this is the minimum that round-trips.
    from telethon.crypto import AuthKey as _AuthKey
    from telethon.sessions import StringSession as _RealStringSession
    _fixture_session = _RealStringSession()
    _fixture_session.set_dc(2, "149.154.167.51", 443)
    _fixture_session.auth_key = _AuthKey(b"0" * 256)
    fake_but_valid_session = _fixture_session.save()

    monkeypatch.setattr(
        userbot, "vault_get",
        lambda servicio, passphrase: {
            "success": True,
            "servicio": servicio,
            "valor": fake_but_valid_session,
            "fecha_agregado": "2026-07-24 00:00:00",
            "notas": "",
        },
    )
    bot = userbot.TelegramUserbot(api_id=1, api_hash="x", vault_passphrase="correct")
    assert bot._target_user_id == userbot.QA_USER_ID
    assert bot._client is not None


def test_telethon_missing_raises_import_error(monkeypatch):
    monkeypatch.setattr(userbot, "TelegramClient", None)
    with pytest.raises(ImportError):
        userbot.TelegramUserbot(api_id=1, api_hash="x", vault_passphrase="whatever")
