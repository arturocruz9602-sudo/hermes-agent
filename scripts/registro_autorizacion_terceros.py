#!/usr/bin/env python3
"""
registro_autorizacion_terceros.py — Registro de autorización de terceros
(HAS §B8 punto 4 / §OT-11 punto 3, USB-llave; puerta que exige §E7 punto 5).

Antes de que el toolkit portable del USB-llave (o cualquier skill de
ciberseguridad doméstica de la Fase 10, aún no construida) toque una
máquina que no es de Arturo, tiene que existir un consentimiento
registrado. El lanzador (`start-*.sh/.command/.bat`, fuera de este
módulo) es quien MUESTRA el texto de consentimiento a quien presta el
equipo; este módulo es solo el candado: registra quién autorizó, para
qué `alcance` (hostname/IP/CIDR) y hasta cuándo, y es la única fuente
de verdad que consulta `exigir_autorizacion()` antes de dejar pasar
una acción.

Mismo patrón que `reglas_recordatorio.py`/`deteccion_espontanea.py`:
    - Nunca autorización indefinida sobre equipo ajeno: toda fila
      expira sola (`vigente_hasta`), igual se puede revocar antes.
    - `_log()` commitea de inmediato — un log de intento denegado que
      se pierde si el caller revienta después es el "silencio como
      estado de fallo" que CLAUDE.md regla 3 prohíbe.

EQUIPOS PROPIOS (pendiente de decisión de Arturo, ver docs/ESTADO.md):
    la lista de hostnames/IPs que NUNCA necesitan registro porque son
    de Arturo (la HP, su MacBook, etc.) no está definida en ningún doc
    todavía. Por default `EQUIPOS_PROPIOS` es un set VACÍO -- decisión
    deliberada: negar por default es más seguro que adivinar mal una
    lista de equipos propios. Se puede pasar explícito por parámetro o
    por `HERMES_EQUIPOS_PROPIOS` (CSV) mientras se define el estándar.

ENTORNOS (igual que cola_v2.py / reglas_recordatorio.py)
    HERMES_ENTORNO=real       -> ~/.hermes/state.db
    HERMES_ENTORNO=simulacion -> <disco externo>/pruebas/state_sim.db

USO
    with RegistroAutorizacionTerceros() as reg:
        reg.registrar("Juan (dueño del laptop)", "192.168.50.12",
                       vigencia_horas=4, chat_id="123")
        reg.exigir_autorizacion("192.168.50.12")   # no lanza -> sigue
        reg.exigir_autorizacion("192.168.50.99")   # lanza AutorizacionRequerida
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
DISCO_EXTERNO = Path(os.environ.get("HERMES_DISCO_PRUEBAS", "/mnt/seagate"))
DIR_PRUEBAS = DISCO_EXTERNO / "hermes_backups" / "pruebas"

RUTAS = {
    "real": HERMES_HOME / "state.db",
    "simulacion": DIR_PRUEBAS / "state_sim.db",
}

VIGENCIA_HORAS_DEFAULT = 24

log = logging.getLogger("hermes.registro_autorizacion_terceros")


def _equipos_propios_default() -> set[str]:
    crudo = os.environ.get("HERMES_EQUIPOS_PROPIOS", "")
    return {e.strip().lower() for e in crudo.split(",") if e.strip()}


class EntornoInvalido(ValueError):
    pass


class AutorizacionInexistente(LookupError):
    pass


class AutorizacionInvalida(RuntimeError):
    """La autorización ya fue revocada: no se revoca dos veces."""


class AlcanceInvalido(ValueError):
    """nombre_autoriza/alcance vacíos, o vigencia_horas <= 0."""


class AutorizacionRequerida(RuntimeError):
    """El objetivo no es equipo propio y no tiene registro vigente: la
    acción se niega (HAS §E7 regla codificada)."""


def _ruta(entorno: str | None) -> Path:
    ent = (entorno or os.environ.get("HERMES_ENTORNO") or "real").strip().lower()
    if ent not in RUTAS:
        raise EntornoInvalido(
            f"entorno '{ent}' no existe; use uno de: {', '.join(sorted(RUTAS))}")
    return RUTAS[ent]


def _ahora() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _normalizar(objetivo: str) -> str:
    return objetivo.strip().lower()


class RegistroAutorizacionTerceros:
    """Registro de consentimiento para tocar equipo ajeno. Context manager,
    misma BD que `cola_v2`/`reglas_recordatorio` (tabla propia).

    `db_path` explícito gana sobre `entorno` (lo usan las pruebas)."""

    def __init__(self, entorno: str | None = None, *, db_path: str | Path | None = None):
        self.ruta = Path(db_path) if db_path is not None else _ruta(entorno)
        self._con: sqlite3.Connection | None = None

    def __enter__(self) -> "RegistroAutorizacionTerceros":
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
            raise RuntimeError("usa RegistroAutorizacionTerceros dentro de un 'with'")
        return self._con

    def _crear_esquema(self) -> None:
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS registro_autorizacion_terceros (
              id INTEGER PRIMARY KEY,
              nombre_autoriza TEXT NOT NULL,
              alcance TEXT NOT NULL,        -- hostname/IP/CIDR, normalizado lower()
              chat_id TEXT,
              vigente_desde TEXT NOT NULL,
              vigente_hasta TEXT NOT NULL,
              revocado_en TEXT,
              creado_en TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_registro_alcance
              ON registro_autorizacion_terceros(alcance);

            -- Silencio no es estado válido de fallo (CLAUDE.md regla 3):
            -- todo intento de autorización, concedido o negado, queda aquí.
            CREATE TABLE IF NOT EXISTS registro_autorizacion_terceros_log (
              id INTEGER PRIMARY KEY,
              registro_id INTEGER,
              ts TEXT NOT NULL,
              evento TEXT NOT NULL,
              ok INTEGER NOT NULL,
              detalle TEXT,
              FOREIGN KEY (registro_id) REFERENCES registro_autorizacion_terceros(id)
            );
            """
        )

    def _log(self, registro_id: int | None, evento: str, ok: bool, *, detalle: str = "") -> None:
        self.con.execute(
            "INSERT INTO registro_autorizacion_terceros_log "
            "(registro_id, ts, evento, ok, detalle) VALUES (?, ?, ?, ?, ?)",
            (registro_id, _iso(_ahora()), evento, 1 if ok else 0, detalle),
        )
        self.con.commit()
        nivel = logging.INFO if ok else logging.WARNING
        log.log(nivel, "registro=%s %s ok=%s %s", registro_id, evento, ok, detalle)

    # ── registro / revocación ────────────────────────────────────────────
    def registrar(self, nombre_autoriza: str, alcance: str, *,
                   vigencia_horas: float = VIGENCIA_HORAS_DEFAULT,
                   chat_id: str | None = None) -> dict:
        """Registra el consentimiento ya mostrado y aceptado (el texto de
        consentimiento lo muestra el lanzador, fuera de este módulo).
        Expira sola a las `vigencia_horas` -- nunca autorización indefinida
        sobre equipo ajeno."""
        nombre = (nombre_autoriza or "").strip()
        obj = _normalizar(alcance or "")
        if not nombre or not obj:
            self._log(None, "registrar", False,
                       detalle=f"nombre={nombre_autoriza!r} alcance={alcance!r}")
            raise AlcanceInvalido("nombre_autoriza y alcance son obligatorios")
        if vigencia_horas <= 0:
            self._log(None, "registrar", False,
                       detalle=f"vigencia_horas={vigencia_horas} <= 0")
            raise AlcanceInvalido("vigencia_horas debe ser > 0")

        ahora = _ahora()
        hasta = ahora + timedelta(hours=vigencia_horas)
        cur = self.con.execute(
            "INSERT INTO registro_autorizacion_terceros "
            "(nombre_autoriza, alcance, chat_id, vigente_desde, vigente_hasta, creado_en) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, obj, str(chat_id) if chat_id is not None else None,
             _iso(ahora), _iso(hasta), _iso(ahora)),
        )
        rid = int(cur.lastrowid)
        self._log(rid, "registrar", True,
                   detalle=f"nombre={nombre!r} alcance={obj!r} hasta={_iso(hasta)}")
        self.con.commit()
        return {"id": rid, "alcance": obj, "vigente_hasta": _iso(hasta)}

    def obtener(self, registro_id: int) -> sqlite3.Row:
        fila = self.con.execute(
            "SELECT * FROM registro_autorizacion_terceros WHERE id = ?",
            (registro_id,)).fetchone()
        if fila is None:
            raise AutorizacionInexistente(f"no existe el registro id={registro_id}")
        return fila

    def revocar(self, registro_id: int) -> sqlite3.Row:
        fila = self.obtener(registro_id)
        if fila["revocado_en"] is not None:
            raise AutorizacionInvalida(
                f"registro id={registro_id} ya estaba revocado en {fila['revocado_en']}")
        self.con.execute(
            "UPDATE registro_autorizacion_terceros SET revocado_en=? WHERE id=?",
            (_iso(_ahora()), registro_id),
        )
        self._log(registro_id, "revocar", True)
        self.con.commit()
        return self.obtener(registro_id)

    # ── consulta ──────────────────────────────────────────────────────────
    def vigentes(self) -> list[sqlite3.Row]:
        ahora_iso = _iso(_ahora())
        return self.con.execute(
            "SELECT * FROM registro_autorizacion_terceros "
            "WHERE revocado_en IS NULL AND vigente_hasta > ? "
            "ORDER BY id", (ahora_iso,)).fetchall()

    # ── la puerta ─────────────────────────────────────────────────────────
    def autoriza(self, objetivo: str, *, equipos_propios: set[str] | None = None) -> bool:
        """True si `objetivo` es equipo propio o tiene un registro vigente
        cuyo alcance coincide exacto. Registra el intento (concedido o no)."""
        obj = _normalizar(objetivo or "")
        propios = equipos_propios if equipos_propios is not None else _equipos_propios_default()
        if obj in propios:
            self._log(None, "autoriza_equipo_propio", True, detalle=obj)
            return True
        for fila in self.vigentes():
            if fila["alcance"] == obj:
                self._log(fila["id"], "autoriza_registro", True, detalle=obj)
                return True
        self._log(None, "autoriza_denegado", False, detalle=obj)
        return False

    def exigir_autorizacion(self, objetivo: str, *,
                             equipos_propios: set[str] | None = None) -> None:
        """No lanza si `autoriza(objetivo)` es True; si no, lanza
        `AutorizacionRequerida` -- "la skill se niega" (HAS §E7)."""
        if not self.autoriza(objetivo, equipos_propios=equipos_propios):
            raise AutorizacionRequerida(
                f"'{objetivo}' no es equipo propio y no tiene registro de "
                f"autorización vigente (HAS §B8.4/§E7)")
