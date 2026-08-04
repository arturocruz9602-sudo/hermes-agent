"""Pruebas del registro de autorización de terceros (HAS §B8 punto 4 /
§OT-11 punto 3 / puerta de §E7).

Invariantes que se clavan aquí:

  (1) `registrar(...)` exige nombre_autoriza y alcance no vacíos, y
      `vigencia_horas` > 0 -- nunca autorización indefinida.
  (2) `autoriza(objetivo)` es True si el objetivo es equipo propio
      (whitelist explícita, nunca adivinada) o si tiene un registro
      vigente con alcance exacto; False en cualquier otro caso.
  (3) una autorización expirada o revocada deja de contar para
      `autoriza()`/`exigir_autorizacion()`.
  (4) `exigir_autorizacion()` no lanza cuando `autoriza()` es True;
      lanza `AutorizacionRequerida` cuando es False -- "la skill se
      niega" (HAS §E7).
  (5) todo intento, concedido o negado, queda logueado (el silencio no
      es estado válido de fallo, CLAUDE.md regla 3).
  (6) una autorización no se revoca dos veces.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from registro_autorizacion_terceros import (  # noqa: E402
    AlcanceInvalido, AutorizacionInexistente, AutorizacionInvalida,
    AutorizacionRequerida, RegistroAutorizacionTerceros)


@pytest.fixture
def reg(tmp_path):
    db = tmp_path / "state_test.db"
    with RegistroAutorizacionTerceros(db_path=db) as r:
        yield r


# ── registrar ─────────────────────────────────────────────────────────────
def test_registrar_ok_normaliza_alcance_a_minusculas(reg):
    r = reg.registrar("Juan (dueño del laptop)", "  Laptop-Prestada.LOCAL  ",
                       vigencia_horas=4, chat_id="123")
    fila = reg.obtener(r["id"])
    assert fila["alcance"] == "laptop-prestada.local"
    assert fila["nombre_autoriza"] == "Juan (dueño del laptop)"
    assert fila["revocado_en"] is None


def test_registrar_nombre_vacio_falla(reg):
    with pytest.raises(AlcanceInvalido):
        reg.registrar("", "192.168.1.5")


def test_registrar_alcance_vacio_falla(reg):
    with pytest.raises(AlcanceInvalido):
        reg.registrar("Juan", "   ")


def test_registrar_vigencia_no_positiva_falla(reg):
    with pytest.raises(AlcanceInvalido):
        reg.registrar("Juan", "192.168.1.5", vigencia_horas=0)


def test_registrar_falla_queda_logueada(reg):
    with pytest.raises(AlcanceInvalido):
        reg.registrar("", "")
    logs = reg.con.execute(
        "SELECT * FROM registro_autorizacion_terceros_log WHERE evento='registrar'"
    ).fetchall()
    assert any(row["ok"] == 0 for row in logs)


# ── autoriza: equipos propios vs registro vigente ────────────────────────
def test_autoriza_equipo_propio_sin_registro(reg):
    assert reg.autoriza("hp-arturo", equipos_propios={"hp-arturo", "macbook-arturo"})
    assert not reg.autoriza("laptop-ajena", equipos_propios={"hp-arturo"})


def test_autoriza_con_registro_vigente(reg):
    reg.registrar("Juan", "192.168.1.5", vigencia_horas=1)
    assert reg.autoriza("192.168.1.5", equipos_propios=set())


def test_autoriza_sin_registro_ni_equipo_propio_es_falso(reg):
    assert not reg.autoriza("192.168.1.99", equipos_propios=set())


def test_autoriza_default_equipos_propios_vacio_sin_env(reg, monkeypatch):
    monkeypatch.delenv("HERMES_EQUIPOS_PROPIOS", raising=False)
    assert not reg.autoriza("hp-arturo")  # nada es "propio" sin decisión explícita


def test_autoriza_lee_equipos_propios_de_env(reg, monkeypatch):
    monkeypatch.setenv("HERMES_EQUIPOS_PROPIOS", "hp-arturo, macbook-arturo")
    assert reg.autoriza("HP-Arturo")  # normaliza a minúsculas de ambos lados


def test_autoriza_registra_intento_concedido_y_negado(reg):
    reg.registrar("Juan", "192.168.1.5", vigencia_horas=1)
    reg.autoriza("192.168.1.5", equipos_propios=set())
    reg.autoriza("192.168.1.77", equipos_propios=set())
    logs = reg.con.execute(
        "SELECT evento, ok FROM registro_autorizacion_terceros_log "
        "WHERE evento IN ('autoriza_registro', 'autoriza_denegado') ORDER BY id"
    ).fetchall()
    assert [(r["evento"], r["ok"]) for r in logs] == [
        ("autoriza_registro", 1), ("autoriza_denegado", 0)]


# ── expiración y revocación ───────────────────────────────────────────────
def test_registro_expirado_no_autoriza(reg):
    r = reg.registrar("Juan", "192.168.1.5", vigencia_horas=1)
    # fuerza la expiración directo en la fila (evita depender del reloj real)
    pasado = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    reg.con.execute(
        "UPDATE registro_autorizacion_terceros SET vigente_hasta=? WHERE id=?",
        (pasado, r["id"]))
    reg.con.commit()
    assert not reg.autoriza("192.168.1.5", equipos_propios=set())
    assert r["id"] not in [f["id"] for f in reg.vigentes()]


def test_revocar_quita_de_vigentes_y_de_autoriza(reg):
    r = reg.registrar("Juan", "192.168.1.5", vigencia_horas=1)
    assert reg.autoriza("192.168.1.5", equipos_propios=set())
    reg.revocar(r["id"])
    assert not reg.autoriza("192.168.1.5", equipos_propios=set())
    assert reg.obtener(r["id"])["revocado_en"] is not None


def test_revocar_dos_veces_falla(reg):
    r = reg.registrar("Juan", "192.168.1.5", vigencia_horas=1)
    reg.revocar(r["id"])
    with pytest.raises(AutorizacionInvalida):
        reg.revocar(r["id"])


def test_revocar_id_inexistente_falla(reg):
    with pytest.raises(AutorizacionInexistente):
        reg.revocar(9999)


# ── la puerta: exigir_autorizacion ────────────────────────────────────────
def test_exigir_autorizacion_no_lanza_si_autoriza(reg):
    reg.registrar("Juan", "192.168.1.5", vigencia_horas=1)
    reg.exigir_autorizacion("192.168.1.5", equipos_propios=set())  # no debe lanzar


def test_exigir_autorizacion_lanza_si_no_autoriza(reg):
    with pytest.raises(AutorizacionRequerida):
        reg.exigir_autorizacion("192.168.1.99", equipos_propios=set())


def test_exigir_autorizacion_equipo_propio_no_lanza(reg):
    reg.exigir_autorizacion("hp-arturo", equipos_propios={"hp-arturo"})
