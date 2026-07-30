"""Unit tests for tools/memoria_hecho_tool.py (pedido de Arturo, 29 Jul 2026:
Hermes debe poder borrar un hecho de memoria_estructurada en vivo, sin
depender de una sesión de Claude Code).

Usa un archivo SQLite temporal (nunca state.db real) con la misma forma de
esquema que memoria_estructurada/sessions tienen en producción.
"""

import json
import sqlite3

import pytest

from tools import memoria_hecho_tool as m

ARTURO_ID = "8899197004"
QA_ID = "8727618189"


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
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
            fuente TEXT,
            origen TEXT,
            user_id TEXT,
            target TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT,
            user_id TEXT
        )
    """)
    conn.execute(
        "INSERT INTO sessions (id, source, user_id) VALUES "
        "('arturo_session', 'telegram', ?), ('qa_session', 'telegram', ?), "
        "('otra_persona_session', 'telegram', '999')",
        (ARTURO_ID, QA_ID),
    )
    conn.execute(
        "INSERT INTO memoria_estructurada (hecho, categoria, fecha_registro, fuente, origen, user_id) VALUES "
        "('Arturo prefiere respuestas breves', 'personal', '2026-07-20', 'x', 'arturo_revision_telegram', ?), "
        "('PRUEBA QA: hecho sintetico que se coló', 'personal', '2026-07-20', 'sandbox', 'arturo_revision_telegram', ?), "
        "('Hecho real de la cuenta QA', 'personal', '2026-07-20', 'x', 'qa', ?)",
        (ARTURO_ID, ARTURO_ID, QA_ID),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(m, "STATE_DB", path)
    monkeypatch.setattr(m, "AUDIT_LOG", tmp_path / "audit.log")
    return path


def test_borra_hecho_real_de_arturo(db_path):
    result = json.loads(m.memoria_hecho_tool(old_text="respuestas breves", session_id="arturo_session"))
    assert result["success"] is True

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT hecho FROM memoria_estructurada WHERE user_id = ?", (ARTURO_ID,)).fetchall()
    conn.close()
    textos = {r[0] for r in rows}
    assert "Arturo prefiere respuestas breves" not in textos


def test_queda_registro_de_auditoria_antes_de_borrar(db_path):
    m.memoria_hecho_tool(old_text="respuestas breves", session_id="arturo_session")
    audit_text = m.AUDIT_LOG.read_text(encoding="utf-8")
    assert "Arturo prefiere respuestas breves" in audit_text
    assert ARTURO_ID in audit_text


def test_no_encuentra_nada_para_texto_ambiguo_o_vacio(db_path):
    result = json.loads(m.memoria_hecho_tool(old_text="", session_id="arturo_session"))
    assert result.get("success") is False
    assert "requerido" in result["error"]


def test_texto_que_no_matchea_nada_no_borra_y_lista_lo_existente(db_path):
    result = json.loads(m.memoria_hecho_tool(old_text="cosa que no existe", session_id="arturo_session"))
    assert result.get("success") is False
    assert "Arturo prefiere respuestas breves" in result["error"]


def test_no_puede_tocar_filas_de_otro_usuario(db_path):
    """Aislamiento estructural: una sesión que no es la de Arturo nunca ve ni
    puede borrar sus hechos, aunque mande el mismo fragmento de texto."""
    result = json.loads(m.memoria_hecho_tool(old_text="respuestas breves", session_id="otra_persona_session"))
    assert result.get("success") is False

    conn = sqlite3.connect(db_path)
    still_there = conn.execute(
        "SELECT 1 FROM memoria_estructurada WHERE hecho = 'Arturo prefiere respuestas breves'"
    ).fetchone()
    conn.close()
    assert still_there is not None


def test_no_puede_tocar_filas_de_qa(db_path):
    """Aunque el texto matchee, origen='qa' nunca es visible/borrable desde
    esta herramienta -- aislamiento estructural con Bloque AG."""
    result = json.loads(m.memoria_hecho_tool(old_text="Hecho real de la cuenta QA", session_id="qa_session"))
    assert result.get("success") is False

    conn = sqlite3.connect(db_path)
    still_there = conn.execute(
        "SELECT 1 FROM memoria_estructurada WHERE hecho = 'Hecho real de la cuenta QA'"
    ).fetchone()
    conn.close()
    assert still_there is not None


def test_sesion_desconocida_no_borra_nada(db_path):
    result = json.loads(m.memoria_hecho_tool(old_text="respuestas breves", session_id="no_existe"))
    assert result.get("success") is False
    assert "verificar" in result["error"]


def test_fragmento_ambiguo_que_matchea_dos_hechos_no_borra_ninguno(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO memoria_estructurada (hecho, categoria, fecha_registro, fuente, origen, user_id) VALUES "
        "('Otro hecho de respuestas breves distinto', 'personal', '2026-07-20', 'x', 'arturo_revision_telegram', ?)",
        (ARTURO_ID,),
    )
    conn.commit()
    conn.close()

    result = json.loads(m.memoria_hecho_tool(old_text="respuestas breves", session_id="arturo_session"))
    assert result.get("success") is False
    assert "coincide con 2" in result["error"]

    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM memoria_estructurada WHERE hecho LIKE '%respuestas breves%'"
    ).fetchone()[0]
    conn.close()
    assert count == 2


def test_registrado_en_registry_con_schema_valido():
    from tools.registry import registry

    entry = registry.get_entry("memoria_hecho")
    assert entry is not None
    assert entry.schema["name"] == "memoria_hecho"
    assert "old_text" in entry.schema["parameters"]["properties"]
