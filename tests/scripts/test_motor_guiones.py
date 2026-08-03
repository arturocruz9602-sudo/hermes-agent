"""Pruebas del motor de guiones (AU-1, r.45-47).

El bloque promete UNA cosa acotada: de una nota de Obsidian, armar el
andamiaje con las tres partes que Arturo pidió que Hermes "siempre tenga en
mente" (gancho / cierre / retención en formato podcast) y MEDIR la retención
de un borrador con números — NO promete escribir la prosa final. Estas
pruebas clavan justo esa frontera:

  - el parseo lee frontmatter real de Obsidian y notas sin frontmatter;
  - el andamiaje SIEMPRE trae las partes obligatorias y un piso de segmentos;
  - el análisis distingue un borrador bueno de uno malo con recomendaciones
    concretas (un gancho largo, cero open-loops, sin payoff, se detectan);
  - el registro en la libreta va a `simulacion`, nunca a lo real (r.20).
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import motor_guiones as mg  # noqa: E402


NOTA_REAL = """---
title: "Video: Segundo cerebro con IA local sin sincronización pagada"
created: 2026-07-29T11:41:58
tags: ["video", "segundo cerebro", "IA local", "productividad"]
origin: hermes
---

Quiero hacer un video explicando cómo armé mi segundo cerebro con IA local.

Idea: Detallar el flujo de captura de ideas desde iPhone y desde la HP.

