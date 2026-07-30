"""Herramienta en vivo para que Hermes corrija su propia memoria estructurada
(``memoria_estructurada``, la que llena ``/memoria``) cuando Arturo se lo pide
explícitamente en la conversación -- sin depender de una sesión de Claude
Code (pedido de Arturo, 29 Jul 2026).

Alcance deliberadamente angosto, mismo principio que memoria_review.py:
- SOLO borra (``remove``). Crear hechos nuevos sigue pasando EXCLUSIVAMENTE
  por la revisión de /memoria, uno por uno -- esta herramienta nunca escribe.
- La identidad de quien pide el borrado se resuelve desde la sesión real de
  Telegram (``session_id`` -> ``sessions.user_id``), nunca desde un
  parámetro que el modelo podría rellenar mal. Estructuralmente no puede
  tocar filas de la cuenta QA (``origen='qa'``) ni de otro user_id.
- Cada borrado queda en un log de auditoría en disco ANTES de borrar, para
  que un borrado "irreversible" desde la conversación siga siendo
  reconstruible a mano si hiciera falta.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from tools.registry import registry, tool_error

logger = logging.getLogger(__name__)

STATE_DB = Path.home() / ".hermes" / "state.db"
AUDIT_LOG = Path.home() / ".hermes" / "logs" / "memoria_hechos_borrados.log"


def _real_user_id_for_session(session_id: Optional[str]) -> Optional[str]:
    """Resuelve el user_id real de Telegram dueño de esta sesión -- nunca se
    confía en un user_id que llegara como argumento del modelo."""
    if not session_id or not STATE_DB.exists():
        return None
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE id = ? AND source = 'telegram'",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row and row[0] else None


def _audit_log(user_id: str, hecho_id: int, hecho: str) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} user_id={user_id} id={hecho_id} hecho={hecho!r}\n")


def memoria_hecho_tool(old_text: str = "", session_id: Optional[str] = None) -> str:
    old_text = (old_text or "").strip()
    if not old_text:
        return tool_error(
            "old_text es requerido -- un fragmento corto y único del hecho a borrar.",
            success=False,
        )

    user_id = _real_user_id_for_session(session_id)
    if not user_id:
        return tool_error(
            "No se pudo verificar de forma segura quién pidió esto -- no se borró nada.",
            success=False,
        )

    conn = sqlite3.connect(STATE_DB)
    try:
        rows = conn.execute(
            "SELECT id, hecho FROM memoria_estructurada "
            "WHERE user_id = ? AND (origen IS NULL OR origen != 'qa') AND hecho LIKE ?",
            (user_id, f"%{old_text}%"),
        ).fetchall()
        if not rows:
            existentes = conn.execute(
                "SELECT hecho FROM memoria_estructurada "
                "WHERE user_id = ? AND (origen IS NULL OR origen != 'qa') ORDER BY id",
                (user_id,),
            ).fetchall()
            listado = "\n".join(f"- {r[0]}" for r in existentes) or "(no hay hechos guardados)"
            return tool_error(
                f'No encontré ningún hecho que contenga "{old_text}". Hechos actuales:\n{listado}',
                success=False,
            )
        if len(rows) > 1:
            listado = "\n".join(f"- {r[1]}" for r in rows)
            return tool_error(
                f'"{old_text}" coincide con {len(rows)} hechos, dame un fragmento más específico:\n{listado}',
                success=False,
            )
        hecho_id, hecho_texto = rows[0]
        _audit_log(user_id, hecho_id, hecho_texto)
        conn.execute("DELETE FROM memoria_estructurada WHERE id = ?", (hecho_id,))
        conn.commit()
    finally:
        conn.close()

    return json.dumps(
        {"success": True, "message": f'Hecho borrado: "{hecho_texto}"'},
        ensure_ascii=False,
    )


MEMORIA_HECHO_SCHEMA = {
    "name": "memoria_hecho",
    "description": (
        "Borra UN hecho ya guardado en la memoria estructurada de Arturo (la que "
        "llena /memoria) cuando el mismo Arturo lo pide explícitamente en la "
        "conversación en curso (ej. 'borra ese hecho que dice que uso DeepSeek "
        "para X'). NUNCA la uses para agregar o editar hechos nuevos -- crear "
        "hechos pasa EXCLUSIVAMENTE por la revisión de /memoria, uno por uno. "
        "Solo bórralo si Arturo señaló ESE hecho específico en este mismo turno "
        "o el inmediatamente anterior -- nunca por iniciativa propia ni por "
        "inferencia."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "old_text": {
                "type": "string",
                "description": "Fragmento corto y único del texto exacto del hecho a borrar.",
            },
        },
        "required": ["old_text"],
    },
}

registry.register(
    name="memoria_hecho",
    toolset="memory",
    schema=MEMORIA_HECHO_SCHEMA,
    handler=lambda args, **kw: memoria_hecho_tool(
        old_text=args.get("old_text", ""),
        session_id=kw.get("session_id"),
    ),
    emoji="🗑️",
)
