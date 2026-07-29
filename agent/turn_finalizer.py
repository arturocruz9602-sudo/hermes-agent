"""Post-loop turn finalization for ``run_conversation``.

Extracted from ``agent/conversation_loop.py`` as part of the god-file
decomposition campaign (``~/.hermes/plans/god-file-decomposition.md``, Phase 1
step 4 — the post-loop ``TurnFinalizer`` seam). ``run_conversation``'s tail
(everything after the main tool-calling ``while`` loop) is lifted here verbatim:
budget-exhaustion summary, trajectory save, session persist, turn diagnostics,
response transforms, result-dict assembly, steer drain, and the memory/skill
review trigger.

Behavior-neutral: the body is moved unchanged. All ``agent.*`` side effects fire
exactly as before; only the post-loop *locals* are passed in as keyword args, and
the assembled ``result`` dict is returned to ``run_conversation`` which returns it
to the caller. The function is synchronous with a single return — mirroring the
region it replaces (no awaits, no early returns).

Module ``logger`` is imported lazily inside the body (``from
agent.conversation_loop import logger``) so this module never imports
``agent.conversation_loop`` at import time -> no import cycle, and the log records
keep the exact logger name (``"agent.conversation_loop"``).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata

from agent.codex_responses_adapter import _summarize_user_message_for_log
from agent.message_content import flatten_message_text


def _is_pure_tool_call_tail(msg: dict) -> bool:
    """An assistant row with ``tool_calls`` but no visible text content of its own.

    Such a row satisfies the role check (``tail role == "assistant"``) while
    carrying none of the delivered answer — see the #43849/#44100 invariant
    block in :func:`finalize_turn`. Uses :func:`flatten_message_text` so that
    multimodal (list-type) content is evaluated by its text parts, not just
    its type.
    """
    if not msg.get("tool_calls"):
        return False
    return not flatten_message_text(msg.get("content")).strip()


# Verification continuation scaffolding flags: verify-on-stop / pre_verify
# inject a synthetic user nudge to keep the agent going one more turn.
# These nudges must be stripped from returned/live history to avoid
# role-alternation breaks and poisoning the resumed transcript. The
# assistant response is real content and is not flagged. (#65919 §7)
_VERIFICATION_CONTINUATION_FLAGS = (
    "_verification_stop_synthetic",
    "_pre_verify_synthetic",
)


def _drop_verification_continuation_scaffolding(messages) -> None:
    """Remove verification-continuation nudge messages from *messages* in place.

    Only the synthetic nudges carry these flags, so this strips just the
    nudges while preserving the real attempted-final-answer that was
    persisted to state.db.
    """
    messages[:] = [
        m for m in messages
        if not (isinstance(m, dict) and any(m.get(f) for f in _VERIFICATION_CONTINUATION_FLAGS))
    ]


# ---------------------------------------------------------------------------
# Deterministic no-fabrication backstop (HAS Tarea 1 mitigation, 18 Jul 2026).
#
# A system-prompt-only instruction ("never claim an action completed without
# a real tool call") was tried first and found to be a soft nudge, not a
# guarantee: verified via real conversation transcripts that a small/cheap
# model (Gemini 2.5 Flash Lite) can still narrate "Hecho, ya lo cree" /
# "He registrado tu color favorito" with zero tool_calls in the turn, even
# with that instruction present. This backstop makes the guarantee at the
# framework level instead of the model level: if the final response text
# reads like a completion claim for a create/save/move/send-type action,
# and no tool call in THIS turn actually succeeded, the response is replaced
# before it ever reaches the user.
#
# Turn-boundary detection mirrors the existing pattern just above (last_reasoning
# extraction): walk ``messages`` backwards and stop at the last ``role == "user"``
# message -- everything after that boundary belongs to the current turn.
#
# Deliberately scoped to "was ANY tool call successful this turn", not an
# allowlist of specific tool names -- an allowlist would need to be kept in
# sync with every new tool the framework or a plugin adds. Every real
# fabrication case observed so far involved zero tool calls of any kind in
# the turn, so this is the precise, proportionate gate for the failure mode
# actually seen (not a claim that it detects 100% of possible phrasings --
# pattern matching on natural language never does).
_ACTION_VERB_STEMS = (
    r"cre|guard|mov|envi|actualiz|elimin|borr|program|agend|registr"
)
_FABRICATED_SUCCESS_RE = re.compile(
    rf"\b(?:he|ya)\b[^.!?\n]{{0,15}}\b(?:{_ACTION_VERB_STEMS})\w*"
    r"|\b(?:created|saved|moved|sent|updated|deleted|scheduled)\b",
    re.IGNORECASE,
)

_NO_FABRICATION_FALLBACK = (
    "⚠️ No puedo confirmar que esa acción se haya completado — no hubo una "
    "llamada real a una herramienta en este turno. Intenta de nuevo siendo "
    "más específico, o dime qué falta para poder hacerlo."
)

# Bloque O.6.1 (27 Jul 2026): post-validacion contra la evidencia real
# inyectada por run_incident_verification() (Bloque O.6,
# agent/complexity_detector.py). Hallazgo real en vivo: incluso con la
# inyeccion llegando correctamente al prompt (confirmado con
# instrumentacion), el modelo puede ignorarla por completo -- llamar su
# propia herramienta sin relacion y afirmar despues "no mostro errores"
# citando un "analisis anterior" no verificable, pese a que la
# evidencia real de ESTE turno decia hay_evidencia_real=true con lineas
# reales de fallo. Es el riesgo que reporte_bloque_o_22jul.md dejo
# pendiente explicitamente: "post-validar la respuesta contra la
# evidencia real, no solo inyectar y confiar en que se use". Backstop
# mecanico y deliberadamente estrecho (mismo espiritu que
# _FABRICATED_SUCCESS_RE): solo dispara cuando SABEMOS que hubo
# evidencia real este turno Y la respuesta la niega explicitamente --
# no intenta validar cada afirmacion del modelo, eso queda fuera de
# alcance.
_O6_EVIDENCE_DENIAL_RE = re.compile(
    r"no\s+(mostr\w*|encontr\w*|hab[ií]a|hay|existe\w*|indic\w*)\s+"
    r"(ning[uú]n\w*\s+)?(error\w*|evidencia\w*|problema\w*|incidente\w*|fall\w*)",
    re.IGNORECASE,
)


def _strip_accents_for_match(text: str) -> str:
    """Normalize accents away so _FABRICATED_SUCCESS_RE doesn't need to
    enumerate every accented conjugation (creé, envié, actualicé, etc.)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


_CODE_FENCE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)


