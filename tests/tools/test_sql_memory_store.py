"""Unit tests for tools/sql_memory_store.py (HAS OT-QA, Opción 3, 24 Jul 2026).

Uses a throwaway temp SQLite file (never the real state.db) with the
same schema shape memoria_estructurada has in production, so these
tests never touch real data.
"""

import sqlite3

import pytest

from tools.sql_memory_store import SqlMemoryStore

QA_ID = "8727618189"
OTHER_ID = "8899197004"  # Arturo's real id -- used to prove isolation


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "state.db"
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE memoria_estructurada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hecho TEXT NOT NULL,
            entidad TEXT,
            categoria TEXT NOT NULL CHECK (categoria IN ('personal', 'académico', 'técnico', 'financiero', 'meta')),
            fecha_registro TEXT NOT NULL,
            vigente_hasta TEXT,
            fuente TEXT
        )
    """)
    conn.commit()
    conn.close()
    return path


def test_add_then_format_for_system_prompt(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    result = store.add("memory", "mi color favorito de prueba es azul")
    assert result["success"] is True
    assert result["entry_count"] == 1

    store.load_from_disk()
    block = store.format_for_system_prompt("memory")
    assert block is not None
    assert "mi color favorito de prueba es azul" in block
    assert "CUENTA QA" in block


def test_replace_finds_by_substring(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    store.add("memory", "uso Bitso para cripto")
    result = store.replace("memory", "Bitso", "ahora uso Binance para cripto")
    assert result["success"] is True
    store.load_from_disk()
    block = store.format_for_system_prompt("memory")
    assert "Binance" in block
    assert "Bitso" not in block


def test_remove_deletes_matching_entry(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    store.add("memory", "hecho de prueba a borrar")
    result = store.remove("memory", "hecho de prueba a borrar")
    assert result["success"] is True
    store.load_from_disk()
    assert store.format_for_system_prompt("memory") is None


def test_memory_and_user_targets_stay_separate(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    store.add("memory", "nota de memoria")
    store.add("user", "perfil de usuario")
    store.load_from_disk()
    assert "nota de memoria" in store.format_for_system_prompt("memory")
    assert "nota de memoria" not in (store.format_for_system_prompt("user") or "")
    assert "perfil de usuario" in store.format_for_system_prompt("user")
    assert "perfil de usuario" not in (store.format_for_system_prompt("memory") or "")


def test_isolation_between_user_ids(db_path):
    """The core promise: two different user_ids never see each other's
    entries, even sharing the exact same table."""
    qa_store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    other_store = SqlMemoryStore(user_id=OTHER_ID, db_path=db_path)

    qa_store.add("memory", "hecho sembrado por QA")
    other_store.add("memory", "hecho sembrado por el otro usuario")

    qa_store.load_from_disk()
    other_store.load_from_disk()

    qa_block = qa_store.format_for_system_prompt("memory")
    other_block = other_store.format_for_system_prompt("memory")

    assert "hecho sembrado por QA" in qa_block
    assert "hecho sembrado por el otro usuario" not in qa_block
    assert "hecho sembrado por el otro usuario" in other_block
    assert "hecho sembrado por QA" not in other_block


def test_rows_are_tagged_origen_qa_and_real_user_id(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    store.add("memory", "hecho cualquiera")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT origen, user_id, target FROM memoria_estructurada").fetchone()
    conn.close()
    assert row["origen"] == "qa"
    assert row["user_id"] == QA_ID
    assert row["target"] == "memory"


def test_apply_batch_mixed_actions(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path)
    store.add("memory", "entrada original")
    result = store.apply_batch("memory", [
        {"action": "add", "content": "segunda entrada"},
        {"action": "replace", "old_text": "original", "content": "entrada modificada"},
    ])
    assert result["success"] is True
    store.load_from_disk()
    block = store.format_for_system_prompt("memory")
    assert "segunda entrada" in block
    assert "entrada modificada" in block
    assert "entrada original" not in block


def test_empty_user_id_rejected():
    with pytest.raises(ValueError):
        SqlMemoryStore(user_id="")


def test_char_limit_enforced(db_path):
    store = SqlMemoryStore(user_id=QA_ID, db_path=db_path, memory_char_limit=10)
    result = store.add("memory", "esto es mas de diez caracteres")
    assert result["success"] is False
    assert "usage" in result
