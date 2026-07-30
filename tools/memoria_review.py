"""Cola de revisión interactiva de candidatos de memoria (HAS OT-4, Bloque 1.1).

Presenta, uno a la vez, los hechos candidatos generados por
``scripts/fase2_extract_candidates.py`` -- vía botones de Telegram
[Aprobar]/[Rechazar] -- y SOLO entonces escribe a ``memoria_estructurada``.
Nunca escribe nada sin ese "sí" explícito de Arturo, candidato por candidato.

Mismo patrón de estado que ``tools/slash_confirm.py`` (dict a nivel de
módulo, keyed por session_key, para que los adaptadores resuelvan el
callback sin referencia al GatewayRunner), pero con una COLA en vez de una
sola confirmación, porque revisar candidatos es por definición un lote.

v1 deliberadamente sin botón "Editar" -- solo Aprobar/Rechazar. Si un hecho
está mal redactado, se rechaza y Arturo se lo dicta a Hermes directo por
chat (``tools/memory_tool.py`` ya cubre ese camino). Supuesto marcado,
reportado en el cierre de sesión del 28 Jul 2026.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.threat_patterns import scan_for_threats

logger = logging.getLogger(__name__)

STATE_DB = Path.home() / ".hermes" / "state.db"
PENDIENTES_DIR = Path.home() / ".hermes"

# Aprobado en platforms/pairing/telegram-approved.json (mismo valor que
# scripts/fase2_extract_candidates.py::ARTURO_USER_ID).
ARTURO_USER_ID = "8899197004"

_SANDBOX_SOURCE = "__sandbox__"

# Candidatos sinteticos para que la cuenta QA (tools/qa_identity.py) pueda
# ejercer el mecanismo real de botones sin tocar jamas la cola real de
# Arturo -- mismo principio que Bloque AG (memoria QA separada por
# origen/user_id en la misma tabla). limpiar_memoria_qa.py ya sabe borrar
# filas origen='qa'.
def _build_sandbox_queue() -> List[Dict[str, Any]]:
    return [
        {
            "texto": "PRUEBA QA: hecho sintetico de prueba del flujo /memoria, no es una afirmacion real.",
            "categoria": "preferencia",
            "fuente_verificada": "sandbox de pruebas, sin sesion real",
            "_source_file": _SANDBOX_SOURCE,
            "_source_index": 0,
        },
        {
            "texto": "PRUEBA QA: segundo hecho sintetico, para probar el encadenado al siguiente candidato.",
            "categoria": "decision",
            "fuente_verificada": "sandbox de pruebas, sin sesion real",
            "_source_file": _SANDBOX_SOURCE,
            "_source_index": 1,
        },
    ]

# El extractor (fase2_extract_candidates.py) propone categorías de TIPO de
# hecho (preferencia/dato_dispositivo/proyecto_en_curso/correccion/decision).
# memoria_estructurada exige una categoría de TEMA con un CHECK constraint
# fijo (personal/académico/técnico/financiero/meta, HAS E3) -- no son el
# mismo eje. Este mapeo es un supuesto marcado, no una equivalencia exacta.
_CATEGORIA_MAP = {
    "preferencia": "personal",
    "dato_dispositivo": "técnico",
    "proyecto_en_curso": "técnico",
    "correccion": "técnico",
    "decision": "personal",
}
_CATEGORIA_DEFAULT = "personal"

# Igual que slash_confirm.py: estado en memoria de proceso, keyed por
# session_key. Una revisión de candidatos no es tan urgente como un
# slash-confirm normal -- 1h de margen entre botones sin que expire.
_pending: Dict[str, Dict[str, Any]] = {}
_lock = threading.RLock()
DEFAULT_TIMEOUT_SECONDS = 3600


def _normalize_texto(texto: str) -> str:
    return " ".join((texto or "").strip().lower().split())


def _load_queue() -> List[Dict[str, Any]]:
    """Junta los candidatos con estado_revision pendiente de todos los
    archivos fase2_pendientes_*.json en disco, en orden de generación.

    Confirmado el 29 jul: corridas concurrentes del extractor (antes del
    candado agregado en fase2_extract_candidates.py) dejaron candidatos con
    texto EXACTAMENTE igual repartidos en varios archivos -- se descarta el
    repetido (se queda el más antiguo) en vez de hacer que Arturo lo revise
    dos veces. No es dedup difuso: solo texto idéntico tras normalizar
    espacios/mayúsculas: dos parafraseos del mismo hecho siguen llegando por
    separado a propósito, porque no hay forma segura de saber que son "el
    mismo hecho" sin usar un modelo -- eso lo evita el candado en el origen.
    """
    queue: List[Dict[str, Any]] = []
    seen_texto: set[str] = set()
    for path in sorted(PENDIENTES_DIR.glob("fase2_pendientes_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        candidatos = data.get("candidatos") or []
        changed = False
        for idx, cand in enumerate(candidatos):
            if "estado_revision" not in cand:
                cand["estado_revision"] = "pendiente"
                changed = True
            if cand.get("estado_revision") != "pendiente":
                continue
            norm = _normalize_texto(cand.get("texto", ""))
            if norm in seen_texto:
                cand["estado_revision"] = "descartado_duplicado"
                changed = True
                logger.info(
                    "candidato duplicado exacto descartado (%s#%d): %.80s",
                    path.name, idx, cand.get("texto", ""),
                )
                continue
            seen_texto.add(norm)
            item = dict(cand)
            item["_source_file"] = str(path)
            item["_source_index"] = idx
            queue.append(item)
        if changed:
            try:
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except OSError as exc:
                logger.warning("No se pudo inicializar estado_revision en %s: %s", path, exc)
    return queue


def build_queue() -> List[Dict[str, Any]]:
    """Punto de entrada público para /memoria: candidatos reales pendientes."""
    return _load_queue()


def build_test_queue() -> List[Dict[str, Any]]:
    """Cola sintética para identidades que no son Arturo (QA, pruebas E2E) --
    ver GatewayRunner._handle_memoria_command. Nunca lee ni escribe los
    archivos fase2_pendientes_*.json reales."""
    return _build_sandbox_queue()


def register(
    session_key: str,
    confirm_id: str,
    queue: List[Dict[str, Any]],
    actor_user_id: str = ARTURO_USER_ID,
    origen: str = "arturo_revision_telegram",
) -> None:
    with _lock:
        _pending[session_key] = {
            "confirm_id": confirm_id,
            "queue": queue,
            "created_at": time.time(),
            "actor_user_id": actor_user_id,
            "origen": origen,
        }


def get_pending(session_key: str) -> Optional[Dict[str, Any]]:
    with _lock:
        entry = _pending.get(session_key)
        return dict(entry) if entry else None


def current_item(session_key: str) -> Optional[Dict[str, Any]]:
    with _lock:
        entry = _pending.get(session_key)
        if not entry or not entry["queue"]:
            return None
        return entry["queue"][0]


def clear(session_key: str) -> None:
    with _lock:
        _pending.pop(session_key, None)


def _mark_source(item: Dict[str, Any], estado: str) -> None:
    if item.get("_source_file") == _SANDBOX_SOURCE:
        return  # candidato sintetico -- nada que marcar en disco
    path = Path(item["_source_file"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        candidatos = data.get("candidatos") or []
        idx = item["_source_index"]
        if 0 <= idx < len(candidatos):
            candidatos[idx]["estado_revision"] = estado
            candidatos[idx]["revisado_en"] = datetime.now().isoformat()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.warning(
            "No se pudo marcar '%s' como %s en %s: %s",
            item.get("texto"), estado, path, exc,
        )


def _insert_fact(item: Dict[str, Any], actor_user_id: str, origen: str) -> Optional[str]:
    """Inserta el hecho aprobado en memoria_estructurada, atribuido a quien
    de verdad lo aprobó (``actor_user_id``/``origen``) -- nunca asumido.

    Devuelve un mensaje de error si algo bloquea la escritura, o None si
    escribió bien.
    """
    texto = (item.get("texto") or "").strip()
    if not texto:
        return "hecho vacío, no se escribió nada"
    threats = scan_for_threats(texto, scope="strict")
    if threats:
        return f"escáner de secretos detectó {threats} -- no se escribió nada"
    categoria = _CATEGORIA_MAP.get(item.get("categoria"), _CATEGORIA_DEFAULT)
    fuente = item.get("fuente_verificada") or ""
    conn = sqlite3.connect(STATE_DB)
    try:
        conn.execute(
            "INSERT INTO memoria_estructurada "
            "(hecho, categoria, fecha_registro, fuente, origen, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                texto,
                categoria,
                datetime.now().isoformat(),
                fuente,
                origen,
                actor_user_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return None


def resolve(
    session_key: str, confirm_id: str, choice: str,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Procesa la cabeza de la cola según ``choice`` ('aprobar'/'rechazar').

    Devuelve ``(mensaje_de_resultado, siguiente_item_o_None)``. Si la cola
    queda vacía después, ``siguiente_item`` es None y el mensaje lo dice.
    """
    with _lock:
        entry = _pending.get(session_key)
        if not entry or entry.get("confirm_id") != confirm_id or not entry["queue"]:
            return ("Esta revisión ya no está activa (expiró o se resolvió en otro lado).", None)
        if time.time() - float(entry.get("created_at", 0) or 0) > DEFAULT_TIMEOUT_SECONDS:
            _pending.pop(session_key, None)
            return ("Esta revisión expiró (más de 1h sin resolver). Corre /memoria de nuevo.", None)
        item = entry["queue"].pop(0)
        actor_user_id = entry.get("actor_user_id", ARTURO_USER_ID)
        origen = entry.get("origen", "arturo_revision_telegram")

    texto = item.get("texto", "(sin texto)")
    if choice == "aprobar":
        error = _insert_fact(item, actor_user_id, origen)
        if error:
            _mark_source(item, "rechazado_error")
            msg = f"❌ No se guardó (\"{texto}\"): {error}"
        else:
            _mark_source(item, "aprobado")
            msg = f"✅ Guardado: \"{texto}\""
    elif choice == "rechazar":
        _mark_source(item, "rechazado")
        msg = f"🗑️ Descartado: \"{texto}\""
    else:
        with _lock:
            entry = _pending.get(session_key)
            if entry is not None:
                entry["queue"].insert(0, item)
        return (f"Opción no reconocida ({choice}).", item)

    with _lock:
        entry = _pending.get(session_key)
        next_item = entry["queue"][0] if entry and entry["queue"] else None
        if next_item is None and entry is not None:
            _pending.pop(session_key, None)
    return (msg, next_item)
