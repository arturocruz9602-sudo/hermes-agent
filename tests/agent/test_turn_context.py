"""Unit tests for the extracted turn prologue (``agent/turn_context.py``).

These exercise ``build_turn_context`` against a lightweight fake agent to
confirm the prologue produces the right ``TurnContext`` and applies the
``agent`` side effects the loop relies on — without spinning up a real
``AIAgent`` or hitting any provider.
"""

from __future__ import annotations

import threading
import types
from unittest.mock import MagicMock, patch

import pytest

from agent.context_compressor import ContextCompressor
from agent.turn_context import TurnContext, build_turn_context
from hermes_state import SessionDB


class _FakeTodoStore:
    def has_items(self):
        return True

    def _hydrate(self, *_a, **_k):
        pass


class _FakeGuardrails:
    def __init__(self):
        self.reset_called = False

    def reset_for_turn(self):
        self.reset_called = True


class _FakeAgent:
    """Minimal stand-in covering only what the prologue touches."""

    def __init__(self):
        self.session_id = "sess-1"
        self.model = "test/model"
        self.provider = "openrouter"
        self.requested_provider = "openrouter"
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = "sk-x"
        self.api_mode = "chat_completions"
        self.platform = "cli"
        self.quiet_mode = True
        self.max_iterations = 90
        self.tools = []
        self.valid_tool_names = set()
        self.enabled_toolsets = None
        self.disabled_toolsets = None
        self._skip_mcp_refresh = False
        self.compression_enabled = False
        self.context_compressor = types.SimpleNamespace(
            protect_first_n=2, protect_last_n=2
        )
        # Make the fake compressor honour the ContextEngine contract that the
        # real code now relies on (should_compress_info returns a (bool, reason)
        # tuple). Without it build_turn_context raises AttributeError.
        def _fake_should_compress(tokens=None):
            return False

        def _fake_should_compress_info(tokens=None):
            return (False, None)

        self.context_compressor.should_compress = _fake_should_compress
        self.context_compressor.should_compress_info = _fake_should_compress_info
        self._cached_system_prompt = "SYSTEM"
        self._memory_store = None
        self._memory_manager = None
        self._memory_nudge_interval = 0
        self._turns_since_memory = 0
        self._user_turn_count = 0
        self._todo_store = _FakeTodoStore()
        self._tool_guardrails = _FakeGuardrails()
        self._compression_warning = None
        self._emit_warning = MagicMock()
        self._last_ctx_overflow_warn = None
        self._interrupt_requested = False
        self._memory_write_origin = "assistant_tool"
        self._stream_context_scrubber = None
        self._stream_think_scrubber = None
        # Attributes the prologue assigns; recorded for assertions.
        self._invalid_tool_retries = -1
        self._vision_supported = None
        self._persist_calls = 0
        self._session_messages = []
        self._pending_cli_user_message = None
        self._session_persist_lock = threading.RLock()
        # Records _cached_system_prompt at the moment _ensure_db_session()
        # is called (regression guard for #45499 turn-setup ordering).
        self._ensure_db_prompt_at_call = "<unset>"

    def _warn_context_overflow_blocked(self, reason, preflight_tokens, threshold_tokens):
        # Mirror the real AIAgent helper so tests can assert the warning fired.
        _warn_kind = (reason or "unknown").split(":", 1)[0]
        _warn_key = ("ctx_overflow_blocked", _warn_kind)
        if self._last_ctx_overflow_warn != _warn_key:
            self._last_ctx_overflow_warn = _warn_key
            self._emit_warning(
                f"⚠ Context is over the compression threshold "
                f"(~{preflight_tokens:,} tokens >= {threshold_tokens:,}) "
                f"but compression is currently blocked ({reason})."
            )

    def _clear_context_overflow_warn(self):
        self._last_ctx_overflow_warn = None

    # --- methods the prologue calls ---
    def _ensure_db_session(self):
        self._ensure_db_prompt_at_call = self._cached_system_prompt

    def _restore_primary_runtime(self):
        pass

    def _cleanup_dead_connections(self):
        return False

    def _emit_status(self, _msg):
        pass

    def _replay_compression_warning(self):
        pass

    def _hydrate_todo_store(self, *_a, **_k):
        pass

    def _safe_print(self, *_a, **_k):
        pass

    def _persist_session(self, *_a, **_k):
        self._persist_calls += 1


