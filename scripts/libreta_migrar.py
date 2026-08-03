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
    (
        2,
        "Frecuencia real de pagos + el negocio de refrescos (31 jul 2026)",
        [
            # pagos_recurrentes asumia mensual (dia_del_mes). La colegiatura
            # real de Arturo es CUATRIMESTRAL y el servicio de la moto
            # BIMESTRAL -- forzarlos a "mensual" habria hecho que Hermes le
            # avisara de pagos que no tocaban. frecuencia_meses reemplaza el
            # supuesto: 1=mensual, 2=bimestral, 4=cuatrimestral, etc.
            # ultimo_pago ancla desde cuando se cuenta el ciclo.
            """
            ALTER TABLE pagos_recurrentes
                ADD COLUMN frecuencia_meses INTEGER NOT NULL DEFAULT 1
                    CHECK (frecuencia_meses > 0)
            """,
            "ALTER TABLE pagos_recurrentes ADD COLUMN ultimo_pago TEXT",
            # El negocio de reventa dentro de la taqueria (compra rejas de
            # refresco a $328, vende por pieza a $20). Arturo NO sabe cuantas
            # piezas trae cada reja -- a proposito no se hardcodea esa cifra:
            # se registra cada compra y cada venta por separado y el margen se
            # calcula cruzando ambas, para que el patron salga solo con el
            # tiempo en vez de asumirlo de entrada.
            """
            CREATE TABLE IF NOT EXISTS negocio_compras (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT    NOT NULL,
                producto  TEXT    NOT NULL,
                unidad    TEXT    NOT NULL DEFAULT 'reja',
                costo_mxn REAL    NOT NULL CHECK (costo_mxn > 0),
                nota      TEXT,
                creado_en TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_negocio_compras_fecha ON negocio_compras(fecha)",
            """
            CREATE TABLE IF NOT EXISTS negocio_ventas (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha               TEXT    NOT NULL,
                producto            TEXT    NOT NULL,
                unidades            INTEGER NOT NULL CHECK (unidades > 0),
                precio_unitario_mxn REAL    NOT NULL CHECK (precio_unitario_mxn > 0),
                nota                TEXT,
                creado_en           TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_negocio_ventas_fecha ON negocio_ventas(fecha)",
        ],
    ),
    (
        3,
        "Banco de ideas de contenido -- rebotar ideas con Hermes, por voz o texto (31 jul 2026)",
        [
            # Distinto de memoria_estructurada (state.db): eso guarda HECHOS
            # sobre Arturo; esto guarda IDEAS DE CONTENIDO con estado propio
            # (pendiente/usada/descartada) y un hueco para que, con el tiempo,
            # Hermes sugiera cuando conviene publicarla segun calendario --
            # el ejemplo de Arturo: "hasta en la musica esperan temporada
            # para saber cuando es buena idea subir una cancion".
            """
            CREATE TABLE IF NOT EXISTS ideas_contenido (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                texto           TEXT    NOT NULL,
                tema            TEXT,
                formato         TEXT,                       -- 'podcast','short','video-ensayo'...
                origen          TEXT    NOT NULL DEFAULT 'conversacion',
                estado          TEXT    NOT NULL DEFAULT 'pendiente'
                                CHECK (estado IN ('pendiente','programada','usada','descartada')),
                fecha_sugerida  TEXT,                        -- cuando Hermes cree que conviene publicarla
                fecha_captura   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                nota            TEXT
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ideas_estado ON ideas_contenido(estado)",
        ],
    ),
    (
        4,
        "Reconciliar con el cuestionario del 01 ago: metas, pagos corregidos, peso y habitos reales (r.19/28/68/72)",
        [
            # Nota: v4 corrige DATOS (no esquema). Asume el camino canonico
            # (F11-e): se aplica sobre la libreta real o una copia restaurada.
            # En BD nueva, los UPDATE son no-op y los INSERT OR IGNORE dejan el
            # estado correcto de todos modos.
            # ── PAGOS: valores confirmados por Arturo el 01 ago (r.19) ──
            # 'internet' era en realidad la recarga de telefono ("el de ley").
            "UPDATE pagos_recurrentes SET nombre='recarga_telefono', nota='recarga de telefono, el de ley (r.19)' WHERE nombre='internet'",
            # gym 400 -> 500
            "UPDATE pagos_recurrentes SET monto_mxn=500 WHERE nombre='gym'",
            # servicio de moto 500 -> 550 (sigue bimestral)
            "UPDATE pagos_recurrentes SET monto_mxn=550 WHERE nombre='servicio_moto'",
            # colegiatura: real ~1100; Arturo pidio inflarla a 1200 como colchon
            "UPDATE pagos_recurrentes SET monto_mxn=1200, nota='cuatrimestral; real ~1100, inflado a 1200 como colchon (Arturo 01 ago); dia del mes por confirmar' WHERE nombre='colegiatura'",
            # deepseek: recarga fija mensual ~dia 28
            "INSERT OR IGNORE INTO pagos_recurrentes (nombre, monto_mxn, dia_del_mes, frecuencia_meses, nota) VALUES ('deepseek', 100, 28, 1, 'recarga fija; Hermes observa el gasto real promedio (r.19)')",
            # gasolina: variable ~200/mes, referencia de presupuesto (no es fijo)
            "INSERT OR IGNORE INTO pagos_recurrentes (nombre, monto_mxn, dia_del_mes, frecuencia_meses, nota) VALUES ('gasolina', 200, NULL, 1, 'variable ~200/mes promedio (r.19); referencia, no fijo')",
            # ── META NUEVA (r.28-31, 35): el capital, no la Mac ──
            "UPDATE ahorro_metas SET nombre='capital_principal', objetivo_mxn=100000, fecha_limite='2027-12-31', activa=1, nota='piso 90,000 (r.28); saldo 0 hoy; el capital ES el fondo de emergencia (r.35); Mac Studio y moto se compran DESDE aqui -- Mac Mini descartada (r.30)' WHERE nombre='Mac Mini o Mac Studio + moto (60,000)'",
            # robustez en BD nueva (si la fila vieja no existia)
            "INSERT OR IGNORE INTO ahorro_metas (nombre, objetivo_mxn, acumulado_mxn, fecha_limite, activa, nota) VALUES ('capital_principal', 100000, 0, '2027-12-31', 1, 'piso 90,000; el capital ES el fondo; Mac Studio/moto desde aqui; Mac Mini descartada')",
            # ── CUERPO: peso real (r.68) y habitos declarados (r.70-72) ──
            "INSERT INTO peso (fecha, kg, nota) SELECT '2026-08-01', 111.5, 'dato real (r.68); meta y ritmo por definir' WHERE NOT EXISTS (SELECT 1 FROM peso WHERE fecha='2026-08-01' AND kg=111.5)",
            "INSERT OR IGNORE INTO habitos (nombre, activo, nota) VALUES ('entrenar',1,'r.72'), ('estudiar',1,'r.72'), ('comer_limpio',1,'registro detallado de comidas (r.70)'), ('trabajo_profundo',1,'marco mental (r.78)'), ('cero_chelas',1,'regla principal; en riesgo explicar lo que se echa a perder + ventajas (r.71)'), ('descanso_estrategico',1,'r.72')",
        ],
    ),
    (
        5,
        "Escuela: horario por foto -- materia/profesor/cuatrimestre en horario (F6-2, OT-6 Bloque 1, HAS 1157)",
        [
            # 'horario' ya servia gimnasio/taqueria con actividad+lugar generico.
            # Estas columnas son NULL para esas filas; solo las de escuela las usan.
            # cuatrimestre es la clave del versionado F7: un horario nuevo archiva
            # (activo=0) al anterior, nunca lo borra -- historial academico permanente.
            "ALTER TABLE horario ADD COLUMN materia TEXT",
            "ALTER TABLE horario ADD COLUMN profesor TEXT",
            "ALTER TABLE horario ADD COLUMN cuatrimestre TEXT",
            "CREATE INDEX IF NOT EXISTS idx_horario_cuatrimestre ON horario(cuatrimestre)",
        ],
    ),
    (
        6,
        "Archivo permanente (F7-1, OT-7): tabla archivos (biblioteca, E2) + "
        "gastos gana comercio/evidencia_id para tickets con evidencia",
        [
            # categoria = que decidio el clasificador de entrada (E1): nunca
            # el tiempo. retention_class='permanent' siempre aqui -- lo
            # efimero (cache/) no se indexa en esta tabla, vive y expira
            # aparte. hash_sha256 evita duplicar la misma foto reenviada.
            """
            CREATE TABLE IF NOT EXISTS archivos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria       TEXT    NOT NULL CHECK (categoria IN
                                    ('ticket','familiar','escuela','contenido','otro')),
                filepath        TEXT    NOT NULL UNIQUE,
                hash_sha256     TEXT    NOT NULL,
                retention_class TEXT    NOT NULL DEFAULT 'permanent'
                                    CHECK (retention_class IN ('cache','permanent')),
                origen_nombre   TEXT,
                nota            TEXT,
                creado_en       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_archivos_categoria ON archivos(categoria)",
            "CREATE INDEX IF NOT EXISTS idx_archivos_hash ON archivos(hash_sha256)",
            "ALTER TABLE gastos ADD COLUMN comercio TEXT",
            "ALTER TABLE gastos ADD COLUMN evidencia_id INTEGER REFERENCES archivos(id)",
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
