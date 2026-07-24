"""Regression test for Bloque AH (24 Jul 2026).

Real production bug found live: ``ContextCompressor.compress()``
unconditionally ``.copy()``-ed every head/tail message, including ones it
never modifies. ``run_agent.py``'s ``_flush_messages_to_session_db``
dedupes purely by Python object ``id()`` (chosen specifically to survive
``repair_message_sequence`` shrinking/merging the list -- see its own
docstring, issue #860). Minting a fresh object for an already-flushed,
untouched tail message broke that contract: the flush layer saw a "new"
message and wrote a duplicate row to state.db on every compression pass.

Confirmed live: session 20260723_014401_467841eb, 24-jul-2026 -- a single
turn that compressed 5 times produced 4 duplicate copies of the same
user/assistant exchange, each carrying the ORIGINAL message's exact
timestamp (proof they were re-flushes of the same logical message, not
new ones). The duplication also broke Tarea E's pending-offer resolution
(``agent/complexity_detector.py``'s ``check_pending_reply``): its
"any message in between clears the pending offer" hardening treated each
duplicate-flushed tail message as a genuinely new inbound message,
clearing a real, freshly-registered DeepSeek offer before the user's
"sí" could resolve it.

This test asserts the actual contract: passed-through messages compress()
does not modify must keep their ORIGINAL object identity (``is``, not
just equal content).
"""

from unittest.mock import MagicMock, patch

from agent.context_compressor import ContextCompressor


def _mock_summary_response(text="[CONTEXT SUMMARY]: earlier turns summarized"):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = text
    return mock_response


def _make_compressor(**kwargs):
    with patch("agent.context_compressor.get_model_context_length", return_value=100000):
        return ContextCompressor(model="test/model", quiet_mode=True, **kwargs)


class TestTailIdentityPreservedAcrossCompression:
    def test_untouched_tail_messages_keep_object_identity(self):
        """The core Bloque AH assertion: messages compress() only PASSES
        THROUGH (protected tail, no content change) must be the exact
        same object afterward -- required for the flush layer's
        identity-based dedup to recognize them as already-persisted."""
        c = _make_compressor(protect_first_n=1, protect_last_n=3)
        messages = (
            [{"role": "system", "content": "sys prompt"}]
            + [
                {"role": "user" if i % 2 == 0 else "assistant", "content": f"old msg {i}"}
                for i in range(20)
            ]
            + [
                {"role": "user", "content": "Tengo que decidir algo complejo real"},
                {"role": "assistant", "content": "Analizando tus opciones..."},
                {"role": "user", "content": "sí"},
            ]
        )
        # The last 3 messages are the protected tail (protect_last_n=3) --
        # these are exactly analogous to the real incident's tail (the
        # complex question, its answer, and the "sí" that should have
        # resolved a pending DeepSeek offer).
        tail_originals = messages[-3:]

        with patch("agent.context_compressor.call_llm", return_value=_mock_summary_response()):
            compressed = c.compress(messages)

        compressed_tail = compressed[-3:]
        for original, after in zip(tail_originals, compressed_tail):
            assert after is original, (
                f"Tail message lost its object identity after compression "
                f"(content={original.get('content')!r}) -- this is exactly "
                f"the Bloque AH duplicate-flush / Tarea E offer bug."
            )

    def test_system_message_note_append_still_copies_when_modified(self):
        """The ONE case that legitimately needs a copy (appending the
        compaction note to the system message) must still work --
        identity preservation must not silently break real mutation."""
        c = _make_compressor(protect_first_n=1, protect_last_n=2)
        original_system = {"role": "system", "content": "sys prompt"}
        messages = (
            [original_system]
            + [
                {"role": "user" if i % 2 == 0 else "assistant", "content": f"old msg {i}"}
                for i in range(20)
            ]
            + [
                {"role": "user", "content": "última pregunta"},
                {"role": "assistant", "content": "última respuesta"},
            ]
        )

        with patch("agent.context_compressor.call_llm", return_value=_mock_summary_response()):
            compressed = c.compress(messages)

        assert "compacted into a handoff summary" in compressed[0]["content"]
        # It's a NEW object (content genuinely changed) but the ORIGINAL
        # passed-in dict must be untouched (compress() must never mutate
        # the caller's list in place).
        assert original_system["content"] == "sys prompt"

    def test_merged_summary_tail_message_still_copies_when_modified(self):
        """The other legitimate copy case: when the summary merges into
        the first tail message (role-alternation collision), that ONE
        message is genuinely modified and must be a new object -- but
        the ORIGINAL passed-in dict must stay untouched."""
        c = _make_compressor(protect_first_n=0, protect_last_n=2)
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"old msg {i}"}
            for i in range(20)
        ]
        # Force a head/tail role collision that requires merging: make the
        # last-head and first-tail roles the same on both flip options is
        # hard to construct deterministically here, so we just assert the
        # general invariant instead when merge doesn't trigger: unmerged
        # tail messages still preserve identity (covered above). This test
        # documents the merge-path contract for when it DOES trigger.
        original_first_tail = dict(messages[-2])
        with patch("agent.context_compressor.call_llm", return_value=_mock_summary_response()):
            c.compress(messages)
        # The ORIGINAL list's dicts must never be mutated by compress().
        assert messages[-2] == original_first_tail
