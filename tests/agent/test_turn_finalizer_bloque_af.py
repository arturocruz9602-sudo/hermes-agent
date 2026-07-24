"""Regression tests for Bloque AF (24 Jul 2026, HAS L13).

Real incident (Bloque AE diagnosis, session 20260723_014401_467841eb,
turn 16560->16561): a trivial test message arrived after 2 real user
messages had gone unanswered for >1h (a crash-orphaned vault-save
request). ``repair_message_sequence`` merges consecutive unanswered
``user`` messages, and a stale-but-structurally-present successful tool
result from that earlier, unrelated vault attempt sat inside the window
``_turn_has_successful_tool_call`` scanned -- so the guard did not block
a fabricated "I saved your password" claim for a message that never
touched the vault.

Separately, live reproduction during Bloque AE found that even when the
guard DOES correctly block a fabrication, ``state.db`` still ended up
with the ORIGINAL fabricated text, because ``_persist_session`` ran
before any of the correction passes (no-fabrication backstop, Bloque O.4
español, Bloque T.6 secret scanner) had a chance to touch
``final_response`` -- and none of them ever wrote back to
``messages[-1]``.

Both are covered here at the unit level (see BLOQUES.md, Bloque AF, for
the live-reproduction evidence).
"""

from agent.turn_finalizer import _turn_has_successful_tool_call, finalize_turn


# ---------------------------------------------------------------------------
# _turn_has_successful_tool_call: recency bound via turn_boundary_idx
# ---------------------------------------------------------------------------

def _messages_with_stale_tool_call_then_backlog():
    """Mirrors the real incident's shape: a real, successful tool call from
    an EARLIER turn, followed by several unanswered ``user`` messages that
    got merged/left adjacent (no assistant reply between them), followed
    by the new trivial message that triggers this turn."""
    return [
        {"role": "user", "content": "Hermes guarda mi contraseña de Cisco"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "function": {"name": "vault", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": '{"success": true, "message": "Guardado"}'},
        {"role": "assistant", "content": "Listo, guardada."},
        # Unanswered backlog (crash-orphaned): no assistant reply between these.
        {"role": "user", "content": "Te corrijo, la contraseña es MOTO"},
        {"role": "user", "content": "hola, esto es una prueba del arnes interno"},
    ]


def test_unbounded_scan_finds_stale_tool_call_old_behavior():
    """Without a boundary index, the free scan stops at the nearest
    role==user (the backlog's first message) -- correctly, since nothing
    is between it and the end. This confirms the plain boundary scan
    alone was never the bug; documented here as the baseline."""
    messages = _messages_with_stale_tool_call_then_backlog()
    assert _turn_has_successful_tool_call(messages) is False


def test_bounded_scan_uses_relocated_turn_boundary_idx():
    """When repair merges the backlog into ONE user message (real
    repair_message_sequence behavior), the stale tool call can end up
    inside the scanned window if the boundary index is wrong. This test
    forces that exact shape and confirms turn_boundary_idx correctly
    excludes the stale tool call by bounding the scan to strictly after
    the real turn-start index."""
    messages = [
        {"role": "user", "content": "Hermes guarda mi contraseña de Cisco"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "function": {"name": "vault", "arguments": "{}"}}],
        },
        # Stale tool result from an earlier, unrelated turn -- sits AFTER
        # the merged backlog user message would structurally land if the
        # merge collapsed everything into a single trailing user turn but
        # the tool result was never dropped (the exact ambiguity found in
        # production forensics).
        {"role": "tool", "tool_call_id": "c1", "content": '{"success": true, "message": "Guardado"}'},
        {
            "role": "user",
            "content": (
                "Te corrijo, la contraseña es MOTO\n\n"
                "hola, esto es una prueba del arnes interno"
            ),
        },
    ]
    # current_turn_user_idx (Bloque Q.1's relocated-by-identity index)
    # correctly points at the merged user message, index 3.
    turn_boundary_idx = 3
    # Sanity: the OLD unbounded scan would stop at THIS SAME user message
    # too (it's the nearest role==user), so in this exact shape both
    # would agree -- the bounded version's value is when the boundary
    # index and the "nearest user" heuristic diverge, which is exercised
    # by the next test.
    assert _turn_has_successful_tool_call(messages, turn_boundary_idx) is False


