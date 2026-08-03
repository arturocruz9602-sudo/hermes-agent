#!/usr/bin/env python3
"""
cola_v2.py — La cola de tareas con GARANTÍA DURA (HAS §E5, OT-5 Bloque 3).

Regla que gobierna todo este archivo (HAS §E5, invariantes verificados por
`tests/test_cola_v2.py`):

    Toda tarea encolada llega, tarde o temprano, a `notificada` o a
    `atorada`+aviso. NUNCA se pierde en silencio.

    (1) toda fila termina en `notificada` o en `atorada` con su aviso enviado;
    (2) `resolved_at NOT NULL  ⇒  notified_at NOT NULL` (resuelta sin avisar es
        un estado prohibido: se reintenta la notificación hasta lograrla);
    (3) el watchdog re-encola tareas huérfanas (>2h en `en_proceso`) sin
        duplicar efectos (idempotencia por `result_hash`).

El silencio nunca es un estado válido de fallo (CLAUDE.md regla 3, HAS
§F9-L6/L14): CADA transición e intento —éxito Y fallo— queda escrito en la
tabla `task_queue_log` y en el logger. Si algo falla, se sabe por qué.

DISEÑO DELIBERADO — el módulo NO llama modelos de pago por su cuenta:
    - `solver`      (cómo se resuelve una tarea) es INYECTABLE.
    - `notificador` (cómo se avisa a Arturo)     es INYECTABLE.
    Así la cola es la espina dorsal de la proactividad sin poder gastar sola:
    quien la usa decide qué proveedor/skill resuelve cada tarea. La escalera
    por defecto es Groq→Gemini→OpenRouter (gratuitos); DeepSeek NUNCA entra
    automático (CLAUDE.md, presupuesto $100 MXN).

ENTORNOS (igual que libreta.py: la arquitectura separa real de simulación)
    HERMES_ENTORNO=real       -> ~/.hermes/state.db      (default, uso diario)
    HERMES_ENTORNO=simulacion -> <disco externo>/pruebas/state_sim.db

USO
    from cola_v2 import ColaTareas
    with ColaTareas() as cola:
        tid = cola.encolar("resumir correo", {"tipo": "resumen"}, chat_id="123")
        cola.procesar_pendientes(solver=mi_solver, notificador=mi_notif)
        cola.watchdog(solver=mi_solver, notificador=mi_notif)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
DISCO_EXTERNO = Path(os.environ.get("HERMES_DISCO_PRUEBAS", "/mnt/seagate"))
DIR_PRUEBAS = DISCO_EXTERNO / "hermes_backups" / "pruebas"

RUTAS = {
    "real": HERMES_HOME / "state.db",
    "simulacion": DIR_PRUEBAS / "state_sim.db",
}

# Escalera de reintentos por defecto (HAS §E5 3.2). Groq→Gemini→OpenRouter, los
# tres gratuitos. DeepSeek NO está aquí a propósito: no se llama automático.
ESCALERA_DEFECTO = ("groq", "gemini", "openrouter")
MAX_INTENTOS_POR_PROVEEDOR = 5      # HAS §E5 3.2
WATCHDOG_UMBRAL_MIN = 120           # HAS §E5 3.3: >2h en_proceso = huérfana
MAX_REINTENTOS_NOTIF = 3            # reintentos inline de la notificación

# Estados de la máquina (HAS §E5).
ENCOLADA = "encolada"
EN_PROCESO = "en_proceso"
RESUELTA = "resuelta"
NOTIFICADA = "notificada"
ATORADA = "atorada"
ESTADOS = (ENCOLADA, EN_PROCESO, RESUELTA, NOTIFICADA, ATORADA)

log = logging.getLogger("hermes.cola_v2")


# ─── errores propios ────────────────────────────────────────────────────
class EntornoInvalido(ValueError):
    pass


class SolverError(RuntimeError):
    """Un intento del solver falló. La cola la captura y reintenta/escala."""


class NotificacionError(RuntimeError):
    """Un intento de notificación falló. La cola NO deja la tarea resuelta
    sin avisar: reintenta y, si no lo logra ahora, la deja pendiente para el
    siguiente barrido (invariante 2)."""


def _ruta(entorno: str | None) -> Path:
    ent = (entorno or os.environ.get("HERMES_ENTORNO") or "real").strip().lower()
    if ent not in RUTAS:
        raise EntornoInvalido(
            f"entorno '{ent}' no existe; use uno de: {', '.join(sorted(RUTAS))}")
    return RUTAS[ent]


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ColaTareas:
    """La cola v2 sobre `state.db`. Context manager.

    `db_path` explícito gana sobre `entorno` (lo usan las pruebas con una BD
    temporal para no tocar producción)."""

    def __init__(self, entorno: str | None = None, *, db_path: str | Path | None = None):
        self.ruta = Path(db_path) if db_path is not None else _ruta(entorno)
        self._con: sqlite3.Connection | None = None

    # ── ciclo de vida ───────────────────────────────────────────────────
    def __enter__(self) -> "ColaTareas":
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self.ruta))
        self._con.row_factory = sqlite3.Row
        self._crear_esquema()
        return self

    def __exit__(self, *exc) -> None:
        if self._con is not None:
            if exc[0] is None:
                self._con.commit()
            self._con.close()
            self._con = None

    @property
    def con(self) -> sqlite3.Connection:
        if self._con is None:
            raise RuntimeError("usa ColaTareas dentro de un 'with'")
        return self._con

    def _crear_esquema(self) -> None:
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS task_queue (
              id INTEGER PRIMARY KEY,
              descripcion TEXT NOT NULL,
              payload TEXT NOT NULL,
              estado TEXT NOT NULL DEFAULT 'encolada',
              proveedor_actual TEXT,
              intentos INTEGER DEFAULT 0,
              result_hash TEXT,
              resultado TEXT,
              chat_id TEXT NOT NULL,
              created_at TEXT, started_at TEXT,
              resolved_at TEXT, notified_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_task_queue_estado
              ON task_queue(estado);

            -- El silencio no es estado válido de fallo: cada intento y cada
            -- transición se escribe aquí, éxito Y fallo.
            CREATE TABLE IF NOT EXISTS task_queue_log (
              id INTEGER PRIMARY KEY,
              task_id INTEGER NOT NULL,
              ts TEXT NOT NULL,
              evento TEXT NOT NULL,
              estado TEXT,
              ok INTEGER NOT NULL,
              detalle TEXT,
              FOREIGN KEY (task_id) REFERENCES task_queue(id)
            );
            CREATE INDEX IF NOT EXISTS idx_task_queue_log_task
              ON task_queue_log(task_id);
            """
        )

    # ── log (éxito Y fallo, siempre) ────────────────────────────────────
    def _log(self, task_id: int, evento: str, ok: bool, *,
             estado: str | None = None, detalle: str = "") -> None:
        self.con.execute(
            "INSERT INTO task_queue_log (task_id, ts, evento, estado, ok, detalle) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, _ahora(), evento, estado, 1 if ok else 0, detalle),
        )
        nivel = logging.INFO if ok else logging.WARNING
        log.log(nivel, "tarea=%s %s ok=%s estado=%s %s",
                task_id, evento, ok, estado, detalle)

    # ── API pública ─────────────────────────────────────────────────────
    def encolar(self, descripcion: str, payload: dict, chat_id: str) -> int:
        """Da de alta una tarea. Devuelve su id."""
        cur = self.con.execute(
            "INSERT INTO task_queue (descripcion, payload, estado, chat_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (descripcion, json.dumps(payload, ensure_ascii=False),
             ENCOLADA, str(chat_id), _ahora()),
        )
        tid = int(cur.lastrowid)
        self._log(tid, "encolar", True, estado=ENCOLADA, detalle=descripcion)
        self.con.commit()
        return tid

    def obtener(self, task_id: int) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM task_queue WHERE id = ?", (task_id,)).fetchone()

    def contar_por_estado(self) -> dict[str, int]:
        filas = self.con.execute(
            "SELECT estado, COUNT(*) n FROM task_queue GROUP BY estado").fetchall()
        return {f["estado"]: f["n"] for f in filas}

    def procesar_pendientes(
        self,
        solver: Callable[[dict, str], str],
        notificador: Callable[[str, str], None],
        *,
        escalera: tuple[str, ...] = ESCALERA_DEFECTO,
        max_intentos: int = MAX_INTENTOS_POR_PROVEEDOR,
        dormir: Callable[[float], None] = time.sleep,
        limite: int | None = None,
    ) -> dict[str, int]:
        """Procesa todas las tareas `encolada` (o `limite` de ellas).

        Devuelve el conteo {resueltas, atoradas} de esta corrida. Antes de
        empezar barre las `resuelta`-sin-notificar pendientes (invariante 2)."""
        self._reintentar_notificaciones(notificador)
        resultado = {"resueltas": 0, "atoradas": 0}
        procesadas = 0
        while True:
            if limite is not None and procesadas >= limite:
                break
            fila = self.con.execute(
                "SELECT id FROM task_queue WHERE estado = ? ORDER BY id LIMIT 1",
                (ENCOLADA,)).fetchone()
            if fila is None:
                break
            estado = self.procesar_una(
                int(fila["id"]), solver, notificador,
                escalera=escalera, max_intentos=max_intentos, dormir=dormir)
            procesadas += 1
            if estado == NOTIFICADA:
                resultado["resueltas"] += 1
            elif estado == ATORADA:
                resultado["atoradas"] += 1
        return resultado

    def procesar_una(
        self,
        task_id: int,
        solver: Callable[[dict, str], str],
        notificador: Callable[[str, str], None],
        *,
        escalera: tuple[str, ...] = ESCALERA_DEFECTO,
        max_intentos: int = MAX_INTENTOS_POR_PROVEEDOR,
        dormir: Callable[[float], None] = time.sleep,
    ) -> str:
        """Lleva UNA tarea por la máquina de estados hasta un estado terminal
        (`notificada` o `atorada`). Devuelve el estado final."""
        # Reclamo atómico: encolada -> en_proceso (solo si sigue encolada).
        cur = self.con.execute(
            "UPDATE task_queue SET estado = ?, started_at = ? "
            "WHERE id = ? AND estado = ?",
            (EN_PROCESO, _ahora(), task_id, ENCOLADA))
        if cur.rowcount == 0:
            # Otro la tomó, o ya no está encolada. No es un fallo: reporta.
            fila = self.obtener(task_id)
            return fila["estado"] if fila else "inexistente"
        self._log(task_id, "tomar", True, estado=EN_PROCESO)
        self.con.commit()

        fila = self.obtener(task_id)
        payload = json.loads(fila["payload"])

        # Escalera de proveedores con reintentos (HAS §E5 3.2).
        resultado = None
        for proveedor in escalera:
            self.con.execute(
                "UPDATE task_queue SET proveedor_actual = ? WHERE id = ?",
                (proveedor, task_id))
            for intento in range(1, max_intentos + 1):
                self.con.execute(
                    "UPDATE task_queue SET intentos = intentos + 1 WHERE id = ?",
                    (task_id,))
                try:
                    resultado = solver(payload, proveedor)
                    self._log(task_id, f"solver:{proveedor}#{intento}", True,
                              estado=EN_PROCESO)
                    break
                except Exception as exc:  # el solver puede lanzar lo que sea
                    self._log(task_id, f"solver:{proveedor}#{intento}", False,
                              estado=EN_PROCESO, detalle=repr(exc))
                    if intento < max_intentos:
                        dormir(min(2 ** (intento - 1), 30))
            if resultado is not None:
                break
        self.con.commit()

        if resultado is None:
            return self._atorar(task_id, notificador, dormir=dormir)

        # en_proceso -> resuelta (con result_hash para idempotencia).
        rhash = hashlib.sha256(resultado.encode("utf-8")).hexdigest()
        self.con.execute(
            "UPDATE task_queue SET estado = ?, resultado = ?, result_hash = ?, "
            "resolved_at = ? WHERE id = ?",
            (RESUELTA, resultado, rhash, _ahora(), task_id))
        self._log(task_id, "resolver", True, estado=RESUELTA)
        self.con.commit()

        # GARANTÍA (HAS §E5 3.4): resuelta SIEMPRE dispara la notificación y
        # solo tras lograrla se marca notificada. Si falla, queda resuelta y el
        # próximo barrido la reintenta — nunca resuelta-sin-avisar.
        aviso = ("Ya está: " + fila["descripcion"] +
                 ". Puedes revisarla ahora o más tarde.")
        if self._notificar(task_id, fila["chat_id"], aviso, notificador,
                           dormir=dormir):
            self.con.execute(
                "UPDATE task_queue SET estado = ?, notified_at = ? WHERE id = ?",
                (NOTIFICADA, _ahora(), task_id))
            self._log(task_id, "notificar", True, estado=NOTIFICADA)
            self.con.commit()
            return NOTIFICADA
        # Notificación no lograda ahora: se queda en RESUELTA (invariante 2).
        self.con.commit()
        return RESUELTA

    def _atorar(self, task_id: int,
                notificador: Callable[[str, str], None],
                *, dormir: Callable[[float], None] = time.sleep) -> str:
        """Los proveedores agotados → atorada + aviso 'necesito ayuda'.
        Una tarea atorada TAMBIÉN debe avisarse (invariante 1)."""
        fila = self.obtener(task_id)
        self.con.execute(
            "UPDATE task_queue SET estado = ? WHERE id = ?", (ATORADA, task_id))
        self._log(task_id, "atorar", True, estado=ATORADA,
                  detalle="escalera de proveedores agotada")
        self.con.commit()
        aviso = ("Necesito ayuda con esta: " + fila["descripcion"] +
                 " (no pude resolverla con los proveedores disponibles).")
        if self._notificar(task_id, fila["chat_id"], aviso, notificador,
                           dormir=dormir):
            self.con.execute(
                "UPDATE task_queue SET notified_at = ? WHERE id = ?",
                (_ahora(), task_id))
            self._log(task_id, "notificar_atorada", True, estado=ATORADA)
        self.con.commit()
        return ATORADA

    def _notificar(self, task_id: int, chat_id: str, texto: str,
                   notificador: Callable[[str, str], None],
                   *, dormir: Callable[[float], None] = time.sleep) -> bool:
        """Intenta notificar con reintentos inline. True si lo logró."""
        for intento in range(1, MAX_REINTENTOS_NOTIF + 1):
            try:
                notificador(str(chat_id), texto)
                self._log(task_id, f"envio_notif#{intento}", True)
                return True
            except Exception as exc:
                self._log(task_id, f"envio_notif#{intento}", False,
                          detalle=repr(exc))
                if intento < MAX_REINTENTOS_NOTIF:
                    dormir(min(2 ** (intento - 1), 30))
        return False

    def _reintentar_notificaciones(
        self, notificador: Callable[[str, str], None],
        *, dormir: Callable[[float], None] = time.sleep) -> int:
        """Barre las tareas `resuelta` sin `notified_at` y las atoradas sin
        aviso, y reintenta la notificación (invariante 2). Devuelve cuántas
        quedaron notificadas en este barrido."""
        pendientes = self.con.execute(
            "SELECT * FROM task_queue "
            "WHERE (estado = ? OR estado = ?) AND notified_at IS NULL",
            (RESUELTA, ATORADA)).fetchall()
        logradas = 0
        for fila in pendientes:
            if fila["estado"] == RESUELTA:
                texto = ("Ya está: " + fila["descripcion"] +
                         ". Puedes revisarla ahora o más tarde.")
            else:
                texto = ("Necesito ayuda con esta: " + fila["descripcion"] +
                         " (no pude resolverla con los proveedores disponibles).")
            if self._notificar(int(fila["id"]), fila["chat_id"], texto,
                               notificador, dormir=dormir):
                if fila["estado"] == RESUELTA:
                    self.con.execute(
                        "UPDATE task_queue SET estado = ?, notified_at = ? "
                        "WHERE id = ?", (NOTIFICADA, _ahora(), fila["id"]))
                else:
                    self.con.execute(
                        "UPDATE task_queue SET notified_at = ? WHERE id = ?",
                        (_ahora(), fila["id"]))
                self._log(int(fila["id"]), "renotificar", True,
                          estado=NOTIFICADA if fila["estado"] == RESUELTA else ATORADA)
                logradas += 1
        self.con.commit()
        return logradas

    def watchdog(
        self,
        solver: Callable[[dict, str], str],
        notificador: Callable[[str, str], None],
        *,
        umbral_min: int = WATCHDOG_UMBRAL_MIN,
        escalera: tuple[str, ...] = ESCALERA_DEFECTO,
        max_intentos: int = MAX_INTENTOS_POR_PROVEEDOR,
        dormir: Callable[[float], None] = time.sleep,
        _ahora_dt: datetime | None = None,
    ) -> dict[str, int]:
        """HAS §E5 3.3: tareas huérfanas (>umbral en `en_proceso`) → re-encolar
        sin duplicar efectos, y volver a procesarlas. Además reintenta las
        notificaciones pendientes. `_ahora_dt` inyectable para las pruebas.

        Idempotencia: una tarea que YA tiene `result_hash` fue resuelta antes
        de morir el proceso; no se re-ejecuta el solver, se salta directo a
        notificar (evita duplicar el efecto externo de la tarea)."""
        ahora = _ahora_dt or datetime.now()
        limite = (ahora - timedelta(minutes=umbral_min)).isoformat(timespec="seconds")
        huerfanas = self.con.execute(
            "SELECT * FROM task_queue WHERE estado = ? AND started_at < ?",
            (EN_PROCESO, limite)).fetchall()

        resultado = {"reencoladas": 0, "resueltas_directo": 0, "renotificadas": 0}
        for fila in huerfanas:
            tid = int(fila["id"])
            if fila["result_hash"]:
                # Ya se había resuelto: no repetir el efecto, ir a resuelta.
                self.con.execute(
                    "UPDATE task_queue SET estado = ?, resolved_at = COALESCE(resolved_at, ?) "
                    "WHERE id = ?", (RESUELTA, _ahora(), tid))
                self._log(tid, "watchdog:ya_resuelta", True, estado=RESUELTA,
                          detalle="result_hash presente, no se re-ejecuta")
                resultado["resueltas_directo"] += 1
            else:
                self.con.execute(
                    "UPDATE task_queue SET estado = ?, started_at = NULL WHERE id = ?",
                    (ENCOLADA, tid))
                self._log(tid, "watchdog:reencolar", True, estado=ENCOLADA,
                          detalle=f"huérfana >{umbral_min}min en en_proceso")
                resultado["reencoladas"] += 1
        self.con.commit()

        resultado["renotificadas"] = self._reintentar_notificaciones(
            notificador, dormir=dormir)
        # Vuelve a procesar lo re-encolado en la misma pasada.
        self.procesar_pendientes(
            solver, notificador, escalera=escalera,
            max_intentos=max_intentos, dormir=dormir)
        return resultado
