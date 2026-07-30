"""HAS v1.6 B9 (30 jul 2026) -- "reglas de comportamiento aprendidas".

La categoría nueva "regla_comportamiento" (propuesta por
scripts/fase2_extract_candidates.py cuando detecta que la misma
corrección se repitió 3+ veces, fuera del repo) debe mapear a "meta" en
memoria_estructurada y pasar por el mismo candado de aprobación
candidato-por-candidato que cualquier otro candidato -- nunca se
auto-adopta.
"""

import sqlite3

import pytest

from tools import memoria_review as mr

ARTURO_ID = "8899197004"


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
    conn.commit()
    conn.close()

    monkeypatch.setattr(mr, "STATE_DB", path)
    return path


def test_regla_comportamiento_mapea_a_meta():
    assert mr._CATEGORIA_MAP["regla_comportamiento"] == "meta"


def test_insert_fact_regla_comportamiento_pasa_el_check_constraint(db_path):
    item = {
        "texto": (
            "Regla de comportamiento propuesta (dicho 3 veces): "
            "Arturo siempre pide respuestas breves en la mañana"
        ),
        "categoria": "regla_comportamiento",
        "fuente_verificada": "session_id=s1 mensaje_id=10 fecha=x ; "
        "session_id=s2 mensaje_id=20 fecha=y ; session_id=s3 mensaje_id=30 fecha=z",
    }
    error = mr._insert_fact(item, ARTURO_ID, "arturo_revision_telegram")
    assert error is None

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT categoria, hecho FROM memoria_estructurada WHERE user_id = ?", (ARTURO_ID,)
    ).fetchone()
    conn.close()
    assert row is not None
    categoria, hecho = row
    assert categoria == "meta"
    assert "dicho 3 veces" in hecho


def test_regla_comportamiento_sigue_el_mismo_candado_de_aprobacion(db_path):
    """Un candidato de regla_comportamiento en la cola solo se escribe tras
    'aprobar' explícito -- 'rechazar' no toca memoria_estructurada, igual
    que cualquier otro candidato (HAS B9: nunca auto-adoptado)."""
    session_key = "arturo:telegram:123"
    queue = [{
        "texto": "Regla de comportamiento propuesta (dicho 3 veces): probar en pty antes de asumir age funciona",
        "categoria": "regla_comportamiento",
        "fuente_verificada": "x",
        "_source_file": mr._SANDBOX_SOURCE,
        "_source_index": 0,
    }]
    mr.register(session_key, "confirm1", queue)

    msg, next_item = mr.resolve(session_key, "confirm1", "rechazar")
    assert "Descartado" in msg
    assert next_item is None

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM memoria_estructurada").fetchone()[0]
    conn.close()
    assert count == 0