Mencionar el uso de Hermes como conector entre Obsidian, Notion y su memoria.
"""


# ── parseo ──────────────────────────────────────────────────────────────────
def test_parsea_frontmatter_real_de_obsidian():
    nota = mg.parse_nota(NOTA_REAL, ruta="x.md")
    assert nota.titulo == "Video: Segundo cerebro con IA local sin sincronización pagada"
    assert nota.tags == ["video", "segundo cerebro", "IA local", "productividad"]
    assert nota.created == "2026-07-29T11:41:58"
    assert "frontmatter" not in nota.cuerpo  # el frontmatter no contamina el cuerpo
    assert len(nota.ideas()) == 3  # tres párrafos = tres semillas


def test_nota_sin_frontmatter_usa_primera_linea_como_titulo():
    nota = mg.parse_nota("# La caída de Roma\n\nAlgo pasó en el 476.")
    assert nota.titulo == "La caída de Roma"  # sin el '#'
    assert nota.tags == []


def test_tags_sin_comillas_tambien_parsean():
    nota = mg.parse_nota("---\ntitle: X\ntags: [a, b, c]\n---\n\ncuerpo")
    assert nota.tags == ["a", "b", "c"]


# ── andamiaje ───────────────────────────────────────────────────────────────
def test_andamiaje_siempre_trae_las_partes_obligatorias_r47():
    """Gancho, cierre y retención (open-loops/transiciones) son el contrato."""
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    assert guion.gancho.strip()
    assert guion.promesa.strip()          # payoff: el gancho abre, el cierre cierra
    assert guion.cierre.strip()
    assert guion.cta.strip()
    assert len(guion.segmentos) == 3      # una semilla por idea de la nota
    # los segmentos intermedios abren bucle y anticipan (retención podcast)
    assert guion.segmentos[0].open_loop
    assert guion.segmentos[0].transicion_microgancho
    # el último no deja bucle colgando ni transición al vacío
    assert guion.segmentos[-1].open_loop is None
    assert guion.segmentos[-1].transicion_microgancho == ""


def test_nota_corta_se_completa_hasta_el_piso_de_segmentos():
    """Aunque la nota sea una línea, el arco narrativo necesita ≥3 segmentos."""
    guion = mg.armar_guion(mg.parse_nota("Napoleón en Waterloo."), segmentos_min=3)
    assert len(guion.segmentos) == 3
    assert "Napoleón" in guion.titulo


def test_andamiaje_no_inventa_prosa_final():
    """AU-1 NO promete edición creativa: el borrador queda vacío, son GUÍAS."""
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    assert guion.borrador is None


# ── análisis de retención ───────────────────────────────────────────────────
def test_andamiaje_completo_puntua_alto():
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    a = mg.analizar_retencion(guion)
    assert a.puntaje == 100
    assert a.gancho_ok
    assert a.open_loops >= 1
    assert a.payoff_resuelve_gancho
    assert a.cta_presente
    assert a.recomendaciones == []


def test_borrador_bueno_detecta_open_loops_y_cta_en_la_prosa():
    """Analiza prosa real, no solo el esqueleto: marcas explícitas cuentan."""
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    guion.borrador = (
        "¿Por qué nadie te dice que puedes tener un segundo cerebro gratis? "
        "Espera, porque al final te muestro el flujo completo. "
        "Ahora pasemos a cómo capturo ideas desde el iPhone. "
        "Pero primero, un problema que todos tienen. "
        "Suscríbete para el siguiente video de la serie."
    )
    a = mg.analizar_retencion(guion)
    assert a.open_loops >= 1
    assert a.transiciones_microgancho >= 1
    assert a.cta_presente
    assert a.palabras > 0
    assert a.duracion_estimada_min > 0


def test_gancho_demasiado_largo_se_penaliza():
    """Tras ~15s sin gancho la retención cae <45%: un gancho de 60 palabras falla."""
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    guion.gancho = " ".join(["palabra"] * 60)  # muy por encima de 40
    guion.borrador = "texto corto"
    a = mg.analizar_retencion(guion)
    assert not a.gancho_ok
    assert any("Gancho" in r for r in a.recomendaciones)
    assert a.puntaje < 100


def test_borrador_sin_open_loops_recomienda_agregarlos():
    guion = mg.armar_guion(mg.parse_nota("Tema plano."), segmentos_min=1)
    # un solo segmento, sin open-loop declarado y prosa sin marcas de bucle
    guion.segmentos = [mg.Segmento(titulo="uno", guia="algo", open_loop=None)]
    guion.borrador = "Hoy hablo de un tema. Es interesante. Fin."
    a = mg.analizar_retencion(guion)
    assert a.open_loops == 0
    assert any("bucle" in r.lower() or "open-loop" in r.lower()
               for r in a.recomendaciones)


def test_sin_payoff_no_resuelve_el_gancho():
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    guion.cierre = ""  # sin cierre, el bucle del gancho queda abierto
    a = mg.analizar_retencion(guion)
    assert not a.payoff_resuelve_gancho
    assert any("promesa" in r.lower() or "payoff" in r.lower()
               for r in a.recomendaciones)


def test_duracion_estimada_escala_con_palabras():
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    guion.borrador = " ".join(["palabra"] * 300)  # 300 palabras
    a = mg.analizar_retencion(guion, ppm=150)
    assert a.duracion_estimada_min == pytest.approx(2.0, abs=0.1)  # 300/150 = 2 min


def test_render_markdown_incluye_secciones_y_analisis():
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    md = mg.guion_a_markdown(guion, mg.analizar_retencion(guion))
    for seccion in ("Gancho", "Promesa", "Desarrollo", "Cierre", "CTA",
                    "Análisis de retención", "Puntaje"):
        assert seccion in md


# ── registro en la libreta (aislado, nunca toca lo real: r.20) ──────────────
@pytest.fixture
def libreta_sim(tmp_path, monkeypatch):
    import libreta as libreta_mod
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
    yield libreta_mod
    importlib.reload(libreta_mod)


def test_registrar_guion_en_libreta_simulacion(libreta_sim):
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    analisis = mg.analizar_retencion(guion)
    with libreta_sim.Libreta("simulacion") as lib:
        gid = mg.registrar_en_libreta(lib, guion, analisis)
        fila = lib.con.execute(
            "SELECT titulo, plataforma, estado, nota FROM guiones WHERE id=?",
            (gid,)).fetchone()
    assert fila["titulo"] == guion.titulo
    assert fila["plataforma"] == "youtube"
    assert fila["estado"] == "escribiendo"
    import json
    payload = json.loads(fila["nota"])
    assert "guion" in payload and "analisis" in payload
    assert payload["analisis"]["puntaje"] == 100


def test_registrar_en_simulacion_no_toca_lo_real(libreta_sim):
    """El límite duro de Arturo (r.20): un guion de prueba no entra a lo real."""
    guion = mg.armar_guion(mg.parse_nota(NOTA_REAL))
    with libreta_sim.Libreta("simulacion") as lib:
        mg.registrar_en_libreta(lib, guion)
    with libreta_sim.Libreta("real") as real:
        assert real.con.execute("SELECT COUNT(*) FROM guiones").fetchone()[0] == 0
