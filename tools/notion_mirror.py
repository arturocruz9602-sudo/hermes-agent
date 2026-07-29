"""Espejo de notas de Obsidian hacia Notion (decisión de Arturo, 29 Jul
2026): cada nota que Hermes guarda en el vault (tools/obsidian_note_tool.py)
también crea una fila numerada en una base de datos de Notion, para que
Arturo la pueda consultar ahí -- o para que Hermes le diga "revisa la
nota 89 en Notion, conecta con esto" -- mientras no tiene forma cómoda
de ver el grafo de Obsidian (diferido hasta la Mac Mini, ver
docs/ESTADO.md).

Best-effort por diseño: si Notion falla por cualquier razón (sin
NOTION_API_KEY todavía, sin red, página raíz no compartida con la
integración), la nota de Obsidian YA se guardó de todos modos -- esto
nunca bloquea ni revierte ese guardado. Ver obsidian_save_note().

Requiere dos variables de entorno en .env (ambas puestas por Arturo,
nunca por Hermes -- son credenciales/config, no algo que se auto-genere):
- NOTION_API_KEY: la ya explicada en el chat (notion.so/my-integrations).
- NOTION_HERMES_ROOT_PAGE_ID: el ID de la página "Hermes" ya compartida
  con la integración (copiar de la URL de esa página en Notion: los 32
  caracteres hex al final, con o sin guiones).

Mecánica de API real (Notion-Version 2025-09-03, "data sources" no
"databases" -- ver ~/.hermes/skills/productivity/notion/SKILL.md,
consolidada hoy mismo).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_NOTION_API_VERSION = "2025-09-03"
_NOTION_DB_TITLE = "Segundo Cerebro"
_COUNTER_PATH = Path.home() / ".hermes" / ".segundo_cerebro_contador"
_DB_ID_CACHE_PATH = Path.home() / ".hermes" / ".segundo_cerebro_notion_db_id"


class NotionMirrorUnavailable(Exception):
    """Notion no está configurada o falló -- el caller debe tratar esto
    como 'no se sincronizó', nunca como fatal para el guardado real en
    Obsidian."""


def _notion_request(method: str, path: str, payload: Optional[dict] = None, timeout: int = 15) -> dict:
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise NotionMirrorUnavailable("NOTION_API_KEY no configurada en .env")

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": _NOTION_API_VERSION,
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise NotionMirrorUnavailable(f"Notion API error {e.code}: {body[:300]}") from e
    except Exception as e:
        raise NotionMirrorUnavailable(f"Notion request failed: {e}") from e


_ROOT_PAGE_TITLE = os.environ.get("NOTION_HERMES_ROOT_PAGE_TITLE", "Hermes")


def _get_root_page_id() -> str:
    """Busca la página raíz por título vía /v1/search en vez de pedirle a
    Arturo que copie un ID de una URL -- un paso menos de configuración.

    Verificado contra la API real de Notion (29 Jul 2026): /v1/search
    con filter object=page devuelve resultados con
    properties.title.title[].plain_text para el título de una página
    normal (no de base de datos). Solo se ejecuta una vez en la
    práctica -- _ensure_database_id() cachea el database_id resultante
    permanentemente, así que esta búsqueda no se repite en cada nota."""
    result = _notion_request("POST", "search", {
        "filter": {"property": "object", "value": "page"},
    })
    for item in result.get("results", []):
        title_prop = (item.get("properties") or {}).get("title") or {}
        title_parts = title_prop.get("title", []) if isinstance(title_prop, dict) else []
        title = "".join(p.get("plain_text", "") for p in title_parts)
        if title.strip().lower() == _ROOT_PAGE_TITLE.strip().lower():
            return item["id"].replace("-", "")
    raise NotionMirrorUnavailable(
        f"No se encontró ninguna página llamada '{_ROOT_PAGE_TITLE}' compartida "
        "con la integración -- crearla en Notion y compartirla (menú '...' -> "
        "'Add connections' -> la integración 'hermes')."
    )


def _load_cached_db_id() -> Optional[str]:
    """El nombre del archivo se conserva (_DB_ID_CACHE_PATH) pero desde el
    fix del 29 Jul 2026 lo que cachea es el data_source_id, no el
    database_id -- ver _create_database para el porqué (API 2025-09-03
    separa el contenedor "database" de su "data source"; las páginas se
    crean apuntando al data_source_id, no al database_id)."""
    try:
        if _DB_ID_CACHE_PATH.exists():
            return _DB_ID_CACHE_PATH.read_text(encoding="utf-8").strip() or None
    except Exception:
        pass
    return None


def _save_cached_db_id(data_source_id: str) -> None:
    try:
        _DB_ID_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DB_ID_CACHE_PATH.write_text(data_source_id, encoding="utf-8")
    except Exception as e:
        logger.warning("notion_mirror: no se pudo cachear el data_source_id: %s", e)


def _create_database(root_page_id: str) -> str:
    """Crea la base 'Segundo Cerebro' una sola vez bajo la página raíz.

    Verificado en vivo contra la API real (29 Jul 2026): POST
    /v1/data_sources para CREAR una base falla en esta versión --
    "Creating new databases with data sources is not supported in this
    endpoint for API version 2025-09-03 and later. Use the Create
    Database API instead." La ruta real de creación sigue siendo POST
    /v1/databases, pero properties va anidado bajo initial_data_source
    (la API separa el contenedor "database" de su "data source" desde
    esta version). Devuelve el data_source_id (lo que de verdad se
    necesita para crear páginas después, no el database_id)."""
    result = _notion_request("POST", "databases", {
        "parent": {"type": "page_id", "page_id": root_page_id},
        "title": [{"type": "text", "text": {"content": _NOTION_DB_TITLE}}],
        "initial_data_source": {
            "properties": {
                "Título": {"title": {}},
                "Número": {"number": {}},
                "Tags": {"multi_select": {"options": []}},
                "Fecha": {"date": {}},
                "Ruta Obsidian": {"rich_text": {}},
                "Resumen": {"rich_text": {}},
            },
        },
    })
    data_sources = result.get("data_sources") or []
    if not data_sources or not data_sources[0].get("id"):
        raise NotionMirrorUnavailable(f"Notion no devolvió un data_source_id: {result}")
    return data_sources[0]["id"]


def _ensure_database_id() -> str:
    cached = _load_cached_db_id()
    if cached:
        return cached
    root_page_id = _get_root_page_id()
    db_id = _create_database(root_page_id)
    _save_cached_db_id(db_id)
    logger.info("notion_mirror: base de datos 'Segundo Cerebro' creada (id=%s)", db_id)
    return db_id


def _next_note_number() -> int:
    """Contador local secuencial -- Hermes es el único escritor de esta
    base, así que un contador local (sin round-trip a Notion) es simple
    y suficiente. No atómico entre procesos concurrentes (aceptable:
    un solo agente escribe esto en la práctica, mismo supuesto que el
    resto de cursores de archivo del proyecto)."""
    current = 0
    try:
        if _COUNTER_PATH.exists():
            current = int(_COUNTER_PATH.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        current = 0
    next_n = current + 1
    _COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    _COUNTER_PATH.write_text(str(next_n), encoding="utf-8")
    return next_n


def _truncate_rich_text(text: str, limit: int = 1900) -> str:
    # Notion rich_text por bloque tiene un tope real (~2000 chars) -- se
    # trunca con aviso en vez de que la llamada falle por longitud.
    if len(text) <= limit:
        return text
    return text[:limit] + "… (nota completa en Obsidian)"


def _excerpt(text: str, limit: int = 200) -> str:
    """Resumen corto para la columna de la tabla -- el contenido REAL
    vive en el cuerpo de la página (_content_to_blocks), no aquí. Antes
    del 29 Jul 2026 el contenido completo se aplastaba en esta propiedad
    -- se veía como una hoja de cálculo, no como una nota de verdad
    (pedido explícito de Arturo: "que sea bonito el boceto, no solo
    todo indexado")."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _content_to_blocks(contenido: str, ruta_obsidian: str) -> list[dict]:
    """Convierte la nota en bloques reales de Notion (párrafos), en vez de
    aplastarla en una propiedad de texto -- así la página se ve como una
    nota (con formato, espaciado, legible) al abrirla, no como una celda
    de tabla. Incluye un callout al inicio señalando la ruta real en
    Obsidian (fuente de verdad -- la nota completa vive ahí)."""
    blocks: list[dict] = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": f"Nota completa en Obsidian: {ruta_obsidian}"}}],
                "icon": {"type": "emoji", "emoji": "📓"},
            },
        }
    ]
    paragraphs = [p.strip() for p in contenido.split("\n\n") if p.strip()]
    for p in paragraphs[:95]:  # tope real de 100 bloques por llamada -- 1 ya usado por el callout
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": _truncate_rich_text(p)}}]},
        })
    return blocks


