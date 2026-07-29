"""HAS Fase 4, Bloque 2 -- tool memory_search (tools/memory_search_tool.py)."""

from __future__ import annotations

import json
from unittest.mock import patch

from tools.memory_search_tool import (
    check_memory_search_requirements,
    memory_search,
)
from agent.memory_semantic import SearchResult


def test_empty_query_returns_error():
    result = json.loads(memory_search(query=""))
    assert result.get("success") is False


def test_no_results_message_mentions_obsidian_gap():
    with patch("agent.memory_semantic.buscar", return_value=[]):
        result = json.loads(memory_search(query="algo que no existe"))
    assert result["success"] is True
    assert result["count"] == 0
    assert "Obsidian" in result["message"]


def test_results_below_threshold_are_filtered():
    weak = SearchResult(
        chunk_id=1, source="raw", source_ref="1-10", content="ruido sin relacion",
        created_at="2026-01-01T00:00:00", importancia=0.3, score=0.1,
    )
    with patch("agent.memory_semantic.buscar", return_value=[weak]):
        result = json.loads(memory_search(query="algo"))
    assert result["count"] == 0


def test_strong_result_passes_through():
    strong = SearchResult(
        chunk_id=2, source="skill", source_ref="hermes-upgrade/SKILL.md",
        content="procedimiento de actualizacion", created_at="2026-01-01T00:00:00",
        importancia=0.3, score=0.8,
    )
    with patch("agent.memory_semantic.buscar", return_value=[strong]):
        result = json.loads(memory_search(query="como actualizo hermes"))
    assert result["success"] is True
    assert result["count"] == 1
    assert result["results"][0]["source_ref"] == "hermes-upgrade/SKILL.md"


def test_top_k_clamped():
    with patch("agent.memory_semantic.buscar", return_value=[]) as mock_buscar:
        memory_search(query="x", top_k=999)
        assert mock_buscar.call_args.kwargs["top_k"] == 10
        memory_search(query="x", top_k=0)
        assert mock_buscar.call_args.kwargs["top_k"] == 1


def test_search_failure_is_fail_safe_not_fatal():
    with patch("agent.memory_semantic.buscar", side_effect=RuntimeError("boom")):
        result = json.loads(memory_search(query="x"))
    assert result.get("success") is False
    assert "unavailable" in result.get("error", "").lower()


def test_requirements_false_when_db_missing(tmp_path):
    with patch("agent.memory_semantic.get_db_path", return_value=tmp_path / "no_existe.db"):
        assert check_memory_search_requirements() is False


def test_requirements_true_when_db_exists(tmp_path):
    db = tmp_path / "memoria_semantica.db"
    db.write_text("")
    with patch("agent.memory_semantic.get_db_path", return_value=db):
        assert check_memory_search_requirements() is True
