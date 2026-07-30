"""Vista "Avance HAS" en Notion (tools/notion_avance_has.py, HAS Fase 5
OT-5 Bloque 2, plan nocturno 30 jul 2026) -- primera de las 6 vistas.

Sin NOTION_API_KEY real disponible en este entorno -- todo mockeado
contra _notion_request, mismo patrón que tests/tools/test_notion_mirror.py.
La resolución de la página raíz y la existencia de "Segundo Cerebro"
como única base compartida SÍ se verificaron contra la API real de
Notion en vivo (ver docs/ESTADO.md, Bloque 5).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tools import notion_avance_has as nah


def _fake_search_result(title: str) -> dict:
    return {
        "results": [
            {
                "id": "3acc1df3-4107-8033-899f-f7a7c3c8ef76",
                "object": "page",
                "properties": {"title": {"title": [{"plain_text": title}]}},
            }
        ]
    }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.setattr(nah, "_PAGE_ID_CACHE_PATH", tmp_path / "page_id")
    monkeypatch.setattr(nah, "_HAS_PROGRESS_SCRIPT", tmp_path / "no_existe_has_progress.py")


def test_missing_api_key_is_fail_safe_not_fatal():
    result = nah.sync_avance_has()
    assert result["success"] is False
    assert "NOTION_API_KEY" in result["error"]


def test_creates_page_once_then_caches_id(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    calls = []

    def fake_request(method, path, payload=None, timeout=15):
        calls.append((method, path, payload))
        if path == "search":
            return _fake_search_result("Hermes")
        if path == "pages":
            return {"id": "page-xyz"}
        if path.startswith("blocks/") and "/children" in path:
            return {"results": []}  # sin hijos previos que borrar
        raise AssertionError(f"unexpected path {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        result = nah.sync_avance_has()

    assert result["success"] is True
    assert result["page_id"] == "page-xyz"
    page_creates = [c for c in calls if c[1] == "pages"]
    assert len(page_creates) == 1

    # Segunda corrida: NO debe volver a buscar/crear la página (cache).
    calls.clear()
    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        result2 = nah.sync_avance_has()
    assert result2["success"] is True
    assert not [c for c in calls if c[1] in ("search", "pages")]


def test_clears_existing_blocks_before_appending_new(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    nah._save_cached_page_id("page-ya-existe")
    deleted = []
    appended = []

    def fake_request(method, path, payload=None, timeout=15):
        if path == "blocks/page-ya-existe/children?page_size=100":
            return {"results": [{"id": "old-block-1"}, {"id": "old-block-2"}]}
        if method == "DELETE" and path.startswith("blocks/old-block"):
            deleted.append(path)
            return {}
        if method == "PATCH" and path == "blocks/page-ya-existe/children":
            appended.append(payload)
            return {}
        raise AssertionError(f"unexpected call {method} {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        result = nah.sync_avance_has()

    assert result["success"] is True
    assert len(deleted) == 2
    assert len(appended) == 1
    assert len(appended[0]["children"]) >= 1  # al menos el callout de "actualizado"


def test_root_page_not_shared_is_fail_safe(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")

    def fake_request(method, path, payload=None, timeout=15):
        if path == "search":
            return {"results": []}
        raise AssertionError(f"unexpected path {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request):
        result = nah.sync_avance_has()

    assert result["success"] is False
    assert "Hermes" in result["error"]


def test_chunk_text_splits_without_cutting_lines_mid_way():
    texto = "\n".join(f"linea {i} con algo de contenido" for i in range(200))
    chunks = nah._chunk_text(texto, limit=200)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200
    # Ninguna linea original se partio a la mitad -- todas reaparecen
    # completas en algun chunk.
    reconstruido = "\n".join(chunks)
    for linea_original in texto.splitlines():
        assert linea_original in reconstruido


def test_build_blocks_never_exceeds_notion_limits():
    texto_largo = "\n".join(f"linea {i}" for i in range(5000))
    blocks = nah._build_blocks(texto_largo)
    assert len(blocks) <= nah._BLOCK_COUNT_LIMIT
    for b in blocks:
        if b["type"] == "code":
            content = b["code"]["rich_text"][0]["text"]["content"]
            assert len(content) <= nah._BLOCK_TEXT_LIMIT


def test_run_has_progress_missing_script_is_fail_safe():
    """_HAS_PROGRESS_SCRIPT apuntado a una ruta que no existe (fixture
    autouse) -- no debe tronar, solo reportarlo en el texto del bloque."""
    output = nah._run_has_progress()
    assert "no encontrado" in output
