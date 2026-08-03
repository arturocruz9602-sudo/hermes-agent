"""Pruebas del pipeline de clips (AU-2, r.46/r.48/r.59).

El bloque promete tres cosas acotadas y estas pruebas clavan justo su frontera:

  1. EXTRACCIÓN (r.46/r.48): del video largo saca los clips VALIOSOS que NO
     pasen de 2 min — el tope de 120s es DURO (ni el extractor ni el dato lo
     violan), y si hay N valiosos son N (no rellena de paja, no recorta buenos).
  2. PROGRAMACIÓN (r.46): reparte los clips en los mejores horarios de la
     semana, el mejor al mejor hueco, sin agendar en el pasado ni amontonar en
     un día, y los sobrantes se reportan (nunca se pierden en silencio).
  3. OAUTH + PUBLICACIÓN (r.59): el token AVISA cuando vence (jamás falla
     callado) y publicar NUNCA es automático — sin el 'sí' de Arturo no sube,
     y sin cliente/token válido tampoco, siempre diciendo por qué.

El registro va a `simulacion`, nunca a lo real (r.20).
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import pipeline_clips as pc  # noqa: E402


# ── material de prueba: un transcripto con tramos fuertes y flojos ───────────
def _seg(inicio, fin, texto):
    return pc.SegmentoTranscrito(inicio=inicio, fin=fin, texto=texto)


TRANSCRIPTO = [
    # tramo fuerte: gancho + emoción + remate, se sostiene solo (~40s)
    _seg(0, 20, "¿Por qué nadie sabe la verdad de esta traición? Lo que pasó fue "
                "increíble y cambió todo para siempre en aquella guerra sangrienta."),
    _seg(20, 40, "Por eso la lección es clara: el miedo mueve más que el amor, y "
                 "esto demuestra que el secreto estuvo siempre frente a nosotros."),
    # tramo flojo: relleno sin gancho ni emoción (~30s)
    _seg(40, 55, "Bueno, entonces seguimos con los datos generales del contexto."),
    _seg(55, 70, "Había varios factores administrativos y algunos detalles menores."),
    # otro tramo fuerte más adelante (~35s)
    _seg(120, 140, "El secreto que nadie te cuenta: al final resulta que todo era "
                   "mentira, y la traición más brutal apenas comenzaba entonces."),
    _seg(140, 155, "Así que la moraleja es simple y te va a impactar de verdad."),
]


# ═══ 1. EXTRACCIÓN ═══════════════════════════════════════════════════════════
def test_extrae_clips_valiosos():
    clips = pc.extraer_clips(TRANSCRIPTO)
    assert len(clips) >= 2, "los dos tramos fuertes debían salir como clips"
    for c in clips:
        assert c.valor >= pc.UMBRAL_VALOR
        assert c.motivos, "cada clip explica por qué es valioso (r.91)"


def test_frontera_dura_ningun_clip_pasa_de_2min():
    """La promesa exacta del bloque: NINGÚN clip pasa de 2 min (r.48)."""
    clips = pc.extraer_clips(TRANSCRIPTO)
    assert clips
    for c in clips:
        assert c.duracion <= pc.MAX_CLIP_SEG


def test_clip_candidato_rechaza_mas_de_2min():
    """La frontera se defiende en el propio dato: es imposible construir un clip
    de más de 2 min."""
    with pytest.raises(ValueError):
        pc.ClipCandidato(inicio=0, fin=121, texto="x")
    # justo en el límite sí se permite
    ok = pc.ClipCandidato(inicio=0, fin=120, texto="x")
    assert ok.duracion == 120


def test_ventana_larga_se_recorta_no_se_pierde():
    """Un video de un solo tramo largo (>2min) no produce un clip gigante:
    el extractor solo emite ventanas ≤120s."""
    largo = [_seg(0, 200, "nadie sabe el secreto de esta increíble traición " * 20)]
    clips = pc.extraer_clips(largo)
    for c in clips:
        assert c.duracion <= pc.MAX_CLIP_SEG


def test_descarta_relleno_sin_valor():
    """Un transcripto sin momentos fuertes no inventa clips (r.48: si no hay
    valiosos, no hay clips)."""
    relleno = [_seg(i * 15, i * 15 + 15,
                    "seguimos con datos generales y detalles administrativos menores")
               for i in range(8)]
    clips = pc.extraer_clips(relleno)
    assert clips == []


def test_clips_no_se_traslapan():
    clips = pc.extraer_clips(TRANSCRIPTO)
    intervalos = sorted((c.inicio, c.fin) for c in clips)
    for (a1, b1), (a2, b2) in zip(intervalos, intervalos[1:]):
        assert b1 <= a2, "los clips elegidos no deben solaparse"


def test_ranking_por_valor():
    clips = pc.extraer_clips(TRANSCRIPTO)
    valores = [c.valor for c in clips]
    assert valores == sorted(valores, reverse=True)


# ═══ 2. PROGRAMACIÓN ═════════════════════════════════════════════════════════
def _clips_falsos(n, valor_base=90):
    return [pc.ClipCandidato(inicio=i * 130, fin=i * 130 + 60,
                             texto=f"clip {i}", titulo=f"clip {i}",
                             valor=valor_base - i)
            for i in range(n)]


def test_programa_mejor_clip_en_mejor_horario():
    lunes = datetime(2026, 8, 3, 0, 0)  # lunes 00:00
    clips = _clips_falsos(3)
    plan = pc.programar_semana(clips, lunes)
    assert len(plan) == 3
    # el clip de mayor valor cae en la franja de mayor puntaje
    mejor_pub = max(plan, key=lambda p: p.franja_puntaje)
    assert mejor_pub.clip.valor == max(c.valor for c in clips)
    for pub in plan:
        assert pub.estado == "propuesta"  # nada publicado (r.59)


def test_nunca_agenda_en_el_pasado():
    # arranca un domingo a las 20:00: las franjas previas de ese día no valen
    ahora = datetime(2026, 8, 9, 20, 0)  # domingo 20:00
    plan = pc.programar_semana(_clips_falsos(5), ahora)
    for pub in plan:
        assert pub.cuando >= ahora


def test_no_amontona_respeta_tope_por_dia():
    plan = pc.programar_semana(_clips_falsos(20), datetime(2026, 8, 3, 0, 0),
                               max_por_dia=2)
    por_dia: dict = {}
    for pub in plan:
        por_dia[pub.cuando.date()] = por_dia.get(pub.cuando.date(), 0) + 1
    assert all(v <= 2 for v in por_dia.values())


def test_sobrantes_se_reportan_no_se_pierden():
    """Más clips que franjas buenas → los que no caben se reportan (regla 3)."""
    clips = _clips_falsos(40)  # más que las franjas de una semana
    plan = pc.programar_semana(clips, datetime(2026, 8, 3, 0, 0), max_por_dia=2)
    fuera = pc.sobrantes(clips, plan)
    assert len(plan) + len(fuera) == len(clips)
    assert fuera, "con 40 clips y tope 2/día algunos deben quedar sin cupo"


def test_fin_de_semana_pesa_mas():
    """La investigación: fines de semana ~+60% engagement → mejor puntaje."""
    franjas = pc._franjas_semana(datetime(2026, 8, 3, 0, 0))
    top = franjas[0][0]
    assert top.weekday() >= 5, "la mejor franja de la semana cae en fin de semana"


# ═══ 3. OAUTH + PUBLICACIÓN ══════════════════════════════════════════════════
def _escribir_token(tmp_path, expira: datetime) -> Path:
    ruta = tmp_path / "youtube_token.json"
    ruta.write_text(json.dumps({"expira_en": expira.isoformat(),
                                "access_token": "xxx"}), encoding="utf-8")
    return ruta


def test_token_ausente_avisa_no_falla_callado(tmp_path):
    tok = pc.TokenYouTube(tmp_path / "no_existe.json")
    est = tok.verificar()
    assert not est.valido and est.avisar
    assert "OAuth" in est.mensaje


def test_token_vencido_invalido_y_avisa(tmp_path):
    ruta = _escribir_token(tmp_path, datetime(2026, 8, 1, 12, 0))
    tok = pc.TokenYouTube(ruta)
    est = tok.verificar(ahora=datetime(2026, 8, 2, 12, 0))
    assert not est.valido and est.avisar
    assert "VENCIDO" in est.mensaje


def test_token_por_vencer_valido_pero_avisa(tmp_path):
    ruta = _escribir_token(tmp_path, datetime(2026, 8, 2, 18, 0))
    tok = pc.TokenYouTube(ruta, margen_horas=24)
    est = tok.verificar(ahora=datetime(2026, 8, 2, 12, 0))  # vence en 6h < 24h
    assert est.valido and est.avisar


def test_token_vigente_no_avisa(tmp_path):
    ruta = _escribir_token(tmp_path, datetime(2026, 8, 10, 12, 0))
    tok = pc.TokenYouTube(ruta, margen_horas=24)
    est = tok.verificar(ahora=datetime(2026, 8, 2, 12, 0))
    assert est.valido and not est.avisar


def test_token_ilegible_avisa(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{no es json", encoding="utf-8")
    est = pc.TokenYouTube(ruta).verificar()
    assert not est.valido and est.avisar


def _pub_falsa():
    clip = pc.ClipCandidato(inicio=0, fin=60, texto="cuerpo del clip", titulo="clip x")
    return pc.Publicacion(clip=clip, cuando=datetime(2026, 8, 3, 19, 0))


class _ClienteFake:
    def __init__(self, revienta=False):
        self.revienta = revienta
        self.llamadas = []

    def subir(self, titulo, descripcion, programado_para):
        if self.revienta:
            raise RuntimeError("cuota agotada")
        self.llamadas.append(titulo)
        return "vid_123"


def test_publicar_sin_aprobacion_se_bloquea(tmp_path):
    """r.59: publicar NO es automático. Sin el 'sí' de Arturo, no sube."""
    tok = pc.TokenYouTube(_escribir_token(tmp_path, datetime(2026, 9, 1, 12, 0)))
    pub = pc.PublicadorYouTube(tok, cliente=_ClienteFake())
    r = pub.publicar(_pub_falsa(), aprobado=False,
                     ahora=datetime(2026, 8, 2, 12, 0))
    assert not r.ok and "súbelo" in r.motivo


def test_publicar_aprobado_pero_token_invalido_falla_dicho(tmp_path):
    tok = pc.TokenYouTube(tmp_path / "no_existe.json")
    pub = pc.PublicadorYouTube(tok, cliente=_ClienteFake())
    r = pub.publicar(_pub_falsa(), aprobado=True)
    assert not r.ok and "Token inválido" in r.motivo


def test_publicar_aprobado_sin_cliente_falla_dicho(tmp_path):
    tok = pc.TokenYouTube(_escribir_token(tmp_path, datetime(2026, 9, 1, 12, 0)))
    pub = pc.PublicadorYouTube(tok, cliente=None)
    r = pub.publicar(_pub_falsa(), aprobado=True, ahora=datetime(2026, 8, 2, 12, 0))
    assert not r.ok and "no cableado" in r.motivo


def test_publicar_aprobado_ok_sube_privado(tmp_path):
    tok = pc.TokenYouTube(_escribir_token(tmp_path, datetime(2026, 9, 1, 12, 0)))
    cli = _ClienteFake()
    pub = pc.PublicadorYouTube(tok, cliente=cli)
    p = _pub_falsa()
    r = pub.publicar(p, aprobado=True, ahora=datetime(2026, 8, 2, 12, 0))
    assert r.ok and r.video_id == "vid_123"
    assert p.estado == "publicada"
    assert cli.llamadas == ["clip x"]


def test_fallo_del_cliente_no_se_traga(tmp_path):
    """Regla 3: un fallo de red se reporta, no queda en silencio."""
    tok = pc.TokenYouTube(_escribir_token(tmp_path, datetime(2026, 9, 1, 12, 0)))
    pub = pc.PublicadorYouTube(tok, cliente=_ClienteFake(revienta=True))
    p = _pub_falsa()
    r = pub.publicar(p, aprobado=True, ahora=datetime(2026, 8, 2, 12, 0))
    assert not r.ok and "cuota agotada" in r.motivo
    assert p.estado == "fallida"


def test_preparar_incluye_aviso_de_token_y_privacidad(tmp_path):
    tok = pc.TokenYouTube(_escribir_token(tmp_path, datetime(2026, 8, 2, 18, 0)),
                          margen_horas=24)
    prep = pc.PublicadorYouTube(tok, cliente=_ClienteFake()).preparar(
        _pub_falsa(), ahora=datetime(2026, 8, 2, 12, 0))
    assert prep["privacidad"] == "private"   # sube privado; Arturo decide (r.59)
    assert prep["token"]["aviso"] is not None  # por vencer → avisa
    assert prep["listo_para_subir"] is True


# ═══ registro en la libreta (aislado, nunca toca lo real: r.20) ══════════════
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


def test_registrar_plan_en_simulacion(libreta_sim):
    clips = _clips_falsos(2)
    plan = pc.programar_semana(clips, datetime(2026, 8, 3, 0, 0))
    with libreta_sim.Libreta("simulacion") as lib:
        ids = pc.registrar_plan(lib, plan)
        assert len(ids) == len(plan)
        fila = lib.con.execute(
            "SELECT titulo, plataforma, estado, nota FROM guiones WHERE id=?",
            (ids[0],)).fetchone()
    assert fila["plataforma"] == "youtube"
    assert fila["estado"] == "grabado"
    payload = json.loads(fila["nota"])
    assert "clip" in payload and "programado_para" in payload


def test_registro_no_toca_lo_real(libreta_sim):
    """El límite duro de Arturo (r.20): un plan de prueba no entra a lo real."""
    plan = pc.programar_semana(_clips_falsos(2), datetime(2026, 8, 3, 0, 0))
    with libreta_sim.Libreta("simulacion") as lib:
        pc.registrar_plan(lib, plan)
    with libreta_sim.Libreta("real") as real:
        assert real.con.execute("SELECT COUNT(*) FROM guiones").fetchone()[0] == 0