def test_bounded_scan_excludes_tool_call_before_a_merged_index_mismatch():
    """Construct the divergence directly: the nearest-role==user heuristic
    and the true (relocated) turn boundary disagree because an orphan
    user message sits between the stale tool call and the real new
    message, WITHOUT the merge having actually collapsed it (e.g. repair
    ran in a different order, or a non-text content blocked the merge).
    Bounding by turn_boundary_idx must still land on the correct message
    and must NOT let the stale tool call count."""
    messages = [
        {"role": "user", "content": "Hermes guarda mi contraseña de Cisco"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "function": {"name": "vault", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": '{"success": true, "message": "Guardado"}'},
        {"role": "assistant", "content": "Listo, guardada."},
        {"role": "user", "content": "hola, esto es una prueba del arnes interno"},
    ]
    turn_boundary_idx = 4  # the real new user message, correctly relocated
    assert _turn_has_successful_tool_call(messages, turn_boundary_idx) is False
    # Old unbounded behavior agrees here too (nearest user == index 4) --
    # this test exists to pin the bounded call's correctness on its own,
    # independent of whether the unbounded heuristic happens to agree.
    assert _turn_has_successful_tool_call(messages) is False


def test_invalid_boundary_index_falls_back_to_unbounded_scan():
    """current_turn_user_idx can be -1 (Bloque Q.1's documented fallback
    when the turn's own message got merged away). The function must not
    crash and must fall back to the original behavior."""
    messages = [
        {"role": "user", "content": "hola"},
        {"role": "tool", "tool_call_id": "c1", "content": '{"success": true}'},
    ]
    # role=="tool" is NOT preceded by role=="user" going backward from the
    # end in this tiny fixture (index 1 is tool, index 0 is user) -- with
    # an invalid boundary (-1) the scan must behave exactly as the
    # original unbounded version: find the tool result before hitting the
    # user message.
    assert _turn_has_successful_tool_call(messages, -1) is True
    assert _turn_has_successful_tool_call(messages, None) is True
    assert _turn_has_successful_tool_call(messages, 99) is True  # out of range -> fallback


# ---------------------------------------------------------------------------
# finalize_turn: messages[-1] stays in sync with corrected final_response
# ---------------------------------------------------------------------------

class _StubBudget:
    used = 1
    max_total = 90
    remaining = 89


class _StubCompressor:
    last_prompt_tokens = 0


class _StubAgent:
    def __init__(self):
        self.max_iterations = 90
        self.iteration_budget = _StubBudget()
        self.context_compressor = _StubCompressor()
        self.model = "stub/model"
        self.provider = "stub"
        self.base_url = "http://stub"
        self.session_id = "sess-1"
        self.quiet_mode = True
        self.platform = "cli"
        self._interrupt_requested = False
        self._interrupt_message = None
        self._tool_guardrail_halt_decision = None
        self._response_was_previewed = False
        self._skill_nudge_interval = 0
        self._iters_since_skill = 0
        for attr in (
            "session_input_tokens", "session_output_tokens",
            "session_cache_read_tokens", "session_cache_write_tokens",
            "session_reasoning_tokens", "session_prompt_tokens",
            "session_completion_tokens", "session_total_tokens",
            "session_estimated_cost_usd",
        ):
            setattr(self, attr, 0)
        self.session_cost_status = "ok"
        self.session_cost_source = "stub"
        self.persisted_messages = None

    def _save_trajectory(self, *a, **k):
        pass

    def _cleanup_task_resources(self, *a, **k):
        pass

    def _drop_trailing_empty_response_scaffolding(self, *a, **k):
        pass

    def _persist_session(self, messages, conversation_history):
        # Snapshot at the moment of persistence -- this is what would
        # actually land in state.db.
        self.persisted_messages = [dict(m) for m in messages]

    def _emit_status(self, *a, **k):
        pass

    def _safe_print(self, *a, **k):
        pass

    def _file_mutation_verifier_enabled(self):
        return False

    def _turn_completion_explainer_enabled(self):
        return False

    def _drain_pending_steer(self):
        return None

    def clear_interrupt(self):
        pass

    def _sync_external_memory_for_turn(self, **k):
        pass


def _finalize(agent, messages, *, final_response, current_turn_user_idx=None):
    return finalize_turn(
        agent,
        final_response=final_response,
        api_call_count=1,
        interrupted=False,
        failed=False,
        messages=messages,
        conversation_history=None,
        effective_task_id="task-1",
        turn_id="turn-1",
        user_message="hola",
        original_user_message="hola",
        _should_review_memory=False,
        _turn_exit_reason="text_response(finish_reason=stop)",
        current_turn_user_idx=current_turn_user_idx,
    )


def test_blocked_fabrication_is_also_corrected_in_persisted_messages():
    """The core Bloque AF fix: when the no-fabrication guard blocks a
    claim, the corrected text must ALSO land in messages[-1] (and
    therefore in whatever _persist_session receives), not just in the
    returned final_response."""
    messages = [
        {"role": "user", "content": "hola, esto es una prueba"},
        {"role": "assistant", "content": "He guardado tu contraseña MOTO para Cisco."},
    ]
    turn_boundary_idx = 0  # the real new user message; nothing after it but the reply
    result = _finalize(
        agent := _StubAgent(),
        messages,
        final_response="He guardado tu contraseña MOTO para Cisco.",
        current_turn_user_idx=turn_boundary_idx,
    )
    assert "No puedo confirmar" in result["final_response"]
    # The in-memory messages list (and therefore what got persisted) must
    # match the CORRECTED text, not the original fabricated claim.
    assert messages[-1]["content"] == result["final_response"]
    assert agent.persisted_messages[-1]["content"] == result["final_response"]
    assert "MOTO" not in agent.persisted_messages[-1]["content"]


def test_non_fabricated_response_persists_unchanged():
    """Control: a normal response with no correction triggered persists
    exactly as generated."""
    messages = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "Hola, jefe. Todo bien por aquí."},
    ]
    agent = _StubAgent()
    result = _finalize(agent, messages, final_response="Hola, jefe. Todo bien por aquí.")
    assert result["final_response"] == "Hola, jefe. Todo bien por aquí."
    assert agent.persisted_messages[-1]["content"] == "Hola, jefe. Todo bien por aquí."


