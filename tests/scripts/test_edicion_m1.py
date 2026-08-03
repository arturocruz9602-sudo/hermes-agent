"""Pruebas de la edición en la M1 (AU-3, Piezas 2 y 3, r.102).

Dos fronteras que el bloque promete y estas pruebas clavan:

  PIEZA 2 — la M1 es PRESTADA (r.102). `SesionM1` DEBE dejar la Mac como estaba:
    - revierte cada config al salir, aunque el bloque de trabajo lance excepción;
    - verifica que revirtió y ALARMA (ReversionError) si no — nunca en silencio;
    - se niega a abrir sesión fuera de la ventana nocturna (ya es de mañana);
    - la config caffeinate se auto-expira del lado de la Mac (tercer candado).

  PIEZA 3 — edición de timeline SIN render: los segmentos conservados son el
    complemento exacto de los cortes; el script generado NO renderiza; y el editor
    se niega a correr sin sesión activa o si el script trae una llamada de render.

El ejecutor SSH es un doble: ninguna prueba toca la M1 real (B10, r.119).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import edicion_m1 as em  # noqa: E402
from corte_silencios import Corte  # noqa: E402


# ── doble del ejecutor SSH: registra comandos y responde a discreción ────────
class EjecutorFake:
    def __init__(self, respuestas=None, fallar=None):
        self.comandos = []
        self.respuestas = respuestas or {}   # subcadena -> salida
        self.fallar = fallar or set()        # subcadenas que deben fallar

    def correr(self, comando):
        self.comandos.append(comando)
        for sub in self.fallar:
            if sub in comando:
                return em.ResultadoComando(ok=False, salida=f"fallo simulado: {sub}", codigo=1)
        for sub, salida in self.respuestas.items():
            if sub in comando:
                return em.ResultadoComando(ok=True, salida=salida)
        return em.ResultadoComando(ok=True, salida="ok")

    def corridos(self, sub):
        return [c for c in self.comandos if sub in c]


NOCHE = datetime(2026, 8, 2, 23, 30)   # dentro de la ventana nocturna
MANANA = datetime(2026, 8, 2, 9, 0)    # fuera: Arturo puede necesitar la Mac


# ═══ PIEZA 2 — la M1 prestada (r.102) ════════════════════════════════════════
def _config_verificable():
    """Config cuyo verificar_cmd reporta '0' (limpia) por defecto."""
    return em.ConfigNocturna(nombre="prueba", aplicar_cmd="aplicar_x",
                             revertir_cmd="revertir_x", verificar_cmd="verificar_x",
                             senal_revertido="0")


def test_aplica_y_revierte_verificando():
    ej = EjecutorFake(respuestas={"verificar_x": "0"})
    with em.SesionM1(ej, configs=[_config_verificable()], ahora=NOCHE) as s:
        assert s.activa
    # al salir: corrió revertir Y verificar
    assert ej.corridos("revertir_x") and ej.corridos("verificar_x")


def test_revierte_aunque_el_trabajo_lance():
    """El corazón de r.102: si el trabajo revienta a media noche, la config IGUAL
    se revierte (está en finally)."""
    ej = EjecutorFake(respuestas={"verificar_x": "0"})
    with pytest.raises(ValueError):
        with em.SesionM1(ej, configs=[_config_verificable()], ahora=NOCHE):
            raise ValueError("algo tronó a media edición")
    assert ej.corridos("revertir_x"), "debió revertir aun con excepción"


def test_alarma_si_no_queda_limpia():
    """Si el verificar reporta que la config sigue puesta (no contiene la señal),
    es ReversionError — la Mac prestada no se deja tocada, y no se calla (regla 3)."""
    ej = EjecutorFake(respuestas={"verificar_x": "1"})  # 1 assertion sigue viva
    with pytest.raises(em.ReversionError):
        with em.SesionM1(ej, configs=[_config_verificable()], ahora=NOCHE):
            pass


def test_se_niega_fuera_de_ventana():
    ej = EjecutorFake()
    with pytest.raises(em.VentanaNocturnaError):
        with em.SesionM1(ej, configs=[_config_verificable()], ahora=MANANA):
            pass
    assert not ej.corridos("aplicar_x"), "no debió ni aplicar de mañana"


def test_falla_al_aplicar_revierte_lo_ya_puesto():
    """Si la 2ª config falla al aplicar, la 1ª (ya puesta) se revierte antes de abortar."""
    c1 = em.ConfigNocturna("a", "aplicar_a", "revertir_a", "verificar_a", "0")
    c2 = em.ConfigNocturna("b", "aplicar_b", "revertir_b", "verificar_b", "0")
    ej = EjecutorFake(respuestas={"verificar_a": "0"}, fallar={"aplicar_b"})
    with pytest.raises(RuntimeError):
        with em.SesionM1(ej, configs=[c1, c2], ahora=NOCHE):
            pass
    assert ej.corridos("revertir_a")


def test_caffeinate_autoexpira_atado_al_deadline():
    """Tercer candado (r.102): caffeinate -t con los segundos hasta las 06:00, así
    se cae solo aunque Hermes muera sin __exit__."""
    ej = EjecutorFake(respuestas={"pmset": "0"})
    s = em.SesionM1(ej, ahora=NOCHE)
    seg = s.segundos_hasta_deadline(NOCHE)  # 23:30 → 06:00 = 6.5h = 23400s
    assert seg == 6 * 3600 + 30 * 60
    cfg = em.caffeinate(seg)
    assert f"-t {seg}" in cfg.aplicar_cmd
    assert "pkill" in cfg.revertir_cmd


def test_deadline_manana_es_hoy_no_futuro_lejano():
    """A la 01:00 el deadline es a las 06:00 del MISMO día (5h), no 29h después."""
    madrugada = datetime(2026, 8, 3, 1, 0)
    s = em.SesionM1(EjecutorFake(), ahora=madrugada)
    assert s.segundos_hasta_deadline(madrugada) == 5 * 3600


def test_caffeinate_logging_exito(capsys):
    lineas = []
    ej = EjecutorFake(respuestas={"pmset": "0"})
    with em.SesionM1(ej, configs=[em.caffeinate(3600)], ahora=NOCHE, logger=lineas.append):
        pass
    txt = "\n".join(lineas)
    assert "aplicada config" in txt and "REVERTIDA y verificada" in txt


# ═══ PIEZA 3 — edición de timeline SIN render ════════════════════════════════
def test_segmentos_conservados_complemento_exacto():
    """Los segmentos conservados son el complemento de los cortes (nunca destruye)."""
    cortes = [Corte(1.25, 2.8), Corte(10.2, 13.5)]
    segs = em.segmentos_conservados(20.0, cortes)
    assert segs == [(0.0, 1.25), (2.8, 10.2), (13.5, 20.0)]


def test_segmentos_sin_cortes_es_la_cinta_entera():
    assert em.segmentos_conservados(10.0, []) == [(0.0, 10.0)]


def test_segmentos_corte_al_inicio_y_al_final():
    cortes = [Corte(0.0, 2.0), Corte(8.0, 10.0)]
    assert em.segmentos_conservados(10.0, cortes) == [(2.0, 8.0)]


def test_script_no_contiene_render():
    """La Pieza 3 es SIN render: el script generado no debe traer ninguna llamada."""
    editor = em.EditorDaVinci(EjecutorFake(), fps=30)
    script = editor.generar_script("proj", "/Users/arturo/Movies/x", 20.0,
                                   [Corte(1.25, 2.8)])
    for prohibido in ("StartRendering", "AddRenderJob", "Render"):
        assert prohibido not in script
    assert "ImportMedia" in script and "AppendToTimeline" in script and "SaveProject" in script


def test_script_frames_al_fps():
    editor = em.EditorDaVinci(EjecutorFake(), fps=30)
    script = editor.generar_script("proj", "/x", 20.0, [Corte(1.25, 2.8)])
    # segmentos (0,1.25)->(0,38) y (2.8,20)->(84,600) @30fps
    assert '"startFrame": 0, "endFrame": 38' in script
    assert '"startFrame": 84, "endFrame": 600' in script


def test_ejecutar_bloquea_sin_sesion_activa():
    editor = em.EditorDaVinci(EjecutorFake())
    sesion = em.SesionM1(EjecutorFake(), ahora=NOCHE)  # nunca se entró: no activa
    r = editor.generar_script("p", "/x", 10.0, [Corte(1.0, 3.0)])
    res = editor.ejecutar(r, sesion)
    assert not res.ok and "no está activa" in res.motivo


def test_ejecutar_bloquea_script_con_render():
    editor = em.EditorDaVinci(EjecutorFake())
    ej = EjecutorFake(respuestas={"verificar_x": "0"})
    with em.SesionM1(ej, configs=[_config_verificable()], ahora=NOCHE) as s:
        malo = "import x\np.StartRendering()\n"
        res = editor.ejecutar(malo, s)
    assert not res.ok and "SIN render" in res.motivo


def test_ejecutar_arma_timeline_dentro_de_sesion():
    ejed = EjecutorFake(respuestas={"python3": "timeline armado: 2 segmentos"})
    editor = em.EditorDaVinci(ejed, fps=30)
    ejses = EjecutorFake(respuestas={"verificar_x": "0"})
    ejses.respuestas["python3"] = "timeline armado: 2 segmentos"
    script = editor.generar_script("p", "/x", 20.0, [Corte(5.0, 8.0)])
    with em.SesionM1(ejses, configs=[_config_verificable()], ahora=NOCHE) as s:
        res = editor.ejecutar(script, s)
    assert res.ok and res.segmentos == 2  # (0,5) y (8,20)


# ═══ render nocturno — automático (r.102) pero acotado ═══════════════════════
def test_render_bloqueado_sin_sesion():
    r = em.render_nocturno(em.SesionM1(EjecutorFake(), ahora=NOCHE), "proj")
    assert not r.ok  # sesión no activa (no se entró al with)


def test_render_corre_dentro_de_sesion():
    ej = EjecutorFake(respuestas={"verificar_x": "0", "StartRendering": "render lanzado"})
    with em.SesionM1(ej, configs=[_config_verificable()], ahora=NOCHE) as s:
        r = em.render_nocturno(s, "proj")
    assert r.ok and ej.corridos("StartRendering")
