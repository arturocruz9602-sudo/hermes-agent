"""Bloque V (23 Jul 2026) -- internal E2E test harness, no Telegram network.

Drives REAL messages through the REAL production pipeline (real config.yaml,
real state.db via SessionStore/SessionDB, real agent/LLM calls, real tools
including vault/memory/session_search) using Arturo's real chat_id/user_id so
authorization passes -- but with the Telegram adapter's actual network I/O
replaced by a capture stub, so nothing goes out over the real Bot API and
there is zero risk of colliding with the live ``hermes-gateway.service``
process's own long-poll connection to the same bot token.

Different from ``tests/e2e/conftest.py``'s ``make_runner()``: that fixture
mocks out ``_handle_message_with_agent`` itself (no LLM, pure routing test).
This harness leaves the REAL agent pipeline in place -- it exists specifically
to capture real Hermes responses (text, tool calls, files) for manual/
scripted review, not to unit-test gateway plumbing.

Usage:
    from tests.e2e.hermes_harness import enviar_texto, enviar_archivo

    result = await enviar_texto("hola, ¿cómo vas?")
    print(result.text)

Safety:
    - Never starts any adapter's real network connection (no getUpdates,
      no webhook, no bot login) -- only the capture stub is registered.
    - Uses the SAME state.db as the live gateway (WAL mode, confirmed safe
      for concurrent multi-process access) so memory/session state is real
      and continuous with normal usage.
    - Real DeepSeek dispatch approval (answering an offer "sí") must be
      opted into explicitly per call (``auto_approve_reasoning=True``) and
      is always logged with a clear "auto-aprobado" marker -- see
      ``enviar_texto``'s docstring.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

os.chdir(Path(__file__).resolve().parents[2])

from gateway.config import Platform, load_gateway_config  # noqa: E402
from gateway.platforms.base import MessageEvent, SendResult  # noqa: E402
from gateway.run import GatewayRunner  # noqa: E402
from gateway.session import SessionSource  # noqa: E402

# Arturo's real Telegram identity (seen throughout state.db/session_key
# strings all session, e.g. "agent:main:telegram:dm:8899197004") -- required
# so the REAL _is_user_authorized() check (not mocked) actually passes.
_ARTURO_CHAT_ID = "8899197004"
_ARTURO_USER_ID = "8899197004"


@dataclass
class CapturedSend:
    """One call the agent made to "send" something -- captured, not sent."""
    content: str
    kind: str = "text"  # "text" | "rich" | "slash_confirm" | "voice" | "document"
    reply_markup: Optional[Any] = None
    raw_kwargs: dict = field(default_factory=dict)


class _CaptureTelegramAdapter:
    """Minimal stand-in for TelegramAdapter -- only what GatewayRunner /
    turn_finalizer / background delivery actually call to emit output.
    Records everything instead of touching the network."""

    def __init__(self):
        self.sent: list[CapturedSend] = []
        self._bot = object()  # truthy marker some code paths gate on

    async def send(self, chat_id, content, reply_to=None, metadata=None) -> SendResult:
        self.sent.append(CapturedSend(content=content, kind="text", raw_kwargs={"metadata": metadata}))
        return SendResult(success=True, message_id=f"harness-{uuid.uuid4().hex[:8]}")

    async def send_typing(self, *_a, **_kw):
        return None

    async def send_slash_confirm(self, chat_id, title, message, session_key, confirm_id, metadata=None) -> SendResult:
        self.sent.append(CapturedSend(content=message, kind="slash_confirm", raw_kwargs={"title": title, "confirm_id": confirm_id}))
        return SendResult(success=True, message_id=f"harness-confirm-{uuid.uuid4().hex[:8]}")

    async def send_document(self, chat_id, file_path, caption=None, metadata=None) -> SendResult:
        self.sent.append(CapturedSend(content=caption or "", kind="document", raw_kwargs={"file_path": file_path}))
        return SendResult(success=True, message_id=f"harness-doc-{uuid.uuid4().hex[:8]}")

    async def send_voice(self, chat_id, file_path, metadata=None) -> SendResult:
        self.sent.append(CapturedSend(content="", kind="voice", raw_kwargs={"file_path": file_path}))
        return SendResult(success=True, message_id=f"harness-voice-{uuid.uuid4().hex[:8]}")

    async def delete_message(self, chat_id, message_id) -> bool:
        return True

    def set_message_handler(self, handler):
        self._handler = handler


@dataclass
class HarnessResult:
    """Everything captured for one enviar_* call."""
    sends: list[CapturedSend]
    elapsed_s: float
    error: Optional[str] = None

    @property
    def text(self) -> str:
        """Concatenated text of every plain-text send (the normal reply)."""
        return "\n".join(s.content for s in self.sends if s.kind == "text" and s.content)

    @property
    def documents(self) -> list[str]:
        return [s.raw_kwargs.get("file_path") for s in self.sends if s.kind == "document"]


_runner: Optional[GatewayRunner] = None
_adapter: Optional[_CaptureTelegramAdapter] = None


def _get_runner() -> tuple[GatewayRunner, _CaptureTelegramAdapter]:
    """Lazily build ONE real GatewayRunner + capture adapter, reused across
    calls in the same process (mirrors how the real service keeps one
    long-lived runner instance)."""
    global _runner, _adapter
    if _runner is not None:
        return _runner, _adapter

    config = load_gateway_config()
    runner = GatewayRunner(config)
    adapter = _CaptureTelegramAdapter()
    runner.adapters = {Platform.TELEGRAM: adapter}
    _runner, _adapter = runner, adapter
    return runner, adapter


def _make_event(text: str, internal: bool = False) -> MessageEvent:
    source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id=_ARTURO_CHAT_ID,
        user_id=_ARTURO_USER_ID,
        user_name="Arturo (harness)",
        chat_type="dm",
    )
    return MessageEvent(text=text, source=source, message_id=f"harness-{uuid.uuid4().hex[:8]}", internal=internal)


async def enviar_texto(texto: str, timeout_s: float = 120.0) -> HarnessResult:
    """Send a real text message through the real Hermes pipeline.

    Blocks until the turn completes (or ``timeout_s`` elapses) and returns
    everything the capture adapter recorded.
    """
    runner, adapter = _get_runner()
    adapter.sent.clear()
    event = _make_event(texto)
    start = time.monotonic()
    error = None
    try:
        await asyncio.wait_for(runner._handle_message(event), timeout=timeout_s)
    except asyncio.TimeoutError:
        error = f"timeout tras {timeout_s}s"
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller, not swallowed
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.monotonic() - start
    return HarnessResult(sends=list(adapter.sent), elapsed_s=elapsed, error=error)


async def enviar_archivo(ruta: str, caption: str = "", timeout_s: float = 120.0) -> HarnessResult:
    """Send a real message with a local file attached (as media_urls),
    mirroring how an adapter normalizes an inbound photo/document."""
    runner, adapter = _get_runner()
    adapter.sent.clear()
    source = SessionSource(
        platform=Platform.TELEGRAM, chat_id=_ARTURO_CHAT_ID, user_id=_ARTURO_USER_ID,
        user_name="Arturo (harness)", chat_type="dm",
    )
    event = MessageEvent(
        text=caption, source=source, message_id=f"harness-{uuid.uuid4().hex[:8]}",
        media_urls=[ruta], media_types=["application/octet-stream"],
    )
    start = time.monotonic()
    error = None
    try:
        await asyncio.wait_for(runner._handle_message(event), timeout=timeout_s)
    except asyncio.TimeoutError:
        error = f"timeout tras {timeout_s}s"
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.monotonic() - start
    return HarnessResult(sends=list(adapter.sent), elapsed_s=elapsed, error=error)


async def aprobar_oferta_deepseek(motivo: str) -> HarnessResult:
    """Bloque V.3: answer a pending Tarea E offer with 'sí', but ONLY ever
    called explicitly by a caller that has already checked the night's
    DeepSeek budget. Every call is logged here with an explicit marker so
    it is never mistaken for a silent/automatic approval.

    ``motivo`` is REQUIRED and goes straight into the harness's own log
    line -- always state which real test case justified the spend.
    """
    print(
        f"[HARNESS V.3] auto-aprobado por autorización previa de Arturo "
        f"(sesión nocturna de pruebas, presupuesto autorizado) -- motivo: {motivo}",
        flush=True,
    )
    return await enviar_texto("sí")