def _make_agent_with_cooldown(db_path, session_id, *, cooldown_until=None):
    agent = _FakeAgent()
    agent.compression_enabled = True
    agent._emit_status = MagicMock()
    agent._compress_context = MagicMock(
        side_effect=lambda messages, *_a, **_k: (messages, "SYSTEM")
    )

    db = SessionDB(db_path=db_path)
    db.create_session(session_id, source="cli")
    if cooldown_until is not None:
        db.record_compression_failure_cooldown(session_id, cooldown_until, "timeout")

    with patch("agent.context_compressor.get_model_context_length", return_value=100000):
        compressor = ContextCompressor(
            model="test/model",
            threshold_percent=0.85,
            protect_first_n=2,
            protect_last_n=2,
            quiet_mode=True,
        )
    compressor.bind_session_state(db, session_id)
    agent.context_compressor = compressor
    agent._session_db = db
    return agent


@pytest.fixture(autouse=True)
def _stub_runtime_main():
    """``build_turn_context`` calls ``auxiliary_client.set_runtime_main`` as a
    production side effect (telling aux tools the live main provider/model).
    That writes a module-level global these unit tests don't care about and
    which would otherwise leak into sibling tests (e.g. provider-parity
    resolution) when the per-test process isolation plugin is disabled. Stub
    it out so the prologue tests stay hermetic.
    """
    with patch("agent.auxiliary_client.set_runtime_main", lambda *a, **k: None):
        yield


def _build(agent, **overrides):
    kwargs = dict(
        agent=agent,
        user_message="hello",
        system_message=None,
        conversation_history=None,
        task_id=None,
        stream_callback=None,
        persist_user_message=None,
        restore_or_build_system_prompt=lambda *a, **k: None,
        install_safe_stdio=lambda: None,
        sanitize_surrogates=lambda s: s,
        summarize_user_message_for_log=lambda s: s,
        set_session_context=lambda _sid: None,
        set_current_write_origin=lambda _o: None,
        ra=lambda: types.SimpleNamespace(_set_interrupt=lambda *a, **k: None),
    )
    kwargs.update(overrides)
    return build_turn_context(**kwargs)


def test_returns_turn_context_with_user_message_appended():
    agent = _FakeAgent()
    ctx = _build(agent)
    assert isinstance(ctx, TurnContext)
    assert ctx.user_message == "hello"
    # The user turn was appended and indexed.
    assert ctx.messages[-1] == {"role": "user", "content": "hello"}
    assert ctx.current_turn_user_idx == len(ctx.messages) - 1
    assert ctx.active_system_prompt == "SYSTEM"


def test_applies_agent_side_effects():
    agent = _FakeAgent()
    _build(agent)
    # Retry counters reset, guardrails reset, vision re-armed, turn counted.
    assert agent._invalid_tool_retries == 0
    assert agent._tool_guardrails.reset_called is True
    assert agent._vision_supported is True
    assert agent._user_turn_count == 1
    # Crash-resilience persistence fired once.
    assert agent._persist_calls == 1
    # task/turn ids assigned on the agent.
    assert agent._current_task_id
    assert agent._current_turn_id


def test_task_id_passthrough():
    agent = _FakeAgent()
    ctx = _build(agent, task_id="fixed-task")
    assert ctx.effective_task_id == "fixed-task"
    assert agent._current_task_id == "fixed-task"


def test_persist_user_message_becomes_original():
    agent = _FakeAgent()
    ctx = _build(agent, user_message="api-prefixed", persist_user_message="clean")
    # original_user_message tracks the clean persist override.
    assert ctx.original_user_message == "clean"
    # but the appended user turn carries the full (sanitized) message.
    assert ctx.messages[-1]["content"] == "api-prefixed"


