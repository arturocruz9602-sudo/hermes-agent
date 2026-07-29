"""Índice semántico de memoria (HAS Fase 4, Bloque 2 -- docs/HAS.md §B9, §E4).

Capa 3 de la arquitectura de memoria de tres capas: embeddings locales
(``intfloat/multilingual-e5-small``, ~470MB, CPU-viable) + ``sqlite-vec``
como almacén vectorial -- cero servicio externo, cero costo por llamada.

Resuelve el fallo real documentado en el HAS: "el dato existía (SSH a la
MacBook, 565 notas) y no lo encontró" -- antes de esto, Hermes solo tenía
memoria estructurada aprobada manualmente, sin forma de buscar por
significado sobre la capa cruda completa.

Este módulo es el núcleo compartido (esquema, embeddings, retrieval
híbrido) usado tanto por el indexador offline (``~/.hermes/scripts/
memoria_indexador.py``, corrido por systemd timer) como por la tool en
vivo (``tools/memory_search_tool.py``) que el agente llama durante una
conversación real.

Degradación con gracia (HAS §B9): si ``intfloat/multilingual-e5-small``
no cabe en RAM/tiempo razonable en la HP, cambiar ``_MODEL_NAME`` a
``paraphrase-multilingual-MiniLM-L12-v2`` y ``_EMBEDDING_DIM`` a 384
(mismo tamaño de vector, no requiere migrar el esquema) -- decisión y
medición real documentadas en docs/ESTADO.md antes de tocar esta
constante.
"""

from __future__ import annotations

import math
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from hermes_constants import get_hermes_home

_MODEL_NAME = "intfloat/multilingual-e5-small"
_EMBEDDING_DIM = 384

# Ranking de retrieval (HAS §E4): score = 0.5·cos_sim + 0.3·recencia_exp + 0.2·importancia.
_W_SIMILARITY = 0.5
_W_RECENCY = 0.3
_W_IMPORTANCE = 0.2
_RECENCY_HALFLIFE_DAYS = 90.0  # exp(-días/90), igual que HAS §E4.

_FTS_CANDIDATES = 20
_VEC_CANDIDATES = 20
_DEFAULT_TOP_K = 5
_DEFAULT_TOKEN_BUDGET = 1200  # HAS §E4: presupuesto de inyección al prompt.
_CHARS_PER_TOKEN_ESTIMATE = 4  # mismo estimador usado en el resto del proyecto.

# Palabras funcionales del español (+ inglés genérico) que NO deben entrar
# a la consulta FTS5 -- sin este filtro, "la"/"por"/"me"/"como" hacen match
# por sí solas contra CUALQUIER chunk que las contenga (casi todos), lo que
# infla el ranking de contenido sin relación real con la pregunta. Bug real
# encontrado en la verificación manual (2026-07-29): una nota de SSH a la
# MacBook (coincidencia semántica y léxica real) rankeó por debajo de un
# hecho sin relación alguna, solo porque compartía "la"/"y" con la consulta.
_STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo",
    "de", "del", "al", "a", "en", "por", "para", "con", "sin", "sobre",
    "y", "o", "u", "e", "ni", "que", "como", "cual", "cuales",
    "me", "te", "se", "le", "les", "nos", "os", "mi", "tu", "su",
    "yo", "ella", "nosotros", "ustedes", "ellos", "ellas",
    "es", "son", "soy", "eres", "esta", "estan", "ser", "estar",
    "the", "a", "an", "of", "to", "in", "on", "for", "is", "are",
}


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,          -- 'raw' | 'hechos' | 'skill' | 'obsidian'
  source_ref TEXT NOT NULL,      -- ruta/fecha+offset del chunk (auditable)
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,      -- del contenido, no del indexado
  importancia REAL DEFAULT 0.3,  -- 0-1; hechos aprobados=0.8, reflexión=0.9
  indexed_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, content=chunks);
