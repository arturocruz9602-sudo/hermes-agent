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


# ── F6-3 (r.62-64): analiza + sugiere, no solo avisa ─────────────────────
# vigilar_correo_escuela.py solo reenviaba remitente/asunto. r.62-64 pide
# que analice el correo y SUGIERA qué hacer, con el formato EXACTO que dio
# Arturo el 04 ago: "Arturo, te llegó tal correo, es una tarea para hoy a
# las 11, ¿qué quieres que realice?" -- y con seguimiento de dos avisos
# para entregas: uno ANTES de la hora límite y uno DESPUÉS preguntando si
# ya se subió (nunca asumir que se hizo).

def test_categorizar_por_asunto():
    assert vce.categorizar("Examen de programación el lunes") == "examen"
    assert vce.categorizar("Fecha límite de entrega del proyecto final") == "entrega"
    assert vce.categorizar("Nueva tarea de base de datos") == "tarea"
    assert vce.categorizar("Convocatoria de becas 2026") == "aviso"
    assert vce.categorizar("Hola, ¿cómo estás?") == "correo"


def test_categorizar_usa_tambien_el_cuerpo():
    # el asunto solo no dice nada, pero el cuerpo sí
    assert vce.categorizar("Aviso importante", "Recuerden que hay examen mañana") == "examen"


def test_extraer_fecha_limite_hoy_con_hora():
    ahora = datetime.datetime(2026, 8, 4, 7, 0)
    texto, dt = vce.extraer_fecha_limite(
        "Es tarea para hoy a las 11, no lo olvides", ahora=ahora)
    assert texto == "hoy a las 11:00"
    assert dt == datetime.datetime(2026, 8, 4, 11, 0)


def test_extraer_fecha_limite_solo_hora_asume_hoy():
    ahora = datetime.datetime(2026, 8, 4, 7, 0)
    texto, dt = vce.extraer_fecha_limite("Entrega antes de las 18:30", ahora=ahora)
    assert texto == "hoy a las 18:30"
    assert dt == datetime.datetime(2026, 8, 4, 18, 30)


def test_extraer_fecha_limite_manana():
    ahora = datetime.datetime(2026, 8, 4, 7, 0)
    texto, dt = vce.extraer_fecha_limite("Sube el archivo mañana a las 9", ahora=ahora)
    assert texto == "mañana a las 09:00"
    assert dt == datetime.datetime(2026, 8, 5, 9, 0)


def test_extraer_fecha_limite_fecha_explicita():
    ahora = datetime.datetime(2026, 8, 4, 7, 0)
    texto, dt = vce.extraer_fecha_limite("Entrega el 10 de agosto a las 23:00", ahora=ahora)
    assert texto == "10/08 a las 23:00"
    assert dt == datetime.datetime(2026, 8, 10, 23, 0)


def test_extraer_fecha_limite_sin_senales_devuelve_none():
    texto, dt = vce.extraer_fecha_limite("Bienvenidos al nuevo cuatrimestre")
    assert texto is None
    assert dt is None


def test_construir_mensaje_formato_exacto_de_arturo():
    msg = vce.construir_mensaje(
        "Coordinación <coord@utrng.edu.mx>", "Tarea de base de datos",
        "tarea", "hoy a las 11", "viene de la escuela")
    assert ("Arturo, te llegó un correo de la escuela, es una tarea para hoy "
            "a las 11, ¿qué quieres que realice?") in msg
    assert "De: Coordinación" in msg
    assert "Asunto: Tarea de base de datos" in msg


def test_construir_mensaje_sin_fecha_no_inventa_una():
    msg = vce.construir_mensaje(
        "prof@utrng.edu.mx", "Aviso general", "aviso", None, "viene de la escuela")
    assert "es un aviso, ¿qué quieres que realice?" in msg


def _preparar_seguimientos(tmp_path, monkeypatch):
    monkeypatch.setattr(vce, "SEGUIMIENTOS", str(tmp_path / "seguimientos.json"))
    monkeypatch.setattr(vce, "LOG", str(tmp_path / "log.txt"))


