#!/usr/bin/env python3
"""
deteccion_espontanea.py — Captura espontánea de compromisos (HAS §C, Fase 9 /
OT-9 punto 2; CUESTIONARIO_MAESTRO r.89).

r.89, textual: *"¿Preguntar antes de agendar capturas espontáneas? Sí, que
siempre pregunte."* Esa es la regla que gobierna TODO este archivo, y gana
sobre la redacción vieja de OT-9 ("modo entrenamiento 2 semanas → luego
automático"): aquí NUNCA hay modo automático. Cada compromiso detectado de
pasada en una conversación ("nos vemos el viernes a las 3") se pregunta,
siempre — "¿la anoto?" / "¿lo agendo?" — antes de crear cualquier cosa.

DISEÑO DELIBERADO — mismo patrón que `cola_v2.py` y `horario_por_foto.py`:
    - `extractor` (cómo se detectan candidatos en el texto) es INYECTABLE.
      El real llama a un modelo gratuito (Gemini/Groq); el simulado (de
      prueba, r.20) usa reglas de texto fijas. Este módulo no llama a
      ningún modelo por su cuenta.
    - Detectar un candidato NUNCA crea una tarea. Solo `confirmar(...,
      aprobado=True)` la crea, y solo llamando a `ColaTareas.encolar(...)`
      explícitamente — es decir, el "sí" de Arturo es la única puerta.
    - Anti-spam (OT-9 punto 2): máximo 3 preguntas por día. Los candidatos
      de más no se pierden ni se preguntan de golpe: quedan `diferida` para
      el barrido del día siguiente.

ENTORNOS (igual que cola_v2.py / libreta.py)
    HERMES_ENTORNO=real       -> ~/.hermes/state.db      (default, uso diario)
    HERMES_ENTORNO=simulacion -> <disco externo>/pruebas/state_sim.db

USO
    from deteccion_espontanea import DetectorEspontaneo
    from cola_v2 import ColaTareas

    with DetectorEspontaneo() as det:
        preguntas = det.detectar(texto, extractor=mi_extractor, chat_id="123")
        for p in preguntas:
            enviar_telegram(p["chat_id"], p["pregunta"])
        # ... cuando Arturo responde "sí" a la captura id=7:
        with ColaTareas() as cola:
            det.confirmar(7, aprobado=True, cola=cola)
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
DISCO_EXTERNO = Path(os.environ.get("HERMES_DISCO_PRUEBAS", "/mnt/seagate"))
DIR_PRUEBAS = DISCO_EXTERNO / "hermes_backups" / "pruebas"

RUTAS = {
    "real": HERMES_HOME / "state.db",
    "simulacion": DIR_PRUEBAS / "state_sim.db",
}

# OT-9 punto 2: "Umbral anti-spam: máx 3 preguntas '¿anoto?' por día."
MAX_PREGUNTAS_DIA = 3

PENDIENTE = "pendiente_confirmacion"
CONFIRMADA = "confirmada"
RECHAZADA = "rechazada"
DIFERIDA = "diferida"
ESTADOS = (PENDIENTE, CONFIRMADA, RECHAZADA, DIFERIDA)

log = logging.getLogger("hermes.deteccion_espontanea")


class EntornoInvalido(ValueError):
    pass


class CapturaInexistente(LookupError):
    pass


class EstadoInvalido(RuntimeError):
    """La captura ya fue resuelta (confirmada/rechazada): no se resuelve dos
    veces (idempotencia — evita crear la tarea por duplicado)."""


def _ruta(entorno: str | None) -> Path:
    ent = (entorno or os.environ.get("HERMES_ENTORNO") or "real").strip().lower()
    if ent not in RUTAS:
        raise EntornoInvalido(
            f"entorno '{ent}' no existe; use uno de: {', '.join(sorted(RUTAS))}")
    return RUTAS[ent]


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class DetectorEspontaneo:
    """Captura espontánea sobre `state.db`. Context manager, comparte la
    misma base que `cola_v2.ColaTareas` (tabla propia, sin pisar la suya).

    `db_path` explícito gana sobre `entorno` (lo usan las pruebas con una BD
    temporal para no tocar producción)."""

    def __init__(self, entorno: str | None = None, *, db_path: str | Path | None = None):
        self.ruta = Path(db_path) if db_path is not None else _ruta(entorno)
        self._con: sqlite3.Connection | None = None

    def __enter__(self) -> "DetectorEspontaneo":
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
            raise RuntimeError("usa DetectorEspontaneo dentro de un 'with'")
        return self._con

    def _crear_esquema(self) -> None:
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS capturas_espontaneas (
              id INTEGER PRIMARY KEY,
              texto_origen TEXT NOT NULL,
              descripcion TEXT NOT NULL,
              fecha_propuesta TEXT,
              hora_propuesta TEXT,
              estado TEXT NOT NULL DEFAULT 'pendiente_confirmacion',
              chat_id TEXT NOT NULL,
              tarea_id INTEGER,
              creado_en TEXT NOT NULL,
              resuelto_en TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_capturas_estado
              ON capturas_espontaneas(estado);
            CREATE INDEX IF NOT EXISTS idx_capturas_creado
              ON capturas_espontaneas(creado_en);

            -- El silencio no es estado válido de fallo (CLAUDE.md regla 3):
            -- cada detección y cada resolución queda aquí, éxito Y fallo.
            CREATE TABLE IF NOT EXISTS capturas_espontaneas_log (
              id INTEGER PRIMARY KEY,
              captura_id INTEGER,
              ts TEXT NOT NULL,
              evento TEXT NOT NULL,
              ok INTEGER NOT NULL,
              detalle TEXT,
              FOREIGN KEY (captura_id) REFERENCES capturas_espontaneas(id)
            );
            """
        )

    def _log(self, captura_id: int | None, evento: str, ok: bool, *, detalle: str = "") -> None:
        """Commitea de inmediato (no espera al commit del caller): un log de
        fallo que se pierde si el caller revienta después es exactamente el
        "silencio como estado de fallo" que CLAUDE.md regla 3 prohíbe."""
        self.con.execute(
            "INSERT INTO capturas_espontaneas_log (captura_id, ts, evento, ok, detalle) "
            "VALUES (?, ?, ?, ?, ?)",
            (captura_id, _ahora(), evento, 1 if ok else 0, detalle),
        )
        self.con.commit()
        nivel = logging.INFO if ok else logging.WARNING
        log.log(nivel, "captura=%s %s ok=%s %s", captura_id, evento, ok, detalle)

    # ── conteo anti-spam ─────────────────────────────────────────────────
    def preguntas_hoy(self) -> int:
        """Cuántas preguntas ya se hicieron hoy (para el tope de 3/día)."""
        fila = self.con.execute(
            "SELECT COUNT(*) n FROM capturas_espontaneas "
            "WHERE substr(creado_en, 1, 10) = ? AND estado != ?",
            (_hoy(), DIFERIDA),
        ).fetchone()
        return int(fila["n"])

    # ── detección (nunca crea nada — solo registra y pregunta) ──────────
    def detectar(
        self,
        texto: str,
        extractor: Callable[[str], list[dict]],
        chat_id: str,
    ) -> list[dict]:
        """Corre `extractor(texto)` y registra cada candidato encontrado.

        Devuelve la lista de preguntas a mandar (solo las que SÍ se van a
        preguntar hoy — las que exceden el tope de 3/día quedan `diferida`,
        sin generar pregunta, para el barrido de mañana). r.89: detectar
        jamás agenda por su cuenta; solo `confirmar(aprobado=True)` lo hace.
        """
        try:
            candidatos = extractor(texto)
        except Exception as exc:  # el extractor puede ser una llamada a un modelo
            self._log(None, "extraccion", False, detalle=str(exc))
            raise

        if not candidatos:
            self._log(None, "extraccion", True, detalle="sin candidatos")
            return []

        preguntas: list[dict] = []
        restantes = max(0, MAX_PREGUNTAS_DIA - self.preguntas_hoy())
        for candidato in candidatos:
            descripcion = (candidato.get("descripcion") or "").strip()
            if not descripcion:
                continue
            estado = PENDIENTE if restantes > 0 else DIFERIDA
            cur = self.con.execute(
                "INSERT INTO capturas_espontaneas "
                "(texto_origen, descripcion, fecha_propuesta, hora_propuesta, "
                " estado, chat_id, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (texto, descripcion, candidato.get("fecha"), candidato.get("hora"),
                 estado, str(chat_id), _ahora()),
            )
            cid = int(cur.lastrowid)
            self._log(cid, "detectar", True,
                      detalle=f"estado={estado} descripcion={descripcion!r}")
            if estado == PENDIENTE:
                restantes -= 1
                preguntas.append({
                    "id": cid,
                    "chat_id": str(chat_id),
                    "pregunta": self.formatear_pregunta(descripcion,
                                                         candidato.get("fecha"),
                                                         candidato.get("hora")),
                })
        self.con.commit()
        return preguntas

    @staticmethod
    def formatear_pregunta(descripcion: str, fecha: str | None, hora: str | None) -> str:
        """r.89: SIEMPRE se pregunta antes de crear. Texto fijo del periodo
        de entrenamiento de OT-9 ("¿la anoto?"), que r.89 vuelve permanente."""
        cuando = " · ".join(x for x in (fecha, hora) if x)
        sufijo = f" ({cuando})" if cuando else ""
        return f"Oí de pasada: \"{descripcion}\"{sufijo}. ¿La anoto?"

    # ── resolución (la ÚNICA puerta que crea algo) ───────────────────────
    def obtener(self, captura_id: int) -> sqlite3.Row:
        fila = self.con.execute(
            "SELECT * FROM capturas_espontaneas WHERE id = ?", (captura_id,)).fetchone()
        if fila is None:
            raise CapturaInexistente(f"no existe la captura id={captura_id}")
        return fila

    def pendientes(self, chat_id: str | None = None) -> list[sqlite3.Row]:
        if chat_id is None:
            return self.con.execute(
                "SELECT * FROM capturas_espontaneas WHERE estado = ? ORDER BY id",
                (PENDIENTE,)).fetchall()
        return self.con.execute(
            "SELECT * FROM capturas_espontaneas WHERE estado = ? AND chat_id = ? ORDER BY id",
            (PENDIENTE, str(chat_id))).fetchall()

    def confirmar(self, captura_id: int, *, aprobado: bool, cola=None) -> sqlite3.Row:
        """Resuelve una captura pendiente. `aprobado=True` requiere `cola`
        (una `cola_v2.ColaTareas` abierta) y es el único código de este
        módulo que crea algo de verdad — vía `cola.encolar(...)`."""
        fila = self.obtener(captura_id)
        if fila["estado"] != PENDIENTE:
            raise EstadoInvalido(
                f"captura id={captura_id} ya está en estado '{fila['estado']}', "
                f"no se resuelve dos veces")

        if aprobado and cola is None:
            raise ValueError("aprobado=True requiere pasar cola=ColaTareas(...) abierta")

        tarea_id = None
        nuevo_estado = CONFIRMADA if aprobado else RECHAZADA
        try:
            if aprobado:
                payload = {
                    "tipo": "recordatorio_espontaneo",
                    "descripcion": fila["descripcion"],
                    "fecha": fila["fecha_propuesta"],
                    "hora": fila["hora_propuesta"],
                    "captura_id": captura_id,
                }
                tarea_id = cola.encolar(fila["descripcion"], payload, fila["chat_id"])
            self.con.execute(
                "UPDATE capturas_espontaneas SET estado=?, tarea_id=?, resuelto_en=? "
                "WHERE id = ?",
                (nuevo_estado, tarea_id, _ahora(), captura_id),
            )
            self._log(captura_id, "confirmar", True,
                      detalle=f"aprobado={aprobado} tarea_id={tarea_id}")
            self.con.commit()
        except Exception as exc:
            self._log(captura_id, "confirmar", False, detalle=str(exc))
            self.con.commit()
            raise
        return self.obtener(captura_id)

    def diferidas_para_reintentar(self) -> list[sqlite3.Row]:
        """Las que excedieron el tope de ayer — el barrido de hoy las vuelve
        a poner en juego (nunca se pierden en silencio)."""
        return self.con.execute(
            "SELECT * FROM capturas_espontaneas WHERE estado = ? ORDER BY id",
            (DIFERIDA,)).fetchall()

    def promover_diferidas(self, limite: int | None = None) -> list[dict]:
        """Convierte `diferida` -> `pendiente_confirmacion` respetando el
        tope diario de hoy, y devuelve las preguntas a mandar."""
        restantes = max(0, MAX_PREGUNTAS_DIA - self.preguntas_hoy())
        if limite is not None:
            restantes = min(restantes, limite)
        preguntas: list[dict] = []
        for fila in self.diferidas_para_reintentar():
            if restantes <= 0:
                break
            self.con.execute(
                "UPDATE capturas_espontaneas SET estado = ? WHERE id = ?",
                (PENDIENTE, fila["id"]),
            )
            self._log(fila["id"], "promover_diferida", True)
            preguntas.append({
                "id": fila["id"],
                "chat_id": fila["chat_id"],
                "pregunta": self.formatear_pregunta(
                    fila["descripcion"], fila["fecha_propuesta"], fila["hora_propuesta"]),
            })
            restantes -= 1
        self.con.commit()
        return preguntas


