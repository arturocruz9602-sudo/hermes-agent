"""Pruebas de verificar_frescura() en vigilar_correo_escuela.py.

Hallazgo real (04 ago 2026): Thunderbird murió 3 días en silencio; el
vigilante seguía leyendo el mismo mbox congelado y reportaba "sin
novedades" con toda honestidad -- porque para él no había nada nuevo. Una
tarea real ("Plan de pruebas") se quedó sin avisar. Arturo lo notó por su
cuenta, no Hermes.

Estas pruebas clavan el arreglo (HAS regla 3: el silencio nunca es un
estado válido de fallo):
  1. Buzón fresco -> no avisa, sigue confiando.
  2. Buzón viejo -> SÍ avisa la primera vez que lo detecta.
  3. Buzón sigue viejo, ya avisado hace poco -> NO reavisa (no satura).
  4. Buzón sigue viejo, pasó el margen de reaviso -> SÍ reavisa.
  5. Buzón se recupera -> avisa que ya volvió y limpia el estado.
  6. El archivo del mbox ni siquiera existe -> también avisa (no solo mtime viejo).
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import vigilar_correo_escuela as vce  # noqa: E402


def _preparar(tmp_path, monkeypatch, *, horas_de_viejo=None):
    mbox = tmp_path / "INBOX"
    mbox.write_text("contenido")
    if horas_de_viejo is not None:
        vieja = (datetime.datetime.now() - datetime.timedelta(hours=horas_de_viejo)).timestamp()
        import os
        os.utime(mbox, (vieja, vieja))
    monkeypatch.setattr(vce, "MBOX", str(mbox))
    monkeypatch.setattr(vce, "SALUD", str(tmp_path / "salud.json"))
    monkeypatch.setattr(vce, "LOG", str(tmp_path / "log.txt"))
    return mbox


def _mock_avisar(monkeypatch, resultados):
    llamadas = []

    def fake_avisar(mensaje):
        llamadas.append(mensaje)
        return resultados.pop(0) if resultados else True

    monkeypatch.setattr(vce, "avisar", fake_avisar)
    return llamadas


def test_buzon_fresco_no_avisa(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=0.5)
    llamadas = _mock_avisar(monkeypatch, [])
    assert vce.verificar_frescura() is True
    assert llamadas == []


def test_buzon_viejo_avisa_la_primera_vez(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    llamadas = _mock_avisar(monkeypatch, [True])
    assert vce.verificar_frescura() is False
    assert len(llamadas) == 1
    assert "sincronizando" in llamadas[0]

    salud = json.loads((tmp_path / "salud.json").read_text())
    assert salud["alertando"] is True
    assert salud["ultima_alerta"] is not None


def test_buzon_sigue_viejo_no_reavisa_de_inmediato(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    llamadas = _mock_avisar(monkeypatch, [True])
    vce.verificar_frescura()  # primera alerta

    llamadas2 = _mock_avisar(monkeypatch, [])
    assert vce.verificar_frescura() is False
    assert llamadas2 == []  # no reavisó, sigue dentro del margen


def test_buzon_sigue_viejo_reavisa_tras_el_margen(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    _mock_avisar(monkeypatch, [True])
    vce.verificar_frescura()  # primera alerta

    hace_rato = datetime.datetime.now() - datetime.timedelta(hours=vce.REALERTA_HORAS + 1)
    salud = json.loads(Path(vce.SALUD).read_text())
    salud["ultima_alerta"] = hace_rato.isoformat()
    Path(vce.SALUD).write_text(json.dumps(salud))

    llamadas2 = _mock_avisar(monkeypatch, [True])
    assert vce.verificar_frescura() is False
    assert len(llamadas2) == 1  # sí reavisó


def test_buzon_se_recupera_avisa_de_vuelta_y_limpia_estado(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    _mock_avisar(monkeypatch, [True])
    vce.verificar_frescura()  # cae

    _preparar(tmp_path, monkeypatch, horas_de_viejo=0.1)  # se repara
    llamadas = _mock_avisar(monkeypatch, [True])
    assert vce.verificar_frescura() is True
    assert len(llamadas) == 1
    assert "volvió" in llamadas[0]

    salud = json.loads((tmp_path / "salud.json").read_text())
    assert salud["alertando"] is False


def test_mbox_inexistente_tambien_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(vce, "MBOX", str(tmp_path / "no_existe"))
    monkeypatch.setattr(vce, "SALUD", str(tmp_path / "salud.json"))
    monkeypatch.setattr(vce, "LOG", str(tmp_path / "log.txt"))
    llamadas = _mock_avisar(monkeypatch, [True])
    assert vce.verificar_frescura() is False
    assert "no existe" in llamadas[0]


def test_avisar_fallido_no_truena(tmp_path, monkeypatch):
    """Si Telegram también está caído, no debe reventar -- solo loguear."""
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    _mock_avisar(monkeypatch, [False])
    assert vce.verificar_frescura() is False  # no lanza excepción
