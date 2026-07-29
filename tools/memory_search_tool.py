#!/usr/bin/env python3
"""memory_search -- HAS Fase 4, Bloque 2: retrieval explícito sobre el
índice semántico de memoria (agent/memory_semantic.py).

Complementa (no reemplaza) session_search: session_search busca en
conversaciones pasadas de ESTA sesión de Hermes vía FTS5 puro;
memory_search busca por SIGNIFICADO sobre TODA la capa cruda indexada,
hechos aprobados, y skills -- resuelve el fallo real "el dato existía y
no lo encontró" cuando la pregunta usa palabras distintas a las
originales (retrieval semántico, no solo léxico).

Automáticamente además se inyecta un resumen top-5 al contexto de cada
turno cuando hay una coincidencia fuerte (ver agent/turn_context.py) --
esta tool es para cuando el agente decide buscar más a fondo o con otra
formulación.
"""

import json
import logging

logger = logging.getLogger(__name__)

_MIN_SCORE_STANDALONE = 0.35  # umbral bajo -- esta tool es invocación explícita,
# el agente ya decidió que vale la pena buscar; no se filtra tan agresivo
# como la inyección automática de cada turno.


def memory_search(query: str = "", top_k: int = 5) -> str:
    if not isinstance(query, str) or not query.strip():
        from tools.registry import tool_error
        return tool_error("memory_search requires a non-empty query", success=False)

    if not isinstance(top_k, int):
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5
    top_k = max(1, min(top_k, 10))

    try:
        from agent.memory_semantic import buscar
        results = buscar(query.strip(), top_k=top_k)
    except Exception as e:
        logger.warning("memory_search failed: %s", e, exc_info=True)
        from tools.registry import tool_error
        return tool_error(f"memory search unavailable: {e}", success=False)

    results = [r for r in results if r.score >= _MIN_SCORE_STANDALONE]

    if not results:
        return json.dumps({
            "success": True,
            "results": [],
            "count": 0,
            "message": (
                "No relevant memory found. This covers indexed raw messages, "
                "approved facts, and skill docs -- NOT the Obsidian vault "
                "(no sync channel to it exists yet, see docs/ESTADO.md)."
            ),
        }, ensure_ascii=False)

    return json.dumps({
        "success": True,
        "results": [
            {
                "source": r.source,
                "source_ref": r.source_ref,
                "content": r.content,
                "created_at": r.created_at,
                "score": round(r.score, 3),
            }
            for r in results
        ],
        "count": len(results),
    }, ensure_ascii=False)


def check_memory_search_requirements() -> bool:
    """Requires the semantic index DB to exist (indexer has run at least once)."""
    try:
        from agent.memory_semantic import get_db_path
        return get_db_path().exists()
    except Exception:
        return False


MEMORY_SEARCH_SCHEMA = {
    "name": "memory_search",
    "description": (
        "Search Hermes's semantic memory index by MEANING, not just keywords -- "
        "covers indexed raw conversation history (chunks of ~10 messages), "
        "approved structured facts (memoria_estructurada), and skill "
        "documentation. Backed by local embeddings (multilingual-e5-small) + "
        "sqlite-vec, hybrid with FTS5 keyword matching, no external API call, "
        "no cost.\n\n"
        "DIFFERENCE FROM session_search: session_search is lexical (FTS5 only) "
        "and scoped to conversation history in THIS session DB. memory_search "
        "is semantic (finds relevant content even when the query uses different "
        "words than the original) and scoped to the indexed corpus described "
        "above.\n\n"
        "KNOWN GAP: the Obsidian vault is NOT indexed yet -- it lives on a "
        "remote machine with no sync channel established to this one. If the "
        "answer might be in Obsidian notes and this tool comes up empty, say so "
        "explicitly instead of concluding the information doesn't exist "
        "anywhere.\n\n"
        "Use this when the user asks about something from the past that isn't "
        "in the current conversation and a plain session_search keyword search "
        "might miss it due to different phrasing."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language question or topic to search for.",
            },
            "top_k": {
                "type": "integer",
                "description": "Max results to return (default 5, max 10).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


from tools.registry import registry  # noqa: E402

registry.register(
    name="memory_search",
    toolset="memory_search",
    schema=MEMORY_SEARCH_SCHEMA,
    handler=lambda args, **kw: memory_search(
        query=args.get("query") or "",
        top_k=args.get("top_k", 5),
    ),
    check_fn=check_memory_search_requirements,
    emoji="🧠",
)