def test_registrar_seguimiento_solo_para_categorias_con_entregable(tmp_path, monkeypatch):
    _preparar_seguimientos(tmp_path, monkeypatch)
    deadline = datetime.datetime(2026, 8, 4, 11, 0)
    vce.registrar_seguimiento("id-1", "Tarea X", "aviso", deadline)
    assert vce.cargar_seguimientos() == []  # "aviso" no tiene entregable

    vce.registrar_seguimiento("id-2", "Tarea X", "tarea", deadline)
    pendientes = vce.cargar_seguimientos()
    assert len(pendientes) == 1
    assert pendientes[0]["id"] == "id-2"
    assert pendientes[0]["aviso_antes_enviado"] is False
    assert pendientes[0]["aviso_despues_enviado"] is False


def test_registrar_seguimiento_no_duplica(tmp_path, monkeypatch):
    _preparar_seguimientos(tmp_path, monkeypatch)
    deadline = datetime.datetime(2026, 8, 4, 11, 0)
    vce.registrar_seguimiento("id-1", "Tarea X", "tarea", deadline)
    vce.registrar_seguimiento("id-1", "Tarea X", "tarea", deadline)
    assert len(vce.cargar_seguimientos()) == 1


def test_verificar_seguimientos_avisa_antes_una_hora_antes(tmp_path, monkeypatch):
    _preparar_seguimientos(tmp_path, monkeypatch)
    deadline = datetime.datetime(2026, 8, 4, 11, 0)
    vce.registrar_seguimiento("id-1", "Tarea X", "tarea", deadline)
    llamadas = _mock_avisar(monkeypatch, [True])

    vce.verificar_seguimientos(ahora=datetime.datetime(2026, 8, 4, 10, 30))

    assert len(llamadas) == 1
    assert "Tarea X" in llamadas[0]
    assert "antes de las 11:00" in llamadas[0]
    pendientes = vce.cargar_seguimientos()
    assert pendientes[0]["aviso_antes_enviado"] is True
    assert pendientes[0]["aviso_despues_enviado"] is False  # aún no toca


def test_verificar_seguimientos_no_avisa_antes_de_tiempo(tmp_path, monkeypatch):
    _preparar_seguimientos(tmp_path, monkeypatch)
    deadline = datetime.datetime(2026, 8, 4, 11, 0)
    vce.registrar_seguimiento("id-1", "Tarea X", "tarea", deadline)
    llamadas = _mock_avisar(monkeypatch, [])

    vce.verificar_seguimientos(ahora=datetime.datetime(2026, 8, 4, 9, 0))

    assert llamadas == []


def test_verificar_seguimientos_NO_manda_el_aviso_despues(tmp_path, monkeypatch):
    """Arturo (04 ago): "si un correo llega aunque yo no te diga nada, que
    no se vuelva a mandar el segundo aviso" -- el aviso DESPUÉS queda solo
    en el log, nunca por Telegram (no hay forma de saber si respondió al
    primero). Mismo patrón que la alarma de frescura (P5-b)."""
    _preparar_seguimientos(tmp_path, monkeypatch)
    deadline = datetime.datetime(2026, 8, 4, 11, 0)
    vce.registrar_seguimiento("id-1", "Tarea X", "tarea", deadline)
    _mock_avisar(monkeypatch, [True])
    vce.verificar_seguimientos(ahora=datetime.datetime(2026, 8, 4, 10, 30))  # aviso antes

    llamadas = _mock_avisar(monkeypatch, [])
    vce.verificar_seguimientos(ahora=datetime.datetime(2026, 8, 4, 12, 0))  # pasó el deadline

    assert llamadas == []  # NO se llamó avisar() para el "después"
    # pero igual se marca resuelto internamente y se limpia de pendientes
    # (evita que este log se repita cada 15 min mientras siga sin resolver)
    assert vce.cargar_seguimientos() == []


def test_verificar_seguimientos_no_reenvia_el_mismo_aviso(tmp_path, monkeypatch):
    _preparar_seguimientos(tmp_path, monkeypatch)
    deadline = datetime.datetime(2026, 8, 4, 11, 0)
    vce.registrar_seguimiento("id-1", "Tarea X", "tarea", deadline)
    _mock_avisar(monkeypatch, [True])
    vce.verificar_seguimientos(ahora=datetime.datetime(2026, 8, 4, 10, 30))

    llamadas = _mock_avisar(monkeypatch, [])
    vce.verificar_seguimientos(ahora=datetime.datetime(2026, 8, 4, 10, 45))  # sigue antes del deadline

    assert llamadas == []  # ya avisado, no reavisa