CREATE TABLE IF NOT EXISTS index_cursor (source TEXT PRIMARY KEY, last_ref TEXT);
"""

_model_lock = threading.Lock()
_model_singleton = None


class SemanticIndexUnavailable(Exception):
    """El índice semántico no está disponible (deps faltantes, modelo no
    cargó, o falla de E/S). Fail-safe: el caller debe tratar esto como
    "sin resultados", nunca como excepción fatal para el turno del agente."""


def get_db_path() -> Path:
    return get_hermes_home() / "memoria_semantica.db"


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    import sqlite_vec

    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    con.executescript(_SCHEMA_SQL)
    # chunks_vec se crea por separado -- vec0 no soporta "IF NOT EXISTS"
    # en todas las versiones, así que se checa contra sqlite_master.
    exists = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunks_vec'"
    ).fetchone()
    if not exists:
        con.execute(
            f"CREATE VIRTUAL TABLE chunks_vec USING vec0(embedding float[{_EMBEDDING_DIM}])"
        )
    con.commit()
    return con


def _get_model():
    """Carga perezosa y memoizada del modelo de embeddings (proceso-local).

    ensure() se llama aquí, no a nivel de módulo, para que importar este
    archivo nunca dispare una instalación -- solo el primer uso real."""
    global _model_singleton
    with _model_lock:
        if _model_singleton is None:
            import os

            from tools.lazy_deps import ensure

            ensure("memory.semantic_index", prompt=False)
            # El modelo ya está en caché local tras la primera descarga --
            # forzar modo offline evita que cada carga intente golpear el
            # Hub de Hugging Face (más lento, y una dependencia de red
            # innecesaria para algo que corre 100% local).
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer

            _model_singleton = SentenceTransformer(_MODEL_NAME)
        return _model_singleton


def _embed(texts: list[str], *, is_query: bool) -> list[list[float]]:
    """e5 requiere el prefijo "query: "/"passage: " -- sin él, la calidad
    de similitud coseno se degrada notablemente (documentado por el
    propio modelo). is_query=True para texto de búsqueda, False para
    contenido que se está indexando."""
    prefix = "query: " if is_query else "passage: "
    model = _get_model()
    prefixed = [prefix + t for t in texts]
    embeddings = model.encode(prefixed, batch_size=16, show_progress_bar=False)
    return [list(map(float, vec)) for vec in embeddings]


def _pack_embedding(vec: list[float]) -> bytes:
    import struct

    return struct.pack(f"{len(vec)}f", *vec)


@dataclass
class Chunk:
    id: int
    source: str
    source_ref: str
    content: str
    created_at: str
    importancia: float


def add_chunk(
    con: sqlite3.Connection,
    *,
    source: str,
    source_ref: str,
    content: str,
    created_at: str,
    importancia: float = 0.3,
) -> int:
    """Inserta un chunk nuevo (contenido + fts + vector). No deduplica --
    el caller (indexador) es responsable de no reinsertar vía su cursor."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    cur = con.execute(
        "INSERT INTO chunks (source, source_ref, content, created_at, importancia, indexed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (source, source_ref, content, created_at, importancia, now),
    )
    chunk_id = cur.lastrowid
    con.execute(
        "INSERT INTO chunks_fts (rowid, content) VALUES (?, ?)", (chunk_id, content)
    )
    embedding = _embed([content], is_query=False)[0]
    con.execute(
        "INSERT INTO chunks_vec (rowid, embedding) VALUES (?, ?)",
        (chunk_id, _pack_embedding(embedding)),
    )
    con.commit()
    return chunk_id


