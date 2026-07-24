"""Telegram userbot for the QA automation account (HAS OT-QA, Bloque AF prep).

GATED BY L13 (see docs/HAS.md, section "OT-QA"): this module can be
imported and its structure exercised, but ``TelegramUserbot`` refuses to
connect until a real session string exists in the vault
(``tools/vault_tool.py``) under the service name ``TELEGRAM_USERBOT_SESSION``.
L13 is the vault's confirmed, unfixed (as of Bloque AE) bug where it can
report a save succeeded without it actually happening -- a Telegram
session string is full account access, the single worst kind of secret
to store somewhere that can lie about having stored it.

Nothing here calls the real Telegram MTProto API on import or at module
load time. ``telethon`` is a lazy dependency
(``tools/lazy_deps.py``: ``platform.telegram_userbot``) -- if it isn't
installed, constructing ``TelegramUserbot`` raises a clear ``ImportError``
instead of failing at import time, so the rest of the codebase can import
this module freely even on a machine that never runs the QA account.

Usage once L13 is closed and Arturo has supplied api_id/api_hash from
my.telegram.org (one-time, see docs/HAS.md OT-QA step (d)):

    from tools.telegram_userbot import login_and_store_session
    await login_and_store_session(api_id, api_hash, phone_number, vault_passphrase)
    # (interactive: Telethon prompts for the login code Telegram sends
    # to the QA account -- relay it once, same as the pairing-code flow)

    from tools.telegram_userbot import TelegramUserbot
    bot = TelegramUserbot(api_id, api_hash, vault_passphrase)
    await bot.connect()
    await bot.enviar_texto("hola")
    respuesta = await bot.leer_respuesta()
    await bot.cerrar_conversacion()
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:  # pragma: no cover - exercised on machines without telethon
    TelegramClient = None  # type: ignore[assignment,misc]
    StringSession = None  # type: ignore[assignment,misc]

from tools.vault_tool import VaultAuthError, vault_get, vault_save

# Hermes QA De La Cruz -- Telegram user_id, authorized in the pairing
# store 24-jul-2026 (see hermes pairing list / telegram-approved.json).
# Not the userbot's own identity -- this is who the OFFICIAL bot
# recognizes on the OTHER end of the conversation the userbot drives.
QA_USER_ID = 8727618189

_VAULT_SERVICE_NAME = "TELEGRAM_USERBOT_SESSION"

# Low-volume by design (HAS OT-QA step 2: "decenas de mensajes/día") --
# a deliberately conservative pace, independent of any Telegram-side
# rate limit, so the QA account never looks like a burst-y automated
# account even once it starts driving real test traffic.
_MIN_SECONDS_BETWEEN_SENDS = 2.0


class L13NotClosedError(RuntimeError):
    """Raised when userbot automation is attempted before a real session
    string exists in the (by definition, at that point verified-safe)
    vault. This is the expected, correct failure mode today -- not a
    bug to work around."""


def _require_telethon() -> None:
    if TelegramClient is None:
        raise ImportError(
            "telethon no está instalado. Instálalo con: "
            "venv/bin/pip install telethon "
            "(o vía tools/lazy_deps.py: platform.telegram_userbot)"
        )


def _get_session_string(vault_passphrase: str) -> Optional[str]:
    """Read the userbot session string from the vault.

    Returns ``None`` when the entry simply doesn't exist yet -- the
    expected state until L13 closes and the one-time login flow runs.
    Raises ``VaultAuthError`` for a wrong passphrase: ``vault_get``
    itself never raises (it returns ``{"success": False, "error":
    "passphrase incorrecta..."}"``), so a wrong passphrase is
    distinguished from "not saved yet" here by that exact error text
    and re-raised -- a wrong passphrase must never be silently treated
    as "no session string configured".
    """
    result = vault_get(_VAULT_SERVICE_NAME, vault_passphrase)
    if result.get("success"):
        return result.get("valor")
    if "passphrase incorrecta" in (result.get("error") or ""):
        raise VaultAuthError(result["error"])
    return None


async def login_and_store_session(
    api_id: int, api_hash: str, phone_number: str, vault_passphrase: str
) -> None:
    """One-time interactive login for the QA account. Telethon will
    prompt for the verification code Telegram sends to that account --
    relay it once (same pattern as the DM pairing code flow). The
    resulting session string is written to the vault via
    ``vault_save`` -- the SAME real save path every other credential
    uses, so this benefits from whatever L13 fix landed (it is not a
    parallel, unaudited storage mechanism).

    MUST NOT be called until L13 is confirmed closed -- see the module
    docstring. Deliberately not gated in code (the vault itself refuses
    nothing today by design, it just may have been unreliable before
    the fix) -- the gate is procedural: don't call this until L13's fix
    is verified live, same standard as everything else in this project.
    """
    _require_telethon()
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        await client.start(phone=phone_number)
        session_string = client.session.save()
    vault_save(_VAULT_SERVICE_NAME, session_string, vault_passphrase)


class TelegramUserbot:
    """Thin async wrapper around Telethon, scoped to exactly the 5
    operations HAS OT-QA needs (enviar_texto, enviar_voz, enviar_foto,
    leer_respuesta, cerrar_conversacion). Not connected until
    ``connect()`` is awaited explicitly -- construction alone never
    touches the network.
    """

    def __init__(self, api_id: int, api_hash: str, vault_passphrase: str):
        _require_telethon()
        session_string = _get_session_string(vault_passphrase)
        if not session_string:
            raise L13NotClosedError(
                "No hay session string en la bóveda todavía "
                f"(servicio '{_VAULT_SERVICE_NAME}'). Esto es lo esperado "
                "hasta que L13 cierre y corra login_and_store_session() "
                "una vez -- ver docs/HAS.md, sección OT-QA."
            )
        self._client = TelegramClient(StringSession(session_string), api_id, api_hash)
        self._target_user_id = QA_USER_ID
        self._last_send_at: float = 0.0

    async def connect(self) -> None:
        await self._client.connect()
        if not await self._client.is_user_authorized():
            raise L13NotClosedError(
                "El session string en la bóveda ya no es válido "
                "(revocado o expirado) -- hace falta correr "
                "login_and_store_session() de nuevo."
            )

    async def _pace(self) -> None:
        loop = asyncio.get_event_loop()
        elapsed = loop.time() - self._last_send_at
        if elapsed < _MIN_SECONDS_BETWEEN_SENDS:
            await asyncio.sleep(_MIN_SECONDS_BETWEEN_SENDS - elapsed)
        self._last_send_at = loop.time()

    async def enviar_texto(self, texto: str) -> None:
        await self._pace()
        await self._client.send_message(self._target_user_id, texto)

    async def enviar_voz(self, ruta_audio: str) -> None:
        await self._pace()
        await self._client.send_file(self._target_user_id, ruta_audio, voice_note=True)

    async def enviar_foto(self, ruta_imagen: str, caption: str = "") -> None:
        await self._pace()
        await self._client.send_file(self._target_user_id, ruta_imagen, caption=caption)

    async def leer_respuesta(self, timeout_s: float = 60.0) -> str:
        """Wait for and return the text of the bot's next reply."""
        async with self._client.conversation(self._target_user_id, timeout=timeout_s) as conv:
            response = await conv.get_response()
            return response.raw_text or ""

    async def cerrar_conversacion(self) -> None:
        await self._client.disconnect()
