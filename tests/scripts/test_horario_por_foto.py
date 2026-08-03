"""Pruebas de horario_por_foto.py (F6-2, OT-6 Bloque 1).

Clavan el doble candado antes de tocar la libreta real:
  (1) parsear_horario() nunca revienta con una fila mala -- la separa en
      errores para que la propuesta se la muestre a Arturo;
  (2) aplicar_horario() se NIEGA sin confirmado=True explícito;
  (3) versionado por cuatrimestre (HAS 1157): un horario nuevo ARCHIVA
      (activo=0) al anterior, nunca lo borra ni lo pisa;
  (4) reaplicar el mismo cuatrimestre es idempotente (no duplica filas).

Todo con SQLite en memoria y el extractor de vision INYECTADO -- nada de
red, nada de la libreta real (el extractor real sigue pendiente: r.91
prohíbe mandar nombres de profesores a una API gratis, ver docstring del
módulo).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from horario_por_foto import (  # noqa: E402
    ConfirmacionRequerida,
    aplicar_horario,
    formatear_propuesta,
    normalizar_dia,
    normalizar_hora,
    parsear_horario,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""
        CREATE TABLE horario (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_semana  INTEGER NOT NULL,
            hora_inicio TEXT    NOT NULL,
            hora_fin    TEXT,
            actividad   TEXT    NOT NULL,
            lugar       TEXT,
            activo      INTEGER NOT NULL DEFAULT 1,
            materia     TEXT,
            profesor    TEXT,
            cuatrimestre TEXT
        )
    """)
    yield c
    c.close()


FILAS_OK = [
    {"dia": "Lunes", "hora_inicio": "8:00", "hora_fin": "9:30",
     "materia": "Programación Web", "aula": "B-204", "profesor": "Ing. Ríos"},
    {"dia": "Miércoles", "hora_inicio": "8am", "hora_fin": "9:30 am",
     "materia": "Programación Web", "aula": "B-204", "profesor": "Ing. Ríos"},
]


# ── normalizar_dia / normalizar_hora ─────────────────────────────────────
@pytest.mark.parametrize("texto,esperado", [
    ("Lunes", 1), ("lun", 1), ("MARTES", 2), ("Miércoles", 3),
    ("miercoles", 3), ("Jueves", 4), ("Viernes", 5), ("Sábado", 6),
    ("Domingo", 7),
])
def test_normalizar_dia_formas_validas(texto, esperado):
    assert normalizar_dia(texto) == esperado


def test_normalizar_dia_invalido():
    with pytest.raises(Exception):
        normalizar_dia("marciano")


@pytest.mark.parametrize("texto,esperado", [
    ("8:00", "08:00"), ("8am", "08:00"), ("8:00 am", "08:00"),
    ("1:30 pm", "13:30"), ("13:30", "13:30"), ("12:00 am", "00:00"),
    ("12:00 pm", "12:00"), ("9", "09:00"),
])
def test_normalizar_hora_formas_validas(texto, esperado):
    assert normalizar_hora(texto) == esperado


def test_normalizar_hora_invalida():
    with pytest.raises(Exception):
        normalizar_hora("mediodía")


# ── parsear_horario: nunca revienta, separa errores ──────────────────────
def test_parsear_filas_validas():
    entradas, errores = parsear_horario(FILAS_OK)
    assert len(entradas) == 2
    assert errores == []
    assert entradas[0].materia == "Programación Web"
    assert entradas[0].dia_semana == 1
    assert entradas[0].hora_inicio == "08:00"


def test_parsear_fila_mala_no_revienta_y_se_reporta():
    filas = FILAS_OK + [
        {"dia": "Lunes", "hora_inicio": "no-se-entiende", "materia": "Cálculo"},
        {"dia": "Lunes", "hora_inicio": "8:00", "materia": ""},  # sin materia
    ]
    entradas, errores = parsear_horario(filas)
    assert len(entradas) == 2  # las 2 buenas SÍ pasan
    assert len(errores) == 2   # las 2 malas se reportan, no se pierden ni truenan


def test_parsear_lista_vacia():
    entradas, errores = parsear_horario([])
    assert entradas == []
    assert errores == []