def test_pending_cli_message_carries_durable_marker_to_new_turn_dict():
    """A close-persisted CLI input must not be written again by turn start."""
    agent = _FakeAgent()
    staged = {"role": "user", "content": "already durable", "_db_persisted": True}
    agent._pending_cli_user_message = staged

    ctx = _build(agent, user_message="already durable")

    assert ctx.messages[-1] is staged
    assert ctx.messages[-1]["content"] == "already durable"
    assert ctx.messages[-1]["_db_persisted"] is True
    assert agent._pending_cli_user_message is None


def test_stale_pending_cli_message_does_not_replace_new_turn_input():
    """A failed prior persistence handoff cannot substitute later user input."""
    agent = _FakeAgent()
    agent._pending_cli_user_message = {"role": "user", "content": "old prompt"}

    stale = agent._pending_cli_user_message
    ctx = _build(
        agent,
        user_message="new prompt",
        conversation_history=[{"role": "assistant", "content": "old answer"}],
    )

    assert ctx.messages[-1]["content"] == "new prompt"
    assert ctx.messages[-1] is not stale
    assert agent._pending_cli_user_message is None


def test_pending_cli_message_uses_clean_override_for_api_local_note():
    """A noted API message reuses the clean staged dict and its DB marker."""
    agent = _FakeAgent()
    staged = {"role": "user", "content": "clean prompt", "_db_persisted": True}
    agent._pending_cli_user_message = staged

    ctx = _build(
        agent,
        user_message="[MODEL NOTE]\n\nclean prompt",
        persist_user_message="clean prompt",
    )

    assert ctx.messages[-1] is staged
    assert ctx.messages[-1]["content"] == "[MODEL NOTE]\n\nclean prompt"
    assert ctx.messages[-1]["_db_persisted"] is True
    assert agent._pending_cli_user_message is None


def test_runtime_main_sync_happens_after_restore():
    agent = _FakeAgent()
    agent.model = "stale-fallback-model"
    agent.provider = "openai-codex"
    agent.base_url = "https://chatgpt.com/backend-api/codex"
    agent.api_key = "fallback-key"
    agent.api_mode = "codex_responses"

    def restore_primary():
        agent.model = "primary-model"
        agent.provider = "anthropic"
        agent.base_url = "https://api.anthropic.com"
        agent.api_key = "primary-key"
        agent.api_mode = "anthropic_messages"
        agent.requested_provider = "anthropic"

    agent._restore_primary_runtime = restore_primary
    calls = []
    with patch(
        "agent.auxiliary_client.set_runtime_main",
        side_effect=lambda *args, **kwargs: calls.append((args, kwargs)),
    ):
        _build(agent)

    assert calls == [(
        ("anthropic", "primary-model"),
        {
            "base_url": "https://api.anthropic.com",
            "api_key": "primary-key",
            "api_mode": "anthropic_messages",
            "auth_mode": "",
            "requested_provider": "anthropic",
        },
    )]


def test_memory_nudge_fires_at_interval():
    agent = _FakeAgent()
    agent._memory_nudge_interval = 1
    agent.valid_tool_names = {"memory"}
    agent._memory_store = object()
    ctx = _build(agent)
    assert ctx.should_review_memory is True
    assert agent._turns_since_memory == 0  # reset after firing


def test_no_review_when_memory_disabled():
    agent = _FakeAgent()
    ctx = _build(agent)
    assert ctx.should_review_memory is False


def test_ensure_db_session_runs_after_system_prompt_restore():
    """Regression for #45499.

    On a fresh API/gateway agent (``_cached_system_prompt is None``) the DB
    session row must be created AFTER the system prompt is restored/built, so
    the persisted snapshot is written non-NULL. If ``_ensure_db_session()``
    ran first it would insert ``system_prompt=NULL`` and trip the misleading
    "stored system prompt is null; rebuilding" warning plus a first-turn
    prefix cache miss.
    """
    agent = _FakeAgent()
    agent._cached_system_prompt = None  # fresh agent, no cached prompt yet

    def _restore(_agent, _system_message, _history):
        _agent._cached_system_prompt = "REBUILT-SYSTEM"

    _build(agent, restore_or_build_system_prompt=_restore)

    # The prompt was populated before the DB row was created.
    assert agent._ensure_db_prompt_at_call == "REBUILT-SYSTEM"
    assert agent._cached_system_prompt == "REBUILT-SYSTEM"


