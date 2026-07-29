"""Bloque de notas de Obsidian (HAS §B7, 29 Jul 2026) -- segundo cerebro
local de Arturo, tools/obsidian_note_tool.py.

Usa tmp_path + monkeypatch de get_vault_root en vez de la ruta real
(/mnt/seagate/obsidian) para no depender de que el disco esté montado
durante los tests.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from tools.obsidian_note_tool import (
    check_obsidian_note_requirements,
    obsidian_save_note,
)


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "obsidian"
    root.mkdir()
    with patch("tools.obsidian_note_tool.get_vault_root", return_value=root):
        yield root


def test_missing_titulo_is_error(vault):
    result = json.loads(obsidian_save_note(titulo="", contenido="algo"))
    assert result["success"] is False


def test_missing_contenido_is_error(vault):
    result = json.loads(obsidian_save_note(titulo="Idea", contenido=""))
    assert result["success"] is False


def test_creates_note_with_frontmatter(vault):
    result = json.loads(obsidian_save_note(titulo="Idea para video", contenido="Contenido real de la nota."))
    assert result["success"] is True
    note_path = vault / result["path"]
    assert note_path.exists()
    text = note_path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "Idea para video" in text
    assert "Contenido real de la nota." in text
    assert "segundo-cerebro" in result["path"]


def test_default_folder_is_segundo_cerebro(vault):
    result = json.loads(obsidian_save_note(titulo="X", contenido="Y"))
    assert result["path"].split("/")[0] == "segundo-cerebro"


def test_custom_folder_respected(vault):
    result = json.loads(obsidian_save_note(titulo="Tema", contenido="Y", carpeta="escuela/calculo"))
    assert result["path"].startswith("escuela/calculo/")


def test_never_overwrites_same_title_same_day(vault):
    r1 = json.loads(obsidian_save_note(titulo="Repetida", contenido="primera version"))
    r2 = json.loads(obsidian_save_note(titulo="Repetida", contenido="segunda version"))
    assert r1["path"] != r2["path"]
    assert (vault / r1["path"]).read_text(encoding="utf-8").find("primera version") != -1
    assert (vault / r2["path"]).read_text(encoding="utf-8").find("segunda version") != -1


def test_real_credential_blocked_by_secret_scanner(vault):
    result = json.loads(obsidian_save_note(
        titulo="Notas de la reunion",
        contenido="La contraseña del router es MiClaveReal2026 y no se la des a nadie.",
    ))
    assert result["success"] is False
    assert "escáner" in result["error"].lower() or "bloqueada" in result["error"].lower()
    # Nada se escribió a disco.
    assert list(vault.rglob("*.md")) == []


def test_vault_missing_returns_clear_error(tmp_path):
    missing = tmp_path / "no_existe"
    with patch("tools.obsidian_note_tool.get_vault_root", return_value=missing):
        result = json.loads(obsidian_save_note(titulo="X", contenido="Y"))
    assert result["success"] is False
    assert "no existe" in result["error"].lower()


def test_check_requirements_false_when_vault_missing(tmp_path):
    with patch("tools.obsidian_note_tool.get_vault_root", return_value=tmp_path / "nope"):
        assert check_obsidian_note_requirements() is False


def test_check_requirements_true_when_vault_exists(vault):
    assert check_obsidian_note_requirements() is True


def test_tags_appear_in_frontmatter(vault):
    result = json.loads(obsidian_save_note(titulo="Con tags", contenido="cuerpo", tags=["ideas", "video"]))
    text = (vault / result["path"]).read_text(encoding="utf-8")
    assert "ideas" in text and "video" in text


def test_folder_path_traversal_sanitized(vault):
    result = json.loads(obsidian_save_note(titulo="X", contenido="Y", carpeta="../../etc"))
    note_path = vault / result["path"]
    # Debe quedar dentro del vault, nunca fuera.
    assert vault in note_path.resolve().parents or note_path.resolve().parent == vault
    assert ".." not in result["path"]