# ── extractor de PRUEBA (r.20: solo laboratorio/tests; el real está pendiente
#    de cablear un modelo gratuito, igual que horario_por_foto._extractor_simulado) ──
_PATRON_FECHA = re.compile(
    r"\b(hoy|mañana|pasado mañana|lunes|martes|mi[eé]rcoles|jueves|viernes|"
    r"s[aá]bado|domingo)\b", re.IGNORECASE)
_PATRON_HORA = re.compile(r"\b([01]?\d|2[0-3])(:[0-5]\d)?\s*(am|pm|hrs?)?\b", re.IGNORECASE)
_DISPARADORES = ("nos vemos", "quedamos", "recuérdame", "recuerdame", "tengo que",
                  "no se me olvide", "hay que", "cita")


def extractor_simulado(texto: str) -> list[dict]:
    """Detector de PRUEBA basado en reglas de texto (sin llamar a ningún
    modelo). Busca menciones de fecha con un disparador de compromiso cerca;
    NO es el extractor de producción (ese usa un modelo gratuito, r.91-style
    decisión pendiente de cablear el proveedor)."""
    candidatos = []
    for frase in re.split(r"[.\n]", texto):
        frase_norm = frase.strip()
        if not frase_norm:
            continue
        if not any(d in frase_norm.lower() for d in _DISPARADORES):
            continue
        m_fecha = _PATRON_FECHA.search(frase_norm)
        if not m_fecha:
            continue
        m_hora = _PATRON_HORA.search(frase_norm)
        candidatos.append({
            "descripcion": frase_norm,
            "fecha": m_fecha.group(0),
            "hora": m_hora.group(0).strip() if m_hora else None,
        })
    return candidatos
