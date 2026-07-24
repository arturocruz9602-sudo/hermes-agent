"""SQL-backed memory store for the QA automation account (HAS OT-QA, Opción 3).

Same public interface ``tools/memory_tool.py``'s ``memory_tool()`` and
``agent/system_prompt.py`` actually call on a store (``add``, ``replace``,
``remove``, ``apply_batch``, ``load_from_disk``, ``format_for_system_prompt``)
-- so it drops into ``agent._memory_store`` as a straight substitute, with
NO changes needed to ``memory_tool()`` itself.

Backed by ``memoria_estructurada`` (state.db), tagged with the REAL acting
``user_id`` and ``origen='qa'`` -- this is what makes HAS
GUION_PRUEBAS.md's M.A5 ("consulta por user_id -- cero cruces")
literally, not just conceptually, true: a real SQL query filtered by
user_id, not a same-file convention.

Deliberately NOT the same code path Arturo's real memory uses
(``tools/memory_tool.py``'s ``MemoryStore``, backed by MEMORY.md/USER.md).
That split is intentional, not a stopgap: HAS Fase 4 already designs
Arturo's real structured memory (Capa 2) as APPROVAL-gated ("hechos
aprobados", weekly review via Telegram) -- auto-committing QA's test
writes the same way would be wrong even once Fase 4 ships for real.
This store's writes are meant to be automatic (it's a test sandbox);
Arturo's are meant to be reviewed. Two mechanisms by design, sharing the
same underlying table.

Scope, deliberately kept small: no drift-detection, no consolidation
prompts, no file locking (SQLite's own transaction handles concurrent
writers) -- this is a testing sandbox, not the elaborate real-memory
workflow. Char budget check is approximate, not exact.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_DB_PATH = Path.home() / ".hermes" / "state.db"

_VALID_TARGETS = {"memory", "user"}
_ENTRY_DELIMITER = "\n§\n"

# memoria_estructurada.categoria has a CHECK constraint limited to a fixed
# set (personal/académico/técnico/financiero/meta) -- QA test entries have
# no real category, 'personal' is the closest generic fit and satisfies
# the constraint without inventing a new allowed value for test data.
_QA_CATEGORIA = "personal"


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Idempotent schema reconciliation for this store's needs.
    ``memoria_estructurada`` predates and lives outside
    ``hermes_state.py``'s declarative schema system -- see
    ``scripts/limpiar_memoria_qa.py``'s module docstring for the same
    note. ``origen`` was added there (23 Jul); ``user_id``/``target``
    are added here."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(memoria_estructurada)")}
    if "origen" not in cols:
        conn.execute("ALTER TABLE memoria_estructurada ADD COLUMN origen TEXT")
    if "user_id" not in cols:
        conn.execute("ALTER TABLE memoria_estructurada ADD COLUMN user_id TEXT")
    if "target" not in cols:
        conn.execute("ALTER TABLE memoria_estructurada ADD COLUMN target TEXT")
    conn.commit()


class SqlMemoryStore:
    """Drop-in replacement for ``tools.memory_tool.MemoryStore``, scoped to
    one ``user_id``. Every row this instance writes/reads carries
    ``origen='qa'`` and that exact ``user_id`` -- never touches (or even
    queries) rows without that origen/user_id pair, so it structurally
    cannot see or affect Arturo's real memory rows (which this store
    never writes -- Arturo's path stays on the file-based MemoryStore,
    untouched)."""

    def __init__(
        self,
        user_id: str,
        db_path: Path = STATE_DB_PATH,
        memory_char_limit: int = 2200,
        user_char_limit: int = 1375,
    ):
        if not user_id:
            raise ValueError("SqlMemoryStore requires a non-empty user_id")
        self.user_id = user_id
        self._db_path = db_path
        self._char_limits = {"memory": memory_char_limit, "user": user_char_limit}
        self._system_prompt_snapshot: Dict[str, str] = {}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        _ensure_columns(conn)
        return conn

    def _rows_for(self, conn: sqlite3.Connection, target: str) -> List[sqlite3.Row]:
        conn.row_factory = sqlite3.Row
        return list(conn.execute(
            "SELECT id, hecho FROM memoria_estructurada "
            "WHERE origen = 'qa' AND user_id = ? AND target = ? "
            "ORDER BY id ASC",
            (self.user_id, target),
        ))

    def _char_count(self, conn: sqlite3.Connection, target: str) -> int:
        rows = self._rows_for(conn, target)
        return len(_ENTRY_DELIMITER.join(r["hecho"] for r in rows))

    # -- Public interface (mirrors tools.memory_tool.MemoryStore) ----------

    def load_from_disk(self) -> None:
        """Same name as the file-backed store for interface compatibility
        (agent/system_prompt.py calls this unconditionally before reading
        format_for_system_prompt) -- here it (re)builds the frozen
        snapshot from SQL instead of re-reading a file."""
        conn = self._connect()
        try:
            for target in _VALID_TARGETS:
                rows = self._rows_for(conn, target)
                entries = [r["hecho"] for r in rows]
                self._system_prompt_snapshot[target] = self._render_block(target, entries)
        finally:
            conn.close()

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    def add(self, target: str, content: str) -> Dict[str, Any]:
        if target not in _VALID_TARGETS:
            return {"success": False, "error": f"Invalid target '{target}'."}
        content = (content or "").strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        conn = self._connect()
        try:
            rows = self._rows_for(conn, target)
            if any(r["hecho"] == content for r in rows):
                return self._success_response(conn, target, "Entry already exists (no duplicate added).")

            limit = self._char_limits[target]
            new_total = len(_ENTRY_DELIMITER.join([r["hecho"] for r in rows] + [content]))
            if new_total > limit:
                current = self._char_count(conn, target)
                return {
                    "success": False,
                    "error": (
                        f"Memory (QA) at {current:,}/{limit:,} chars. "
                        "Consolidate or remove entries before adding more."
                    ),
                    "usage": f"{current:,}/{limit:,}",
                }

            conn.execute(
                "INSERT INTO memoria_estructurada "
                "(hecho, entidad, categoria, fecha_registro, fuente, origen, user_id, target) "
                "VALUES (?, 'QA', ?, ?, 'qa_memory_tool', 'qa', ?, ?)",
                (content, _QA_CATEGORIA, time.strftime("%Y-%m-%d %H:%M:%S"), self.user_id, target),
            )
            conn.commit()
            return self._success_response(conn, target, "Entry added.")
        finally:
            conn.close()

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        if target not in _VALID_TARGETS:
            return {"success": False, "error": f"Invalid target '{target}'."}
        old_text = (old_text or "").strip()
        new_content = (new_content or "").strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete entries."}

        conn = self._connect()
        try:
            rows = self._rows_for(conn, target)
            match = next((r for r in rows if old_text in r["hecho"]), None)
            if match is None:
                return self._missing_old_text_error(conn, target)

            conn.execute(
                "UPDATE memoria_estructurada SET hecho = ?, fecha_registro = ? WHERE id = ?",
                (new_content, time.strftime("%Y-%m-%d %H:%M:%S"), match["id"]),
            )
            conn.commit()
            return self._success_response(conn, target, "Entry replaced.")
        finally:
            conn.close()

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        if target not in _VALID_TARGETS:
            return {"success": False, "error": f"Invalid target '{target}'."}
        old_text = (old_text or "").strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        conn = self._connect()
        try:
            rows = self._rows_for(conn, target)
            match = next((r for r in rows if old_text in r["hecho"]), None)
            if match is None:
                return self._missing_old_text_error(conn, target)

            conn.execute("DELETE FROM memoria_estructurada WHERE id = ?", (match["id"],))
            conn.commit()
            return self._success_response(conn, target, "Entry removed.")
        finally:
            conn.close()

    def apply_batch(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for op in operations or []:
            action = op.get("action")
            if action == "add":
                results.append(self.add(target, op.get("content", "")))
            elif action == "replace":
                results.append(self.replace(target, op.get("old_text", ""), op.get("content", "")))
            elif action == "remove":
                results.append(self.remove(target, op.get("old_text", "")))
            else:
                results.append({"success": False, "error": f"Unknown action '{action}'."})
        conn = self._connect()
        try:
            ok = all(r.get("success") for r in results)
            return {
                "success": ok,
                "done": ok,
                "target": target,
                "results": results,
                **({"usage": self._success_response(conn, target)["usage"]} if ok else {}),
            }
        finally:
            conn.close()

    # -- Internal helpers ----------------------------------------------

    def _success_response(self, conn: sqlite3.Connection, target: str, message: str = None) -> Dict[str, Any]:
        rows = self._rows_for(conn, target)
        current = self._char_count(conn, target)
        limit = self._char_limits[target]
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        resp = {
            "success": True,
            "done": True,
            "target": target,
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(rows),
        }
        if message:
            resp["message"] = message
        resp["note"] = "Write saved (cuenta QA). This update is complete — do not repeat it."
        return resp

    def _missing_old_text_error(self, conn: sqlite3.Connection, target: str) -> Dict[str, Any]:
        rows = self._rows_for(conn, target)
        return {
            "success": False,
            "error": "No entry found containing that text.",
            "current_entries": [r["hecho"] for r in rows],
        }

    def _render_block(self, target: str, entries: List[str]) -> str:
        if not entries:
            return ""
        limit = self._char_limits[target]
        content = _ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        label = "USER PROFILE (who the user is)" if target == "user" else "MEMORY (your personal notes)"
        header = f"{label} — CUENTA QA, prueba, no es la memoria real de Arturo [{pct}% — {current:,}/{limit:,} chars]"
        separator = "═" * 46
        return f"{separator}\n{header}\n{separator}\n{content}"
