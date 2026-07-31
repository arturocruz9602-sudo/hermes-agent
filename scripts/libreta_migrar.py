#!/usr/bin/env python3
"""
libreta_migrar.py — Crea y versiona "la libreta": el esquema donde Hermes anota
la vida de Arturo.

El problema que resuelve (diagnosticado el 31 jul 2026): Hermes YA tiene skills
de finanzas, salud, escuela y YouTube, pero en las 27 tablas de state.db no
existe NI UNA de gastos, peso, entrenamientos ni tareas. Sabe hacer las cosas y
no tiene donde anotarlas. Por eso todo se le olvida.

Vive en su propia BD (~/.hermes/libreta.db) y no en state.db, a proposito:
state.db es del proyecto original y el gateway la escribe en vivo. Ver ESTADO.md.

Es idempotente: se puede correr las veces que haga falta.

USO:
  python3 libreta_migrar.py            → aplica lo que falte
  python3 libreta_migrar.py --estado   → solo informa, no toca nada
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import RUTAS, entorno_activo  # noqa: E402

# Cada migracion es (version, descripcion, [sentencias]). Nunca se edita una ya
# aplicada: se agrega una nueva abajo.
MIGRACIONES = [
    (
        1,
        "Esquema inicial de la libreta: dinero, cuerpo, tiempo y escuela",
        [
            # ── DINERO ────────────────────────────────────────────────────
            # Montos en REAL (pesos con centavos). Supuesto explicito: para el
            # uso de Arturo -- sumas de decenas a miles de pesos -- el error de
            # coma flotante es irrelevante y gana la legibilidad.
            """
            CREATE TABLE IF NOT EXISTS ingresos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT    NOT NULL,              -- ISO 8601 (YYYY-MM-DD)
                monto_mxn   REAL    NOT NULL CHECK (monto_mxn > 0),
                fuente      TEXT    NOT NULL,              -- 'sueldo', 'clases', ...
                nota        TEXT,
                creado_en   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ingresos_fecha ON ingresos(fecha)",
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha         TEXT    NOT NULL,
                monto_mxn     REAL    NOT NULL CHECK (monto_mxn > 0),
                categoria     TEXT    NOT NULL,            -- 'comida', 'escuela', ...
                descripcion   TEXT,
                recurrente_id INTEGER REFERENCES pagos_recurrentes(id),
                creado_en     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_gastos_categoria ON gastos(categoria)",
            """
            CREATE TABLE IF NOT EXISTS pagos_recurrentes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre       TEXT    NOT NULL UNIQUE,      -- 'colegiatura', 'internet'
                monto_mxn    REAL    NOT NULL CHECK (monto_mxn > 0),
                dia_del_mes  INTEGER CHECK (dia_del_mes BETWEEN 1 AND 31),
                activo       INTEGER NOT NULL DEFAULT 1,
                nota         TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ahorro_metas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL UNIQUE,    -- 'Mac Mini', 'los 60 mil'
                objetivo_mxn   REAL    NOT NULL CHECK (objetivo_mxn > 0),
                acumulado_mxn  REAL    NOT NULL DEFAULT 0,
                fecha_limite   TEXT,
                activa         INTEGER NOT NULL DEFAULT 1,
                nota           TEXT
            )
            """,
            # ── CUERPO ────────────────────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS peso (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT    NOT NULL,
                kg        REAL    NOT NULL CHECK (kg > 0 AND kg < 400),
                nota      TEXT,
                creado_en TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_peso_fecha ON peso(fecha)",
            """
            CREATE TABLE IF NOT EXISTS entrenamientos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha        TEXT    NOT NULL,
                tipo         TEXT    NOT NULL,             -- 'pesas', 'correr', ...
                duracion_min INTEGER CHECK (duracion_min > 0),
                nota         TEXT,
                creado_en    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_entrenamientos_fecha ON entrenamientos(fecha)",
            """
            CREATE TABLE IF NOT EXISTS habitos (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT    NOT NULL UNIQUE,
                activo INTEGER NOT NULL DEFAULT 1,
                nota   TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS habitos_registro (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                habito_id INTEGER NOT NULL REFERENCES habitos(id),
                fecha     TEXT    NOT NULL,
                cumplido  INTEGER NOT NULL DEFAULT 1,
                UNIQUE (habito_id, fecha)
            )
            """,
            # ── TIEMPO ────────────────────────────────────────────────────
            """
            CREATE TABLE IF NOT EXISTS horario (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_semana  INTEGER NOT NULL CHECK (dia_semana BETWEEN 1 AND 7), -- 1=lunes
                hora_inicio TEXT    NOT NULL,             -- 'HH:MM'
                hora_fin    TEXT,
                actividad   TEXT    NOT NULL,
                lugar       TEXT,
                activo      INTEGER NOT NULL DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS citas (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora         TEXT    NOT NULL,       -- ISO 8601
                titulo             TEXT    NOT NULL,
                lugar              TEXT,
                nota               TEXT,
                recordar_min_antes INTEGER DEFAULT 60,
                avisado            INTEGER NOT NULL DEFAULT 0,
                creado_en          TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas(fecha_hora)",
            # ── ESCUELA Y TRABAJO ─────────────────────────────────────────
            # tareas_escuela nace del hallazgo del 31 jul: las tareas de Arturo
            # llegan a su correo institucional y nadie las anotaba.
            """
            CREATE TABLE IF NOT EXISTS tareas_escuela (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo        TEXT    NOT NULL,
                materia       TEXT,
                maestro       TEXT,
                fecha_entrega TEXT,
                estado        TEXT    NOT NULL DEFAULT 'pendiente'
                              CHECK (estado IN ('pendiente','en_curso','entregada','vencida')),
                origen        TEXT,                        -- 'correo', 'arturo', ...
                correo_msgid  TEXT UNIQUE,                 -- evita duplicar el mismo correo
                nota          TEXT,
                creado_en     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_tareas_entrega ON tareas_escuela(fecha_entrega)",
            "CREATE INDEX IF NOT EXISTS idx_tareas_estado ON tareas_escuela(estado)",
            """
            CREATE TABLE IF NOT EXISTS guiones (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo     TEXT    NOT NULL,
                plataforma TEXT,                           -- 'youtube', ...
                estado     TEXT    NOT NULL DEFAULT 'idea'
                           CHECK (estado IN ('idea','escribiendo','listo','grabado','publicado')),
                fecha      TEXT,
                nota       TEXT,
                creado_en  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
        ],
    ),
]


def version_actual(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS libreta_migraciones (
            version     INTEGER PRIMARY KEY,
            descripcion TEXT NOT NULL,
            aplicada_en TEXT NOT NULL
        )
    """)
    con.commit()
    r = con.execute("SELECT COALESCE(MAX(version), 0) FROM libreta_migraciones").fetchone()
    return r[0]


def _entorno_de_argv():
    """--entorno X, o la variable HERMES_ENTORNO, o 'real'."""
    if "--entorno" in sys.argv:
        i = sys.argv.index("--entorno")
        if i + 1 < len(sys.argv):
            return entorno_activo(sys.argv[i + 1])
        print("🔴 --entorno necesita un valor: real | simulacion")
        sys.exit(2)
    return entorno_activo()


def main():
    solo_estado = "--estado" in sys.argv
    entorno = _entorno_de_argv()
    LIBRETA = str(RUTAS[entorno])
    Path(LIBRETA).parent.mkdir(parents=True, exist_ok=True)
    nueva = not os.path.exists(LIBRETA)
    print(f"entorno: {entorno} -> {LIBRETA}")

    con = sqlite3.connect(LIBRETA)
    con.execute("PRAGMA foreign_keys = ON")
    actual = version_actual(con)
    objetivo = max(v for v, _, _ in MIGRACIONES)

    if solo_estado:
        print(f"BD: {LIBRETA} ({'nueva' if nueva else 'existente'})")
        print(f"version aplicada: {actual} · disponible: {objetivo}")
        for v, d, _ in MIGRACIONES:
            print(f"   [{'x' if v <= actual else ' '}] v{v} — {d}")
        con.close()
        return

    aplicadas = 0
    for v, desc, sentencias in sorted(MIGRACIONES):
        if v <= actual:
            continue
        print(f"aplicando v{v}: {desc}")
        try:
            for s in sentencias:
                con.execute(s)
            con.execute(
                "INSERT INTO libreta_migraciones (version, descripcion, aplicada_en) VALUES (?,?,?)",
                (v, desc, datetime.now().isoformat(timespec="seconds")),
            )
            con.commit()
            aplicadas += 1
        except Exception as e:
            con.rollback()
            print(f"🔴 FALLO en v{v}: {e}")
            con.close()
            sys.exit(1)

    tablas = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    print(f"✅ {aplicadas} migracion(es) aplicada(s) · {len(tablas)} tablas")
    print("   " + ", ".join(tablas))
    con.close()


if __name__ == "__main__":
    main()
