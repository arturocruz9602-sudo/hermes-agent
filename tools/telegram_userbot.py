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
my.telegram.org (one-time, see docs/HAS.md OT-QA step (d)). Login is a
TWO-STEP process on purpose (``start_login`` / ``complete_login``)
instead of Telethon's blocking ``client.start()`` -- that call does a
synchronous ``input()`` for the verification code, which has no
terminal to read from when driven from an automated tool call. The
two calls share the SAME underlying connection (module-level
``_pending_login_client``) when run in the same process -- an earlier
version reconnected fresh in ``complete_login()`` and that broke real
logins with ``PhoneCodeExpiredError`` (see the comment above
``_pending_login_client`` for the real incident):

    from tools.telegram_userbot import start_login, complete_login
    phone_code_hash = await start_login(api_id, api_hash, phone_number)
    # Telegram just sent a real code to the QA account -- Arturo relays it
    await complete_login(api_id, api_hash, phone_number, phone_code_hash,
                          code, vault_passphrase)

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

from tools.qa_identity import QA_USER_ID
from tools.vault_tool import VaultAuthError, vault_get, vault_save

# QA_USER_ID (imported above) is who the OFFICIAL bot recognizes on the
# OTHER end of the conversation the userbot drives -- not the userbot's
# own identity.

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


class TwoFactorPasswordNeeded(RuntimeError):
    """Raised by complete_login() when the QA account has a 2FA cloud
    password set. Not handled automatically on purpose -- that password
    is a separate secret this module has no story for yet; surfacing a
    clear error beats silently prompting for one more credential."""


#  Real incident (27 Jul 2026, OT-QA live login): the original version of
#  this module disconnected after ``start_login()`` and opened a brand
#  new ``TelegramClient(StringSession(), ...)`` in ``complete_login()``
#  -- two independent sessions, on the theory that only
#  ``phone_code_hash`` needed to survive between them (Telethon's own
#  docs read that way). That theory is wrong in practice: signing in
#  from a DIFFERENT client than the one that requested the code makes
#  Telegram reject it with ``PhoneCodeExpiredError`` even seconds after
#  a fresh code was sent -- confirmed against real codes, 4 failed
#  attempts in a row, root-caused via Telethon issue #799 ("the
#  confirmation code has expired when using two different clients").
#  Fix: keep the SAME connected client alive (module-level) between the
#  two calls instead of reconnecting. The two-call shape is kept
#  (``start_login`` still returns immediately, no blocking ``input()``)
#  so an agent can still drive this across two separate tool calls --
#  only the underlying connection is now shared, not recreated.
_pending_login_client: Optional["TelegramClient"] = None


async def start_login(api_id: int, api_hash: str, phone_number: str) -> str:
    """Step 1 of 2 for the one-time QA account login (see module
    docstring). Connects and requests a real login code -- Telegram
    sends it to the QA account for real at this point. Returns
    ``phone_code_hash``: pass it to ``complete_login()`` along with the
    code Arturo relays.

    The connection is kept OPEN (module-level ``_pending_login_client``)
    until ``complete_login()`` runs, in the SAME process -- see the
    real-incident comment above for why a fresh reconnect in step 2
    breaks sign-in. If ``complete_login()`` ends up running in a
    different process, it falls back to a fresh client (same risk as
    before the fix, but only as a last resort).

    MUST NOT be called until L13 is confirmed closed -- see the module
    docstring. Deliberately not gated in code (the vault itself refuses
    nothing today by design, it just may have been unreliable before
    the fix) -- the gate is procedural: don't call this until L13's fix
    is verified live, same standard as everything else in this project.
    """
    global _pending_login_client
    _require_telethon()
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(phone_number)
    except Exception:
        await client.disconnect()
        raise
    _pending_login_client = client
    return sent.phone_code_hash


async def complete_login(
    api_id: int, api_hash: str, phone_number: str, phone_code_hash: str,
    code: str, vault_passphrase: str,
) -> None:
    """Step 2 of 2: submits the code Arturo relayed, completes the
    login, and writes the resulting session string to the vault via
    ``vault_save`` -- the SAME real save path every other credential
    uses, so this benefits from whatever L13 fix landed (it is not a
    parallel, unaudited storage mechanism).

    Reuses the still-open client from ``start_login()`` when this runs
    in the same process (the normal case) -- see the real-incident
    comment above ``_pending_login_client`` for why a fresh client here
    breaks sign-in. Falls back to a new connection only if no pending
    client is found (e.g. a different process ran ``start_login()``)."""
    global _pending_login_client
    _require_telethon()
    from telethon.errors import SessionPasswordNeededError

    client = _pending_login_client
    _pending_login_client = None
    if client is None:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
    try:
        try:
            await client.sign_in(
                phone=phone_number, code=code, phone_code_hash=phone_code_hash,
            )
        except SessionPasswordNeededError as exc:
            raise TwoFactorPasswordNeeded(
                "La cuenta QA tiene una contraseña de dos pasos (2FA) "
                "configurada -- este flujo no la maneja todavía. "
                "Desactívala temporalmente en Telegram (Ajustes > "
                "Privacidad y seguridad > Verificación en dos pasos) o "
                "dime la contraseña para agregarla al flujo."
            ) from exc
        session_string = client.session.save()
    finally:
        await client.disconnect()
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