# ── Between-turns MCP refresh (cache-safe late-binding) ──────────────────────
#
# A slow MCP server that connects after the agent's build-time tool snapshot
# must become callable by the user's NEXT turn — without mutating an in-flight
# turn's cached request prefix. The prologue is exactly that boundary, so the
# refresh hook lives here. These assert the contract (R1/R2/R6 in the spec),
# not timing permutations.


def test_between_turns_refresh_adds_late_tool_when_servers_registered():
    """R1: a tool that registered since build lands in this turn's snapshot."""
    agent = _FakeAgent()

    new_def = {"type": "function", "function": {"name": "mcp_x_tool", "description": "", "parameters": {}}}

    import model_tools
    with patch("tools.mcp_tool.has_registered_mcp_tools", return_value=True), \
         patch.object(model_tools, "get_tool_definitions", return_value=[new_def]):
        _build(agent)

    assert "mcp_x_tool" in agent.valid_tool_names
    assert any(t["function"]["name"] == "mcp_x_tool" for t in agent.tools)


def test_between_turns_refresh_skipped_when_no_servers():
    """R6: the common case (no MCP servers) never walks the registry."""
    agent = _FakeAgent()
    import model_tools

    with patch("tools.mcp_tool.has_registered_mcp_tools", return_value=False), \
         patch.object(model_tools, "get_tool_definitions") as gtd:
        _build(agent)

    gtd.assert_not_called()


def test_between_turns_refresh_skipped_when_skip_flag_set():
    """Internal forks (background_review) set _skip_mcp_refresh to keep tools[]
    byte-identical to the parent for cache parity — the hook must honor it even
    when MCP servers are registered."""
    agent = _FakeAgent()
    agent._skip_mcp_refresh = True
    import model_tools

    with patch("tools.mcp_tool.has_registered_mcp_tools", return_value=True), \
         patch.object(model_tools, "get_tool_definitions") as gtd:
        _build(agent)

    gtd.assert_not_called()


def test_between_turns_refresh_no_churn_when_unchanged():
    """R2: an unchanged tool set leaves the snapshot object identity intact
    (no needless swap → nothing for the next request prefix to diff against)."""
    agent = _FakeAgent()
    same = [{"type": "function", "function": {"name": "a", "description": "", "parameters": {}}}]
    agent.tools = same
    agent.valid_tool_names = {"a"}

    import model_tools
    with patch("tools.mcp_tool.has_registered_mcp_tools", return_value=True), \
         patch.object(
             model_tools, "get_tool_definitions",
             return_value=[{"type": "function", "function": {"name": "a", "description": "", "parameters": {}}}],
         ):
        _build(agent)

    assert agent.tools is same  # not replaced → no churn


def test_preflight_skips_when_persisted_cooldown_survives_restart(tmp_path):
    agent = _make_agent_with_cooldown(
        tmp_path / "state.db",
        "sess-1",
        cooldown_until=4_000_000_000.0,
    )

    with patch("agent.turn_context._should_run_preflight_estimate", return_value=True), \
         patch("agent.turn_context.estimate_request_tokens_rough", return_value=999_999):
        ctx = _build(agent)

    assert isinstance(ctx, TurnContext)
    agent._emit_status.assert_not_called()
    agent._compress_context.assert_not_called()


def test_preflight_still_runs_for_other_session_with_same_db(tmp_path):
    db_path = tmp_path / "state.db"
    _make_agent_with_cooldown(
        db_path,
        "sess-1",
        cooldown_until=4_000_000_000.0,
    )
    agent = _make_agent_with_cooldown(db_path, "sess-2")

    with patch("agent.turn_context._should_run_preflight_estimate", return_value=True), \
         patch("agent.turn_context.estimate_request_tokens_rough", return_value=999_999):
        ctx = _build(agent)

    assert isinstance(ctx, TurnContext)
    agent._emit_status.assert_called_once()
    agent._compress_context.assert_called()


