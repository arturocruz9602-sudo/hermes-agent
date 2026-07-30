"""Vista "Avance HAS" en Notion (HAS Fase 5, OT-5 Bloque 2, plan nocturno
30 jul 2026) -- la primera de las 6 vistas operativas planeadas.

Snapshot en vivo del avance automatizado (salida real de
``~/.hermes/scripts/has_progress.py``) en una sola página bajo "Hermes"
en Notion, que se REEMPLAZA en cada sync -- no es un historial que
crece, es un tablero que muestra el estado ACTUAL. Sync unidireccional
Hermes->Notion, nunca al revés (Notion aquí es solo lectura para
Arturo, igual que ``notion_mirror.py``).

Best-effort por diseño, mismo principio que ``notion_mirror.py``: si
Notion falla (sin API key, sin red, página raíz no compartida), el
sync se salta sin tronar nada más -- este módulo nunca es una
dependencia dura de otro mecanismo.

**Las otras 5 vistas planeadas (Hoy, Kanban espejo, Finanzas, Cola de
tareas, Escuela) NO están construidas todavía.** Verificado en vivo
contra la API real de Notion (30 jul 2026): de las bases de datos
personales de Arturo mencionadas en
``~/.hermes/skills/productivity/notion/SKILL.md`` ("Finanzas",
"Proyectos", "Tareas académicas", "Ideas"), NINGUNA está compartida con
la integración hoy -- solo "Segundo Cerebro" (creada por
``notion_mirror.py`` esta misma noche) aparece en ``/v1/search``.
Finanzas/Escuela necesitan que Arturo comparta esas bases existentes
con la integración antes de que Hermes pueda escribir ahí. Kanban
espejo/Cola de tareas no tienen ese bloqueo (Hermes ya es dueño de
``kanban.db``/``task_queue``), pero sí necesitan una decisión de diseño
(¿base nueva dedicada, o reusar "Proyectos"?) antes de construirlas --
ver docs/ESTADO.md, Bloque 5.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from tools import notion_mirror as _nm

# Se llama siempre como _nm.<nombre> (nunca importado por nombre suelto) a
# propósito: _get_root_page_id() internamente llama a
# tools.notion_mirror._notion_request -- si este módulo importara
# _notion_request por nombre, un test que solo mockeara
# tools.notion_avance_has._notion_request dejaría pasar la llamada REAL
# de dentro de _get_root_page_id sin querer (encontrado en vivo
# escribiendo las pruebas de este mismo módulo, 30 jul 2026 -- un mock
# a medias que parecía funcionar hasta que pegó contra la API real).
NotionMirrorUnavailable = _nm.NotionMirrorUnavailable

logger = logging.getLogger(__name__)

_PAGE_TITLE = "Avance HAS"
_PAGE_ID_CACHE_PATH = Path.home() / ".hermes" / ".avance_has_notion_page_id"
_HAS_PROGRESS_SCRIPT = Path.home() / ".hermes" / "scripts" / "has_progress.py"
_BLOCK_TEXT_LIMIT = 1900  # tope real de rich_text de Notion es ~2000 chars
_BLOCK_COUNT_LIMIT = 100  # tope real de bloques por llamada de creación


def _load_cached_page_id() -> Optional[str]:
    try:
        if _PAGE_ID_CACHE_PATH.exists():
            return _PAGE_ID_CACHE_PATH.read_text(encoding="utf-8").strip() or None
    except Exception:
        pass
    return None


def _save_cached_page_id(page_id: str) -> None:
    try:
        _PAGE_ID_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PAGE_ID_CACHE_PATH.write_text(page_id, encoding="utf-8")
    except Exception as e:
        logger.warning("notion_avance_has: no se pudo cachear el page_id: %s", e)


def _create_page(root_page_id: str) -> str:
    result = _nm._notion_request("POST", "pages", {
        "parent": {"type": "page_id", "page_id": root_page_id},
        "properties": {
            "title": {"title": [{"text": {"content": _PAGE_TITLE}}]},
        },
    })
    page_id = result.get("id")
    if not page_id:
        raise NotionMirrorUnavailable(f"Notion no devolvió un page_id: {result}")
    return page_id


def _ensure_page_id() -> str:
    cached = _load_cached_page_id()
    if cached:
        return cached
    root_page_id = _nm._get_root_page_id()
    page_id = _create_page(root_page_id)
    _save_cached_page_id(page_id)
    logger.info("notion_avance_has: página 'Avance HAS' creada (id=%s)", page_id)
    return page_id


def _run_has_progress() -> str:
    """Corre has_progress.py (SIN --quiet -- aquí sí queremos el detalle
    completo, línea por línea, para el tablero) y regresa su salida."""
    if not _HAS_PROGRESS_SCRIPT.exists():
        return f"has_progress.py no encontrado en {_HAS_PROGRESS_SCRIPT}"
    try:
        result = subprocess.run(
            [sys.executable, str(_HAS_PROGRESS_SCRIPT)],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        return f"error corriendo has_progress.py: {type(e).__name__}: {e}"
    return result.stdout or result.stderr or "(sin salida)"


def _chunk_text(text: str, limit: int = _BLOCK_TEXT_LIMIT) -> list[str]:
    """Parte *text* en trozos de a lo más *limit* chars, sin cortar
    líneas a la mitad (mejor legibilidad en el bloque de código)."""
    lines = text.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        if current and current_len + len(line) + 1 > limit:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def _build_blocks(progress_output: str) -> list[dict]:
    blocks: list[dict] = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": (
                    f"Actualizado automáticamente cada 15 min -- última "
                    f"corrida: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )}}],
                "icon": {"type": "emoji", "emoji": "🔄"},
            },
        },
    ]
    for chunk in _chunk_text(progress_output):
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"text": {"content": chunk}}],
                "language": "plain text",
            },
        })
    return blocks[:_BLOCK_COUNT_LIMIT]


def _clear_page_blocks(page_id: str) -> None:
    """Borra todos los bloques hijos existentes de la página -- así cada
    sync REEMPLAZA el contenido en vez de acumularlo (esto es un
    tablero de estado actual, no un historial que crece)."""
    result = _nm._notion_request("GET", f"blocks/{page_id}/children?page_size=100")
    for child in result.get("results", []):
        child_id = child.get("id")
        if child_id:
            _nm._notion_request("DELETE", f"blocks/{child_id}")


def sync_avance_has() -> dict:
    """Punto de entrada del sync -- llamado por el timer nocturno cada
    15 min. Nunca lanza excepción hacia el caller: siempre regresa un
    dict con 'success' (fail-safe, mismo principio que
    notion_mirror.mirror_note_to_notion)."""
    if not os.environ.get("NOTION_API_KEY"):
        return {"success": False, "error": "NOTION_API_KEY no configurada en .env"}
    try:
        page_id = _ensure_page_id()
        progress_output = _run_has_progress()
        _clear_page_blocks(page_id)
        blocks = _build_blocks(progress_output)
        _nm._notion_request("PATCH", f"blocks/{page_id}/children", {"children": blocks})
    except NotionMirrorUnavailable as e:
        logger.warning("notion_avance_has: sync falló (fail-safe): %s", e)
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001 -- fail-safe por diseño, nunca tronar el timer
        logger.warning("notion_avance_has: sync falló con error inesperado: %s", e)
        return {"success": False, "error": f"{type(e).__name__}: {e}"}
    return {"success": True, "page_id": page_id}


if __name__ == "__main__":
    # Carga .env explícitamente -- este módulo se invoca como script suelto
    # desde el timer systemd (hermes-notion-avance-has.service), que no
    # garantiza heredar el entorno de shell donde vive NOTION_API_KEY.
    from hermes_cli.env_loader import load_hermes_dotenv

    load_hermes_dotenv()
    resultado = sync_avance_has()
    print(resultado)
    raise SystemExit(0 if resultado.get("success") else 1)
