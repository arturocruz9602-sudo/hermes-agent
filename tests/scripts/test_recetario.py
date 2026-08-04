"""Pruebas del recetario de soluciones (HAS §F10, `docs/recetario/`).

Invariantes que se clavan aquí:

  (1) `buscar()` encuentra las recetas reales existentes por palabra
      clave del síntoma/componente, ordenadas por relevancia.
  (2) `buscar()` no encuentra nada para una consulta sin relación.
  (3) `validar_todas()` no reporta problemas sobre las 2 recetas reales
      que ya viven en `docs/recetario/` -- si esto falla, alguien rompió
      el formato documentado en README.md sin querer.
  (4) `validar_receta()` detecta cada tipo de defecto por separado:
      front-matter faltante, campo vacío, autor inválido, fecha mal
      formada, sección faltante, secciones fuera de orden, nombre de
      archivo no descriptivo ("receta-1.md").
  (5) `nueva_receta()` nunca escribe un archivo inválido -- si faltan
      datos, lanza `RecetaInvalida` y no toca disco.
  (6) `nueva_receta()` con datos completos escribe un archivo que
      `validar_receta()` acepta y que `buscar()` puede encontrar después.
  (7) `nueva_receta()` nunca sobreescribe una receta existente.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import recetario  # noqa: E402


@pytest.fixture(autouse=True)
def _recetario_temporal(tmp_path, monkeypatch):
    """Aísla cada prueba en un docs/recetario/ temporal y vacío."""
    destino = tmp_path / "recetario"
    destino.mkdir()
    monkeypatch.setattr(recetario, "DIR_RECETARIO", destino)
    return destino


def _sembrar_recetas_reales(destino: Path) -> None:
    origen = RAIZ / "docs" / "recetario"
    for ruta in origen.glob("*.md"):
        if ruta.name == "README.md":
            continue
        (destino / ruta.name).write_text(ruta.read_text(encoding="utf-8"), encoding="utf-8")


# --- buscar() -----------------------------------------------------------

def test_buscar_encuentra_receta_real_por_palabra_clave(_recetario_temporal):
    _sembrar_recetas_reales(_recetario_temporal)
    resultados = recetario.buscar("telethon phone code expired")
    assert resultados, "debía encontrar la receta de Telethon"
    nombres = [r.name for r, _score in resultados]
    assert "telethon-signin-cliente-distinto-al-que-pidio-codigo.md" in nombres


def test_buscar_ordena_por_relevancia(_recetario_temporal):
    _sembrar_recetas_reales(_recetario_temporal)
    resultados = recetario.buscar("compactación compresión threshold")
    assert resultados
    mejor = resultados[0][0].name
    assert mejor == "compactacion-en-cascada-target-mayor-al-disparador.md"


def test_buscar_sin_coincidencias_devuelve_lista_vacia(_recetario_temporal):
    _sembrar_recetas_reales(_recetario_temporal)
    assert recetario.buscar("carburador motocicleta engranaje oxidado") == []


def test_buscar_consulta_vacia_o_trivial_no_revienta(_recetario_temporal):
    _sembrar_recetas_reales(_recetario_temporal)
    assert recetario.buscar("") == []
    assert recetario.buscar("de la a") == []  # todas <=2 letras, sin señal


def test_buscar_directorio_recetario_inexistente_no_revienta(tmp_path, monkeypatch):
    monkeypatch.setattr(recetario, "DIR_RECETARIO", tmp_path / "no-existe")
    assert recetario.buscar("cualquier cosa") == []


# --- validar_receta() / validar_todas() sobre las recetas reales ---------

def test_las_dos_recetas_reales_pasan_validacion(_recetario_temporal):
    _sembrar_recetas_reales(_recetario_temporal)
    problemas = recetario.validar_todas()
    assert problemas == {}, f"recetas reales con problemas de formato: {problemas}"


def test_validar_detecta_frontmatter_faltante(tmp_path):
    ruta = tmp_path / "sin-frontmatter.md"
    ruta.write_text("## Síntoma\n\nalgo\n", encoding="utf-8")
    problemas = recetario.validar_receta(ruta)
    assert any("front-matter" in p for p in problemas)


def test_validar_detecta_campo_vacio(tmp_path):
    ruta = tmp_path / "campo-vacio.md"
    ruta.write_text(
        "---\nfecha: 2026-08-03\nautor: claude-code\nsintoma_corto: \ncomponente: x\n---\n\n"
        "## Síntoma\n\na\n\n## Diagnóstico\n\nb\n\n## Solución paso a paso\n\nc\n\n"
        "## Verificación\n\nd\n\n## Cuándo NO aplica\n\ne\n",
        encoding="utf-8",
    )
    problemas = recetario.validar_receta(ruta)
    assert any("sintoma_corto" in p for p in problemas)


def test_validar_detecta_autor_invalido(tmp_path):
    ruta = tmp_path / "autor-malo.md"
    ruta.write_text(
        "---\nfecha: 2026-08-03\nautor: arturo\nsintoma_corto: x\ncomponente: x\n---\n\n"
        "## Síntoma\n\na\n\n## Diagnóstico\n\nb\n\n## Solución paso a paso\n\nc\n\n"
        "## Verificación\n\nd\n\n## Cuándo NO aplica\n\ne\n",
        encoding="utf-8",
    )
    problemas = recetario.validar_receta(ruta)
    assert any("autor" in p for p in problemas)


def test_validar_detecta_fecha_mal_formada(tmp_path):
    ruta = tmp_path / "fecha-mala.md"
    ruta.write_text(
        "---\nfecha: 03/08/2026\nautor: hermes\nsintoma_corto: x\ncomponente: x\n---\n\n"
        "## Síntoma\n\na\n\n## Diagnóstico\n\nb\n\n## Solución paso a paso\n\nc\n\n"
        "## Verificación\n\nd\n\n## Cuándo NO aplica\n\ne\n",
        encoding="utf-8",
    )
    problemas = recetario.validar_receta(ruta)
    assert any("fecha" in p for p in problemas)


def test_validar_detecta_seccion_faltante(tmp_path):
    ruta = tmp_path / "sin-verificacion.md"
    ruta.write_text(
        "---\nfecha: 2026-08-03\nautor: hermes\nsintoma_corto: x\ncomponente: x\n---\n\n"
        "## Síntoma\n\na\n\n## Diagnóstico\n\nb\n\n## Solución paso a paso\n\nc\n\n"
        "## Cuándo NO aplica\n\ne\n",
        encoding="utf-8",
    )
    problemas = recetario.validar_receta(ruta)
    assert any("Verificación" in p for p in problemas)


def test_validar_detecta_secciones_fuera_de_orden(tmp_path):
    ruta = tmp_path / "desordenada.md"
    ruta.write_text(
        "---\nfecha: 2026-08-03\nautor: hermes\nsintoma_corto: x\ncomponente: x\n---\n\n"
        "## Diagnóstico\n\nb\n\n## Síntoma\n\na\n\n## Solución paso a paso\n\nc\n\n"
        "## Verificación\n\nd\n\n## Cuándo NO aplica\n\ne\n",
        encoding="utf-8",
    )
    problemas = recetario.validar_receta(ruta)
    assert any("orden" in p for p in problemas)


def test_validar_detecta_nombre_de_archivo_no_descriptivo(tmp_path):
    ruta = tmp_path / "receta-1.md"
    ruta.write_text(
        "---\nfecha: 2026-08-03\nautor: hermes\nsintoma_corto: x\ncomponente: x\n---\n\n"
        "## Síntoma\n\na\n\n## Diagnóstico\n\nb\n\n## Solución paso a paso\n\nc\n\n"
        "## Verificación\n\nd\n\n## Cuándo NO aplica\n\ne\n",
        encoding="utf-8",
    )
    problemas = recetario.validar_receta(ruta)
    assert any("descriptivo" in p for p in problemas)


# --- nueva_receta() -------------------------------------------------------

def _kwargs_receta_valida(**overrides):
    base = dict(
        autor="hermes",
        nombre="prueba-nueva-receta",
        sintoma_corto="síntoma corto de prueba",
        componente="scripts/recetario.py",
        sintoma="descripción del síntoma",
        diagnostico="causa raíz confirmada",
        solucion="pasos reproducibles",
        verificacion="cómo se confirmó",
        cuando_no_aplica="condiciones donde no aplica",
    )
    base.update(overrides)
    return base


def test_nueva_receta_escribe_archivo_valido_y_buscable(_recetario_temporal):
    ruta = recetario.nueva_receta(**_kwargs_receta_valida())
    assert ruta.exists()
    assert recetario.validar_receta(ruta) == []
    resultados = recetario.buscar("síntoma corto de prueba")
    assert any(r.name == "prueba-nueva-receta.md" for r, _score in resultados)


def test_nueva_receta_rechaza_autor_invalido(_recetario_temporal):
    with pytest.raises(recetario.RecetaInvalida):
        recetario.nueva_receta(**_kwargs_receta_valida(autor="arturo"))
    assert recetario.listar_recetas() == []


def test_nueva_receta_rechaza_campo_faltante_sin_tocar_disco(_recetario_temporal):
    with pytest.raises(recetario.RecetaInvalida):
        recetario.nueva_receta(**_kwargs_receta_valida(sintoma_corto=""))
    assert recetario.listar_recetas() == []


def test_nueva_receta_no_sobreescribe_existente(_recetario_temporal):
    recetario.nueva_receta(**_kwargs_receta_valida())
    with pytest.raises(recetario.RecetaInvalida):
        recetario.nueva_receta(**_kwargs_receta_valida())
    assert len(recetario.listar_recetas()) == 1
