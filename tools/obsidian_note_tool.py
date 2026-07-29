#!/usr/bin/env python3
"""obsidian_note -- HAS §B7: Hermes escribe en Obsidian SOLO notas de
conocimiento (apuntes, investigación, ideas conectadas), nunca estado
operativo (eso es Notion, tools/notion no vive aquí).

Decisión de arquitectura (29 Jul 2026, pedido explícito de Arturo): el
vault vive SOLO en esta máquina (sin sync a la MacBook) -- Arturo le
manda ideas/notas por chat y Hermes las va guardando aquí, organizadas.
Para visualizar desde la Mac: montar esta carpeta por SFTP (Finder ->
"Conectar al servidor") y abrir un Obsidian normal ahí -- sin sync,
sin costo, sin terminal de su parte.

Nunca sobrescribe una nota existente en silencio -- cada llamada crea
un archivo nuevo (con sufijo numérico si el nombre colisiona). El
escáner de secretos corre ANTES de escribir, mismo mecanismo real que
memory_tool.py usa para memoria estructurada (scope="strict") --
ninguna nota puede contener una credencial real sin que esto la
bloquee primero.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_VAULT_ROOT = "/mnt/seagate/obsidian"
_DEFAULT_FOLDER = "segundo-cerebro"


def get_vault_root() -> Path:
    return Path(os.environ.get("HERMES_OBSIDIAN_VAULT", _DEFAULT_VAULT_ROOT))


def _slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug[:80] or "nota"


def _unique_note_path(folder: Path, date_prefix: str, slug: str) -> Path:
    base = folder / f"{date_prefix}_{slug}.md"
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = folder / f"{date_prefix}_{slug}-{i}.md"
        if not candidate.exists():
            return candidate
        i += 1


def _format_frontmatter(*, title: str, tags: list[str], created: str) -> str:
    # ensure_ascii=False -- sin esto, cualquier acento/ñ sale escapado como
    # ó en el archivo (JSON valido, YAML lo parsea bien, pero se ve
    # feo si Arturo abre el .md crudo fuera de Obsidian). Bug real
    # encontrado en la primera nota real creada por el agente (29 Jul 2026).
    tags_yaml = (
        "[" + ", ".join(json.dumps(t, ensure_ascii=False) for t in tags) + "]"
        if tags else "[]"
    )
    return (
        "---\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"created: {created}\n"
        f"tags: {tags_yaml}\n"
        "origin: hermes\n"
        "---\n\n"
    )


def obsidian_save_note(
    titulo: str = "",
    contenido: str = "",
    tags: Optional[list] = None,
    carpeta: str = _DEFAULT_FOLDER,
) -> str:
    from tools.registry import tool_error

    if not isinstance(titulo, str) or not titulo.strip():
        return tool_error("obsidian_note requires a non-empty 'titulo'", success=False)
    if not isinstance(contenido, str) or not contenido.strip():
        return tool_error("obsidian_note requires non-empty 'contenido'", success=False)

    tags = tags if isinstance(tags, list) else []
    tags = [str(t) for t in tags if isinstance(t, (str, int, float))]

    # Nunca guardar sin escanear primero -- misma regla que memoria
    # estructurada (tools/memory_tool.py, tools/threat_patterns.py).
    try:
        from tools.threat_patterns import first_threat_message
        threat = first_threat_message(f"{titulo}\n{contenido}", scope="strict")
        if threat:
            return tool_error(
                f"Nota bloqueada por el escáner de secretos: {threat}", success=False,
            )
    except Exception as e:
        logger.warning("obsidian_note: threat scan failed, blocking to be safe: %s", e, exc_info=True)
        return tool_error(f"No se pudo escanear la nota antes de guardarla: {e}", success=False)

    vault_root = get_vault_root()
    if not vault_root.exists():
        return tool_error(
            f"El vault de Obsidian no existe todavia en {vault_root} -- "
            "requiere crearse una vez con permisos de Arturo (mkdir + chown), "
            "ver docs/ESTADO.md.",
            success=False,
        )

    carpeta_limpia = re.sub(r"[^a-zA-Z0-9_/-]", "", carpeta or _DEFAULT_FOLDER).strip("/") or _DEFAULT_FOLDER
    folder = vault_root / carpeta_limpia
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return tool_error(f"No se pudo crear la carpeta {folder}: {e}", success=False)

    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    date_prefix = time.strftime("%Y-%m-%d")
    slug = _slugify(titulo)
    note_path = _unique_note_path(folder, date_prefix, slug)

    body = _format_frontmatter(title=titulo, tags=tags, created=now) + contenido.rstrip() + "\n"
    try:
        note_path.write_text(body, encoding="utf-8")
    except Exception as e:
        return tool_error(f"No se pudo escribir la nota: {e}", success=False)

    return json.dumps({
        "success": True,
        "path": str(note_path.relative_to(vault_root)),
        "message": f"Nota guardada en {note_path.relative_to(vault_root)}",
    }, ensure_ascii=False)


def check_obsidian_note_requirements() -> bool:
    return get_vault_root().exists()


OBSIDIAN_NOTE_SCHEMA = {
    "name": "obsidian_note",
    "description": (
        "Save a knowledge note (idea, research, connected concept) to Arturo's "
        "local Obsidian vault -- his 'second brain'. Use this for durable "
        "knowledge worth keeping and cross-referencing later (ideas for "
        "content, research findings, deep notes on a topic), NOT for "
        "operational state (tasks, todos, status) -- that belongs in the "
        "todo/kanban tools instead, per the Notion/Obsidian split (HAS §B7).\n\n"
        "Never silently overwrites -- each call creates a new dated note file. "
        "If the user wants to add to an existing note, use file tools "
        "(read_file/patch) on the specific note path instead of this tool.\n\n"
        "The note goes through the same secret scanner as structured memory -- "
        "a note containing a real credential will be blocked, not saved."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "titulo": {
                "type": "string",
                "description": "Note title (used to generate the filename).",
            },
            "contenido": {
                "type": "string",
                "description": "Note body in Markdown. Use [[wikilinks]] to reference other notes by title for Obsidian's graph view.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for the note's frontmatter (Obsidian tag search/graph filtering).",
            },
            "carpeta": {
                "type": "string",
                "description": "Subfolder inside the vault (default 'segundo-cerebro'). Use topic-specific folders (e.g. 'escuela/matematicas', 'guiones') when it clearly fits an existing HAS-defined category.",
                "default": "segundo-cerebro",
            },
        },
        "required": ["titulo", "contenido"],
    },
}


from tools.registry import registry  # noqa: E402

registry.register(
    name="obsidian_note",
    toolset="obsidian_note",
    schema=OBSIDIAN_NOTE_SCHEMA,
    handler=lambda args, **kw: obsidian_save_note(
        titulo=args.get("titulo") or "",
        contenido=args.get("contenido") or "",
        tags=args.get("tags"),
        carpeta=args.get("carpeta") or _DEFAULT_FOLDER,
    ),
    check_fn=check_obsidian_note_requirements,
    emoji="🗒️",
)