def test_expired_cooldown_allows_preflight(tmp_path):
    agent = _make_agent_with_cooldown(
        tmp_path / "state.db",
        "sess-1",
        cooldown_until=1.0,
    )

    with patch("agent.turn_context._should_run_preflight_estimate", return_value=True), \
         patch("agent.turn_context.estimate_request_tokens_rough", return_value=999_999):
        ctx = _build(agent)

    assert isinstance(ctx, TurnContext)
    agent._emit_status.assert_called_once()
    agent._compress_context.assert_called()


# ===========================================================================
# Bloque S / E11 (23 Jul 2026) -- conversation-size hygiene.
#
# Real incident that motivated this: a live Telegram conversation grew to
# 263,966 tokens without ever triggering compression, because the existing
# compressor's threshold is computed against the PRIMARY model's context
# window (Gemini, ~1,048,576 tokens) -- comfortably under its ~50% threshold
# even though the request already broke every fallback provider in the
# escalation chain (Groq 128k, OpenRouter 262,144). These tests exercise the
# new absolute, primary-model-independent thresholds
# (ESCALATION_SAFE_TRIGGER_TOKENS / ESCALATION_HARD_CAP_TOKENS) added to
# close that gap.
# ===========================================================================

_TOKENS_PER_CHAR = 0.25  # matches the fake estimator below


def _msg(role: str, tokens: int) -> dict:
    """A synthetic message whose estimated size is exactly ``tokens``."""
    return {"role": role, "content": "x" * int(tokens / _TOKENS_PER_CHAR)}


def _fake_token_estimate(messages, **_kwargs) -> int:
    return sum(int(len(m.get("content") or "") * _TOKENS_PER_CHAR) for m in messages)


class _FakeCompressor:
    """Stand-in for ``ContextCompressor`` sized like the real primary-model
    bug: a huge ``threshold_tokens`` (Gemini-sized), so ``should_compress``
    alone would never fire for a 300k-token conversation."""

    def __init__(self, protect_first_n=2, protect_last_n=20):
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.context_length = 1_048_576
        self.threshold_tokens = 524_288  # 50% of Gemini's real context window
        self.last_prompt_tokens = -1
        self.last_real_prompt_tokens = 0
        self.compression_count = 0

    def should_compress(self, prompt_tokens: int) -> bool:
        return prompt_tokens >= self.threshold_tokens


class _CompressingFakeAgent(_FakeAgent):
    """``_FakeAgent`` plus a working (fake) compression pipeline.

    ``_compress_context`` mimics real compression well enough to test
    control flow: collapse everything outside the protected first/last
    ranges into one small summary message, honoring whatever
    ``context_compressor.protect_last_n`` is set to *at call time* (Bloque
    S.1's hard-cap path temporarily lowers it mid-turn).
    """

    def __init__(self, big_tail_tokens: int = 0):
        super().__init__()
        self.compression_enabled = True
        self.context_compressor = _FakeCompressor()
        self._compress_calls = 0
        self._emitted = []
        self._big_tail_tokens = big_tail_tokens

    def _compress_context(self, messages, system_message, *, approx_tokens=None, task_id=None):
        self._compress_calls += 1
        c = self.context_compressor
        first_n = c.protect_first_n
        last_n = c.protect_last_n
        if len(messages) <= first_n + last_n + 1:
            return messages, system_message  # nothing left to compress
        head = messages[:first_n]
        tail = messages[-last_n:] if last_n else []
        summary = [_msg("user", 500)]  # one small summary of the compressed middle
        return head + summary + tail, system_message

    def _emit_status(self, msg):
        self._emitted.append(msg)


