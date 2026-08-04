"""Pruebas de la ventana de mantenimiento nocturna (HAS §E14, r.103).

Tres fronteras que el bloque promete y estas pruebas clavan:

  1. VENTANA HORARIA: `correr()` se niega a trabajar fuera de 2:00-5:00 salvo
     `forzar=True` -- un mantenimiento que invade horario de servicio es bug
     (HAS §E14), no característica.
  2. GATE TÉRMICO (r.103): `gate_termico()` pausa mientras la HP esté a
     >=85°C y sigue en cuanto baja -- con lector/dormir inyectados, nunca
     duerme ni lee /sys de verdad en la prueba.
  3. SKILLS STALE (HAS §F5/§E3): `detectar_skills_stale()` marca solo las
     `status: active` con `last_verified` > 180 días; `acumular()` las encola
     sin duplicar; `correr()` las procesa sobre la GARANTÍA DURA ya probada
     de `cola_v2` (F5-2) -- toda tarea termina `notificada` o `atorada`.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import ventana_mantenimiento as vm  # noqa: E402
from cola_v2 import ATORADA, ENCOLADA, NOTIFICADA, ColaTareas  # noqa: E402

NO_DORMIR = lambda _s: None  # noqa: E731 -- sin esperas reales en pruebas


@pytest.fixture
def cola(tmp_path):
    db = tmp_path / "state_test.db"
    with ColaTareas(db_path=db) as c:
        yield c


def _skill(tmp_path, nombre, *, status="active", last_verified="2026-07-28"):
    d = tmp_path / nombre
    d.mkdir(parents=True, exist_ok=True)
    fm_lv = f"last_verified: {last_verified}\n" if last_verified else ""
    (d / "SKILL.md").write_text(
        "---\n"
        f"name: {nombre}\n"
        f"status: {status}\n"
        f"{fm_lv}"
        "---\n"
        "# contenido\n",
        encoding="utf-8",
    )
    return d / "SKILL.md"


# ── 1. ventana horaria ───────────────────────────────────────────────────────
@pytest.mark.parametrize("hora,esperado", [(1, False), (2, True), (4, True), (5, False), (14, False)])
def test_en_ventana_solo_2_a_5(hora, esperado):
    ahora = datetime(2026, 8, 3, hora, 30)
    assert vm.en_ventana(ahora) is esperado


def test_correr_se_niega_fuera_de_ventana_sin_forzar(cola):
    r = vm.correr(cola, ahora=datetime(2026, 8, 3, 14, 0), gate=lambda: None)
    assert r == {"corrido": False, "razon": "fuera de ventana 2:00-5:00 (HAS E14)",
                 "resueltas": 0, "atoradas": 0}


def test_correr_con_forzar_ignora_horario(cola):
    r = vm.correr(cola, forzar=True, ahora=datetime(2026, 8, 3, 14, 0), gate=lambda: None)
    assert r["corrido"] is True


# ── 2. gate térmico ──────────────────────────────────────────────────────────
def test_gate_termico_pasa_directo_si_temp_baja():
    llamadas = {"avisar": 0}
    vm.gate_termico(lector=lambda: 50, dormir=NO_DORMIR,
                     avisar=lambda *_a: llamadas.__setitem__("avisar", llamadas["avisar"] + 1))
    assert llamadas["avisar"] == 0


def test_gate_termico_pausa_hasta_que_baja():
    lecturas = iter([90, 87, 85, 60])
    pausas = []
    vm.gate_termico(lector=lambda: next(lecturas), dormir=lambda s: pausas.append(s),
                     avisar=lambda *_a: None)
    # 90, 87 y 85 (>=85 umbral) disparan pausa; 60 corta el ciclo.
    assert pausas == [30, 30, 30]


def test_gate_termico_temp_ilegible_no_bloquea():
    vm.gate_termico(lector=lambda: None, dormir=NO_DORMIR, avisar=lambda *_a: None)  # no cuelga


# ── 3. skills stale ──────────────────────────────────────────────────────────
def test_detectar_skills_stale_marca_solo_vencidas_y_activas(tmp_path):
    _skill(tmp_path, "vieja-activa", status="active", last_verified="2026-01-01")   # 214d
    _skill(tmp_path, "reciente-activa", status="active", last_verified="2026-07-28")  # 6d
    _skill(tmp_path, "vieja-inactiva", status="deprecated", last_verified="2026-01-01")
    _skill(tmp_path, "sin-fecha", status="active", last_verified=None)

    hallazgos = vm.detectar_skills_stale(tmp_path, hoy=date(2026, 8, 3))

    assert [h["skill"] for h in hallazgos] == ["vieja-activa"]
    assert hallazgos[0]["dias_de_atraso"] == 214


def test_acumular_encola_y_no_duplica(tmp_path, cola):
    _skill(tmp_path, "vieja-activa", status="active", last_verified="2026-01-01")

    n1 = vm.acumular(cola, skills_dir=tmp_path, hoy=date(2026, 8, 3))
    n2 = vm.acumular(cola, skills_dir=tmp_path, hoy=date(2026, 8, 3))  # misma pasada, no duplica

    assert n1 == 1
    assert n2 == 0
    assert cola.contar_por_estado() == {ENCOLADA: 1}
    assert vm.contar_por_estado_mantenimiento(cola) == {ENCOLADA: 1}


def test_contar_por_estado_mantenimiento_ignora_otros_chat_id(cola):
    cola.encolar("otra cosa de otro subsistema", {"tipo": "x"}, chat_id="8727618189")
    assert vm.contar_por_estado_mantenimiento(cola) == {}


def test_correr_procesa_stale_y_deja_evidencia_hasta_estado_terminal(tmp_path, cola):
    _skill(tmp_path, "vieja-activa", status="active", last_verified="2026-01-01")
    vm.acumular(cola, skills_dir=tmp_path, hoy=date(2026, 8, 3))

    r = vm.correr(cola, forzar=True, dormir=NO_DORMIR, gate=lambda: None)

    assert r["corrido"] is True
    assert r["resueltas"] == 1
    estado = cola.contar_por_estado()
    assert estado == {NOTIFICADA: 1}

    ev = vm.reporte_evidencia(cola)
    assert len(ev) == 1
    assert ev[0]["estado"] == NOTIFICADA
    assert "sigue stale" in ev[0]["resultado"]
    assert "vieja-activa" in ev[0]["resultado"]


def test_correr_skill_ya_corregida_entre_acumular_y_correr_no_marca_stale(tmp_path, cola):
    skill_md = _skill(tmp_path, "vieja-activa", status="active", last_verified="2026-01-01")
    vm.acumular(cola, skills_dir=tmp_path, hoy=date(2026, 8, 3))

    # se "arregla" antes de que corra la ventana esa noche.
    skill_md.write_text(
        "---\nname: vieja-activa\nstatus: active\nlast_verified: 2026-08-03\n---\n# ok\n",
        encoding="utf-8",
    )

    vm.correr(cola, forzar=True, dormir=NO_DORMIR, gate=lambda: None)
    ev = vm.reporte_evidencia(cola)
    assert "ya no está stale" in ev[0]["resultado"]


def test_correr_skill_borrada_entre_acumular_y_correr_no_truena(tmp_path, cola):
    skill_md = _skill(tmp_path, "vieja-activa", status="active", last_verified="2026-01-01")
    vm.acumular(cola, skills_dir=tmp_path, hoy=date(2026, 8, 3))

    skill_md.unlink()

    r = vm.correr(cola, forzar=True, dormir=NO_DORMIR, gate=lambda: None)
    assert r["resueltas"] == 1
    ev = vm.reporte_evidencia(cola)
    assert "ya no existe" in ev[0]["resultado"]


def test_solver_mantenimiento_tipo_desconocido_atora(cola):
    tid = cola.encolar("mantenimiento raro", {"tipo": "algo_no_soportado"}, chat_id="ventana_mantenimiento")
    estado = cola.procesar_una(tid, vm.solver_mantenimiento, vm.notificador_mantenimiento,
                                max_intentos=1, dormir=NO_DORMIR)
    assert estado == ATORADA
