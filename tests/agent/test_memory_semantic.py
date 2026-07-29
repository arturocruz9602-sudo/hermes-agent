"""HAS Fase 4, Bloque 2 -- índice semántico de memoria (agent/memory_semantic.py).

Ejercita el modelo real de embeddings (intfloat/multilingual-e5-small,
descargado localmente) contra una base de datos temporal -- no hay mock
de sentence-transformers/sqlite-vec, porque el bug real que motivó estos
tests (FTS5 con stopwords sin filtrar, y la sintaxis k=/LIMIT de
sqlite-vec) solo se manifiesta contra el pipeline real. Se salta si el
modelo no está disponible localmente (offline sin caché) para no romper
un entorno sin la descarga de ~470MB.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("HF_HUB_OFFLINE", "1")

pytest.importorskip("sqlite_vec")
pytest.importorskip("sentence_transformers")

import agent.memory_semantic as ms


def _model_available() -> bool:
    try:
        ms._get_model()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(),
    reason="modelo intfloat/multilingual-e5-small no disponible localmente",
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "memoria_semantica_test.db"


def test_schema_creates_all_tables(db_path):
    con = ms._connect(db_path)
    try:
        names = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
        }
        assert {"chunks", "chunks_fts", "chunks_vec", "index_cursor"} <= names
    finally:
        con.close()


def test_add_chunk_and_exact_keyword_match(db_path):
    con = ms._connect(db_path)
    try:
        ms.add_chunk(
            con, source="hechos", source_ref="h1",
            content="El presupuesto mensual de Hermes es 100 pesos mexicanos.",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"), importancia=0.8,
        )
    finally:
        con.close()

    resultados = ms.buscar("presupuesto mensual Hermes", db_path=db_path)
    assert resultados, "debia encontrar al menos un resultado"
    assert "presupuesto" in resultados[0].content.lower()


def test_stopwords_do_not_cause_false_positive_match(db_path):
    """Regresión del bug real (2026-07-29): sin filtrar stopwords, una
    consulta con "la"/"por"/"me" hace match contra CUALQUIER chunk que
    comparta esas palabras comunes, no solo contenido relacionado."""
    con = ms._connect(db_path)
    try:
        ms.add_chunk(
            con, source="hechos", source_ref="h1",
            content="A Arturo le gusta el futbol los domingos por la tarde.",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"), importancia=0.3,
        )
    finally:
        con.close()

    fts_query = ms._sanitize_fts_query("como me conecto por ssh a la macbook")
    for stopword in ("como", "me", "por", "la", "a"):
        assert f'"{stopword}"' not in fts_query, (
            f"la stopword {stopword!r} no debia quedar en la consulta FTS: {fts_query!r}"
        )


def test_semantically_similar_content_ranks_above_unrelated(db_path):
    """Con importancia y recencia IGUALES entre los dos chunks, la
    similitud semántica debe decidir el orden -- aísla el componente de
    cos_sim del resto de la fórmula de ranking."""
    con = ms._connect(db_path)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        ms.add_chunk(
            con, source="obsidian", source_ref="ssh.md",
            content="Para conectarte por SSH a la MacBook usa la llave "
            "en ~/.ssh/id_ed25519_macbook con el puerto 2222.",
            created_at=now, importancia=0.5,
        )
        ms.add_chunk(
            con, source="obsidian", source_ref="receta.md",
            content="Receta de tacos al pastor: marinar la carne con "
            "achiote, piña y cebolla por dos horas antes de asar.",
            created_at=now, importancia=0.5,
        )
    finally:
        con.close()

    resultados = ms.buscar("como me conecto por ssh a la macbook", db_path=db_path)
    assert resultados
    assert "ssh" in resultados[0].content.lower()


def test_empty_query_returns_no_results(db_path):
    assert ms.buscar("", db_path=db_path) == []
    assert ms.buscar("   ", db_path=db_path) == []


def test_buscar_on_missing_db_is_fail_safe(tmp_path):
    """DB que no existe aun (primer arranque, indexador no ha corrido) no
    debe lanzar -- debe devolver lista vacia."""
    missing = tmp_path / "no_existe" / "memoria_semantica.db"
    assert ms.buscar("cualquier cosa", db_path=missing) == []


def test_token_budget_never_truncates_a_single_chunk_mid_sentence(db_path):
    con = ms._connect(db_path)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        for i in range(3):
            ms.add_chunk(
                con, source="hechos", source_ref=f"h{i}",
                content=f"Hecho de prueba numero {i} sobre el presupuesto de Hermes " * 50,
                created_at=now, importancia=0.8,
            )
    finally:
        con.close()

    resultados = ms.buscar("presupuesto Hermes", token_budget=100, db_path=db_path)
    for r in resultados:
        assert r.content.endswith("Hermes ") or r.content.endswith(str(len(r.content)))
        # el contenido nunca se corta a mitad de caracter -- viene completo o no viene.


def test_format_for_prompt_cites_source():
    result = ms.SearchResult(
        chunk_id=1, source="obsidian", source_ref="notas/ssh.md",
        content="contenido de ejemplo", created_at="2026-01-01T00:00:00",
        importancia=0.5, score=0.9,
    )
    text = ms.format_for_prompt([result])
    assert "obsidian" in text
    assert "notas/ssh.md" in text
    assert "contenido de ejemplo" in text


def test_format_for_prompt_empty_list():
    assert ms.format_for_prompt([]) == ""