def _build_big_conversation(n_messages: int, tokens_each: int, big_tail_tokens: int = 0) -> list:
    history = [_msg("user" if i % 2 == 0 else "assistant", tokens_each) for i in range(n_messages)]
    if big_tail_tokens:
        # Put the oversized message inside the default protect_last_n=20
        # window so normal compression alone can't shrink it away.
        history[-5] = _msg("assistant", big_tail_tokens)
    return history


def test_escalation_trigger_fires_when_primary_threshold_would_not():
    """A 300k-token conversation must compress even though it is far below
    the primary model's own (huge) compression threshold (524,288)."""
    agent = _CompressingFakeAgent()
    history = _build_big_conversation(n_messages=300, tokens_each=1_000)  # ~300,000 tokens

    with patch("agent.turn_context.estimate_request_tokens_rough", side_effect=_fake_token_estimate), \
         patch("agent.turn_context.estimate_messages_tokens_rough", side_effect=_fake_token_estimate):
        ctx = _build(agent, conversation_history=history)

    assert agent._compress_calls >= 1, "escalation trigger never invoked _compress_context"
    final_tokens = _fake_token_estimate(ctx.messages)
    assert final_tokens < 30_000, (
        f"compressed conversation still ~{final_tokens} tokens -- "
        "escalation trigger should have collapsed it well under 30k"
    )
    # The one-time size notice (S.4) must have fired exactly once.
    notices = [m for m in agent._emitted if "empiezo fresco" not in m and "ya está larga" in m]
    assert len(notices) == 1


def test_escalation_notice_sent_only_once_per_agent():
    agent = _CompressingFakeAgent()
    history = _build_big_conversation(n_messages=300, tokens_each=1_000)

    with patch("agent.turn_context.estimate_request_tokens_rough", side_effect=_fake_token_estimate), \
         patch("agent.turn_context.estimate_messages_tokens_rough", side_effect=_fake_token_estimate):
        _build(agent, conversation_history=history)
        # Second turn in the same (still oversized) conversation.
        history2 = _build_big_conversation(n_messages=300, tokens_each=1_000)
        _build(agent, conversation_history=history2)

    size_notices = [m for m in agent._emitted if "ya está larga" in m]
    assert len(size_notices) == 1, f"size notice should fire once per agent, got {len(size_notices)}"


def test_hard_cap_forces_extra_trim_when_normal_pass_is_not_enough():
    """S.1: a message so large it survives inside the normally-protected
    tail must still get trimmed if the turn is above the 40k hard cap after
    the first compression pass."""
    agent = _CompressingFakeAgent()
    # One message inside the protected last-20 window is 60,000 tokens on
    # its own -- normal compression (which leaves protect_last_n intact)
    # cannot get this turn under the 40k hard cap without the S.1 fallback
    # that temporarily shrinks protect_last_n.
    history = _build_big_conversation(n_messages=300, tokens_each=1_000, big_tail_tokens=60_000)

    with patch("agent.turn_context.estimate_request_tokens_rough", side_effect=_fake_token_estimate), \
         patch("agent.turn_context.estimate_messages_tokens_rough", side_effect=_fake_token_estimate):
        ctx = _build(agent, conversation_history=history)

    final_tokens = _fake_token_estimate(ctx.messages)
    assert final_tokens <= 40_000, (
        f"turn still ~{final_tokens} tokens after the hard-cap pass -- "
        "S.1's protect_last_n fallback did not engage correctly"
    )
    # protect_last_n must be restored to its original value afterwards,
    # regardless of whether the hard-cap path ran.
    assert agent.context_compressor.protect_last_n == 20


def test_short_conversation_never_triggers_compression():
    """Sanity check: normal-sized conversations are untouched -- Bloque S
    must not make the agent compress every turn."""
    agent = _CompressingFakeAgent()
    history = _build_big_conversation(n_messages=10, tokens_each=200)  # ~2,000 tokens

    with patch("agent.turn_context.estimate_request_tokens_rough", side_effect=_fake_token_estimate), \
         patch("agent.turn_context.estimate_messages_tokens_rough", side_effect=_fake_token_estimate):
        _build(agent, conversation_history=history)

    assert agent._compress_calls == 0
    assert agent._emitted == []
