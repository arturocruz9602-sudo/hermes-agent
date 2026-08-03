"""Pruebas de la cola de tareas v2 (HAS §E5) — los invariantes de la GARANTÍA.

La cola es la espina dorsal de la proactividad: si una tarea encolada se
pierde en silencio, Arturo deja de confiar en que Hermes cumple. Estas pruebas
clavan los tres invariantes de HAS §E5 con solver/notificador FALSOS (nada de
red, nada de modelos de pago):

  (1) toda fila termina en `notificada` o en `atorada` con su aviso enviado;
  (2) resolved_at ⇒ notified_at (resuelta-sin-avisar es un estado prohibido);
  (3) el watchdog re-encola huérfanas sin duplicar efectos (result_hash).

Y que TODO —éxito Y fallo— queda en task_queue_log (el silencio no es estado
válido de fallo).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import cola_v2  # noqa: E402
from cola_v2 import (ATORADA, ENCOLADA, EN_PROCESO, NOTIFICADA, RESUELTA,  # noqa: E402
                     ColaTareas)


# ── dobles de prueba (solver + notificador inyectables) ─────────────────────
def solver_ok(payload, proveedor):
    return f"resultado[{proveedor}]:{payload}"


def solver_siempre_falla(payload, proveedor):
    raise RuntimeError(f"proveedor {proveedor} caído")


class SolverFallaN:
    """Falla las primeras N llamadas; luego responde. Cuenta llamadas."""
    def __init__(self, fallas):
        self.fallas = fallas
        self.llamadas = 0

    def __call__(self, payload, proveedor):
        self.llamadas += 1
        if self.llamadas <= self.fallas:
            raise RuntimeError(f"falla #{self.llamadas} ({proveedor})")
        return f"ok tras {self.llamadas} llamadas"


class Notificador:
    """Registra los avisos enviados. Puede fallar las primeras N veces."""
    def __init__(self, fallas=0):
        self.fallas = fallas
        self.enviados = []
        self.intentos = 0

    def __call__(self, chat_id, texto):
        self.intentos += 1
        if self.intentos <= self.fallas:
            raise RuntimeError("Telegram caído")
        self.enviados.append((chat_id, texto))


NO_DORMIR = lambda _s: None  # noqa: E731  — sin esperas reales en pruebas


@pytest.fixture
def cola(tmp_path):
    """Una cola sobre una BD temporal (jamás toca producción)."""
    db = tmp_path / "state_test.db"
    with ColaTareas(db_path=db) as c:
        yield c


# ── esquema / alta ──────────────────────────────────────────────────────────
def test_encolar_crea_fila_encolada(cola):
    tid = cola.encolar("resumir correo", {"tipo": "resumen"}, chat_id="123")
    fila = cola.obtener(tid)
    assert fila["estado"] == ENCOLADA
    assert fila["chat_id"] == "123"
    assert fila["created_at"] is not None
    # y quedó registrado en el log
    logs = cola.con.execute(
        "SELECT * FROM task_queue_log WHERE task_id=?", (tid,)).fetchall()
    assert any(row["evento"] == "encolar" and row["ok"] == 1 for row in logs)


# ── camino feliz + invariante 2 ─────────────────────────────────────────────
def test_flujo_feliz_llega_a_notificada(cola):
    tid = cola.encolar("tarea buena", {"x": 1}, chat_id="c1")
    notif = Notificador()
    estado = cola.procesar_una(tid, solver_ok, notif, dormir=NO_DORMIR)
    assert estado == NOTIFICADA
    fila = cola.obtener(tid)
    assert fila["estado"] == NOTIFICADA
    # invariante 2: resuelta ⇒ notificada
    assert fila["resolved_at"] is not None
    assert fila["notified_at"] is not None
    assert fila["result_hash"] is not None
    assert len(notif.enviados) == 1
    assert "Ya está" in notif.enviados[0][1]


# ── escalera de reintentos ──────────────────────────────────────────────────
def test_reintenta_dentro_del_mismo_proveedor(cola):
    tid = cola.encolar("tarea intermitente", {}, chat_id="c1")
    solver = SolverFallaN(fallas=2)  # falla 2, éxito al 3er intento (mismo prov)
    notif = Notificador()
    estado = cola.procesar_una(tid, solver, notif,
                               escalera=("groq",), dormir=NO_DORMIR)
    assert estado == NOTIFICADA
    assert solver.llamadas == 3
    assert cola.obtener(tid)["intentos"] == 3


def test_escala_al_siguiente_proveedor(cola):
    tid = cola.encolar("tarea", {}, chat_id="c1")
    # groq falla sus 5 intentos; gemini responde al 6º intento global
    solver = SolverFallaN(fallas=5)
    notif = Notificador()
    estado = cola.procesar_una(
        tid, solver, notif, escalera=("groq", "gemini"),
        max_intentos=5, dormir=NO_DORMIR)
    assert estado == NOTIFICADA
    assert cola.obtener(tid)["proveedor_actual"] == "gemini"


# ── invariante 1: atorada SIEMPRE avisa ─────────────────────────────────────
def test_toda_la_escalera_falla_queda_atorada_y_avisa(cola):
    tid = cola.encolar("tarea imposible", {}, chat_id="c9")
    notif = Notificador()
    estado = cola.procesar_una(
        tid, solver_siempre_falla, notif,
        escalera=("groq", "gemini", "openrouter"), max_intentos=2,
        dormir=NO_DORMIR)
    assert estado == ATORADA
    fila = cola.obtener(tid)
    assert fila["estado"] == ATORADA
    # una atorada TAMBIÉN se notifica (invariante 1)
    assert fila["notified_at"] is not None
    assert len(notif.enviados) == 1
    assert "Necesito ayuda" in notif.enviados[0][1]
    # 3 proveedores × 2 intentos = 6 fallos del solver, todos logueados
    fallos = cola.con.execute(
        "SELECT COUNT(*) n FROM task_queue_log "
        "WHERE task_id=? AND evento LIKE 'solver:%' AND ok=0", (tid,)).fetchone()
    assert fallos["n"] == 6


# ── invariante 2: notificación falla → NO queda resuelta-sin-avisar ─────────
def test_notif_falla_queda_resuelta_y_se_renotifica_despues(cola):
    tid = cola.encolar("tarea", {}, chat_id="c1")
    # notificador que falla sus 3 reintentos inline esta vuelta
    notif = Notificador(fallas=99)
    estado = cola.procesar_una(tid, solver_ok, notif, dormir=NO_DORMIR)
    assert estado == RESUELTA           # resuelta pero NO notificada
    fila = cola.obtener(tid)
    assert fila["resolved_at"] is not None
    assert fila["notified_at"] is None  # todavía no
    assert fila["estado"] == RESUELTA

    # segundo barrido con un notificador que ahora SÍ funciona
    notif_ok = Notificador()
    logradas = cola._reintentar_notificaciones(notif_ok, dormir=NO_DORMIR)
    assert logradas == 1
    fila = cola.obtener(tid)
    assert fila["estado"] == NOTIFICADA
    assert fila["notified_at"] is not None  # invariante 2 se restablece


def test_procesar_pendientes_barre_resueltas_sin_avisar_primero(cola):
    # deja una resuelta-sin-avisar de una corrida anterior
    tid1 = cola.encolar("vieja", {}, chat_id="c1")
    cola.procesar_una(tid1, solver_ok, Notificador(fallas=99), dormir=NO_DORMIR)
    assert cola.obtener(tid1)["estado"] == RESUELTA
    # nueva corrida: encola otra y procesa TODO con notificador sano
    cola.encolar("nueva", {}, chat_id="c1")
    notif = Notificador()
    res = cola.procesar_pendientes(solver_ok, notif, dormir=NO_DORMIR)
    # la vieja se renotifica y la nueva se resuelve+notifica
    assert cola.obtener(tid1)["estado"] == NOTIFICADA
    assert res["resueltas"] == 1
    estados = cola.contar_por_estado()
    assert estados.get(NOTIFICADA) == 2


# ── invariante 3: watchdog re-encola huérfanas sin duplicar ─────────────────
def test_watchdog_reencola_huerfana_en_proceso(cola):
    tid = cola.encolar("colgada", {}, chat_id="c1")
    # simula tarea atascada en en_proceso desde hace 3h, sin result_hash
    viejo = (datetime.now() - timedelta(hours=3)).isoformat(timespec="seconds")
    cola.con.execute(
        "UPDATE task_queue SET estado=?, started_at=? WHERE id=?",
        (EN_PROCESO, viejo, tid))
    cola.con.commit()

    notif = Notificador()
    res = cola.watchdog(solver_ok, notif, dormir=NO_DORMIR)
    assert res["reencoladas"] == 1
    # el watchdog re-encola Y vuelve a procesar → termina notificada
    fila = cola.obtener(tid)
    assert fila["estado"] == NOTIFICADA
    reencolar = cola.con.execute(
        "SELECT COUNT(*) n FROM task_queue_log "
        "WHERE task_id=? AND evento='watchdog:reencolar'", (tid,)).fetchone()
    assert reencolar["n"] == 1


def test_watchdog_no_reejecuta_solver_si_ya_tenia_result_hash(cola):
    # tarea que murió DESPUÉS de resolver pero ANTES de notificar:
    # en_proceso + result_hash presente. No debe re-ejecutar el solver.
    tid = cola.encolar("resuelta a medias", {}, chat_id="c1")
    viejo = (datetime.now() - timedelta(hours=3)).isoformat(timespec="seconds")
    cola.con.execute(
        "UPDATE task_queue SET estado=?, started_at=?, result_hash=?, resultado=? "
        "WHERE id=?", (EN_PROCESO, viejo, "abc123", "ya-hecho", tid))
    cola.con.commit()

    solver = SolverFallaN(fallas=0)  # cuenta llamadas
    notif = Notificador()
    res = cola.watchdog(solver, notif, dormir=NO_DORMIR)
    assert res["resueltas_directo"] == 1
    assert res["reencoladas"] == 0
    assert solver.llamadas == 0         # idempotencia: no se repitió el efecto
    # y termina notificada por el barrido de renotificación
    assert cola.obtener(tid)["estado"] == NOTIFICADA


def test_watchdog_ignora_en_proceso_reciente(cola):
    tid = cola.encolar("recien tomada", {}, chat_id="c1")
    reciente = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    cola.con.execute(
        "UPDATE task_queue SET estado=?, started_at=? WHERE id=?",
        (EN_PROCESO, reciente, tid))
    cola.con.commit()
    res = cola.watchdog(solver_ok, Notificador(), dormir=NO_DORMIR)
    assert res["reencoladas"] == 0
    assert cola.obtener(tid)["estado"] == EN_PROCESO  # se le respeta su tiempo


# ── el gran invariante: NADA se pierde en silencio ──────────────────────────
def test_lote_mixto_todo_termina_en_estado_terminal_con_aviso(cola):
    """15 tareas sintéticas (HAS §E5 verificación E2E): unas se resuelven, otras
    se atoran; TODAS deben acabar notificada o atorada+aviso, y TODAS deben
    tener rastro en el log."""
    notif = Notificador()

    def solver_mixto(payload, proveedor):
        if payload["n"] % 5 == 0:       # 1 de cada 5 es imposible
            raise RuntimeError("imposible")
        return f"hecho {payload['n']}"

    ids = [cola.encolar(f"tarea {n}", {"n": n}, chat_id="c1")
           for n in range(1, 16)]
    cola.procesar_pendientes(
        solver_mixto, notif, escalera=("groq", "gemini", "openrouter"),
        max_intentos=1, dormir=NO_DORMIR)

    estados = cola.contar_por_estado()
    # invariante 1: no queda NADA en estados no-terminales
    assert estados.get(ENCOLADA, 0) == 0
    assert estados.get(EN_PROCESO, 0) == 0
    assert estados.get(RESUELTA, 0) == 0
    assert estados.get(NOTIFICADA) == 12   # 15 - 3 imposibles (5,10,15)
    assert estados.get(ATORADA) == 3

    # cada fila tiene aviso registrado y rastro en el log
    for tid in ids:
        fila = cola.obtener(tid)
        assert fila["estado"] in (NOTIFICADA, ATORADA)
        assert fila["notified_at"] is not None
        n_logs = cola.con.execute(
            "SELECT COUNT(*) n FROM task_queue_log WHERE task_id=?",
            (tid,)).fetchone()["n"]
        assert n_logs >= 2   # al menos encolar + un terminal
    # y hubo avisos para las 15
    assert len(notif.enviados) == 15
