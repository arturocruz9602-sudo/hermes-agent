"""Pruebas de la libreta de Arturo — con las variables que rompen cosas.

Pedido textual suyo el 31 jul 2026: *"por favor las pruebas si las pruebas y
todas sus variables posibles, todo estara mal para mi porque mi dia a dia sera
mas frustrante de lo que deberia"*. Tiene razon: una libreta que falla en
silencio es peor que no tener libreta, porque el confia y no revisa.

Cubre: aislamiento real/simulacion, reloj virtual, fronteras de fecha (fin de
mes, año bisiesto, cambio de año), montos limite, duplicados, texto hostil
(comillas, emojis, SQL), y los estados de tareas y citas.
"""

from __future__ import annotations

import importlib
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import libreta as libreta_mod  # noqa: E402


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Un par de libretas (real y simulacion) recien migradas, en tmp."""
    rutas = {"real": tmp_path / "libreta.db",
             "simulacion": tmp_path / "sim" / "libreta_sim.db"}
    monkeypatch.setattr(libreta_mod, "RUTAS", rutas)
    for ent, ruta in rutas.items():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "libreta_migrar.py"),
             "--entorno", ent],
            capture_output=True, text=True,
            env={"HOME": str(tmp_path), "HERMES_HOME": str(tmp_path),
                 "PATH": "/usr/bin:/bin"},
        )
        assert r.returncode == 0, r.stderr
    monkeypatch.delenv("HERMES_FECHA_SIMULADA", raising=False)
    monkeypatch.delenv("HERMES_ENTORNO", raising=False)
    return rutas


# ── lo que Arturo no puede permitirse que falle ──────────────────────────

def test_lo_simulado_jamas_toca_lo_real(entorno):
    """El limite duro de Arturo: los datos de prueba no contaminan lo real."""
    with libreta_mod.Libreta("simulacion") as sim:
        sim.registrar_gasto(500, "inventado", "esto es una prueba")
        sim.registrar_tarea("tarea falsa", fecha_entrega="2026-12-01")
        sim.agendar_cita("2026-12-01T10:00", "cita falsa")

    with libreta_mod.Libreta("real") as real:
        assert real.con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 0
        assert real.con.execute("SELECT COUNT(*) FROM tareas_escuela").fetchone()[0] == 0
        assert real.con.execute("SELECT COUNT(*) FROM citas").fetchone()[0] == 0


def test_el_reloj_falso_no_aplica_en_el_entorno_real(entorno, monkeypatch):
    """Un olvido de variable no debe escribir fechas falsas en datos reales."""
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2030-01-01T00:00")
    with libreta_mod.Libreta("simulacion") as sim:
        assert sim.hoy() == "2030-01-01"
    with libreta_mod.Libreta("real") as real:
        assert real.hoy() != "2030-01-01"


def test_entorno_inventado_se_rechaza(entorno):
    with pytest.raises(libreta_mod.EntornoInvalido):
        libreta_mod.Libreta("produccion")


def test_libreta_inexistente_dice_como_arreglarlo(tmp_path, monkeypatch):
    monkeypatch.setattr(libreta_mod, "RUTAS", {"real": tmp_path / "no-existe.db"})
    with pytest.raises(FileNotFoundError, match="libreta_migrar"):
        with libreta_mod.Libreta("real"):
            pass


# ── el reloj virtual y las fronteras de fecha ────────────────────────────

@pytest.mark.parametrize("fecha,esperado", [
    ("2026-12-31T23:59", "2026-12-31"),   # ultimo dia del año
    ("2028-02-29T12:00", "2028-02-29"),   # año bisiesto
    ("2027-01-01T00:00", "2027-01-01"),   # primer dia del año
    ("2026-08-31T23:59", "2026-08-31"),   # fin de mes
    ("2026-09-01", "2026-09-01"),         # sin hora
])
def test_reloj_virtual_en_fechas_frontera(entorno, monkeypatch, fecha, esperado):
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", fecha)
    with libreta_mod.Libreta("simulacion") as lib:
        assert lib.hoy() == esperado


def test_reloj_virtual_con_basura_falla_fuerte_y_explica(entorno, monkeypatch):
    """Mejor un error ruidoso que una fecha inventada en silencio."""
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "mañana por la tarde")
    with pytest.raises(ValueError, match="ISO 8601"):
        libreta_mod.hoy("simulacion")


def test_cambio_de_año_no_pierde_la_tarea(entorno, monkeypatch):
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-12-30T08:00")
    with libreta_mod.Libreta("simulacion") as lib:
        lib.registrar_tarea("entrega de enero", fecha_entrega="2027-01-05")
        assert len(lib.tareas_pendientes(dentro_de_dias=10)) == 1
        assert len(lib.tareas_pendientes(dentro_de_dias=3)) == 0


# ── dinero ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("monto", [0, -1, -0.01])
def test_gasto_invalido_se_rechaza(entorno, monto):
    with libreta_mod.Libreta("simulacion") as lib:
        with pytest.raises(sqlite3.IntegrityError):
            lib.registrar_gasto(monto, "x")


def test_centavos_no_se_pierden_al_sumar(entorno):
    with libreta_mod.Libreta("simulacion") as lib:
        for _ in range(3):
            lib.registrar_gasto(0.10, "prueba", fecha="2026-08-01")
        total = lib.con.execute("SELECT SUM(monto_mxn) FROM gastos").fetchone()[0]
    assert round(total, 2) == 0.30


def test_balance_solo_cuenta_el_rango_pedido(entorno):
    with libreta_mod.Libreta("simulacion") as lib:
        lib.registrar_ingreso(1000, "sueldo", fecha="2026-07-15")
        lib.registrar_ingreso(2000, "sueldo", fecha="2026-08-15")
        lib.registrar_gasto(300, "comida", fecha="2026-08-20")
        b = lib.balance(desde="2026-08-01", hasta="2026-08-31")
    assert b["ingresos"] == 2000 and b["gastos"] == 300 and b["saldo"] == 1700


def test_meta_de_ahorro_acumula_y_no_se_duplica(entorno):
    with libreta_mod.Libreta("simulacion") as lib:
        lib.meta_ahorro("Mac Mini", objetivo=16500)
        lib.meta_ahorro("Mac Mini", objetivo=17000)   # actualiza, no duplica
        lib.abonar_meta("Mac Mini", 5000)
        lib.abonar_meta("Mac Mini", 2500)
        m = lib.meta_ahorro("Mac Mini")
        n = lib.con.execute("SELECT COUNT(*) FROM ahorro_metas").fetchone()[0]
    assert n == 1 and m["objetivo_mxn"] == 17000 and m["acumulado_mxn"] == 7500


# ── escuela ──────────────────────────────────────────────────────────────

def test_el_mismo_correo_no_crea_dos_tareas(entorno):
    """Si el vigilante relee el buzon, no debe duplicar la tarea."""
    with libreta_mod.Libreta("simulacion") as lib:
        primero = lib.registrar_tarea("TAREA 4:BD_AGENCIA",
                                      correo_msgid="<x@classroom>")
        repetido = lib.registrar_tarea("TAREA 4:BD_AGENCIA",
                                       correo_msgid="<x@classroom>")
        n = lib.con.execute("SELECT COUNT(*) FROM tareas_escuela").fetchone()[0]
    assert primero is not None and repetido is None and n == 1


def test_tareas_sin_fecha_no_desaparecen(entorno, monkeypatch):
    """Una tarea sin fecha sigue siendo pendiente; no se cuela en 'proximos dias'."""
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-08-03T08:00")
    with libreta_mod.Libreta("simulacion") as lib:
        lib.registrar_tarea("sin fecha conocida")
        lib.registrar_tarea("con fecha", fecha_entrega="2026-08-05")
        assert len(lib.tareas_pendientes()) == 2
        assert len(lib.tareas_pendientes(dentro_de_dias=7)) == 1


def test_vencer_tareas_es_idempotente_y_respeta_hoy(entorno, monkeypatch):
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-08-10T08:00")
    with libreta_mod.Libreta("simulacion") as lib:
        lib.registrar_tarea("vieja", fecha_entrega="2026-08-01")
        lib.registrar_tarea("de hoy", fecha_entrega="2026-08-10")
        lib.registrar_tarea("futura", fecha_entrega="2026-08-20")
        assert lib.marcar_vencidas() == 1        # solo la vieja
        assert lib.marcar_vencidas() == 0        # correr otra vez no cambia nada
        estados = dict(lib.con.execute("SELECT titulo, estado FROM tareas_escuela"))
    assert estados == {"vieja": "vencida", "de hoy": "pendiente",
                       "futura": "pendiente"}


def test_estado_inventado_se_rechaza(entorno):
    with libreta_mod.Libreta("simulacion") as lib:
        with pytest.raises(sqlite3.IntegrityError):
            lib.con.execute(
                "INSERT INTO tareas_escuela (titulo, estado) VALUES (?,?)",
                ("x", "mas o menos"))


# ── citas y avisos ───────────────────────────────────────────────────────

def test_el_aviso_salta_en_su_ventana_y_no_antes(entorno, monkeypatch):
    with libreta_mod.Libreta("simulacion") as lib:
        lib.agendar_cita("2026-08-04T09:00", "colegiatura", recordar_min_antes=720)

    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-08-03T08:00")  # 25 h antes
    with libreta_mod.Libreta("simulacion") as lib:
        assert lib.pendientes_de_avisar() == []

    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-08-03T21:30")  # 11.5 h antes
    with libreta_mod.Libreta("simulacion") as lib:
        avisos = lib.pendientes_de_avisar()
        assert len(avisos) == 1
        lib.marcar_avisada(avisos[0]["id"])

    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-08-04T08:00")
    with libreta_mod.Libreta("simulacion") as lib:
        assert lib.pendientes_de_avisar() == []   # no repite el aviso


def test_cita_ya_pasada_sigue_saliendo_hasta_avisarla(entorno, monkeypatch):
    """Si Hermes estuvo caido, al volver no debe tragarse el aviso."""
    with libreta_mod.Libreta("simulacion") as lib:
        lib.agendar_cita("2026-08-04T09:00", "dentista", recordar_min_antes=60)
    monkeypatch.setenv("HERMES_FECHA_SIMULADA", "2026-08-06T10:00")
    with libreta_mod.Libreta("simulacion") as lib:
        assert len(lib.pendientes_de_avisar()) == 1


# ── texto hostil ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("texto", [
    "TAREA 4:BD_AGENCIA",
    "Evaluación de la experiencia — ñ, á, ü",
    "comillas 'simples' y \"dobles\"",
    "'; DROP TABLE gastos; --",
    "emoji 🎓📚 y salto\nde linea",
    "x" * 500,
])
def test_texto_raro_entra_y_sale_igual(entorno, texto):
    with libreta_mod.Libreta("simulacion") as lib:
        lib.registrar_tarea(texto)
    with libreta_mod.Libreta("simulacion") as lib:
        guardado = lib.con.execute(
            "SELECT titulo FROM tareas_escuela").fetchone()["titulo"]
        # la tabla sigue existiendo: nada de inyeccion
        assert lib.con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 0
    assert guardado == texto


# ── consistencia ─────────────────────────────────────────────────────────

def test_un_error_a_medias_no_deja_basura(entorno):
    """Si algo revienta dentro del with, no se guarda a medias."""
    with pytest.raises(RuntimeError):
        with libreta_mod.Libreta("simulacion") as lib:
            lib.registrar_gasto(100, "comida")
            raise RuntimeError("algo se rompio")
    with libreta_mod.Libreta("simulacion") as lib:
        assert lib.con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 0


def test_solo_lectura_no_deja_escribir(entorno):
    with libreta_mod.Libreta("simulacion", solo_lectura=True) as lib:
        with pytest.raises(sqlite3.OperationalError):
            lib.registrar_gasto(50, "comida")


def test_migrar_dos_veces_no_duplica_nada(entorno):
    """El migrador se puede correr sin miedo."""
    antes = None
    for _ in range(2):
        r = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "libreta_migrar.py"),
             "--entorno", "simulacion", "--estado"],
            capture_output=True, text=True,
            env={"HOME": str(entorno["real"].parent),
                 "HERMES_HOME": str(entorno["real"].parent), "PATH": "/usr/bin:/bin"},
        )
        assert r.returncode == 0
        if antes is None:
            antes = r.stdout
    with libreta_mod.Libreta("simulacion") as lib:
        n = lib.con.execute(
            "SELECT COUNT(*) FROM libreta_migraciones").fetchone()[0]
    assert n == 1
