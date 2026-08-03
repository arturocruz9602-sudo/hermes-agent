"""Vista "Finanzas" en Notion (HAS Fase 5, OT-5 Bloque 2, Bloque F5-1
"Tablero único" -- 02 ago 2026) -- segunda de las 6 vistas operativas,
después de "Avance HAS" (tools/notion_avance_has.py, mismo patrón).

Snapshot en vivo del dinero real de Arturo (``~/.hermes/libreta.db``, la
libreta reconciliada de AR, no ``state.db``) en una sola página bajo
"Hermes" en Notion, que se REEMPLAZA en cada sync -- no es un historial
que crece, es un tablero del mes actual. Sync unidireccional
Hermes->Notion (Notion es espejo de solo lectura para Arturo, B7:
Obsidian/libreta.db son la fuente de verdad, nunca Notion).

Solo lee la libreta (``solo_lectura=True``, mismo patrón que
brief_matutino.py / cierre_del_dia_audio.py) -- este módulo nunca
escribe un gasto ni una meta.

Best-effort por diseño, mismo principio que notion_avance_has.py: si
Notion falla (sin API key, sin red, página raíz no compartida) o si la
libreta no existe todavía, el sync se salta sin tronar nada más.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from libreta import Libreta, entorno_activo  # noqa: E402

from tools import notion_mirror as _nm

# Mismo motivo que notion_avance_has.py: siempre _nm.<nombre>, nunca
# importado suelto -- _get_root_page_id() llama _notion_request por
# dentro, y un mock solo de este módulo dejaría pasar esa llamada real.
NotionMirrorUnavailable = _nm.NotionMirrorUnavailable

logger = logging.getLogger(__name__)

_PAGE_TITLE = "Finanzas"
_PAGE_ID_CACHE_PATH = Path.home() / ".hermes" / ".finanzas_notion_page_id"
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
        logger.warning("notion_finanzas: no se pudo cachear el page_id: %s", e)


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
    logger.info("notion_finanzas: página 'Finanzas' creada (id=%s)", page_id)
    return page_id


def _heading(texto: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": texto}}]},
    }


def _bullet(texto: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"text": {"content": texto}}]},
    }


def _paragraph(texto: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": texto}}]},
    }


def _read_libreta_snapshot(entorno: Optional[str] = None) -> dict:
    """Lee el mes en curso de la libreta -- devuelve datos crudos, sin
    tocar Notion, para poder probar el armado de bloques por separado."""
    ent = entorno_activo(entorno)
    with Libreta(ent, solo_lectura=True) as lib:
        balance = lib.balance()
        categorias = lib.gastos_por_categoria()
        # A diferencia del brief en audio (que filtra los sin fecha porque
        # no son accionables al hablarlos), aquí SÍ se muestran: es
        # justo la señal de "falta confirmar día de pago" que el propio
        # docstring de pagos_recurrentes_por_vencer describe.
        pagos = list(lib.pagos_recurrentes_por_vencer(dentro_de_dias=7))
        metas = list(lib.con.execute(
            "SELECT * FROM ahorro_metas WHERE activa = 1 ORDER BY nombre"
        ))
    return {"balance": balance, "categorias": categorias, "pagos": pagos, "metas": metas}


def _build_blocks(snapshot: dict) -> list[dict]:
    balance = snapshot["balance"]
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
        _heading(f"Balance del mes ({balance['desde']} a {balance['hasta']})"),
        _paragraph(
            f"Ingresos: ${balance['ingresos']:.0f} MXN · "
            f"Gastos: ${balance['gastos']:.0f} MXN · "
            f"Saldo: ${balance['saldo']:.0f} MXN"
        ),
    ]

    blocks.append(_heading("Gastos por categoría"))
    if snapshot["categorias"]:
        for c in snapshot["categorias"]:
            blocks.append(_bullet(f"{c['categoria']}: ${c['total']:.0f} MXN ({c['n']} mov.)"))
    else:
        blocks.append(_paragraph("Sin gastos registrados este mes."))

    blocks.append(_heading("Metas de ahorro"))
    if snapshot["metas"]:
        for m in snapshot["metas"]:
            faltante = m["objetivo_mxn"] - m["acumulado_mxn"]
            limite = f" · límite {m['fecha_limite']}" if m["fecha_limite"] else ""
            blocks.append(_bullet(
                f"{m['nombre']}: ${m['acumulado_mxn']:.0f} de ${m['objetivo_mxn']:.0f} MXN "
                f"(faltan ${faltante:.0f}){limite}"
            ))
    else:
        blocks.append(_paragraph("Sin metas activas."))

    blocks.append(_heading("Pagos próximos (7 días)"))
    if snapshot["pagos"]:
        for p in snapshot["pagos"]:
            vence = p["proximo_pago"] or "por confirmar (sin día registrado aún)"
            blocks.append(_bullet(f"{p['nombre']}: ${p['monto_mxn']:.0f} MXN — vence {vence}"))
    else:
        blocks.append(_paragraph("Ningún pago recurrente activo."))

    return blocks[:_BLOCK_COUNT_LIMIT]


def _clear_page_blocks(page_id: str) -> None:
    """Reemplaza en vez de acumular -- mismo patrón que notion_avance_has.py."""
    result = _nm._notion_request("GET", f"blocks/{page_id}/children?page_size=100")
    for child in result.get("results", []):
        child_id = child.get("id")
        if child_id:
            _nm._notion_request("DELETE", f"blocks/{child_id}")


def sync_finanzas(entorno: Optional[str] = None) -> dict:
    """Punto de entrada del sync -- llamado por el timer cada 15 min.
    Nunca lanza excepción hacia el caller: siempre regresa un dict con
    'success' (fail-safe, mismo principio que notion_avance_has.py)."""
    if not os.environ.get("NOTION_API_KEY"):
        return {"success": False, "error": "NOTION_API_KEY no configurada en .env"}
    try:
        snapshot = _read_libreta_snapshot(entorno)
        page_id = _ensure_page_id()
        blocks = _build_blocks(snapshot)
        _clear_page_blocks(page_id)
        _nm._notion_request("PATCH", f"blocks/{page_id}/children", {"children": blocks})
    except NotionMirrorUnavailable as e:
        logger.warning("notion_finanzas: sync falló (fail-safe): %s", e)
        return {"success": False, "error": str(e)}
    except FileNotFoundError as e:
        logger.warning("notion_finanzas: libreta no encontrada (fail-safe): %s", e)
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001 -- fail-safe por diseño, nunca tronar el timer
        logger.warning("notion_finanzas: sync falló con error inesperado: %s", e)
        return {"success": False, "error": f"{type(e).__name__}: {e}"}
    return {"success": True, "page_id": page_id}


if __name__ == "__main__":
    # Carga .env explícitamente -- este módulo se invoca como script suelto
    # desde el timer systemd (hermes-notion-finanzas.service), que no
    # garantiza heredar el entorno de shell donde vive NOTION_API_KEY.
    from hermes_cli.env_loader import load_hermes_dotenv

    load_hermes_dotenv()
    resultado = sync_finanzas()
    print(resultado)
    raise SystemExit(0 if resultado.get("success") else 1)
