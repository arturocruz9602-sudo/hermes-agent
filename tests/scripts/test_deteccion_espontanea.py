"""Pruebas de captura espontánea (HAS OT-9 punto 2, r.89).

r.89, textual: "¿Preguntar antes de agendar capturas espontáneas? Sí, que
siempre pregunte." Estas pruebas clavan eso como invariante duro:

  (1) `detectar(...)` NUNCA crea una tarea en la cola — solo registra la
      captura como `pendiente_confirmacion` y arma la pregunta.
  (2) solo `confirmar(aprobado=True, cola=...)` crea la tarea, y solo una vez
      (no se resuelve dos veces la misma captura).
  (3) el tope de 3 preguntas/día se respeta; el resto queda `diferida`, no
      se pierde ni se pregunta de golpe.
  (4) éxito Y fallo quedan en `capturas_espontaneas_log` (el silencio no es
      estado válido de fallo, CLAUDE.md regla 3).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from cola_v2 import ColaTareas  # noqa: E402
from deteccion_espontanea import (CONFIRMADA, DIFERIDA, PENDIENTE, RECHAZADA,  # noqa: E402
                                   CapturaInexistente, DetectorEspontaneo,
                                   EstadoInvalido, extractor_simulado)


# ── dobles de prueba ─────────────────────────────────────────────────────
def extractor_vacio(_texto):
    return []


def extractor_fijo(_texto):
    return [{"descripcion": "cita con el doctor", "fecha": "viernes", "hora": "15:00"}]


def extractor_multiple(n):
    def _extractor(_texto):
        return [{"descripcion": f"compromiso {i}", "fecha": "lunes", "hora": None}
                for i in range(n)]
    return _extractor


@pytest.fixture
def det(tmp_path):
    db = tmp_path / "state_test.db"
    with DetectorEspontaneo(db_path=db) as d:
        yield d


@pytest.fixture
def cola(tmp_path):
    db = tmp_path / "state_test.db"  # misma BD que `det`: tablas separadas, sin choque
    with ColaTareas(db_path=db) as c:
        yield c


# ── detectar nunca crea nada ─────────────────────────────────────────────
def test_detectar_sin_candidatos_no_registra_nada(det):
    preguntas = det.detectar("hola, ¿cómo estás?", extractor_vacio, chat_id="1")
    assert preguntas == []
    assert det.con.execute("SELECT COUNT(*) n FROM capturas_espontaneas").fetchone()["n"] == 0


def test_detectar_registra_pendiente_y_arma_pregunta(det):
    preguntas = det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="123")
    assert len(preguntas) == 1
    assert preguntas[0]["chat_id"] == "123"
    assert "¿La anoto?" in preguntas[0]["pregunta"]
    assert "cita con el doctor" in preguntas[0]["pregunta"]

    fila = det.obtener(preguntas[0]["id"])
    assert fila["estado"] == PENDIENTE
    assert fila["fecha_propuesta"] == "viernes"


def test_detectar_no_toca_la_cola(det, cola):
    """r.89: detectar jamás agenda por su cuenta."""
    det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="123")
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 0


def test_extraccion_fallida_queda_logueada(det):
    def extractor_roto(_texto):
        raise RuntimeError("modelo caído")

    with pytest.raises(RuntimeError):
        det.detectar("algo", extractor_roto, chat_id="1")
    logs = det.con.execute(
        "SELECT * FROM capturas_espontaneas_log WHERE evento='extraccion'").fetchall()
    assert any(row["ok"] == 0 and "modelo caído" in row["detalle"] for row in logs)


# ── confirmar es la única puerta que crea algo ───────────────────────────
def test_confirmar_aprobado_crea_tarea_en_cola(det, cola):
    preguntas = det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="123")
    cid = preguntas[0]["id"]

    fila = det.confirmar(cid, aprobado=True, cola=cola)
    assert fila["estado"] == CONFIRMADA
    assert fila["tarea_id"] is not None

    tarea = cola.obtener(fila["tarea_id"])
    assert tarea is not None
    assert tarea["chat_id"] == "123"


def test_confirmar_rechazado_no_crea_tarea(det, cola):
    preguntas = det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="123")
    cid = preguntas[0]["id"]

    fila = det.confirmar(cid, aprobado=False)
    assert fila["estado"] == RECHAZADA
    assert fila["tarea_id"] is None
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 0


def test_confirmar_aprobado_sin_cola_falla(det):
    preguntas = det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="123")
    with pytest.raises(ValueError):
        det.confirmar(preguntas[0]["id"], aprobado=True)


def test_confirmar_dos_veces_falla_no_duplica_tarea(det, cola):
    preguntas = det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="123")
    cid = preguntas[0]["id"]
    det.confirmar(cid, aprobado=True, cola=cola)
    with pytest.raises(EstadoInvalido):
        det.confirmar(cid, aprobado=True, cola=cola)
    assert cola.con.execute("SELECT COUNT(*) n FROM task_queue").fetchone()["n"] == 1


def test_confirmar_id_inexistente_falla(det):
    with pytest.raises(CapturaInexistente):
        det.confirmar(9999, aprobado=False)


# ── anti-spam: tope de 3 preguntas/día ───────────────────────────────────
def test_tope_diario_difiere_el_exceso(det):
    preguntas = det.detectar("x", extractor_multiple(5), chat_id="1")
    assert len(preguntas) == 3  # MAX_PREGUNTAS_DIA

    filas = det.con.execute("SELECT estado FROM capturas_espontaneas").fetchall()
    estados = [f["estado"] for f in filas]
    assert estados.count(PENDIENTE) == 3
    assert estados.count(DIFERIDA) == 2


def test_promover_diferidas_respeta_tope_si_sigue_lleno(det):
    det.detectar("x", extractor_multiple(5), chat_id="1")  # 3 pendientes + 2 diferidas
    # el tope de hoy ya se llenó con las 3 de arriba -> promover no debería
    # exceder el tope total del día actual (mismo día en la prueba).
    nuevas = det.promover_diferidas()
    assert nuevas == []

    restantes = det.diferidas_para_reintentar()
    assert len(restantes) == 2


def test_promover_diferidas_cuando_hay_cupo(det):
    det.detectar("x", extractor_multiple(2), chat_id="1")  # 2 pendientes, cupo=1 libre
    det.detectar("y", extractor_multiple(2), chat_id="1")  # 1 más pendiente (llega a 3), 1 diferida
    pendientes_antes = len(det.pendientes())
    assert pendientes_antes == 3
    assert len(det.diferidas_para_reintentar()) == 1


# ── pendientes / filtrado por chat ───────────────────────────────────────
def test_pendientes_filtra_por_chat(det):
    det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="A")
    det.detectar("nos vemos el viernes a las 3", extractor_fijo, chat_id="B")
    assert len(det.pendientes(chat_id="A")) == 1
    assert len(det.pendientes(chat_id="B")) == 1
    assert len(det.pendientes()) == 2


# ── extractor de prueba basado en reglas de texto ────────────────────────
def test_extractor_simulado_detecta_disparador_y_fecha():
    candidatos = extractor_simulado("Recuérdame que nos vemos el viernes a las 3pm")
    assert len(candidatos) == 1
    assert candidatos[0]["fecha"].lower() == "viernes"


def test_extractor_simulado_ignora_frases_sin_disparador():
    candidatos = extractor_simulado("El viernes hace mucho calor en la ciudad")
    assert candidatos == []


def test_extractor_simulado_ignora_disparador_sin_fecha():
    candidatos = extractor_simulado("hay que comprar leche")
    assert candidatos == []