def test_sync_does_not_touch_tool_call_bearing_last_message_with_real_text():
    """Guard rail: if messages[-1] is an assistant message WITH
    tool_calls AND its own non-empty text (a mid-turn step, not the final
    answer), the sync must never overwrite it -- only a plain final-answer
    message qualifies."""
    messages = [
        {"role": "user", "content": "haz algo"},
        {
            "role": "assistant",
            "content": "voy a revisar eso",
            "tool_calls": [{"id": "c1", "function": {"name": "noop", "arguments": "{}"}}],
        },
    ]
    agent = _StubAgent()
    _finalize(agent, messages, final_response="texto que no debería aterrizar aqui")
    assert messages[-1]["content"] == "voy a revisar eso"
    assert messages[-1]["tool_calls"]


def test_sync_fills_empty_pure_tool_call_tail():
    """Reconciled with upstream's own #43849/#44100 fix (56ac96976,
    71157cbf6 -- landed 18/19 Jul 2026 upstream, merged into this fork by
    the 0.19.x rebase that also carries Bloque AF): a tail assistant row
    with tool_calls but NO text of its own is a *pure tool-call turn* --
    the delivered final_response never reaches the transcript otherwise,
    and the next turn re-answers the backlog. This is intentionally the
    opposite of the guard above, which only protects a tail that already
    carries its own real text."""
    messages = [
        {"role": "user", "content": "haz algo"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "function": {"name": "noop", "arguments": "{}"}}],
        },
    ]
    agent = _StubAgent()
    _finalize(agent, messages, final_response="texto que sí debería aterrizar aqui")
    assert messages[-1]["content"] == "texto que sí debería aterrizar aqui"
    assert messages[-1]["tool_calls"]
