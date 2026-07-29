"""Espejo de notas de Obsidian hacia Notion (tools/notion_mirror.py,
decisión de Arturo, 29 Jul 2026).

Sin NOTION_API_KEY real disponible en este entorno -- todo mockeado
contra _notion_request. La resolución de la página raíz vía búsqueda
por título SÍ se verificó contra la API real de Notion en vivo (ver
docs/ESTADO.md) -- el shape mockeado aquí (properties.title.title[].
plain_text) es el mismo que devolvió la API real.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tools import notion_mirror


def _fake_search_result(title: str) -> dict:
    return {
        "results": [
            {
                "id": "3acc1df3-4107-8033-899f-f7a7c3c8ef76",
                "object": "page",
                "properties": {
                    "title": {"title": [{"plain_text": title}]},
                },
            }
        ]
    }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.setattr(notion_mirror, "_COUNTER_PATH", tmp_path / "contador")
    monkeypatch.setattr(notion_mirror, "_DB_ID_CACHE_PATH", tmp_path / "db_id")


def test_missing_api_key_is_fail_safe_not_fatal():
    result = notion_mirror.mirror_note_to_notion(
        titulo="X", contenido="Y", tags=[], ruta_obsidian="segundo-cerebro/x.md",
        fecha="2026-07-29",
    )
    assert result["success"] is False
    assert result["numero"] is None
    assert "NOTION_API_KEY" in result["error"]


def test_root_page_not_found_is_fail_safe(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    with patch("tools.notion_mirror._notion_request", return_value={"results": []}):
        result = notion_mirror.mirror_note_to_notion(
            titulo="X", contenido="Y", tags=[], ruta_obsidian="segundo-cerebro/x.md",
            fecha="2026-07-29",
        )
    assert result["success"] is False
    assert "Hermes" in result["error"]


def test_finds_root_page_by_title_real_api_shape(monkeypatch):
    """El shape mockeado aquí es el mismo devuelto por la API real de
    Notion (verificado en vivo, 29 Jul 2026) -- properties.title.title
    con plain_text, no properties.Name como en un item de base de datos."""
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    calls = []

    def fake_request(method, path, payload=None, timeout=15):
        calls.append((method, path, payload))
        if path == "search":
            return _fake_search_result("Hermes")
        if path == "databases":
            return {"data_sources": [{"id": "db-abc"}]}
        if path == "pages":
            return {"id": "page-xyz"}
        raise AssertionError(f"unexpected path {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        result = notion_mirror.mirror_note_to_notion(
            titulo="X", contenido="Y", tags=[], ruta_obsidian="segundo-cerebro/x.md",
            fecha="2026-07-29",
        )
    assert result["success"] is True
    search_calls = [c for c in calls if c[1] == "search"]
    assert len(search_calls) == 1


def test_title_match_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")

    def fake_request(method, path, payload=None, timeout=15):
        if path == "search":
            return _fake_search_result("HERMES")
        if path == "databases":
            return {"data_sources": [{"id": "db-abc"}]}
        if path == "pages":
            return {"id": "page-xyz"}
        raise AssertionError(f"unexpected path {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        result = notion_mirror.mirror_note_to_notion(
            titulo="X", contenido="Y", tags=[], ruta_obsidian="segundo-cerebro/x.md",
            fecha="2026-07-29",
        )
    assert result["success"] is True


def test_creates_database_once_then_caches_id(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    calls = []

    def fake_request(method, path, payload=None, timeout=15):
        calls.append((method, path, payload))
        if path == "search":
            return _fake_search_result("Hermes")
        if path == "databases":
            return {"data_sources": [{"id": "db-abc"}]}
        if path == "pages":
            return {"id": "page-xyz"}
        raise AssertionError(f"unexpected path {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        r1 = notion_mirror.mirror_note_to_notion(
            titulo="Primera", contenido="cuerpo", tags=["a"],
            ruta_obsidian="segundo-cerebro/1.md", fecha="2026-07-29",
        )
        r2 = notion_mirror.mirror_note_to_notion(
            titulo="Segunda", contenido="cuerpo2", tags=["b"],
            ruta_obsidian="segundo-cerebro/2.md", fecha="2026-07-29",
        )

    assert r1["success"] is True and r1["numero"] == 1
    assert r2["success"] is True and r2["numero"] == 2
    # La base de datos (y la busqueda de la pagina raiz) solo se hacen
    # UNA vez -- la segunda llamada usa el cache del database_id.
    db_creation_calls = [c for c in calls if c[1] == "databases"]
    search_calls = [c for c in calls if c[1] == "search"]
    assert len(db_creation_calls) == 1
    assert len(search_calls) == 1


def test_numbers_increment_sequentially_across_calls(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    (tmp_path / "db_id").write_text("db-cached", encoding="utf-8")

    with patch("tools.notion_mirror._notion_request", return_value={"id": "page-xyz"}):
        numbers = [
            notion_mirror.mirror_note_to_notion(
                titulo=f"Nota {i}", contenido="x", tags=[],
                ruta_obsidian=f"segundo-cerebro/{i}.md", fecha="2026-07-29",
            )["numero"]
            for i in range(5)
        ]
    assert numbers == [1, 2, 3, 4, 5]


def test_notion_api_error_is_fail_safe(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")

    with patch("tools.notion_mirror._notion_request", side_effect=notion_mirror.NotionMirrorUnavailable("boom")):
        result = notion_mirror.mirror_note_to_notion(
            titulo="X", contenido="Y", tags=[], ruta_obsidian="segundo-cerebro/x.md",
            fecha="2026-07-29",
        )
    assert result["success"] is False
    assert "boom" in result["error"]


def test_long_content_truncated_for_rich_text_limit():
    long_text = "a" * 3000
    truncated = notion_mirror._truncate_rich_text(long_text)
    assert len(truncated) < 2000
    assert truncated.endswith("Obsidian)")


def test_short_content_not_truncated():
    assert notion_mirror._truncate_rich_text("hola") == "hola"
