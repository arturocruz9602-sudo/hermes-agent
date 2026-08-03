"""Pruebas del corte de silencios §E6 (AU-3, Pieza 1, r.49).

El bloque promete UNA cosa acotada y estas pruebas clavan justo su frontera:
cortar silencios SIN destruir habla, y PROBARLO antes de entregar.

  1. PLAN (§E6): respeta los parámetros exactos — no corta huecos <300 ms (misma
     oración) ni <500 ms (silencio corto), conserva 200 ms antes / 250 ms después
     de cada palabra, y ningún corte toca jamás el span de una palabra.
  2. VERIFICACIÓN (§E6): compara conteo de palabras y WER; falla si se pierde
     aunque sea una palabra o el WER pasa de 2 %.
  3. RELAJACIÓN Y FALLBACK (§E6): reproduce el fallo real de r.49 (la cola de una
     consonante final tomada por silencio) — la primera pasada la pierde, el loop
     de relajación (umbral +3 dB, padding +50 ms) la rescata; y si NADA la salva,
     entrega el original con "no pude cortar sin riesgo", nunca un corte que destruye.

Todo es determinista y sin audio: el oráculo modela el fallo de r.49 a partir de
la cola de fade de cada palabra (r.20 — laboratorio).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import corte_silencios as cs  # noqa: E402


# ── material de prueba ───────────────────────────────────────────────────────
def _p(inicio, fin, texto, cola_ms=0.0):
    return cs.Palabra(inicio=inicio, fin=fin, texto=texto, cola_ms=cola_ms)


# Habla con: dos palabras pegadas (<300ms), un hueco corto (400ms, no cortable),
# un silencio largo cortable (~1.6s), y una palabra final que se apaga (cola 400ms).
PALABRAS = [
    _p(0.0, 0.6, "Hola"),
    _p(0.75, 1.4, "jefe"),                    # hueco 150ms → misma oración
    _p(1.8, 2.4, "hoy"),                      # hueco 400ms → corto, no se corta
    _p(4.0, 4.6, "empezamos"),                # hueco 1.6s → cortable
    _p(4.9, 6.2, "temprano", cola_ms=400),    # hueco 300ms; se apaga al final
    _p(8.0, 8.5, "listo"),                    # hueco 1.8s → cortable
]


# ═══ 1. PLAN DE CORTES ═══════════════════════════════════════════════════════
def test_no_corta_dentro_de_una_oracion():
    """<300 ms entre palabras = misma oración: jamás se corta (§E6)."""
    palabras = [_p(0.0, 0.6, "una"), _p(0.75, 1.3, "sola"), _p(1.45, 2.0, "oración")]
    assert cs.plan_cortes(palabras) == []


def test_no_corta_silencio_corto():
    """Un hueco de 400 ms está por debajo del mínimo de 500 ms: no se corta."""
    palabras = [_p(0.0, 1.0, "uno"), _p(1.4, 2.0, "dos")]  # hueco 400ms
    assert cs.plan_cortes(palabras) == []


def test_corta_silencio_largo():
    """Un hueco de 1.6 s se corta, conservando 250 ms tras la palabra previa y
    200 ms antes de la siguiente."""
    palabras = [_p(0.0, 1.0, "uno"), _p(2.6, 3.2, "dos")]  # hueco 1.6s
    cortes = cs.plan_cortes(palabras)
    assert len(cortes) == 1
    c = cortes[0]
    assert c.inicio == pytest.approx(1.0 + 0.250)   # 250 ms tras "uno"
    assert c.fin == pytest.approx(2.6 - 0.200)      # 200 ms antes de "dos"


def test_padding_se_come_hueco_apenas_mayor_que_umbral():
    """Un hueco de 500 ms cumple el mínimo pero el padding (200+250=450) casi lo
    tapa: quedan 50 ms cortables. Un hueco donde el padding lo cubre entero → nada."""
    justo = [_p(0.0, 1.0, "a"), _p(1.5, 2.0, "b")]     # hueco 500ms → 50ms cortable
    assert len(cs.plan_cortes(justo)) == 1
    tapado = [_p(0.0, 1.0, "a"), _p(1.44, 2.0, "b")]   # hueco 440ms <500 → ni se considera
    assert cs.plan_cortes(tapado) == []


def test_ningun_corte_toca_habla():
    """Invariante estructural §E6: ningún corte invade el span de una palabra ni
    su padding. Es el corazón del bloque."""
    cortes = cs.plan_cortes(PALABRAS)
    assert cortes, "debía haber al menos un corte en el material"
    assert cs._corte_invade_habla(PALABRAS, cortes, cs.ParametrosCorte()) is None


def test_detecta_corte_que_invade_habla():
    """Si a mano se mete un corte que muerde una palabra, el invariante lo detecta."""
    malo = [cs.Corte(inicio=4.5, fin=5.0)]  # cae dentro de "empezamos"/"temprano"
    msg = cs._corte_invade_habla(PALABRAS, malo, cs.ParametrosCorte())
    assert msg is not None and "invade" in msg


# ═══ 2. VERIFICACIÓN §E6 ═════════════════════════════════════════════════════
def test_verificacion_ok_sin_perdida():
    v = cs.verificar_corte(["hola", "jefe", "listo"], ["hola", "jefe", "listo"])
    assert v.ok and v.palabras_perdidas == 0 and v.wer == 0.0


def test_verificacion_falla_por_palabra_perdida():
    """Perder aunque sea una palabra reprueba, sin importar el WER (criterio 0)."""
    v = cs.verificar_corte(["hola", "jefe", "listo"], ["hola", "listo"])
    assert not v.ok and v.palabras_perdidas == 1


def test_verificacion_falla_por_wer_alto():
    """Mismo conteo pero palabras cambiadas: WER supera 2 % → reprueba."""
    v = cs.verificar_corte(["uno", "dos", "tres", "cuatro"], ["uno", "XXX", "tres", "cuatro"])
    assert v.palabras_perdidas == 0 and v.wer > cs.MAX_WER and not v.ok


def test_wer_calculo():
    assert cs._wer(["a", "b", "c", "d"], ["a", "b", "c", "d"]) == 0.0
    assert cs._wer(["a", "b", "c", "d"], ["a", "x", "c", "d"]) == pytest.approx(0.25)
    assert cs._wer([], []) == 0.0


# ═══ 3. PIPELINE: relajación y fallback (§E6, el fallo de r.49) ═══════════════
def test_corte_limpio_pasa_a_la_primera():
    """Sin palabras que se apaguen, el corte se verifica a la primera iteración."""
    palabras = [_p(0.0, 1.0, "uno"), _p(3.0, 4.0, "dos"), _p(6.0, 7.0, "tres")]
    res = cs.cortar_con_verificacion(palabras)
    assert not res.entrego_original
    assert res.iteraciones == 1
    assert res.verificacion.ok and res.cortes


def test_rescata_cola_de_consonante_con_relajacion():
    """EL corazón de r.49: 'temprano' se apaga (cola 400 ms). La primera pasada
    (padding 250 ms) la recorta y la verificación FALLA; al relajar umbral+padding
    se rescata y la segunda pasada pasa con 0 palabras perdidas."""
    res = cs.cortar_con_verificacion(PALABRAS)
    assert not res.entrego_original, "el loop de relajación debía rescatar la palabra"
    assert res.iteraciones >= 2, "la primera pasada debía fallar y forzar relajación"
    assert res.verificacion.ok and res.verificacion.palabras_perdidas == 0


def test_relajacion_aumenta_padding_50ms_y_umbral():
    p0 = cs.ParametrosCorte()
    p1 = p0.relajado()
    assert p1.pad_antes_ms == p0.pad_antes_ms + 50
    assert p1.pad_despues_ms == p0.pad_despues_ms + 50
    assert p1.captura_fade_ms > p0.captura_fade_ms  # umbral +3dB rescata más cola


def test_fallback_entrega_original_si_no_puede_cortar_sin_riesgo():
    """Una cola imposible de cubrir (2 s) NO se rescata ni tras 3 iteraciones:
    el pipeline entrega el ORIGINAL con el motivo, jamás un corte que destruye."""
    palabras = [
        _p(0.0, 1.0, "arranque"),
        _p(3.0, 4.0, "desvanece", cola_ms=2000),  # cola gigantesca, incubrible
        _p(6.0, 7.0, "final"),
    ]
    res = cs.cortar_con_verificacion(palabras)
    assert res.entrego_original
    assert res.cortes == []
    assert res.iteraciones == cs.MAX_ITER
    assert "no pude cortar sin riesgo" in res.motivo


def test_transcriptor_inyectable():
    """El transcriptor es un puerto: se inyecta uno que reporta pérdida y el
    pipeline lo respeta (no abre Whisper ni red solo, B10/r.119)."""
    palabras = [_p(0.0, 1.0, "uno"), _p(3.0, 4.0, "dos"), _p(6.0, 7.0, "tres")]
    llamadas = {"n": 0}

    def transcriptor_que_pierde(pals, cortes, params):
        llamadas["n"] += 1
        return ["uno", "tres"]  # siempre "pierde" dos, nunca verifica

    res = cs.cortar_con_verificacion(palabras, transcribir_resultado=transcriptor_que_pierde)
    assert llamadas["n"] == cs.MAX_ITER  # se le llamó en cada intento
    assert res.entrego_original          # nunca logró verificar → original


def test_registra_exito_y_fallo_en_logger():
    """Nada corre en silencio (regla 3): el logger recibe tanto el fallo de la
    primera iteración como el éxito final."""
    lineas = []
    cs.cortar_con_verificacion(PALABRAS, logger=lineas.append)
    texto = "\n".join(lineas)
    assert "FALLA" in texto and "OK" in texto
    assert "relajo" in texto


# ═══ 4. CLI ══════════════════════════════════════════════════════════════════
def test_cli_end_to_end(tmp_path):
    ruta = tmp_path / "palabras.json"
    ruta.write_text(json.dumps([
        {"inicio": 0.0, "fin": 1.0, "texto": "hola"},
        {"inicio": 3.0, "fin": 4.0, "texto": "jefe"},
        {"inicio": 6.0, "fin": 7.0, "texto": "listo"},
    ]), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "corte_silencios.py"), str(ruta)],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert "cortes" in r.stdout and "verificación §E6" in r.stdout
