"""Pruebas de motor_sugerencias_gasto.py (Bloque F8-1, Fase 7 / E10).

Cubre las dos formas de sugerencia que pide r.25 ("sí, que me haga
sugerencias"): (1) gasto individual atípico avisado apenas se detecta, y
(2) categoría disparada en la semana, para el consolidado dominical.
También clava r.24 (todos los gastos cuentan), r.26 (ninguna categoría es
intocable -- no hay lista de exclusión) y que todo mensaje sugiere sin
decidir (cierra preguntando, nunca asume ni promete).

Usa el mismo fixture aislado de test_libreta.py (real/simulación en
tmp_path) en vez del disco de pruebas compartido: los umbrales exigen
datos exactos y deterministas, no lo que haya quedado acumulado ahí.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import libreta as libreta_mod  # noqa: E402
import motor_sugerencias_gasto as motor  # noqa: E402


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Copia del fixture de test_libreta.py: real/simulación recién
    migradas en tmp_path, para no tocar datos reales ni el disco de
    pruebas compartido."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_DISCO_PRUEBAS", str(tmp_path / "externo"))
    monkeypatch.delenv("HERMES_FECHA_SIMULADA", raising=False)
    monkeypatch.delenv("HERMES_ENTORNO", raising=False)
    (tmp_path / "externo").mkdir(parents=True, exist_ok=True)
    importlib.reload(libreta_mod)
    monkeypatch.setattr(libreta_mod, "_verificar_disco_de_pruebas", lambda: None)

    entorno_hijo = {"HOME": str(tmp_path), "HERMES_HOME": str(tmp_path),
                    "HERMES_DISCO_PRUEBAS": str(tmp_path / "externo"),
                    "PATH": "/usr/bin:/bin"}
    for ent in ("real", "simulacion"):
        r = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "libreta_migrar.py"),
             "--entorno", ent],
            capture_output=True, text=True, env=entorno_hijo,
        )
        assert r.returncode == 0, r.stderr
    yield dict(libreta_mod.RUTAS)
    monkeypatch.undo()
    importlib.reload(libreta_mod)


@pytest.fixture
def estado_aislado(tmp_path, monkeypatch):
    """Redirige ESTADO/LOG del motor a tmp_path (no ~/.hermes real)."""
    monkeypatch.setattr(motor, "ESTADO", str(tmp_path / "vistos.json"))
    monkeypatch.setattr(motor, "LOG", str(tmp_path / "motor.log"))
    return tmp_path


def _fake_avisar(monkeypatch, resultados=None):
    """Reemplaza motor.avisar por un stub que solo registra llamadas
    (nunca toca Telegram de verdad); resultados fija el retorno por llamada
    en orden, o True siempre si no se da."""
    llamadas = []

    def fake(mensaje):
        ok = resultados.pop(0) if resultados else True
        llamadas.append((mensaje, ok))
        return ok

    monkeypatch.setattr(motor, "avisar", fake)
    return llamadas


# ── gasto individual atípico ────────────────────────────────────────────

class TestDetectarAtipico:
    def test_gasto_varias_veces_el_promedio_es_atipico(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(100, "comida", "tacos", fecha="2026-07-01")
            gid = lib.registrar_gasto(400, "comida", "cena cara", fecha="2026-08-01")
            gasto = lib.con.execute("SELECT * FROM gastos WHERE id=?", (gid,)).fetchone()
            h = motor.detectar_atipico(lib, gasto)
        assert h is not None
        assert h["categoria"] == "comida"
        assert h["monto"] == 400
        assert h["veces"] == pytest.approx(4.0)

    def test_gasto_normal_no_es_atipico(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(200, "gasolina", None, fecha="2026-07-01")
            gid = lib.registrar_gasto(210, "gasolina", None, fecha="2026-08-01")
            gasto = lib.con.execute("SELECT * FROM gastos WHERE id=?", (gid,)).fetchone()
            h = motor.detectar_atipico(lib, gasto)
        assert h is None

    def test_bajo_el_piso_en_pesos_no_dispara_aunque_el_multiplicador_sea_alto(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(10, "cafe", None, fecha="2026-07-01")
            gid = lib.registrar_gasto(35, "cafe", None, fecha="2026-08-01")  # 3.5x, pero $35 < piso
            gasto = lib.con.execute("SELECT * FROM gastos WHERE id=?", (gid,)).fetchone()
            h = motor.detectar_atipico(lib, gasto)
        assert h is None

    def test_sin_historico_minimo_no_dispara(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            lib.registrar_gasto(100, "ropa", None, fecha="2026-07-01")  # solo 1 previo
            gid = lib.registrar_gasto(500, "ropa", None, fecha="2026-08-01")
            gasto = lib.con.execute("SELECT * FROM gastos WHERE id=?", (gid,)).fetchone()
            h = motor.detectar_atipico(lib, gasto)
        assert h is None

    def test_ninguna_categoria_esta_excluida(self, entorno):
        """r.26: 'ninguno; acepto sus sugerencias' -- ni el negocio ni la
        inversión en IA están exentos de la misma regla."""
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(50, "inversion_ia", None, fecha="2026-07-01")
            gid = lib.registrar_gasto(300, "inversion_ia", None, fecha="2026-08-01")
            gasto = lib.con.execute("SELECT * FROM gastos WHERE id=?", (gid,)).fetchone()
            h = motor.detectar_atipico(lib, gasto)
        assert h is not None


class TestMensajeAtipico:
    def test_mensaje_trae_numeros_reales_y_pregunta_sin_prometer(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(100, "comida", "tacos", fecha="2026-07-01")
            gid = lib.registrar_gasto(400, "comida", "cena cara", fecha="2026-08-01")
            gasto = lib.con.execute("SELECT * FROM gastos WHERE id=?", (gid,)).fetchone()
            h = motor.detectar_atipico(lib, gasto)
            msg = motor.construir_mensaje_atipico(h)
        assert "$400.00" in msg
        assert "comida" in msg
        assert "cena cara" in msg
        assert msg.strip().endswith("?")
        assert "voy a" not in msg.lower() and "haré" not in msg.lower()


class TestEvaluarInmediato:
    def test_avisa_solo_lo_nuevo_y_no_reavisa_en_la_siguiente_corrida(self, entorno, estado_aislado, monkeypatch):
        llamadas = _fake_avisar(monkeypatch)
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(100, "comida", "tacos", fecha="2026-07-01")
            motor.evaluar_inmediato(lib)  # marca esos 3 como ya vistos (nada atípico)
            assert llamadas == []

            lib.registrar_gasto(400, "comida", "cena cara", fecha="2026-08-01")
            avisados = motor.evaluar_inmediato(lib)
            assert len(avisados) == 1
            assert len(llamadas) == 1

            # sin gastos nuevos: la segunda corrida no reavisa el mismo hallazgo
            avisados_2 = motor.evaluar_inmediato(lib)
            assert avisados_2 == []
            assert len(llamadas) == 1

    def test_gasto_normal_no_genera_aviso(self, entorno, estado_aislado, monkeypatch):
        llamadas = _fake_avisar(monkeypatch)
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(200, "gasolina", None, fecha="2026-07-01")
            lib.registrar_gasto(210, "gasolina", None, fecha="2026-08-01")
            avisados = motor.evaluar_inmediato(lib)
        assert avisados == []
        assert llamadas == []

    def test_fallo_al_avisar_igual_avanza_el_estado_para_no_reintentar_para_siempre(self, entorno, estado_aislado, monkeypatch):
        llamadas = _fake_avisar(monkeypatch, resultados=[False])
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(100, "comida", "tacos", fecha="2026-07-01")
            gid = lib.registrar_gasto(400, "comida", "cena cara", fecha="2026-08-01")
            avisados = motor.evaluar_inmediato(lib)
        assert avisados == []  # el aviso falló, no cuenta como avisado
        # pero el estado sí avanza hasta el último id visto (mismo criterio que
        # vigilar_correo_escuela: un fallo de Telegram no debe reintentar para
        # siempre el mismo correo/gasto en cada corrida)
        assert motor.cargar_ultimo_id() == gid

    def test_estado_ilegible_no_reavisa_el_historico_completo(self, entorno, estado_aislado, monkeypatch):
        """Mismo criterio que vigilar_correo_escuela.py: un archivo de estado
        roto se trata como 'ya vi todo hasta ahora', no como primera corrida
        del historico completo."""
        with libreta_mod.Libreta("real") as lib:
            for _ in range(3):
                lib.registrar_gasto(100, "comida", "tacos", fecha="2026-07-01")
            lib.registrar_gasto(400, "comida", "cena vieja atipica", fecha="2026-07-15")

        Path(motor.ESTADO).parent.mkdir(parents=True, exist_ok=True)
        Path(motor.ESTADO).write_text("{esto no es json valido")

        llamadas = _fake_avisar(monkeypatch)
        with libreta_mod.Libreta("real") as lib:
            avisados = motor.evaluar_inmediato(lib)
        assert avisados == []
        assert llamadas == []


# ── categoría disparada (consolidado dominical) ─────────────────────────

class TestDetectarCategoriasDisparadas:
    def test_categoria_que_se_duplico_se_detecta(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            # 4 semanas previas ~$200/semana en gasolina
            for semana in range(1, 5):
                fecha = motor.fecha_hace_n_dias(7 * semana, "2026-08-09")
                lib.registrar_gasto(200, "gasolina", None, fecha=fecha)
            # semana actual: $400 (100% mas)
            lib.registrar_gasto(400, "gasolina", None, fecha="2026-08-09")
            hallazgos = motor.detectar_categorias_disparadas(lib, hoy_str="2026-08-09")
        disparadas = {h["categoria"]: h for h in hallazgos}
        assert "gasolina" in disparadas
        assert disparadas["gasolina"]["variacion_pct"] == pytest.approx(100.0)

    def test_categoria_estable_no_se_detecta(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for semana in range(1, 5):
                fecha = motor.fecha_hace_n_dias(7 * semana, "2026-08-09")
                lib.registrar_gasto(200, "gym", None, fecha=fecha)
            lib.registrar_gasto(205, "gym", None, fecha="2026-08-09")
            hallazgos = motor.detectar_categorias_disparadas(lib, hoy_str="2026-08-09")
        assert "gym" not in {h["categoria"] for h in hallazgos}

    def test_categoria_nueva_sin_historico_no_se_marca_disparada(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            lib.registrar_gasto(500, "mudanza", None, fecha="2026-08-09")
            hallazgos = motor.detectar_categorias_disparadas(lib, hoy_str="2026-08-09")
        assert "mudanza" not in {h["categoria"] for h in hallazgos}

    def test_categoria_bajo_el_piso_no_se_marca_aunque_se_haya_disparado(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for semana in range(1, 5):
                fecha = motor.fecha_hace_n_dias(7 * semana, "2026-08-09")
                lib.registrar_gasto(10, "cafe", None, fecha=fecha)
            lib.registrar_gasto(40, "cafe", None, fecha="2026-08-09")  # 300% mas, pero $40 < piso $100
            hallazgos = motor.detectar_categorias_disparadas(lib, hoy_str="2026-08-09")
        assert "cafe" not in {h["categoria"] for h in hallazgos}


class TestConsolidadoDominical:
    def test_con_hallazgos_lista_categorias_y_cierra_preguntando(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            for semana in range(1, 5):
                fecha = motor.fecha_hace_n_dias(7 * semana, "2026-08-09")
                lib.registrar_gasto(200, "gasolina", None, fecha=fecha)
            lib.registrar_gasto(400, "gasolina", None, fecha="2026-08-09")
            msg = motor.construir_consolidado_dominical(lib, hoy_str="2026-08-09")
        assert "gasolina" in msg
        assert "$400.00" in msg
        assert msg.strip().endswith("?")

    def test_sin_hallazgos_dice_que_todo_esta_normal(self, entorno):
        with libreta_mod.Libreta("real") as lib:
            lib.registrar_gasto(50, "comida", None, fecha="2026-08-09")
            msg = motor.construir_consolidado_dominical(lib, hoy_str="2026-08-09")
        assert "normal" in msg.lower() or "sin categorías" in msg.lower() or "sin categorias" in msg.lower()

    def test_evaluar_dominical_llama_avisar_con_el_consolidado(self, entorno, monkeypatch):
        llamadas = _fake_avisar(monkeypatch)
        with libreta_mod.Libreta("real") as lib:
            lib.registrar_gasto(50, "comida", None, fecha=lib.hoy())
            ok = motor.evaluar_dominical(lib)
        assert ok is True
        assert len(llamadas) == 1

    def test_evaluar_dominical_reporta_fallo_si_avisar_falla(self, entorno, monkeypatch):
        _fake_avisar(monkeypatch, resultados=[False])
        with libreta_mod.Libreta("real") as lib:
            lib.registrar_gasto(50, "comida", None, fecha=lib.hoy())
            ok = motor.evaluar_dominical(lib)
        assert ok is False


class TestEstadoPersistente:
    def test_guardar_y_cargar_ultimo_id(self, estado_aislado):
        assert motor.cargar_ultimo_id() == 0
        motor.guardar_ultimo_id(42)
        assert motor.cargar_ultimo_id() == 42

    def test_log_escribe_al_archivo(self, estado_aislado):
        motor.log("linea de prueba")
        contenido = Path(motor.LOG).read_text(encoding="utf-8")
        assert "linea de prueba" in contenido


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
