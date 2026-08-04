"""Pruebas de verificar_frescura() en vigilar_correo_escuela.py.

Hallazgo real (04 ago 2026): Thunderbird murió 3 días en silencio; el
vigilante seguía leyendo el mismo mbox congelado y reportaba "sin
novedades" con toda honestidad -- porque para él no había nada nuevo. Una
tarea real ("Plan de pruebas") se quedó sin avisar. Arturo lo notó por su
cuenta, no Hermes.

Corrección del mismo día: la primera alerta real (buzón quieto 4h, con
Thunderbird en realidad vivo y conectado) resultó ser una falsa alarma --
Arturo pidió que estos avisos de SALUD ya no lleguen por Telegram, solo
quiere avisos de correos reales. AVISAR_FRESCURA_POR_TELEGRAM=False por
default: el hallazgo se sigue detectando y queda en el log (para
diagnóstico), pero no se envía nada. El interruptor sigue existiendo por
si algún día hace falta reactivarlo con evidencia nueva.

Estas pruebas clavan:
  1. Buzón fresco -> nunca avisa.
  2-6. Buzón viejo/recuperado/inexistente, CON el interruptor apagado
       (default de Arturo) -> se detecta y se loguea, pero NUNCA se llama
       a avisar() (Telegram).
  7-8. Con el interruptor prendido explícitamente -> se preserva el
       comportamiento viejo (avisa, dedupe, reavisa tras el margen), por
       si se reactiva en el futuro.
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


# ── default de Arturo (04 ago): SIN Telegram, solo log ──────────────────
def test_buzon_viejo_por_default_NO_avisa_por_telegram(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    llamadas = _mock_avisar(monkeypatch, [])
    assert vce.verificar_frescura() is False
    assert llamadas == []  # el punto central del cambio: nunca llama avisar()

    salud = json.loads((tmp_path / "salud.json").read_text())
    assert salud["alertando"] is True  # el estado SÍ se sigue registrando

    log = (tmp_path / "log.txt").read_text()
    assert "sin sincronizar" in log  # queda evidencia para diagnóstico


def test_mbox_inexistente_por_default_NO_avisa_por_telegram(tmp_path, monkeypatch):
    monkeypatch.setattr(vce, "MBOX", str(tmp_path / "no_existe"))
    monkeypatch.setattr(vce, "SALUD", str(tmp_path / "salud.json"))
    monkeypatch.setattr(vce, "LOG", str(tmp_path / "log.txt"))
    llamadas = _mock_avisar(monkeypatch, [])
    assert vce.verificar_frescura() is False
    assert llamadas == []
    assert "no existe" in (tmp_path / "log.txt").read_text()


def test_buzon_se_recupera_por_default_NO_avisa_de_vuelta(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    _mock_avisar(monkeypatch, [])
    vce.verificar_frescura()  # cae

    _preparar(tmp_path, monkeypatch, horas_de_viejo=0.1)  # se repara
    llamadas = _mock_avisar(monkeypatch, [])
    assert vce.verificar_frescura() is True
    assert llamadas == []

    salud = json.loads((tmp_path / "salud.json").read_text())
    assert salud["alertando"] is False  # el estado igual se limpia


def test_dedupe_sigue_funcionando_aunque_no_avise_por_telegram(tmp_path, monkeypatch):
    """El registro de 'ya sé que está caído' no depende del canal de aviso."""
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    _mock_avisar(monkeypatch, [])
    vce.verificar_frescura()

    assert vce.verificar_frescura() is False  # sigue detectando, sin tronar
    salud = json.loads((tmp_path / "salud.json").read_text())
    assert salud["alertando"] is True


# ── interruptor prendido explícitamente: se preserva el código viejo ────
def test_con_telegram_prendido_avisa_la_primera_vez(tmp_path, monkeypatch):
    monkeypatch.setattr(vce, "AVISAR_FRESCURA_POR_TELEGRAM", True)
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    llamadas = _mock_avisar(monkeypatch, [True])
    assert vce.verificar_frescura() is False
    assert len(llamadas) == 1
    assert "sincronizando" in llamadas[0]


def test_con_telegram_prendido_reavisa_tras_el_margen(tmp_path, monkeypatch):
    monkeypatch.setattr(vce, "AVISAR_FRESCURA_POR_TELEGRAM", True)
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


def test_con_telegram_prendido_avisar_fallido_no_truena(tmp_path, monkeypatch):
    monkeypatch.setattr(vce, "AVISAR_FRESCURA_POR_TELEGRAM", True)
    _preparar(tmp_path, monkeypatch, horas_de_viejo=5)
    _mock_avisar(monkeypatch, [False])
    assert vce.verificar_frescura() is False  # no lanza excepción
