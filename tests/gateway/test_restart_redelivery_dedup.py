"""Tests for /restart idempotency guard against Telegram update re-delivery.

When PTB's graceful-shutdown ACK call (the final `get_updates` on exit) fails
with a network error, Telegram re-delivers the `/restart` message to the new
gateway process.  Without a dedup guard, the new gateway would process
`/restart` again and immediately restart — a self-perpetuating loop.
"""
import json
import time
from unittest.mock import MagicMock

import pytest

import gateway.run as gateway_run
from gateway.platforms.base import MessageEvent, MessageType
from tests.gateway.restart_test_helpers import make_restart_runner, make_restart_source


def _make_restart_event(update_id: int | None = 100) -> MessageEvent:
    return MessageEvent(
        text="/restart",
        message_type=MessageType.TEXT,
        source=make_restart_source(),
        message_id="m1",
        platform_update_id=update_id,
    )


@pytest.mark.asyncio
async def test_redelivered_restart_with_older_update_id_is_ignored(tmp_path, monkeypatch):
    """update_id strictly LESS than the recorded one is also a redelivery."""
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    marker = tmp_path / ".restart_last_processed.json"
    marker.write_text(json.dumps({
        "platform": "telegram",
        "update_id": 12345,
        "requested_at": time.time() - 5,
    }))

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock()

    event = _make_restart_event(update_id=12344)  # older update — shouldn't happen,
                                                  # but if Telegram does re-deliver
                                                  # something older, treat as stale
    result = await runner._handle_restart_command(event)

    assert result == ""
    runner.request_restart.assert_not_called()


@pytest.mark.asyncio
async def test_stale_marker_older_than_5min_does_not_block(tmp_path, monkeypatch):
    """A marker older than the 5-minute window is ignored — fresh /restart proceeds."""
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    marker = tmp_path / ".restart_last_processed.json"
    marker.write_text(json.dumps({
        "platform": "telegram",
        "update_id": 12345,
        "requested_at": time.time() - 600,  # 10 minutes ago
    }))

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock(return_value=True)

    # Same update_id as the stale marker, but the marker is too old to trust
    event = _make_restart_event(update_id=12345)
    result = await runner._handle_restart_command(event)

    assert "Restarting gateway" in result
    runner.request_restart.assert_called_once()


@pytest.mark.asyncio
async def test_event_without_update_id_bypasses_dedup(tmp_path, monkeypatch):
    """Events with no platform_update_id (non-Telegram, CLI fallback) aren't gated."""
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    marker = tmp_path / ".restart_last_processed.json"
    marker.write_text(json.dumps({
        "platform": "telegram",
        "update_id": 999999,
        "requested_at": time.time(),
    }))

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock(return_value=True)

    # No update_id — the dedup check should NOT kick in
    event = _make_restart_event(update_id=None)
    result = await runner._handle_restart_command(event)

    assert "Restarting gateway" in result
    runner.request_restart.assert_called_once()


@pytest.mark.asyncio
async def test_different_platform_bypasses_dedup(tmp_path, monkeypatch):
    """Marker from Telegram doesn't block a /restart from another platform."""
    from gateway.config import Platform
    from gateway.session import SessionSource

    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    marker = tmp_path / ".restart_last_processed.json"
    marker.write_text(json.dumps({
        "platform": "telegram",
        "update_id": 12345,
        "requested_at": time.time(),
    }))

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock(return_value=True)

    # /restart from Discord — not a redelivery candidate
    discord_source = SessionSource(
        platform=Platform.DISCORD,
        chat_id="discord-chan",
        chat_type="dm",
        user_id="u1",
    )
    event = MessageEvent(
        text="/restart",
        message_type=MessageType.TEXT,
        source=discord_source,
        message_id="m1",
        platform_update_id=12345,
    )
    result = await runner._handle_restart_command(event)

    assert "Restarting gateway" in result
    runner.request_restart.assert_called_once()


@pytest.mark.asyncio
async def test_marker_missing_but_booted_from_restart_ignores_redelivery(tmp_path, monkeypatch):
    """Missing marker + just booted from a /restart + young process → treat as stale.

    Reproduces the infinite-loop scenario (issue #18528): the dedup marker went
    missing, so the update_id comparison can't run. Because this process booted
    from a chat-originated /restart and is still within the post-boot window,
    the redelivered /restart is suppressed instead of re-restarting the gateway.
    """
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock(return_value=True)
    runner._booted_from_restart = True
    runner._startup_time = time.time()

    event = _make_restart_event(update_id=100)
    result = await runner._handle_restart_command(event)

    assert result == ""  # silently ignored
    runner.request_restart.assert_not_called()
    # One-shot: the flag is consumed so a later legitimate /restart is honored.
    assert runner._booted_from_restart is False


