#!/usr/bin/env python3
"""
reglas_recordatorio.py — Motor de reglas explícitas (HAS §C Fase 9 / OT-9
punto 1: "recuérdame X los domingos 8pm").

Mismo doble candado que `deteccion_espontanea.py` y `horario_por_foto.py`
(r.89 "pregunta antes de crear" + OT-9 "parser NL → regla estructurada →
confirmación"):
    1. `proponer()` interpreta el texto (vía un `parser` INYECTABLE — el real
       llama a un modelo gratuito, el simulado usa reglas de texto fijas,
       igual que `deteccion_espontanea.extractor_simulado`) y arma una
       PROPUESTA legible. Nunca activa la regla por su cuenta.
    2. `confirmar(aprobado=True)` es la única puerta que activa una regla.
    3. Una regla activa NUNCA ejecuta directo: `disparar_hoy()` la manda a
       `cola_v2.ColaTareas.encolar(...)` — incluso el disparo pasa por la
       cola con garantía dura (HAS §E5), nunca por un side-effect suelto.

Reutiliza `normalizar_dia`/`normalizar_hora` de `horario_por_foto.py` (mismo
vocabulario de días/horas que ya usa Arturo, sin reinventar el parseo).

ENTORNOS (igual que cola_v2.py / deteccion_espontanea.py)
    HERMES_ENTORNO=real       -> ~/.hermes/state.db
    HERMES_ENTORNO=simulacion -> <disco externo>/pruebas/state_sim.db

USO
    from reglas_recordatorio import MotorReglas
    from cola_v2 import ColaTareas

    with MotorReglas() as motor:
        p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                            parser=mi_parser, chat_id="123")
        # ... Arturo responde "sí" a la propuesta p["id"]:
        motor.confirmar(p["id"], aprobado=True)
        # ... en el barrido diario (systemd timer / loop):
        with ColaTareas() as cola:
            motor.disparar_hoy(datetime.now(), cola)
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from horario_por_foto import ExtraccionInvalida, normalizar_dia, normalizar_hora  # noqa: E402

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
DISCO_EXTERNO = Path(os.environ.get("HERMES_DISCO_PRUEBAS", "/mnt/seagate"))
DIR_PRUEBAS = DISCO_EXTERNO / "hermes_backups" / "pruebas"

RUTAS = {
    "real": HERMES_HOME / "state.db",
    "simulacion": DIR_PRUEBAS / "state_sim.db",
}

PENDIENTE = "pendiente_confirmacion"
ACTIVA = "activa"
RECHAZADA = "rechazada"
ESTADOS = (PENDIENTE, ACTIVA, RECHAZADA)

log = logging.getLogger("hermes.reglas_recordatorio")

# Puerto inyectable: texto libre -> {"descripcion": str, "dias": [str...], "hora": str}
# Días y hora en crudo (p.ej. "domingos", "8pm") -- proponer() los normaliza
# con normalizar_dia/normalizar_hora, igual que horario_por_foto.
ParserRegla = Callable[[str], dict]


class EntornoInvalido(ValueError):
    pass


class ReglaInexistente(LookupError):
    pass


class EstadoInvalido(RuntimeError):
    """La regla ya fue resuelta (activa/rechazada): no se resuelve dos veces."""


class ParseoInvalido(ValueError):
    """El parser no devolvió una regla utilizable (sin días, sin hora, etc.)."""


def _ruta(entorno: str | None) -> Path:
    ent = (entorno or os.environ.get("HERMES_ENTORNO") or "real").strip().lower()
    if ent not in RUTAS:
        raise EntornoInvalido(
            f"entorno '{ent}' no existe; use uno de: {', '.join(sorted(RUTAS))}")
    return RUTAS[ent]


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class MotorReglas:
    """Reglas de recordatorio recurrente sobre `state.db`. Context manager,
    misma BD que `cola_v2`/`deteccion_espontanea` (tabla propia).

    `db_path` explícito gana sobre `entorno` (lo usan las pruebas)."""

    def __init__(self, entorno: str | None = None, *, db_path: str | Path | None = None):
        self.ruta = Path(db_path) if db_path is not None else _ruta(entorno)
        self._con: sqlite3.Connection | None = None

    def __enter__(self) -> "MotorReglas":
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
            raise RuntimeError("usa MotorReglas dentro de un 'with'")
        return self._con

    def _crear_esquema(self) -> None:
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS reglas_recordatorio (
              id INTEGER PRIMARY KEY,
              texto_origen TEXT NOT NULL,
              descripcion TEXT NOT NULL,
              dias_semana TEXT NOT NULL,   -- CSV de ints 1=lunes..7=domingo
              hora TEXT NOT NULL,          -- 'HH:MM' 24h
              estado TEXT NOT NULL DEFAULT 'pendiente_confirmacion',
              chat_id TEXT NOT NULL,
              creado_en TEXT NOT NULL,
              resuelto_en TEXT,
              ultima_ejecucion TEXT        -- 'YYYY-MM-DD' del último disparo
            );
            CREATE INDEX IF NOT EXISTS idx_reglas_estado
              ON reglas_recordatorio(estado);

            -- Silencio no es estado válido de fallo (CLAUDE.md regla 3).
            CREATE TABLE IF NOT EXISTS reglas_recordatorio_log (
              id INTEGER PRIMARY KEY,
              regla_id INTEGER,
              ts TEXT NOT NULL,
              evento TEXT NOT NULL,
              ok INTEGER NOT NULL,
              detalle TEXT,
              FOREIGN KEY (regla_id) REFERENCES reglas_recordatorio(id)
            );
            """
        )

    def _log(self, regla_id: int | None, evento: str, ok: bool, *, detalle: str = "") -> None:
        """Commitea de inmediato (no espera al commit del caller): un log de
        fallo que se pierde si el caller revienta después es exactamente el
        "silencio como estado de fallo" que CLAUDE.md regla 3 prohíbe."""
        self.con.execute(
            "INSERT INTO reglas_recordatorio_log (regla_id, ts, evento, ok, detalle) "
            "VALUES (?, ?, ?, ?, ?)",
            (regla_id, _ahora(), evento, 1 if ok else 0, detalle),
        )
        self.con.commit()
        nivel = logging.INFO if ok else logging.WARNING
        log.log(nivel, "regla=%s %s ok=%s %s", regla_id, evento, ok, detalle)

    # ── propuesta (nunca activa nada) ────────────────────────────────────
    def proponer(self, texto: str, parser: ParserRegla, chat_id: str) -> dict:
        """Interpreta `texto` con `parser` y registra una PROPUESTA. Nunca
        activa la regla — solo `confirmar(aprobado=True)` lo hace."""
        try:
            crudo = parser(texto)
        except Exception as exc:
            self._log(None, "parseo", False, detalle=str(exc))
            raise

        descripcion = (crudo.get("descripcion") or "").strip()
        dias_crudos = crudo.get("dias") or []
        hora_cruda = crudo.get("hora")
        if not descripcion or not dias_crudos or not hora_cruda:
            self._log(None, "parseo", False,
                      detalle=f"regla incompleta: {crudo!r}")
            raise ParseoInvalido(f"el texto no rindió una regla utilizable: {texto!r}")

        try:
            dias = sorted({normalizar_dia(d) for d in dias_crudos})
            hora = normalizar_hora(hora_cruda)
        except ExtraccionInvalida as exc:
            self._log(None, "parseo", False, detalle=str(exc))
            raise ParseoInvalido(str(exc)) from exc

        cur = self.con.execute(
            "INSERT INTO reglas_recordatorio "
            "(texto_origen, descripcion, dias_semana, hora, estado, chat_id, creado_en) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (texto, descripcion, ",".join(str(d) for d in dias), hora,
             PENDIENTE, str(chat_id), _ahora()),
        )
        rid = int(cur.lastrowid)
        self._log(rid, "proponer", True, detalle=f"{descripcion!r} dias={dias} hora={hora}")
        self.con.commit()
        return {
            "id": rid,
            "chat_id": str(chat_id),
            "pregunta": self.formatear_confirmacion(descripcion, dias, hora),
        }

    @staticmethod
    def formatear_confirmacion(descripcion: str, dias: list[int], hora: str) -> str:
        from horario_por_foto import DIAS_NOMBRE
        nombres = ", ".join(DIAS_NOMBRE[d].capitalize() for d in dias)
        return f"¿Te recuerdo \"{descripcion}\" los {nombres} a las {hora}?"

    # ── resolución ────────────────────────────────────────────────────────
    def obtener(self, regla_id: int) -> sqlite3.Row:
        fila = self.con.execute(
            "SELECT * FROM reglas_recordatorio WHERE id = ?", (regla_id,)).fetchone()
        if fila is None:
            raise ReglaInexistente(f"no existe la regla id={regla_id}")
        return fila

    def pendientes(self, chat_id: str | None = None) -> list[sqlite3.Row]:
        if chat_id is None:
            return self.con.execute(
                "SELECT * FROM reglas_recordatorio WHERE estado = ? ORDER BY id",
                (PENDIENTE,)).fetchall()
        return self.con.execute(
            "SELECT * FROM reglas_recordatorio WHERE estado = ? AND chat_id = ? ORDER BY id",
            (PENDIENTE, str(chat_id))).fetchall()

    def activas(self) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM reglas_recordatorio WHERE estado = ? ORDER BY id",
            (ACTIVA,)).fetchall()

    def confirmar(self, regla_id: int, *, aprobado: bool) -> sqlite3.Row:
        fila = self.obtener(regla_id)
        if fila["estado"] != PENDIENTE:
            raise EstadoInvalido(
                f"regla id={regla_id} ya está en estado '{fila['estado']}', "
                f"no se resuelve dos veces")
        nuevo_estado = ACTIVA if aprobado else RECHAZADA
        self.con.execute(
            "UPDATE reglas_recordatorio SET estado=?, resuelto_en=? WHERE id = ?",
            (nuevo_estado, _ahora(), regla_id),
        )
        self._log(regla_id, "confirmar", True, detalle=f"aprobado={aprobado}")
        self.con.commit()
        return self.obtener(regla_id)

    # ── disparo (única vía de ejecución: siempre por la cola) ────────────
    def disparar_hoy(self, ahora: datetime, cola) -> list[int]:
        """Encola (vía `cola.encolar`) cada regla activa cuyo día/hora ya
        llegó hoy y no se ha disparado hoy — idempotente por día: llamar
        varias veces el mismo día no duplica el encolado."""
        hoy_iso = ahora.strftime("%Y-%m-%d")
        hoy_dia = ahora.isoweekday()  # 1=lunes..7=domingo, igual que dias_semana
        hoy_hora = ahora.strftime("%H:%M")
        disparadas: list[int] = []
        for fila in self.activas():
            if fila["ultima_ejecucion"] == hoy_iso:
                continue
            dias = {int(d) for d in fila["dias_semana"].split(",") if d}
            if hoy_dia not in dias:
                continue
            if hoy_hora < fila["hora"]:
                continue
            try:
                cola.encolar(
                    fila["descripcion"],
                    {"tipo": "recordatorio_regla", "regla_id": fila["id"],
                     "hora": fila["hora"]},
                    fila["chat_id"],
                )
                self.con.execute(
                    "UPDATE reglas_recordatorio SET ultima_ejecucion=? WHERE id=?",
                    (hoy_iso, fila["id"]),
                )
                self._log(fila["id"], "disparar", True, detalle=f"fecha={hoy_iso}")
                self.con.commit()
                disparadas.append(int(fila["id"]))
            except Exception as exc:
                self._log(fila["id"], "disparar", False, detalle=str(exc))
                self.con.commit()
                raise
        return disparadas