def _strip_code_blocks_for_fabrication_check(text: str) -> str:
    """Remove fenced code blocks before scanning for a fabricated-success
    claim (Bloque O.0, 22 Jul 2026 -- real false positive found in
    production: a code EXAMPLE Gemini wrote contained the English comment
    ``# print(f"Cache updated for '{clave}'")`` inside a normal, correct
    explanation of a real bug -- the word "updated" inside that code
    comment matched _FABRICATED_SUCCESS_RE and replaced a perfectly good
    answer with the no-fabrication fallback. Code examples routinely
    contain words like created/saved/updated/deleted in comments,
    variable names, or print statements without the ASSISTANT claiming
    to have done anything -- only the assistant's own prose (outside
    code fences) is a meaningful signal here."""
    return _CODE_FENCE_BLOCK_RE.sub(" ", text)


def _turn_has_successful_tool_call(
    messages: list, turn_boundary_idx: "int | None" = None
) -> bool:
    """True if a non-error tool result exists in the CURRENT turn.

    Walks ``messages`` backwards from the end and stops at the last
    ``role == "user"`` message (turn boundary) -- same technique used a few
    lines below for last_reasoning extraction.

    Bloque AF (24 Jul 2026 -- Bloque AE diagnosis, HAS L13): the plain
    "stop at the last role==user" boundary is structurally correct on its
    own, but real production evidence (session 20260723_014401_467841eb,
    turn 16560->16561) showed the boundary can land past several
    consecutive UNANSWERED user messages that ``repair_message_sequence``
    merges together (a crash-orphaned request sitting unanswered for
    >1h, then a new trivial message arriving later). In that shape, a
    stale-but-structurally-present tool result from an EARLIER,
    unrelated turn can still sit inside the scanned window.

    ``turn_boundary_idx``, when provided, is the SAME index
    ``conversation_loop.py`` already tracks as ``current_turn_user_idx``
    -- relocated by object identity after
    ``repair_message_sequence_with_cursor()`` (Bloque Q.1 fix) -- so it
    reflects the true position of THIS turn's user message post-repair,
    not just "whatever role==user happens to be nearest the end". When
    valid (``0 <= turn_boundary_idx < len(messages)``), the scan is
    bounded to strictly after that index instead of free-scanning
    backward for any role==user. Falls back to the original unbounded
    scan when the index is absent or was invalidated (-1, e.g. the
    turn's own message got merged away during repair) -- some check is
    better than none, and the unbounded scan is still correct in the
    common case where there's no unanswered backlog to conflate with.
    """
    if turn_boundary_idx is not None and 0 <= turn_boundary_idx < len(messages):
        _start = turn_boundary_idx
    else:
        _start = -1
    for i in range(len(messages) - 1, _start, -1):
        msg = messages[i]
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "user":
            break
        if msg.get("role") == "tool":
            content = msg.get("content")
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    parsed = None
                if isinstance(parsed, dict) and "error" in parsed:
                    continue  # this specific tool call failed -- keep scanning
                return True
            elif content is not None:
                return True  # non-string (e.g. multimodal) content -- treat as success
    return False