# ── formatear_propuesta: legible, incluye pregunta de confirmación ───────
def test_formatear_propuesta_incluye_pregunta_y_errores():
    entradas, _ = parsear_horario(FILAS_OK)
    texto = formatear_propuesta(entradas, ["fila 3: hora ilegible"], "2026-C3")
    assert "2026-C3" in texto
    assert "¿Lo doy de alta así?" in texto
    assert "Programación Web" in texto
    assert "fila 3: hora ilegible" in texto


# ── aplicar_horario: el candado de confirmación ──────────────────────────
def test_aplicar_sin_confirmar_se_niega(conn):
    entradas, _ = parsear_horario(FILAS_OK)
    with pytest.raises(ConfirmacionRequerida):
        aplicar_horario(conn, entradas, "2026-C3", confirmado=False)
    assert conn.execute("SELECT COUNT(*) FROM horario").fetchone()[0] == 0


def test_aplicar_confirmado_inserta(conn):
    entradas, _ = parsear_horario(FILAS_OK)
    n = aplicar_horario(conn, entradas, "2026-C3", confirmado=True)
    assert n == 2
    filas = conn.execute(
        "SELECT materia, dia_semana, cuatrimestre, activo FROM horario"
    ).fetchall()
    assert len(filas) == 2
    assert all(f[2] == "2026-C3" and f[3] == 1 for f in filas)


def test_aplicar_sin_entradas_falla(conn):
    with pytest.raises(ValueError):
        aplicar_horario(conn, [], "2026-C3", confirmado=True)


# ── versionado por cuatrimestre: archiva, nunca pisa ni borra ────────────
def test_cuatrimestre_nuevo_archiva_el_anterior_sin_borrarlo(conn):
    entradas1, _ = parsear_horario(FILAS_OK)
    aplicar_horario(conn, entradas1, "2026-C2", confirmado=True)

    entradas2, _ = parsear_horario([
        {"dia": "Martes", "hora_inicio": "10:00", "hora_fin": "11:30",
         "materia": "Estructuras de Datos", "aula": "A-101", "profesor": "Ing. Paz"},
    ])
    aplicar_horario(conn, entradas2, "2026-C3", confirmado=True)

    viejas = conn.execute(
        "SELECT activo FROM horario WHERE cuatrimestre='2026-C2'"
    ).fetchall()
    nuevas = conn.execute(
        "SELECT activo FROM horario WHERE cuatrimestre='2026-C3'"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM horario").fetchone()[0]

    assert all(v[0] == 0 for v in viejas)   # archivadas, no activas
    assert len(viejas) == 2                  # pero SIGUEN en la tabla (no borradas)
    assert all(v[0] == 1 for v in nuevas)   # las nuevas sí activas
    assert total == 3                        # 2 viejas + 1 nueva, nada perdido


def test_reaplicar_mismo_cuatrimestre_es_idempotente(conn):
    entradas, _ = parsear_horario(FILAS_OK)
    n1 = aplicar_horario(conn, entradas, "2026-C3", confirmado=True)
    n2 = aplicar_horario(conn, entradas, "2026-C3", confirmado=True)
    total = conn.execute("SELECT COUNT(*) FROM horario").fetchone()[0]
    assert n1 == 2
    assert n2 == 0       # nada nuevo que insertar
    assert total == 2    # no se duplicó


def test_gym_y_taqueria_no_se_ven_afectados_por_archivado_de_escuela(conn):
    # 'horario' es compartido: filas sin materia (gym/taqueria) deben
    # sobrevivir intactas al archivado de un cuatrimestre nuevo.
    conn.execute(
        "INSERT INTO horario (dia_semana, hora_inicio, hora_fin, actividad, "
        "lugar, activo) VALUES (1, '18:00', '22:30', 'taqueria', NULL, 1)"
    )
    entradas, _ = parsear_horario(FILAS_OK)
    aplicar_horario(conn, entradas, "2026-C3", confirmado=True)
    taqueria = conn.execute(
        "SELECT activo FROM horario WHERE actividad='taqueria'"
    ).fetchone()
    assert taqueria[0] == 1
