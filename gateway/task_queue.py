"""Cola v2 (HAS §E5, OT-5 Bloque 3, 29 Jul 2026): cola de tareas GENERAL
con garantía de notificación.

Corre DENTRO del proceso vivo del gateway (mismo patrón que
``GatewayKanbanWatchersMixin`` en gateway/kanban_watchers.py) -- no como
un script externo disparado por systemd timer. Confirmado hoy mismo en
esta misma sesión (ver docs/BLOQUES.md, hallazgo de OT-4 Bloque 1.3):
``hermes cron run`` desde fuera del proceso del gateway NO logra
entregar por Telegram (sin adaptador vivo); el tick interno SÍ entrega,
porque usa ``self.adapters`` -- la conexión ya viva. Repetir ese error
aquí habría dejado la "garantía de notificación" rota desde el diseño.

Deliberadamente NO reemplaza ``mensajes_pendientes``/Tarea C (ver el
comentario junto al ``CREATE TABLE task_queue`` en hermes_state.py) --
ese mecanismo sigue vivo sin tocar, ya probado en producción para
reintentos de turnos de chat por cuota agotada. Cola v2 es la máquina
de estados GENERAL que HAS pide para trabajo encolado nuevo (Fase 6-9:
recordatorios, análisis en segundo plano, etc.) -- migrar Tarea C
completa habría significado reescribir ~15 puntos de gateway/run.py que
hoy entregan mensajes reales en producción; se decidió no arriesgar eso
en la misma sesión (documentado como decisión, no como pendiente
olvidado).

Escalera de reintentos (HAS OT-5 3.2): Groq -> Gemini -> OpenRouter
(los nombres de modelo de litellm/config.yaml: chat-fallback,
chat-primary, chat-fallback3), máximo 5 intentos por proveedor. Si los
3 agotan sus intentos (15 intentos totales), la tarea pasa a 'atorada'.

Watchdog (HAS OT-5 3.3): tareas >2h en 'en_proceso' se re-encolan --
corre cada 30 min, no en cada tick del worker principal.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PROVIDER_LADDER = ["chat-fallback", "chat-primary", "chat-fallback3"]  # Groq, Gemini, OpenRouter
_MAX_ATTEMPTS_PER_PROVIDER = 5
_WATCHDOG_INTERVAL_SECONDS = 30 * 60
_ORPHAN_THRESHOLD_SECONDS = 2 * 60 * 60
_WORKER_TICK_SECONDS = 15


class TaskLadderExhausted(Exception):
    """Los 3 proveedores de la escalera agotaron sus intentos."""

    def __init__(self, message: str, intentos: int):
        super().__init__(message)
        self.intentos = intentos


def _call_provider(model_name: str, prompt: str, *, timeout: int = 30) -> str:
    """Llama a un modelo real vía el proxy local de LiteLLM (mismo
    mecanismo que agent/complexity_detector.py::_call_cheap_model_json,
    reutilizado en vez de duplicado). Lanza en cualquier fallo -- el
    caller decide el reintento/siguiente proveedor de la escalera."""
    from agent.complexity_detector import _resolve_litellm_credentials

    base_url, api_key = _resolve_litellm_credentials()
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = (body.get("choices") or [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError(f"proveedor {model_name} devolvió una respuesta vacía")
    return content


def process_task_ladder(payload_json: str) -> tuple[str, str, int]:
    """Intenta la escalera completa de proveedores para una tarea.

    Devuelve (resultado, proveedor_que_funciono, intentos_totales).
    Lanza TaskLadderExhausted si los 3 proveedores agotan sus intentos
    (HAS OT-5 3.2: máx 5 intentos por proveedor). Función síncrona a
    propósito -- el caller la corre en un hilo (asyncio.to_thread) para
    no bloquear el loop del gateway."""
    try:
        payload = json.loads(payload_json)
    except (json.JSONDecodeError, TypeError):
        payload = {}
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    prompt = prompt or payload_json

    intentos_totales = 0
    last_error: Optional[Exception] = None
    for provider in _PROVIDER_LADDER:
        for attempt in range(_MAX_ATTEMPTS_PER_PROVIDER):
            intentos_totales += 1
            try:
                resultado = _call_provider(provider, prompt)
                return resultado, provider, intentos_totales
            except Exception as e:
                last_error = e
                logger.debug(
                    "task_queue: intento %d/%d con %s falló: %s",
                    attempt + 1, _MAX_ATTEMPTS_PER_PROVIDER, provider, e,
                )
    raise TaskLadderExhausted(
        f"los 3 proveedores agotaron sus {_MAX_ATTEMPTS_PER_PROVIDER} intentos cada uno: {last_error}",
        intentos_totales,
    )


class GatewayTaskQueueMixin:
    """Mixin para GatewayRunner (gateway/run.py) -- ver docstring del módulo."""

    async def _task_queue_watcher(self, interval: float = _WORKER_TICK_SECONDS) -> None:
        # Espera inicial: deja que el gateway termine de conectar adapters
        # antes del primer intento de notificación (mismo patrón que
        # _kanban_notifier_watcher).
        await asyncio.sleep(5)
        last_watchdog = 0.0
        while self._running:
            try:
                if getattr(self, "_session_db", None) is not None:
                    await self._task_queue_process_one_tick()
                    now = time.time()
                    if now - last_watchdog >= _WATCHDOG_INTERVAL_SECONDS:
                        await self._task_queue_watchdog_tick()
                        last_watchdog = now
            except Exception:
                logger.exception("task_queue watcher: fallo en un tick")
            for _ in range(int(interval)):
                if not self._running:
                    break
                await asyncio.sleep(1)

    async def _task_queue_process_one_tick(self) -> None:
        # 1. Reintentar notificaciones pendientes ANTES de reclamar tarea
        #    nueva -- la garantía de notificación tiene prioridad sobre
        #    procesar más trabajo.
        try:
            unnotified = await self._session_db.get_unnotified_tasks()
        except Exception:
            logger.exception("task_queue: no se pudieron leer tareas sin notificar")
            unnotified = []
        for task in unnotified:
            await self._task_queue_notify(task, stuck=(task["estado"] == "atorada"))

        # 2. Reclamar y procesar UNA tarea nueva por tick -- simple y
        #    suficiente para el volumen esperado; varios ticks seguidos
        #    procesan varias tareas encoladas.
        task = await self._session_db.claim_next_task()
        if task is None:
            return
        await self._task_queue_run_ladder(task)

    async def _task_queue_run_ladder(self, task: dict[str, Any]) -> None:
        task_id = task["id"]
        try:
            resultado, proveedor, intentos = await asyncio.to_thread(
                process_task_ladder, task["payload"],
            )
        except TaskLadderExhausted as e:
            await self._session_db.mark_task_stuck(task_id, e.intentos)
            stuck_task = dict(task)
            stuck_task["estado"] = "atorada"
            await self._task_queue_notify(stuck_task, stuck=True)
            return
        except Exception:
            logger.exception("task_queue: fallo inesperado procesando tarea %s", task_id)
            await self._session_db.mark_task_stuck(task_id, int(task.get("intentos") or 0) + 1)
            return

        result_hash = hashlib.sha256(f"{task_id}:{resultado}".encode("utf-8")).hexdigest()[:16]
        resolved = await self._session_db.mark_task_resolved(
            task_id, resultado, result_hash, intentos, proveedor=proveedor,
        )
        if resolved:
            fresh = dict(task)
            fresh["resultado"] = resultado
            fresh["estado"] = "resuelta"
            await self._task_queue_notify(fresh, stuck=False)
        # resolved=False significa que el watchdog ya re-encoló esta fila
        # (zombie que termina tarde) -- no hacer nada, el resultado de
        # este intento tardío se descarta a propósito (ver mark_task_resolved).

    async def _task_queue_notify(self, task: dict[str, Any], *, stuck: bool) -> None:
        from gateway.config import Platform

        platform_str = task.get("platform") or "telegram"
        try:
            platform = Platform(platform_str)
        except ValueError:
            logger.warning(
                "task_queue: plataforma desconocida %r para tarea %s -- no se puede notificar",
                platform_str, task["id"],
            )
            return
        adapter = self.adapters.get(platform)
        if adapter is None:
            logger.debug(
                "task_queue: adapter %s no conectado todavía, se reintenta en el siguiente tick",
                platform_str,
            )
            return

        if stuck:
            msg = (
                f"⚠️ No pude resolver esta tarea (#{task['id']}: {task['descripcion']}) "
                f"tras agotar los 3 proveedores -- necesito ayuda con esta."
            )
        else:
            msg = (
                f"✅ Ya está (#{task['id']}: {task['descripcion']}). "
                f"Puedes revisarla ahora o más tarde.\n\n{task['resultado']}"
            )

        try:
            send_res = await adapter.send(task["chat_id"], msg)
            if getattr(send_res, "success", True) is False:
                raise RuntimeError("adapter.send() reportó fallo")
        except Exception as e:
            logger.warning(
                "task_queue: fallo notificando tarea %s (se reintenta en el "
                "siguiente tick, la fila NO se marca notificada): %s",
                task["id"], e,
            )
            return

        await self._session_db.mark_task_notified(task["id"], keep_stuck=stuck)

    async def _task_queue_watchdog_tick(self) -> None:
        try:
            orphaned = await self._session_db.get_orphaned_processing_tasks(_ORPHAN_THRESHOLD_SECONDS)
        except Exception:
            logger.exception("task_queue watchdog: no se pudieron leer tareas huérfanas")
            return
        for task in orphaned:
            reclaimed = await self._session_db.reclaim_orphaned_task(task["id"])
            if reclaimed:
                logger.warning(
                    "task_queue watchdog: tarea %s huérfana (>2h en 'en_proceso'), re-encolada",
                    task["id"],
                )