@pytest.mark.asyncio
async def test_marker_missing_fresh_boot_allows_restart(tmp_path, monkeypatch):
    """Missing marker on a genuine fresh boot (not from /restart) → /restart proceeds.

    The guard must NOT swallow the first /restart a user sends shortly after a
    normal (non-restart) startup: _booted_from_restart stays False, so the
    fallback returns False and the restart goes through.
    """
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock(return_value=True)
    runner._booted_from_restart = False
    runner._startup_time = time.time()

    event = _make_restart_event(update_id=100)
    result = await runner._handle_restart_command(event)

    assert "Restarting gateway" in result
    runner.request_restart.assert_called_once()


@pytest.mark.asyncio
async def test_marker_missing_booted_from_restart_but_old_process_allows(tmp_path, monkeypatch):
    """Missing marker + booted from /restart but past the window → /restart proceeds.

    A /restart arriving long after boot is a genuine user action, not a boot-time
    redelivery, so the uptime bound stops the guard from suppressing it forever.
    """
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.delenv("INVOCATION_ID", raising=False)

    runner, _adapter = make_restart_runner()
    runner.request_restart = MagicMock(return_value=True)
    runner._booted_from_restart = True
    runner._startup_time = time.time() - 120  # well past the 60s window

    event = _make_restart_event(update_id=100)
    result = await runner._handle_restart_command(event)

    assert "Restarting gateway" in result
    runner.request_restart.assert_called_once()


# ---------------------------------------------------------------------------
# General redelivery guard (_is_duplicate_update / _mark_update_processed).
#
# _is_stale_restart_redelivery above only protects /restart. Ordinary
# messages had no equivalent guard: a Telegram re-delivery (PTB's graceful-
# shutdown get_updates ACK failing, same root cause as /restart's) was
# reprocessed as a brand-new turn. Confirmed as the cause of a broken reply
# on 2026-07-29 (docs/ESTADO.md): one message redelivered 7x during a burst
# of gateway restarts, and the resulting confusion bled into the next,
# unrelated message.
# ---------------------------------------------------------------------------

def _make_text_event(update_id: int | None, text: str = "hola") -> MessageEvent:
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=make_restart_source(),
        message_id="m1",
        platform_update_id=update_id,
    )


def test_is_duplicate_update_false_when_nothing_recorded_yet(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    runner, _adapter = make_restart_runner()

    assert runner._is_duplicate_update(_make_text_event(update_id=500)) is False


def test_mark_then_is_duplicate_detects_redelivery(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    runner, _adapter = make_restart_runner()

    runner._mark_update_processed(_make_text_event(update_id=500))

    marker = tmp_path / ".last_update_id.json"
    assert json.loads(marker.read_text()) == {"telegram": 500}
    # Same update_id again (redelivery) -> duplicate.
    assert runner._is_duplicate_update(_make_text_event(update_id=500)) is True
    # Older update_id -> also a duplicate.
    assert runner._is_duplicate_update(_make_text_event(update_id=499)) is True
    # Strictly newer update_id -> not a duplicate.
    assert runner._is_duplicate_update(_make_text_event(update_id=501)) is False


def test_is_duplicate_update_ignores_events_without_platform_update_id(tmp_path, monkeypatch):
    """Non-Telegram platforms (no numeric update id) are never gated."""
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    runner, _adapter = make_restart_runner()

    event = _make_text_event(update_id=None)
    runner._mark_update_processed(event)  # no-op, nothing to record
    assert not (tmp_path / ".last_update_id.json").exists()
    assert runner._is_duplicate_update(event) is False


def test_mark_update_processed_never_moves_backwards(tmp_path, monkeypatch):
    """A late-arriving smaller update_id must not clobber a larger recorded one."""
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    runner, _adapter = make_restart_runner()

    runner._mark_update_processed(_make_text_event(update_id=500))
    runner._mark_update_processed(_make_text_event(update_id=10))  # stale/out-of-order

    marker = tmp_path / ".last_update_id.json"
    assert json.loads(marker.read_text()) == {"telegram": 500}