def _recency_score(created_at: str, now: Optional[float] = None) -> float:
    now = now if now is not None else time.time()
    try:
        created_epoch = time.mktime(time.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return 0.0
    days = max(0.0, (now - created_epoch) / 86400.0)
    return math.exp(-days / _RECENCY_HALFLIFE_DAYS)


@dataclass
class SearchResult:
    chunk_id: int
    source: str
    source_ref: str
    content: str
    created_at: str
    importancia: float
    score: float


def buscar(
    query: str,
    *,
    top_k: int = _DEFAULT_TOP_K,
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
    db_path: Optional[Path] = None,
) -> list[SearchResult]:
    """Retrieval híbrido (HAS §E4): unión de FTS5 top-20 + vector top-20,
    re-rankeada con score = 0.5·cos_sim + 0.3·recencia_exp + 0.2·importancia.

    Fail-safe: cualquier error (deps faltantes, DB no existe, modelo no
    carga) devuelve lista vacía -- nunca lanza hacia el turno del agente.
    """
    if not query or not query.strip():
        return []
    try:
        con = _connect(db_path)
    except Exception:
        return []

    try:
        # Salida temprana barata: si el índice todavía no tiene nada (recién
        # instalado, antes del primer backfill; o una DB de pruebas
        # aislada), no tiene sentido cargar el modelo de embeddings solo
        # para no encontrar nada. Además evita que CADA test que ejercita
        # build_turn_context() dispare una carga real del modelo (~470MB,
        # 10-20s la primera vez) sin ninguna relación con lo que ese test
        # prueba -- bug real encontrado al conectar esto a turn_context.py
        # (2026-07-29): 22 tests de test_turn_context.py pasaron de <1s a
        # 14s por esto antes de este guard.
        has_any = con.execute("SELECT 1 FROM chunks LIMIT 1").fetchone()
        if not has_any:
            return []

        candidates: dict[int, dict] = {}

        # --- FTS5 (keyword) ---
        try:
            fts_query = _sanitize_fts_query(query)
            if fts_query:
                rows = con.execute(
                    "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (fts_query, _FTS_CANDIDATES),
                ).fetchall()
                for (rowid,) in rows:
                    candidates.setdefault(rowid, {})["fts_hit"] = True
        except Exception:
            pass

        # --- vectorial (semántico) ---
        try:
            query_embedding = _embed([query], is_query=True)[0]
            rows = con.execute(
                "SELECT rowid, distance FROM chunks_vec WHERE embedding MATCH ? AND k = ?",
                (_pack_embedding(query_embedding), _VEC_CANDIDATES),
            ).fetchall()
            for rowid, distance in rows:
                # sqlite-vec vec0 usa distancia L2 sobre vectores normalizados
                # por sentence-transformers ~ aproxima 1 - cos_sim para
                # vectores unitarios; clamp por seguridad numérica.
                cos_sim = max(0.0, 1.0 - (distance**2) / 2.0)
                entry = candidates.setdefault(rowid, {})
                entry["cos_sim"] = max(entry.get("cos_sim", 0.0), cos_sim)
        except Exception:
            pass

        if not candidates:
            return []

        chunk_ids = list(candidates.keys())
        placeholders = ",".join("?" * len(chunk_ids))
        rows = con.execute(
            f"SELECT id, source, source_ref, content, created_at, importancia "
            f"FROM chunks WHERE id IN ({placeholders})",
            chunk_ids,
        ).fetchall()

        now = time.time()
        results: list[SearchResult] = []
        for chunk_id, source, source_ref, content, created_at, importancia in rows:
            sig = candidates[chunk_id]
            cos_sim = sig.get("cos_sim", 0.0)
            recency = _recency_score(created_at, now)
            score = (
                _W_SIMILARITY * cos_sim
                + _W_RECENCY * recency
                + _W_IMPORTANCE * importancia
            )
            results.append(
                SearchResult(
                    chunk_id=chunk_id, source=source, source_ref=source_ref,
                    content=content, created_at=created_at,
                    importancia=importancia, score=score,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return _apply_token_budget(results[:top_k], token_budget)
    finally:
        con.close()


def _sanitize_fts_query(query: str) -> str:
    """FTS5 MATCH interpreta operadores especiales (", -, *, etc.) -- una
    consulta en lenguaje natural con esos caracteres literalmente rompe la
    sintaxis de la consulta. Reduce a tokens alfanuméricos con las palabras
    funcionales quitadas (_STOPWORDS_ES) y los une por OR (favorece recall
    sobre los términos que sí importan; el vector cubre precisión
    semántica). Sin el filtro de stopwords, "la"/"por"/"me" hacen match
    contra casi cualquier chunk -- ver comentario en _STOPWORDS_ES."""
    tokens = re.findall(r"[\w][\w\-áéíóúñÁÉÍÓÚÑ]*", query, flags=re.UNICODE)
    tokens = [t for t in tokens if len(t) >= 2 and t.lower() not in _STOPWORDS_ES]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens[:12])


def _apply_token_budget(results: list[SearchResult], token_budget: int) -> list[SearchResult]:
    """Recorta la lista para no exceder el presupuesto de inyección (HAS
    §E4: 1,200 tokens), estimando tokens ~= chars/4. Nunca trunca el
    contenido de un chunk individual -- lo omite completo si no cabe,
    para no inyectar contexto cortado a media frase."""
    kept: list[SearchResult] = []
    used = 0
    for r in results:
        est_tokens = max(1, len(r.content) // _CHARS_PER_TOKEN_ESTIMATE)
        if used + est_tokens > token_budget and kept:
            break
        kept.append(r)
        used += est_tokens
    return kept


def format_for_prompt(results: list[SearchResult]) -> str:
    """Formatea resultados de buscar() para inyección directa al contexto
    del agente -- cada resultado con su fuente citada (auditable, igual
    que memoria_estructurada.fuente)."""
    if not results:
        return ""
    lines = ["[Memoria relevante encontrada -- cita la fuente si la usas]"]
    for r in results:
        lines.append(f"- ({r.source}: {r.source_ref}) {r.content}")
    return "\n".join(lines)