def mirror_note_to_notion(
    *, titulo: str, contenido: str, tags: list[str], ruta_obsidian: str, fecha: str,
) -> dict:
    """Crea la fila en Notion para una nota ya guardada en Obsidian.

    Devuelve {"success": bool, "numero": int|None, "error": str|None}.
    Nunca lanza -- fail-safe por diseño, ver docstring del módulo.

    Orden deliberado: valida credenciales/prerequisitos y resuelve la
    base de datos ANTES de gastar un número del contador -- si algo
    falla antes de escribir la fila real, el contador no debe avanzar
    (evita huecos en la numeración por intentos fallidos)."""
    if not os.environ.get("NOTION_API_KEY"):
        return {"success": False, "numero": None, "error": "NOTION_API_KEY no configurada en .env"}
    try:
        data_source_id = _ensure_database_id()
        numero = _next_note_number()
        _notion_request("POST", "pages", {
            "parent": {"type": "data_source_id", "data_source_id": data_source_id},
            "icon": {"type": "emoji", "emoji": "🧠"},
            "properties": {
                "Título": {"title": [{"text": {"content": titulo}}]},
                "Número": {"number": numero},
                "Tags": {"multi_select": [{"name": t} for t in tags[:20]]},
                "Fecha": {"date": {"start": fecha}},
                "Ruta Obsidian": {"rich_text": [{"text": {"content": ruta_obsidian}}]},
                "Resumen": {"rich_text": [{"text": {"content": _excerpt(contenido)}}]},
            },
            "children": _content_to_blocks(contenido, ruta_obsidian),
        })
        return {"success": True, "numero": numero, "error": None}
    except NotionMirrorUnavailable as e:
        logger.info("notion_mirror: no se sincronizo (best-effort, no bloquea Obsidian): %s", e)
        return {"success": False, "numero": None, "error": str(e)}
    except Exception as e:
        logger.warning("notion_mirror: fallo inesperado (best-effort): %s", e, exc_info=True)
        return {"success": False, "numero": None, "error": str(e)}