def finalize_turn(
    agent,
    *,
    final_response,
    api_call_count,
    interrupted,
    failed,
    messages,
    conversation_history,
    effective_task_id,
    turn_id,
    user_message,
    original_user_message,
    _should_review_memory,
    _turn_exit_reason,
    _pending_verification_response=None,
    _pending_verification_response_previewed=False,
    current_turn_user_idx=None,
):
    """Run the post-loop finalization and return the turn ``result`` dict.

    Lifted verbatim from ``run_conversation`` (the region after the main agent
    loop). See module docstring.
    """
    from agent.conversation_loop import logger

    budget_exhausted = (
        api_call_count >= agent.max_iterations
        or agent.iteration_budget.remaining <= 0
    )
    budget_fallback_eligible = (
        budget_exhausted
        and not interrupted
        and not failed
        and str(_turn_exit_reason) in {"unknown", "budget_exhausted"}
    )
    continuation_budget_exhausted = (
        final_response is None
        and bool(_pending_verification_response)
        and budget_fallback_eligible
    )

    iteration_limit_fallback = False
    preserved_verification_fallback = False
    if continuation_budget_exhausted:
        # A verification/continuation gate deliberately withheld a composed
        # answer, then consumed the remaining budget before producing a newer
        # one. Preserve that exact answer instead of replacing it with another
        # fallible model call. The explicit pending value is the provenance
        # guard: unrelated error/recovery exits can never enter this branch.
        final_response = _pending_verification_response
        # Mark the turn as previewed only when the reused candidate was
        # actually streamed to the user as interim content. (#65919 review:
        # response-loss blocker)
        if _pending_verification_response_previewed:
            agent._response_was_previewed = True
        _turn_exit_reason = f"max_iterations_reached({api_call_count}/{agent.max_iterations})"
        iteration_limit_fallback = True
        preserved_verification_fallback = True
    elif final_response is None and budget_fallback_eligible:
        # Budget exhausted — ask the model for a summary via one extra
        # API call with tools stripped.  _handle_max_iterations injects a
        # user message and makes a single toolless request.
        _turn_exit_reason = f"max_iterations_reached({api_call_count}/{agent.max_iterations})"
        agent._emit_status(
            f"⚠️ Iteration budget exhausted ({api_call_count}/{agent.max_iterations}) "
            "— asking model to summarise"
        )
        if not agent.quiet_mode:
            agent._safe_print(
                f"\n⚠️  Iteration budget exhausted ({api_call_count}/{agent.max_iterations}) "
                "— requesting summary..."
            )
        final_response = agent._handle_max_iterations(messages, api_call_count)
        iteration_limit_fallback = True

    if iteration_limit_fallback:
        # If running as a kanban worker, signal the dispatcher that the
        # worker could not complete (rather than treating it as a
        # protocol violation). This applies whether the user-facing fallback
        # came from the summary call or an explicitly pending continuation;
        # both exhausted the task budget and must advance the failure circuit.
        #
        # We route through ``_record_task_failure(outcome="timed_out")``
        # rather than ``kanban_block`` so this counts toward the dispatcher's
        # consecutive-failure circuit breaker (#29747 gap 2).
        _kanban_task = os.environ.get("HERMES_KANBAN_TASK")
        if _kanban_task:
            try:
                from hermes_cli import kanban_db as _kb
                _conn = _kb.connect()
                try:
                    _kb._record_task_failure(
                        _conn,
                        _kanban_task,
                        error=(
                            f"Iteration budget exhausted "
                            f"({api_call_count}/{agent.max_iterations}) — "
                            "task could not complete within the allowed "
                            "iterations"
                        ),
                        outcome="timed_out",
                        release_claim=True,
                        end_run=True,
                        event_payload_extra={
                            "budget_used": api_call_count,
                            "budget_max": agent.max_iterations,
                        },
                    )
                    logger.info(
                        "recorded budget-exhausted failure for task %s (%d/%d)",
                        _kanban_task, api_call_count, agent.max_iterations,
                    )
                finally:
                    try:
                        _conn.close()
                    except Exception:
                        pass
            except Exception:
                logger.warning(
                    "Failed to record budget-exhausted failure for task %s",
                    _kanban_task,
                    exc_info=True,
                )

    # Determine if conversation completed successfully
    normal_text_response = str(_turn_exit_reason).startswith("text_response(")
    completed = (
        final_response is not None
        and not failed
        and (
            api_call_count < agent.max_iterations
            or normal_text_response
        )
    )

    # Preflight can seed the display count before the provider receives the
    # request. Roll that estimate back only when an interrupt wins the race
    # before any successful provider response. Compaction state remains owned
    # by the real-usage/post-compaction path, including its ``-1`` sentinel.
    # Guard rules (test-double density on this path is high):
    #  - snapshot is type-pinned to a real int — MagicMock agents auto-create
    #    truthy Mock attributes that must never arm the rollback;
    #  - the received-response flag is pinned to ``is not True`` — its real
    #    domain is True/False, and only a literal True means a provider
    #    response completed;
    #  - the compressor method gets a getattr+callable guard — SimpleNamespace
    #    compressor doubles and plugin context engines lack it.
    _preflight_snapshot = getattr(
        agent, "_turn_preflight_display_snapshot", None
    )
    if (
        interrupted is True
        and isinstance(_preflight_snapshot, int)
        and not isinstance(_preflight_snapshot, bool)
        and getattr(agent, "_turn_received_provider_response", False) is not True
        and getattr(agent, "context_compressor", None) is not None
    ):
        _rollback_fn = getattr(
            agent.context_compressor,
            "rollback_interrupted_preflight_display_tokens",
            None,
        )
        if callable(_rollback_fn):
            _rollback_fn(_preflight_snapshot)

    # Post-loop cleanup must never lose the response.  Trajectory save,
    # resource teardown, and session persistence all touch fallible
    # surfaces — file I/O / JSON serialization (_save_trajectory), remote
    # VM/browser teardown over the network (_cleanup_task_resources), and
    # SQLite writes (_persist_session).  A raise from any of them used to
    # propagate straight out of run_conversation, discarding the partial
    # final_response the caller is waiting for (subprocess wrappers saw an
    # empty stdout with no traceback — #8049).  Each step is now guarded
    # independently so one failure can't skip the others, and any errors
    # are surfaced on the result dict via ``cleanup_errors`` rather than
    # killing the turn.
    _cleanup_errors = []

    # Save trajectory if enabled.  ``user_message`` may be a multimodal
    # list of parts; the trajectory format wants a plain string.
    try:
        agent._save_trajectory(messages, _summarize_user_message_for_log(user_message), completed)
    except Exception as _save_err:
        _cleanup_errors.append(f"save_trajectory: {_save_err}")
        logger.error("finalize_turn: _save_trajectory failed: %s", _save_err, exc_info=True)

    # Clean up VM and browser for this task after conversation completes
    try:
        agent._cleanup_task_resources(effective_task_id)
    except Exception as _cleanup_err:
        _cleanup_errors.append(f"cleanup_task_resources: {_cleanup_err}")
        logger.error("finalize_turn: _cleanup_task_resources failed: %s", _cleanup_err, exc_info=True)

    # Drop private retry scaffolding early (unrelated to final_response
    # content -- internal empty-response-retry housekeeping). Otherwise a
    # later user "continue" turn can replay assistant("(empty)") / recovery
    # nudges and fall into the same empty-response loop again. The actual
    # session PERSIST is deferred past the response-correction chain below
    # (Bloque AF, 24 Jul 2026 -- see the comment at that call site for why).
    try:
        agent._drop_trailing_empty_response_scaffolding(messages)

        # Drop verification-continuation nudges (synthetic user messages)
        # from the live history before the tail-assistant check — only the
        # nudges need stripping; the assistant candidate persists in
        # state.db. (#65919 §7)
        _drop_verification_continuation_scaffolding(messages)

        # Some recovery/fallback paths return a real final_response without
        # adding a closing assistant message to the transcript (e.g. the
        # partial-stream and prior-turn-content recovery ``break`` sites in
        # ``conversation_loop``). If persisted as-is, the durable session can
        # end at a tool/user message even though the caller — and the gateway
        # platform — already saw a completed assistant response. The next turn
        # then replays a user-only backlog and the model re-answers every
        # "unanswered" message. Close the durable turn at the source, at the
        # single chokepoint every recovery ``break`` flows through, so the
        # invariant "delivered final_response ⇒ assistant row in transcript"
        # holds regardless of which path produced it. (#43849 / #44100)
        #
        # Compare content (not just role) so a verification candidate that
        # matches the final response is not duplicated at budget
        # exhaustion. (#65919 §7)
        if final_response and not interrupted:
            try:
                _tail = messages[-1] if messages else None
            except Exception:
                _tail = None
            _tail_role = _tail.get("role") if isinstance(_tail, dict) else None
            if _tail_role != "assistant":
                # Tail is not an assistant row — append the final response
                # so the durable turn closes with the answer (#43849/#44100).
                messages.append({"role": "assistant", "content": final_response})
            elif isinstance(_tail, dict) and _tail.get("content") != final_response and _is_pure_tool_call_tail(_tail):
                # The tail IS an assistant row, but a *pure tool-call turn*:
                # tool_calls with no text of its own. The role check alone
                # leaves the #43849/#44100 invariant unmet — the user saw a
                # response that never reached the transcript, and the next turn
                # replays the user backlog and re-answers it (the very symptom
                # this block was added for). Fill that row's empty content
                # instead of appending, so the durable turn ends with the answer
                # without disturbing the tool-call structure or creating an
                # assistant→assistant pair.
                #
                # The ``content != final_response`` guard prevents filling when
                # the tail already carries the final response text (verification
                # candidate collapse — the provisional answer was persisted and
                # reused as the terminal response, #65919 §7).
                _tail["content"] = final_response
                # The row may have already been flushed to SQLite by the
                # incremental tool-call persist (conversation_loop.py:4990),
                # which stamps ``_DB_PERSISTED_MARKER`` so subsequent flushes
                # skip it. Pop the marker so the next ``_persist_session``
                # re-writes the filled content to the durable store —
                # otherwise ``/resume`` reloads ``content=""`` and the bug
                # resurfaces cross-session.
                _tail.pop("_db_persisted", None)
    except Exception as _scaffold_err:
        _cleanup_errors.append(f"drop_trailing_empty_response_scaffolding: {_scaffold_err}")
        logger.error(
            "finalize_turn: _drop_trailing_empty_response_scaffolding failed: %s",
            _scaffold_err, exc_info=True,
        )

    # ── Turn-exit diagnostic log ─────────────────────────────────────
    # Always logged at INFO so agent.log captures WHY every turn ended.
    # When the last message is a tool result (agent was mid-work), log
    # at WARNING — this is the "just stops" scenario users report.
    _last_msg_role = messages[-1].get("role") if messages else None
    _last_tool_name = None
    if _last_msg_role == "tool":
        # Walk back to find the assistant message with the tool call
        for _m in reversed(messages):
            if _m.get("role") == "assistant" and _m.get("tool_calls"):
                _tcs = _m["tool_calls"]
                if _tcs and isinstance(_tcs[0], dict):
                    _last_tool_name = _tcs[-1].get("function", {}).get("name")
                break

    _turn_tool_count = sum(
        1 for m in messages
        if isinstance(m, dict) and m.get("role") == "assistant" and m.get("tool_calls")
    )
    _resp_len = len(final_response) if final_response else 0
    _budget_used = agent.iteration_budget.used if agent.iteration_budget else 0
    _budget_max = agent.iteration_budget.max_total if agent.iteration_budget else 0

    _diag_msg = (
        "Turn ended: reason=%s model=%s api_calls=%d/%d budget=%d/%d "
        "tool_turns=%d last_msg_role=%s response_len=%d session=%s"
    )
    _diag_args = (
        _turn_exit_reason, agent.model, api_call_count, agent.max_iterations,
        _budget_used, _budget_max,
        _turn_tool_count, _last_msg_role, _resp_len,
        agent.session_id or "none",
    )

    if _last_msg_role == "tool" and not interrupted:
        # Agent was mid-work — this is the "just stops" case.
        logger.warning(
            "Turn ended with pending tool result (agent may appear stuck). "
            + _diag_msg + " last_tool=%s",
            *_diag_args, _last_tool_name,
        )
    else:
        logger.info(_diag_msg, *_diag_args)

    # File-mutation verifier footer.
    # If one or more ``write_file`` / ``patch`` calls failed during this
    # turn and were never superseded by a successful write to the same
    # path, append an advisory footer to the assistant response.  This
    # catches the specific case — reported by Ben Eng (#15524-adjacent)
    # — where a model issues a batch of parallel patches, half of them
    # fail with "Could not find old_string", and the model summarises
    # the turn claiming every file was edited.  The user then has to
    # manually run ``git status`` to catch the lie.  With this footer
    # the truth is surfaced on every turn, so over-claiming is
    # structurally impossible past the model.
    #
    # Gate: only applied when a real text response exists for this
    # turn and the user didn't interrupt.  Empty/interrupted turns
    # already have other surface text that shouldn't be augmented.
    if final_response and not interrupted:
        try:
            _failed = getattr(agent, "_turn_failed_file_mutations", None) or {}
            if _failed and agent._file_mutation_verifier_enabled():
                footer = agent._format_file_mutation_failure_footer(_failed)
                if footer:
                    final_response = final_response.rstrip() + "\n\n" + footer
        except Exception as _ver_err:
            logger.debug("file-mutation verifier footer failed: %s", _ver_err)

    # Turn-completion explainer.
    # When a turn ends abnormally after substantive work — empty content
    # after retries, a partial/truncated stream, a still-pending tool
    # result, or an iteration/budget limit — the user otherwise gets a
    # blank or fragmentary response box with no consolidated reason why
    # the agent stopped (#34452).  Surface a single user-visible
    # explanation derived from ``_turn_exit_reason``, mirroring the
    # file-mutation verifier footer pattern above.
    #
    # Gate carefully so healthy turns stay quiet:
    #   - ``text_response(...)`` exits never produce an explanation
    #     (handled inside the formatter), so a terse ``Done.`` is silent.
    #   - We only ACT when there is no genuinely usable reply this turn:
    #     an empty response, the "(empty)" terminal sentinel, or a
    #     suspiciously short partial fragment with no terminating
    #     punctuation (e.g. "The").  A real short answer keeps its text.
    if not interrupted:
        try:
            if agent._turn_completion_explainer_enabled():
                _stripped = (final_response or "").strip()
                _is_empty_terminal = _stripped == "" or _stripped == "(empty)"
                # A short fragment that is not a normal text_response exit
                # and lacks sentence-ending punctuation is treated as a
                # truncated partial (the "The" case from #34452).
                _is_partial_fragment = (
                    not _is_empty_terminal
                    and not preserved_verification_fallback
                    and not str(_turn_exit_reason).startswith("text_response")
                    and len(_stripped) <= 24
                    and _stripped[-1:] not in {".", "!", "?", "。", "！", "？", "`", ")"}
                )
                _is_partial_stream_recovery = (
                    str(_turn_exit_reason) == "partial_stream_recovery"
                )
                if (
                    _is_empty_terminal
                    or _is_partial_fragment
                    or _is_partial_stream_recovery
                ):
                    _explanation = agent._format_turn_completion_explanation(
                        _turn_exit_reason
                    )
                    if _explanation:
                        if _is_empty_terminal:
                            # Replace the bare "(empty)"/blank sentinel with
                            # the actionable explanation.
                            final_response = _explanation
                        else:
                            # Keep the partial fragment, append the reason so
                            # the user sees both what arrived and why it
                            # stopped.
                            final_response = (
                                _stripped + "\n\n" + _explanation
                            )
        except Exception as _exp_err:
            logger.debug("turn-completion explainer failed: %s", _exp_err)

    _response_transformed = False

    # Plugin hook: transform_llm_output
    # Fired once per turn after the tool-calling loop completes.
    # Plugins can transform the LLM's output text before it's returned.
    # First hook to return a string wins; None/empty return leaves text unchanged.
    if final_response and not interrupted:
        try:
            from hermes_cli.plugins import invoke_hook as _invoke_hook
            _transform_results = _invoke_hook(
                "transform_llm_output",
                response_text=final_response,
                session_id=agent.session_id or "",
                model=agent.model,
                platform=getattr(agent, "platform", None) or "",
            )
            for _hook_result in _transform_results:
                if isinstance(_hook_result, str) and _hook_result:
                    final_response = _hook_result
                    _response_transformed = True
                    break  # First non-empty string wins
        except Exception as exc:
            logger.warning("transform_llm_output hook failed: %s", exc)

    # No-fabrication backstop (HAS Tarea 1 mitigation, 18 Jul 2026). Runs
    # after transform_llm_output (so it checks the text plugins actually
    # produced) and before post_llm_call / result assembly (so every
    # downstream consumer -- hooks, session persistence, the platform
    # adapter that delivers to the user -- sees the corrected text, never
    # the original fabricated claim. See module-level comment above
    # _FABRICATED_SUCCESS_RE for why this is framework-level, not a second
    # system-prompt instruction.
    if final_response and not interrupted:
        _no_fab_check_text = _strip_code_blocks_for_fabrication_check(final_response)
        if _FABRICATED_SUCCESS_RE.search(_strip_accents_for_match(_no_fab_check_text)):
            # Bloque AF (24 Jul 2026): bound the scan to THIS turn via the
            # already-repair-relocated current_turn_user_idx (Bloque Q.1)
            # instead of trusting the nearest role==user unconditionally --
            # see _turn_has_successful_tool_call's docstring for the real
            # incident this fixes.
            if not _turn_has_successful_tool_call(messages, current_turn_user_idx):
                logger.warning(
                    "Blocked a fabricated success claim (no successful "
                    "tool_call this turn): %r",
                    final_response[:200],
                )
                final_response = _NO_FABRICATION_FALLBACK

    # Bloque O.6.1 (27 Jul 2026): ver comentario junto a
    # _O6_EVIDENCE_DENIAL_RE arriba. Solo dispara si O.6 SI inyecto
    # evidencia real este turno (agent._te_pre_response_data_summary,
    # poblado en agent/turn_context.py) con hay_evidencia_real=true, y
    # la respuesta final la contradice explicitamente.
    if final_response and not interrupted:
        _o6_summary = getattr(agent, "_te_pre_response_data_summary", None)
        if _o6_summary and '"hay_evidencia_real": true' in _o6_summary:
            if _O6_EVIDENCE_DENIAL_RE.search(_strip_accents_for_match(final_response)):
                logger.warning(
                    "Bloque O.6.1: respuesta contradice evidencia real "
                    "inyectada este turno (hay_evidencia_real=true): %r",
                    final_response[:200],
                )
                final_response = (
                    "⚠️ Iba a decirte que no había evidencia de esto, pero "
                    "SÍ encontré evidencia real este turno -- te la paso tal "
                    "cual, sin interpretar, para no arriesgarme a "
                    "contradecirla:\n\n" + _o6_summary
                )

    # Bloque O.1.2 (29 Jul 2026): cierra el hueco arquitectónico de O.1 vs
    # web_search nativo. O.1 (agent/turn_context.py) solo reconcilia precios
    # contra Brave/CoinGecko que EL PROPIO CÓDIGO inyecta antes del turno --
    # no tiene visibilidad sobre datos que el modelo obtiene por su cuenta
    # llamando a web_search DURANTE el turno. Bug real confirmado
    # (docs/ESTADO.md): ETH $1,917-1,929 vs $1,736.63 real presentados sin
    # aviso, mensaje 15885, conflicto originado en 3 llamadas nativas a
    # web_search, no en la inyección de O.1. Igual que O.6.1: corre
    # POST-respuesta, sobre el texto final real. A diferencia de O.6.1, NO
    # reemplaza la respuesta (no sabemos cuál número específico está mal,
    # solo que hay un conflicto real) -- solo la marca, mismo criterio de
    # >5% que ya usa O.1 para el conflicto Brave-vs-CoinGecko.
    if final_response and not interrupted and current_turn_user_idx is not None:
        try:
            _called_web_search_this_turn = any(
                isinstance(m, dict) and m.get("role") == "tool" and m.get("name") == "web_search"
                for m in messages[current_turn_user_idx:]
            )
            if _called_web_search_this_turn:
                from agent.complexity_detector import (
                    _PRICE_MENTION_RE, fetch_coingecko_prices,
                )

                _real_prices = fetch_coingecko_prices(final_response) or {}
                _mentioned = [
                    float(m.replace(",", "")) for m in _PRICE_MENTION_RE.findall(final_response)
                ]
                for _coin, _real_price in _real_prices.items():
                    if not _real_price:
                        continue
                    _conflicting = [
                        p for p in _mentioned if abs(p - _real_price) / _real_price > 0.05
                    ]
                    if _conflicting:
                        logger.warning(
                            "Bloque O.1.2: respuesta con web_search real menciona "
                            "$%.2f para %s, CoinGecko real dice $%.2f (>5%% diff)",
                            _conflicting[0], _coin, _real_price,
                        )
                        final_response += (
                            f"\n\n⚠️ Posible conflicto de precio: mencioné una cifra "
                            f"que no coincide con el precio real y actual de {_coin} "
                            f"ahora mismo (CoinGecko: ${_real_price:,.2f}) -- puede "
                            f"que haya usado una cifra vieja de la búsqueda."
                        )
        except Exception:
            logger.warning("Bloque O.1.2: fallo el chequeo de conflicto de precios", exc_info=True)

    # Bloque O.4 (22 Jul 2026): enforcement de español. Corre despues del
    # backstop anti-fabricacion (para no re-traducir el mensaje de
    # fallback, que ya esta en español) y antes de Tarea E (para que la
    # autoevaluacion de la respuesta opere sobre el texto final real que
    # se le va a entregar a Arturo).
    if final_response and not interrupted:
        try:
            from agent.complexity_detector import (
                regenerate_in_spanish, response_looks_like_english,
            )

            if response_looks_like_english(final_response):
                logger.warning(
                    "Bloque O.4: respuesta parece estar en ingles, "
                    "regenerando en español: %r", final_response[:150],
                )
                _es_response = regenerate_in_spanish(final_response)
                if _es_response:
                    final_response = _es_response
                else:
                    # Bloque O.4 -- hallazgo real en producción: cuando la
                    # regeneración falla Y el texto original ya se veía
                    # incompleto/roto (cortado a media oración, sin
                    # puntuación final -- señal real de una respuesta
                    # truncada, no solo "en inglés"), mandar el texto
                    # original de todos modos expone razonamiento interno
                    # crudo al usuario (visto en vivo: texto en inglés tipo
                    # "Okay, the user is asking... Let me check...",
                    # cortado a media palabra). Mejor un aviso claro que
                    # texto roto.
                    _looks_truncated = not final_response.rstrip().endswith((".", "!", "?", "```", ":", ")"))
                    if _looks_truncated:
                        logger.warning(
                            "Bloque O.4: regenerate_in_spanish fallo Y la "
                            "respuesta se ve truncada/rota -- se reemplaza "
                            "por un aviso en vez de mandar texto crudo: %r",
                            final_response[:150],
                        )
                        final_response = (
                            "⚠️ Tuve un problema generando una respuesta clara "
                            "para esto. Intenta de nuevo, por favor."
                        )
                    else:
                        logger.warning(
                            "Bloque O.4: regenerate_in_spanish fallo -- se "
                            "manda la respuesta original (posiblemente en "
                            "inglés, pero no se ve truncada)",
                        )
        except Exception:
            logger.warning("Bloque O.4: fallo el enforcement de español", exc_info=True)

    # Bloque T.6 (23 Jul 2026): escáner de secretos en la salida. Corre
    # después del enforcement de español (para escanear el texto REAL que
    # se va a entregar) y antes de Tarea E. Motivo real, no teórico: Hermes
    # ya repitió API keys reales en sus propias respuestas dos veces en
    # este proyecto (4-jul, 20-jul -- ver docs/HISTORIAL.md). Reutiliza el
    # mismo escáner de patrones que ya usan memory_tool.py/skills install
    # (tools/threat_patterns.py), scope="strict" (incluye hardcoded_secret).
    if final_response and not interrupted:
        try:
            from tools.threat_patterns import scan_for_threats

            _secret_findings = [
                f for f in scan_for_threats(final_response, scope="strict")
                if f == "hardcoded_secret"
            ]
            if _secret_findings:
                logger.warning(
                    "Bloque T.6: respuesta bloqueada -- parece contener un "
                    "secreto/credencial real (%s). Texto original NO se "
                    "manda. Primeros 80 chars (para diagnóstico en logs, no "
                    "para el usuario): %r",
                    _secret_findings, final_response[:80],
                )
                final_response = (
                    "⚠️ Bloqueé mi propia respuesta porque parecía contener "
                    "una credencial o secreto real. No se envió. Si esto es "
                    "un falso positivo, dime y lo reviso."
                )
        except Exception:
            logger.warning("Bloque T.6: fallo el escáner de salida", exc_info=True)

    # Persist session to both JSON log and SQLite -- deliberately placed
    # HERE, after every correction pass that can replace `final_response`
    # (transform_llm_output, the no-fabrication backstop, Bloque O.4
    # español, Bloque T.6 secret scanner) and BEFORE post_llm_call/Tarea E
    # (Bloque AF, 24 Jul 2026 -- real bug found and verified live during
    # Bloque AE's diagnosis: `messages[-1]` gets appended with the model's
    # RAW output inside the main loop, before finalize_turn ever runs: if
    # persistence happened at its original position -- right after
    # trajectory save / resource cleanup, near the top of this function --
    # every one of those corrections only ever patched the local
    # `final_response` variable, never `messages[-1]["content"]`. Verified
    # live: a fabricated claim that the anti-fabrication guard correctly
    # blocked (delivery got the safe fallback) still landed in `state.db`
    # with the ORIGINAL fabricated text, because persistence had already
    # run before the guard fired. Same exposure applied to O.4 (English
    # leaking into persisted history) and T.6 (a real secret the scanner
    # blocked from delivery could still end up saved to disk). Moved
    # AFTER those passes, with `messages[-1]` explicitly re-synced to the
    # corrected `final_response` first, closes all three at once.
    #
    # Kept BEFORE post_llm_call/Tarea E on purpose: Tarea E's DeepSeek
    # offer text is deliberately NOT part of persisted history (see that
    # block's own comment -- "lo persistido refleja la respuesta real de
    # Hermes, no esta oferta"). Moving persist any later would silently
    # break that existing, intentional invariant.
    if (
        final_response is not None
        and not interrupted
        and messages
        and isinstance(messages[-1], dict)
        and messages[-1].get("role") == "assistant"
        and not messages[-1].get("tool_calls")
    ):
        # The terminal message IS this turn's text answer -- keep the
        # persisted/in-memory history in sync with whatever correction
        # pass last touched `final_response`. Deliberately narrow: only
        # overwrites when messages[-1] is unambiguously the plain final
        # answer (no tool_calls), so a mid-turn assistant message that
        # happens to be last for some other reason is never clobbered.
        messages[-1]["content"] = final_response

    try:
        # When the turn was interrupted and the last message is a tool
        # result, append a synthetic assistant message to close the
        # tool-call sequence. Without this, the session persists a
        # ``tool → user`` alternation that strict providers (Gemini,
        # Claude) reject, causing them to hallucinate a continuation of
        # the user's message on the next turn (#48879).
        #
        # ``_drop_trailing_empty_response_scaffolding`` (run earlier, near
        # trajectory save) only rewinds the tool tail when an
        # empty-response scaffolding flag is present; a clean ``/stop``
        # interrupt after a successful tool sets no such flag, so the tool
        # result survives as the tail and we close it here instead. On an
        # interrupt ``final_response`` is typically empty, so fall back to
        # an explicit placeholder rather than persisting an empty-content
        # assistant turn.
        if interrupted:
            from agent.message_sanitization import close_interrupted_tool_sequence
            close_interrupted_tool_sequence(messages, final_response)

        # The model has completed its request, so replace API-local
        # voice/model/skill guidance with the clean user input before writing the
        # final durable snapshot and returning the continuation history. Earlier
        # turn-start flushes use the DB-only override because their messages are
        # still needed for the API request; this finalizer runs after that request
        # is complete (#48677 / #63766). Runs here, right before the actual
        # persist below (Bloque AF moved persist past the correction chain).
        _apply_override = getattr(agent, "_apply_persist_user_message_override", None)
        if callable(_apply_override):
            _apply_override(messages)

        agent._persist_session(messages, conversation_history)
    except Exception as _persist_err:
        _cleanup_errors.append(f"persist_session: {_persist_err}")
        logger.error("finalize_turn: _persist_session failed: %s", _persist_err, exc_info=True)

    # Plugin hook: post_llm_call
    # Fired once per turn after the tool-calling loop completes.
    # Plugins can use this to persist conversation data (e.g. sync
    # to an external memory system).
    if final_response and not interrupted:
        try:
            from hermes_cli.plugins import invoke_hook as _invoke_hook
            _invoke_hook(
                "post_llm_call",
                session_id=agent.session_id,
                task_id=effective_task_id,
                turn_id=turn_id,
                user_message=original_user_message,
                assistant_response=final_response,
                conversation_history=list(messages),
                model=agent.model,
                platform=getattr(agent, "platform", None) or "",
            )
        except Exception as exc:
            logger.warning("post_llm_call hook failed: %s", exc)

    # Context engine observation hook: notify the active engine that this
    # turn has finished, with the finalized transcript. Complements the
    # per-request select_context() hook (selection before the request;
    # observation after the turn). No-op default, fail-open.
    try:
        from agent.conversation_loop import _notify_context_engine_turn_complete
        # Forward the turn's canonical usage when the host has it. The loop
        # stashes the most recent API response's usage dict (the same
        # canonical buckets fed to ``update_from_response``) on the agent as
        # ``_last_turn_usage``. It is ``None`` on turns that never reached a
        # provider response (early failure / interrupt), which is exactly the
        # contract: real usage when available, ``None`` otherwise.
        _turn_usage = getattr(agent, "_last_turn_usage", None)
        _notify_context_engine_turn_complete(
            agent,
            messages,
            usage=_turn_usage,
            logger=logger,
            turn_id=turn_id,
            task_id=effective_task_id,
            api_call_count=api_call_count,
            interrupted=interrupted,
            failed=failed,
            turn_exit_reason=_turn_exit_reason,
        )
    except Exception as exc:
        logger.warning("on_turn_complete notification failed: %s", exc)

    # Tarea E (HAS, 19 Jul 2026) -- oferta NO bloqueante de razonamiento
    # profundo (chat-reasoning/deepseek-v4-pro). Corre despues de
    # post_llm_call (lo persistido refleja la respuesta real de Hermes, no
    # esta oferta) y antes de armar `result`. NUNCA bloquea el turno ni
    # decide escalar sola -- ver agent/complexity_detector.py, invariante de
    # seguridad en el docstring del modulo. Cualquier fallo aqui deja
    # final_response intacto (fail-safe: el turno normal nunca se rompe por
    # esto).
    #
    # BUG REAL encontrado y corregido 19 Jul 2026 (root cause, no solo
    # sintoma): la version original de este bloque solo hacia
    # `final_response = final_response + build_offer_text(...)`. Eso
    # funciona en CLI (probado 3/3), pero en el gateway real la respuesta
    # se entrega por STREAMING -- gateway/stream_consumer.py::finish() solo
    # marca el fin de un buffer que YA se envio integro a Telegram delta a
    # delta mientras el LLM generaba texto, antes de que finalize_turn
    # corriera. Modificar final_response aqui llega demasiado tarde para
    # streaming: nunca lo vio ni Telegram ni state.db (confirmado con
    # logging de diagnostico real: offer_category='1_razonamiento' se
    # calculo bien, pero el mensaje persistido no tenia el texto).
    # Fix: usar agent.background_review_callback -- el mismo mecanismo
    # real que el framework ya usa para "Self-improvement review: Memory
    # updated" (agent/background_review.py) -- que manda un mensaje NUEVO
    # y separado via el adapter de la plataforma DESPUES de que la
    # respuesta principal termine de transmitirse (con cola interna para
    # evitar que se entrelace con el streaming en curso). Ese callback es
    # None en CLI (agent_init.py), asi que ahi se mantiene el append
    # directo de siempre como fallback.
    # CAUSA RAIZ REAL encontrada 20 Jul 2026: un turno ya despachado a la
    # fuerza a chat-reasoning/chat-fallback2 (Tarea D o el despacho real de
    # esta misma Tarea E) corre por el loop normal del agente y llega
    # exactamente hasta aqui -- si su propia respuesta contiene señales de
    # complejidad (muy probable: son respuestas de razonamiento profundo),
    # este bloque le registraba una oferta NUEVA para la misma sesion justo
    # despues de resolver la anterior. Eso deja una oferta pendiente viva
    # que un mensaje del usuario completamente distinto, llegando poco
    # despues, puede terminar resolviendo por el simple hecho de ser "el
    # siguiente mensaje" -- sin que haya ningun bug en parse_yes_no ni en
    # el endurecimiento del 19 Jul (ninguno de los dos filtra POR QUE
    # existe la oferta, solo el texto de la respuesta). No tiene sentido
    # ademas ofrecer "mas razonamiento" inmediatamente despues de un turno
    # que ya fue despachado a razonamiento. Se corta aqui, en el origen.
    _te_dispatched_models = {"chat-reasoning", "chat-fallback2"}
    if final_response and not interrupted and agent.model not in _te_dispatched_models:
        try:
            # Bloque O (22 Jul 2026): deroga los criterios (a)/(b)/(c) de
            # Bloque L y el gate de Bloque M como código Python heurístico.
            # self_assess_response() le pide a Gemini que evalúe su PROPIA
            # respuesta (autoevaluación real, no regex) -- should_offer_v2()
            # decide si eso amerita ofrecer DeepSeek.
            from agent.complexity_detector import (
                build_offer_text_v2, offers_today_count, register_offer,
                register_offer_v2, self_assess_response, should_offer,
                should_offer_v2, _OFFER_DAILY_CAP,
            )
            from tools.approval import get_current_session_key

            _te_session_key = get_current_session_key()
            _te_category = "tarea_e_v2"  # ya no hay taxonomia -- una sola categoria fija

            _te_assessment = self_assess_response(
                original_user_message or "", final_response or "",
            )
            _te_wants_offer = should_offer_v2(_te_assessment)
            # Doble anti-spam: el throttle de 30 min ya existente (should_offer)
            # SIGUE aplicando, mas el tope diario nuevo de Bloque O.2.
            _te_offer_category = (
                should_offer(_te_session_key, [_te_category])
                if _te_wants_offer else None
            )
            _te_under_daily_cap = offers_today_count(_te_session_key) < _OFFER_DAILY_CAP

            if _te_offer_category and _te_under_daily_cap:
                # Bloque I (mismo fix que las notificaciones de despacho):
                # InsightsEngine/sessions.actual_cost_usd no reflejaba el
                # gasto real de DeepSeek via el proxy local -- se usa el
                # ledger real que litellm mismo escribe por llamada.
                _te_monthly_spend = 0.0
                try:
                    import sys as _te_sys

                    if "/home/arturo/.hermes/scripts" not in _te_sys.path:
                        _te_sys.path.insert(0, "/home/arturo/.hermes/scripts")
                    from deepseek_cost_ledger import read_month_total as _te_read_ledger

                    _te_monthly_spend = _te_read_ledger("deepseek")
                except Exception:
                    logger.debug(
                        "Tarea E: no se pudo calcular el gasto del mes, "
                        "se ofrece con $0.00", exc_info=True,
                    )

                _te_motivo = (
                    "una decisión con varias variables dependientes entre sí"
                    if _te_assessment.get("multivariable")
                    else "algo que no resolví del todo con confianza"
                )
                _te_offer_text = build_offer_text_v2(
                    motivo=_te_motivo,
                    # Bloque O.1: si la compuerta pre-respuesta ya trajo
                    # datos (Brave/CoinGecko), la oferta los referencia en
                    # vez de repetir un snippet crudo de la propia respuesta.
                    resumen=getattr(agent, "_te_pre_response_data_summary", None),
                    que_me_falto=_te_assessment.get("que_me_falto"),
                    monthly_spend_usd=_te_monthly_spend,
                )

                _te_bg_cb = getattr(agent, "background_review_callback", None)
                if callable(_te_bg_cb):
                    _te_bg_cb(_te_offer_text)
                else:
                    final_response = final_response + "\n\n---\n" + _te_offer_text
                register_offer(
                    _te_session_key, _te_offer_category,
                    original_message=original_user_message or "",
                    context_data="",
                )
                register_offer_v2(_te_session_key)
        except Exception:
            logger.warning(
                "Tarea E: fallo agregando la oferta de razonamiento profundo "
                "(no afecta la respuesta normal)", exc_info=True,
            )

    # Extract reasoning from the CURRENT turn only.  Walk backwards
    # but stop at the user message that started this turn — anything
    # earlier is from a prior turn and must not leak into the reasoning
    # box (confusing stale display; #17055).  Within the current turn
    # we still want the *most recent* non-empty reasoning: many
    # providers (Claude thinking, DeepSeek v4, Codex Responses) emit
    # reasoning on the tool-call step and leave the final-answer step
    # with reasoning=None, so picking only the last assistant would
    # silently drop legitimate same-turn reasoning.
    last_reasoning = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            break  # turn boundary — don't cross into prior turns
        if msg.get("role") == "assistant" and msg.get("reasoning"):
            last_reasoning = msg["reasoning"]
            break

    # Build result with interrupt info if applicable
    result = {
        "final_response": final_response,
        "last_reasoning": last_reasoning,
        "messages": messages,
        "api_calls": api_call_count,
        "completed": completed,
        "turn_exit_reason": _turn_exit_reason,
        "failed": failed,
        "partial": False,  # True only when stopped due to invalid tool calls
        "interrupted": interrupted,
        "response_transformed": _response_transformed,
        "response_previewed": getattr(agent, "_response_was_previewed", False),
        "model": agent.model,
        "provider": agent.provider,
        "base_url": agent.base_url,
        "input_tokens": agent.session_input_tokens,
        "output_tokens": agent.session_output_tokens,
        "cache_read_tokens": agent.session_cache_read_tokens,
        "cache_write_tokens": agent.session_cache_write_tokens,
        "reasoning_tokens": agent.session_reasoning_tokens,
        "prompt_tokens": agent.session_prompt_tokens,
        "completion_tokens": agent.session_completion_tokens,
        "total_tokens": agent.session_total_tokens,
        "last_prompt_tokens": getattr(agent.context_compressor, "last_prompt_tokens", 0) or 0,
        "estimated_cost_usd": agent.session_estimated_cost_usd,
        "cost_status": agent.session_cost_status,
        "cost_source": agent.session_cost_source,
        # Requested service tier (from request_overrides.extra_body), for
        # billing audits by callers like `hermes -z --usage-file`.
        "service_tier": (
            (getattr(agent, "request_overrides", {}) or {}).get("extra_body") or {}
        ).get("service_tier"),
        "session_id": agent.session_id,
    }
    if agent._tool_guardrail_halt_decision is not None:
        result["guardrail"] = agent._tool_guardrail_halt_decision.to_metadata()
    # Surface any post-loop cleanup failures so the caller can distinguish a
    # clean turn from one whose trajectory/session/resource teardown raised
    # (the response is still returned either way — #8049).
    if _cleanup_errors:
        result["cleanup_errors"] = _cleanup_errors
    # If a /steer landed after the final assistant turn (no more tool
    # batches to drain into), hand it back to the caller so it can be
    # delivered as the next user turn instead of being silently lost.
    _leftover_steer = agent._drain_pending_steer()
    if _leftover_steer:
        result["pending_steer"] = _leftover_steer
    agent._response_was_previewed = False

    # Include interrupt message if one triggered the interrupt
    if interrupted and agent._interrupt_message:
        result["interrupt_message"] = agent._interrupt_message

    # Clear interrupt state after handling
    agent.clear_interrupt()

    # Clear stream callback so it doesn't leak into future calls
    agent._stream_callback = None

    # Check skill trigger NOW — based on how many tool iterations THIS turn used.
    _should_review_skills = False
    if (agent._skill_nudge_interval > 0
            and agent._iters_since_skill >= agent._skill_nudge_interval
            and "skill_manage" in agent.valid_tool_names):
        _should_review_skills = True
        agent._iters_since_skill = 0

    # External memory provider: sync the completed turn + queue next prefetch.
    agent._sync_external_memory_for_turn(
        original_user_message=original_user_message,
        final_response=final_response,
        interrupted=interrupted,
        messages=messages,
    )

    # Background memory/skill review — runs AFTER the response is delivered
    # so it never competes with the user's task for model attention.
    if final_response and not interrupted and (_should_review_memory or _should_review_skills):
        try:
            agent._spawn_background_review(
                messages_snapshot=list(messages),
                review_memory=_should_review_memory,
                review_skills=_should_review_skills,
            )
        except Exception:
            pass  # Background review is best-effort

    # Note: Memory provider on_session_end() + shutdown_all() are NOT
    # called here — run_conversation() is called once per user message in
    # multi-turn sessions. Shutting down after every turn would kill the
    # provider before the second message. Actual session-end cleanup is
    # handled by the CLI (atexit / /reset) and gateway (session expiry /
    # _reset_session).

    # Plugin hook: on_session_end
    # Fired at the very end of every run_conversation call.
    # Plugins can use this for cleanup, flushing buffers, etc.
    try:
        from hermes_cli.plugins import invoke_hook as _invoke_hook
        _invoke_hook(
            "on_session_end",
            session_id=agent.session_id,
            task_id=effective_task_id,
            turn_id=turn_id,
            completed=completed,
            interrupted=interrupted,
            model=agent.model,
            platform=getattr(agent, "platform", None) or "",
        )
    except Exception as exc:
        logger.warning("on_session_end hook failed: %s", exc)

    agent._turn_preflight_display_snapshot = None
    agent._turn_received_provider_response = False

    return result