# ── parser de PRUEBA (r.20: solo laboratorio/tests; el real cablea un modelo
#    gratuito, igual que deteccion_espontanea.extractor_simulado) ───────────
_PATRON_HORA = re.compile(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", re.IGNORECASE)
_DIAS_PALABRA = re.compile(
    r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bados?|domingos?)\b",
    re.IGNORECASE)


# Días cuyo singular ya termina en 's' en español (lunes, martes, miércoles,
# jueves, viernes: invariantes, "los lunes" no "los luneses"). Solo sábado y
# domingo pluralizan agregando 's' -- a esos hay que quitárselo antes de
# pasarlos a normalizar_dia() (que espera el singular).
_DIAS_INVARIANTES = {"lunes", "martes", "miercoles", "miércoles", "jueves", "viernes"}


def parser_simulado(texto: str) -> dict:
    """Detector de PRUEBA basado en reglas de texto para frases del tipo
    'recuérdame <algo> los <días> a las <hora>'. NO es el parser de
    producción (ese usa un modelo gratuito, decisión de proveedor pendiente
    igual que horario_por_foto)."""
    dias_norm = []
    for d in _DIAS_PALABRA.findall(texto):
        dias_norm.append(d[:-1] if d.lower() not in _DIAS_INVARIANTES else d)

    hora = None
    if " a las " in texto:
        m_hora = _PATRON_HORA.search(texto.split(" a las ")[-1])
        if m_hora:
            hora = m_hora.group(1).strip()

    m_desc = re.search(r"recu[eé]rdame\s+(?:que\s+|de\s+)?(.+?)\s+los\s+", texto, re.IGNORECASE)
    descripcion = m_desc.group(1).strip() if m_desc else ""

    return {"descripcion": descripcion, "dias": dias_norm, "hora": hora}
