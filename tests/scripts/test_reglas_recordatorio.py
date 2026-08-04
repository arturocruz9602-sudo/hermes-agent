"""Pruebas del motor de reglas explícitas (HAS OT-9 punto 1).

Invariantes que se clavan aquí:

  (1) `proponer(...)` interpreta el texto pero NUNCA activa la regla — solo
      la deja `pendiente_confirmacion` con una pregunta legible.
  (2) solo `confirmar(aprobado=True)` la activa; una regla no se resuelve
      dos veces.
  (3) `disparar_hoy(...)` solo dispara reglas ACTIVAS cuyo día/hora ya
      llegó, y solo una vez por día (idempotente) — y siempre pasa por
      `cola_v2.ColaTareas.encolar`, nunca por un side-effect suelto.
  (4) un texto que no rinde días/hora utilizables falla con `ParseoInvalido`
      y queda logueado (el silencio no es estado válido de fallo).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from cola_v2 import ColaTareas  # noqa: E402
from reglas_recordatorio import (ACTIVA, PENDIENTE, RECHAZADA,  # noqa: E402
                                  EstadoInvalido, MotorReglas, ParseoInvalido,
                                  ReglaInexistente, parser_simulado)


def parser_fijo(_texto):
    return {"descripcion": "sacar la basura", "dias": ["domingo"], "hora": "8pm"}


def parser_incompleto(_texto):
    return {"descripcion": "", "dias": [], "hora": None}


@pytest.fixture
def motor(tmp_path):
    db = tmp_path / "state_test.db"
    with MotorReglas(db_path=db) as m:
        yield m


@pytest.fixture
def cola(tmp_path):
    db = tmp_path / "state_test.db"  # misma BD que `motor`: tablas separadas
    with ColaTareas(db_path=db) as c:
        yield c


# ── proponer nunca activa nada ───────────────────────────────────────────
def test_proponer_registra_pendiente_normalizado(motor):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    fila = motor.obtener(p["id"])
    assert fila["estado"] == PENDIENTE
    assert fila["dias_semana"] == "7"          # domingo = 7
    assert fila["hora"] == "20:00"             # 8pm normalizado a 24h
    assert "domingo" in p["pregunta"].lower()


def test_proponer_no_activa_ni_toca_la_cola(motor, cola):
    motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                   parser=parser_fijo, chat_id="123")
    assert motor.activas() == []
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 0


def test_proponer_con_parser_incompleto_falla_y_loguea(motor):
    with pytest.raises(ParseoInvalido):
        motor.proponer("algo vago", parser=parser_incompleto, chat_id="1")
    logs = motor.con.execute(
        "SELECT * FROM reglas_recordatorio_log WHERE evento='parseo'").fetchall()
    assert any(row["ok"] == 0 for row in logs)


def test_proponer_con_parser_que_avienta_excepcion_se_propaga_y_loguea(motor):
    def parser_roto(_texto):
        raise RuntimeError("modelo caído")

    with pytest.raises(RuntimeError):
        motor.proponer("algo", parser=parser_roto, chat_id="1")
    logs = motor.con.execute(
        "SELECT * FROM reglas_recordatorio_log WHERE evento='parseo'").fetchall()
    assert any("modelo caído" in row["detalle"] for row in logs)


# ── confirmar es la única puerta que activa ──────────────────────────────
def test_confirmar_aprobado_activa(motor):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    fila = motor.confirmar(p["id"], aprobado=True)
    assert fila["estado"] == ACTIVA
    assert len(motor.activas()) == 1


def test_confirmar_rechazado_no_activa(motor):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    fila = motor.confirmar(p["id"], aprobado=False)
    assert fila["estado"] == RECHAZADA
    assert motor.activas() == []


def test_confirmar_dos_veces_falla(motor):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    motor.confirmar(p["id"], aprobado=True)
    with pytest.raises(EstadoInvalido):
        motor.confirmar(p["id"], aprobado=True)


def test_confirmar_id_inexistente_falla(motor):
    with pytest.raises(ReglaInexistente):
        motor.confirmar(9999, aprobado=True)


# ── disparo: solo activas, solo cuando llega el día/hora, una vez al día ─
def test_disparar_hoy_dispara_activa_en_su_dia_y_hora(motor, cola):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    motor.confirmar(p["id"], aprobado=True)

    domingo_noche = datetime(2026, 8, 2, 20, 30)  # 2-ago-2026 es domingo
    assert domingo_noche.isoweekday() == 7
    disparadas = motor.disparar_hoy(domingo_noche, cola)
    assert disparadas == [p["id"]]

    tarea = cola.con.execute("SELECT * FROM task_queue").fetchone()
    assert tarea["descripcion"] == "sacar la basura"
    assert tarea["chat_id"] == "123"


def test_disparar_hoy_no_dispara_otro_dia(motor, cola):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    motor.confirmar(p["id"], aprobado=True)

    lunes = datetime(2026, 8, 3, 20, 30)  # 3-ago-2026 es lunes
    assert lunes.isoweekday() == 1
    assert motor.disparar_hoy(lunes, cola) == []
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 0


def test_disparar_hoy_no_dispara_antes_de_la_hora(motor, cola):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    motor.confirmar(p["id"], aprobado=True)

    domingo_temprano = datetime(2026, 8, 2, 7, 0)
    assert motor.disparar_hoy(domingo_temprano, cola) == []


def test_disparar_hoy_es_idempotente_mismo_dia(motor, cola):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    motor.confirmar(p["id"], aprobado=True)

    domingo_noche = datetime(2026, 8, 2, 20, 30)
    motor.disparar_hoy(domingo_noche, cola)
    otra_pasada = datetime(2026, 8, 2, 21, 0)  # mismo día, más tarde
    disparadas_2 = motor.disparar_hoy(otra_pasada, cola)
    assert disparadas_2 == []
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 1


def test_disparar_hoy_vuelve_a_disparar_el_domingo_siguiente(motor, cola):
    p = motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                       parser=parser_fijo, chat_id="123")
    motor.confirmar(p["id"], aprobado=True)

    motor.disparar_hoy(datetime(2026, 8, 2, 20, 30), cola)
    siguiente_domingo = datetime(2026, 8, 9, 20, 30)
    assert motor.disparar_hoy(siguiente_domingo, cola) == [p["id"]]
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 2


def test_pendientes_filtra_por_chat(motor):
    motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                   parser=parser_fijo, chat_id="A")
    motor.proponer("recuérdame sacar la basura los domingos a las 8pm",
                   parser=parser_fijo, chat_id="B")
    assert len(motor.pendientes(chat_id="A")) == 1
    assert len(motor.pendientes()) == 2


# ── parser de prueba basado en reglas de texto ───────────────────────────
def test_parser_simulado_dias_invariantes_y_hora():
    r = parser_simulado("recuérdame que llame al doctor los lunes y jueves a las 10am")
    assert r["descripcion"] == "llame al doctor"
    assert r["dias"] == ["lunes", "jueves"]
    assert r["hora"] == "10am"


def test_parser_simulado_dias_pluralizados_sabado_domingo():
    r = parser_simulado("recuérdame regar las plantas los sábados a las 9am")
    assert r["dias"] == ["sábado"]


def test_parser_simulado_sin_hora_devuelve_none():
    r = parser_simulado("recuérdame algo los domingos")
    assert r["hora"] is None
