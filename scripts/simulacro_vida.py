#!/usr/bin/env python3
"""
simulacro_vida.py — Ensaya la vida de Arturo dentro del entorno de simulacion.

Autorizado por el 31 jul 2026: inventar escenarios cotidianos y adelantar el
reloj para probar la logica sin esperar meses. Limite textual suyo: *"Nunca
deben contaminar mi informacion real"* -- por eso este script SE NIEGA a correr
fuera del entorno de simulacion.

Reproduce las frases que el mismo puso de ejemplo:
    "Mañana tengo que pagar la colegiatura"
    "Dentro de tres dias comprare la Mac Mini"
    "El viernes termina el cuatrimestre"
    "La proxima semana tengo una cita medica"
    "El lunes debo entregar un proyecto"

USO
    python3 simulacro_vida.py            → siembra los datos y corre el guion
    python3 simulacro_vida.py --limpiar  → borra y vuelve a sembrar
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import RUTAS, Libreta  # noqa: E402

# Candado duro: este script solo existe para el entorno de pruebas.
os.environ["HERMES_ENTORNO"] = "simulacion"

DIA0 = "2026-08-03"  # lunes. El "hoy" desde el que arranca el ensayo.


def _fecha(dias: int, hora: str | None = None) -> str:
    d = datetime.fromisoformat(DIA0) + timedelta(days=dias)
    return f"{d:%Y-%m-%d}" + (f"T{hora}" if hora else "")


def sembrar(lib: Libreta) -> None:
    """Un mes verosimil de la vida de Arturo. Todo inventado, todo en sim."""
    # ── dinero que entra ──────────────────────────────────────────────
    for semana in range(4):
        lib.registrar_ingreso(3800, "sueldo escuela", "quincena",
                              fecha=_fecha(-28 + semana * 7))
        lib.registrar_ingreso(600, "clases particulares", "sabado",
                              fecha=_fecha(-25 + semana * 7))

    # ── dinero que sale ───────────────────────────────────────────────
    cotidianos = [
        ("comida", 95), ("transporte", 40), ("comida", 130),
        ("transporte", 40), ("comida", 85), ("internet", 450),
        ("comida", 210), ("escuela", 180), ("transporte", 40),
        ("salud", 320), ("comida", 105), ("entretenimiento", 199),
    ]
    for i, (cat, monto) in enumerate(cotidianos):
        lib.registrar_gasto(monto, cat, "gasto del dia", fecha=_fecha(-26 + i * 2))

    # ── la meta que el nombro ─────────────────────────────────────────
    lib.meta_ahorro("Mac Mini", objetivo=16500, fecha_limite=_fecha(60))
    lib.abonar_meta("Mac Mini", 14200)  # casi alcanzada, a proposito

    lib.con.execute(
        "INSERT OR IGNORE INTO pagos_recurrentes (nombre, monto_mxn, dia_del_mes, nota) "
        "VALUES (?,?,?,?)", ("colegiatura", 2400, 4, "simulado"))
    lib.con.execute(
        "INSERT OR IGNORE INTO pagos_recurrentes (nombre, monto_mxn, dia_del_mes, nota) "
        "VALUES (?,?,?,?)", ("internet", 450, 5, "simulado"))

    # ── lo que dijo de pasada, sin pedir que se guardara ──────────────
    lib.agendar_cita(_fecha(1, "09:00"), "Pagar la colegiatura",
                     nota="lo dijo de pasada: 'mañana tengo que pagar la colegiatura'",
                     recordar_min_antes=720)
    lib.agendar_cita(_fecha(4, "23:59"), "Termina el cuatrimestre",
                     nota="'el viernes termina el cuatrimestre'", recordar_min_antes=1440)
    lib.agendar_cita(_fecha(7, "11:30"), "Cita medica", lugar="clinica",
                     nota="'la proxima semana tengo una cita medica'", recordar_min_antes=1440)

    # ── escuela ───────────────────────────────────────────────────────
    lib.registrar_tarea("Proyecto final de Base de Datos", materia="Base de Datos",
                        maestro="Diana Hernandez Orozco", fecha_entrega=_fecha(0),
                        origen="correo", correo_msgid="<sim-1@classroom>",
                        nota="'el lunes debo entregar un proyecto'")
    lib.registrar_tarea("Analisis del entorno", materia="Administracion",
                        maestro="Paulina Xitlali Reyna Corrales", fecha_entrega=_fecha(3),
                        origen="correo", correo_msgid="<sim-2@classroom>")
    lib.registrar_tarea("Evidencia de aprendizaje", materia="Calidad",
                        maestro="Dulce Liliana Estrada Bahena", fecha_entrega=_fecha(-2),
                        origen="correo", correo_msgid="<sim-3@classroom>")

    # ── cuerpo ────────────────────────────────────────────────────────
    for i, kg in enumerate([79.8, 79.4, 79.1, 78.6, 78.4]):
        lib.registrar_peso = None  # (no hay helper aun; se escribe directo)
        lib.con.execute("INSERT INTO peso (fecha, kg) VALUES (?,?)",
                        (_fecha(-28 + i * 7), kg))
    for i in range(9):
        lib.con.execute(
            "INSERT INTO entrenamientos (fecha, tipo, duracion_min) VALUES (?,?,?)",
            (_fecha(-27 + i * 3), "pesas" if i % 2 else "correr", 45 + (i % 3) * 10))


def guion(lib: Libreta, etiqueta: str) -> None:
    """Que sabe Hermes en este momento del tiempo simulado."""
    print(f"\n{'='*66}\n  {etiqueta}  (hoy simulado: {lib.hoy()})\n{'='*66}")

    b = lib.balance(desde=_fecha(-30), hasta=lib.hoy())
    print(f"\n💰 Dinero del periodo: entraron ${b['ingresos']:,.0f} · "
          f"salieron ${b['gastos']:,.0f} · saldo ${b['saldo']:,.0f}")
    for r in lib.gastos_por_categoria(desde=_fecha(-30), hasta=lib.hoy())[:3]:
        print(f"     {r['categoria']:<16} ${r['total']:>8,.0f}  ({r['n']} veces)")

    meta = lib.meta_ahorro("Mac Mini")
    falta = meta["objetivo_mxn"] - meta["acumulado_mxn"]
    pct = 100 * meta["acumulado_mxn"] / meta["objetivo_mxn"]
    print(f"\n🎯 Mac Mini: ${meta['acumulado_mxn']:,.0f} de ${meta['objetivo_mxn']:,.0f} "
          f"({pct:.0f}%) — faltan ${falta:,.0f}")

    vencidas = lib.marcar_vencidas()
    if vencidas:
        print(f"\n⏰ {vencidas} tarea(s) pasaron a VENCIDA al avanzar el tiempo")
    pend = lib.tareas_pendientes()
    if pend:
        print("\n📚 Tareas pendientes:")
        for t in pend:
            print(f"     {t['fecha_entrega'] or 'sin fecha'} | {t['titulo']} "
                  f"({t['materia']})")

    avisos = lib.pendientes_de_avisar()
    if avisos:
        print("\n🔔 Hermes AVISARIA ahora mismo de:")
        for c in avisos:
            print(f"     {c['fecha_hora']} | {c['titulo']}")
            if c["nota"]:
                print(f"                        └─ {c['nota']}")
    else:
        print("\n🔕 Nada que avisar todavia")


def main() -> None:
    ruta = RUTAS["simulacion"]
    if not ruta.exists():
        print(f"🔴 falta el entorno de simulacion. Corre:\n"
              f"   python3 libreta_migrar.py --entorno simulacion")
        sys.exit(1)

    if "--limpiar" in sys.argv:
        ruta.unlink()
        os.system(f"{sys.executable} "
                  f"{Path(__file__).parent / 'libreta_migrar.py'} --entorno simulacion "
                  f">/dev/null")
        print("entorno de simulacion recreado desde cero")

    os.environ.pop("HERMES_FECHA_SIMULADA", None)
    with Libreta("simulacion") as lib:
        ya = lib.con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0]
        if not ya:
            sembrar(lib)
            print(f"sembrado: un mes de vida simulada, arrancando en {DIA0}")

    # ── el viaje en el tiempo ────────────────────────────────────────
    for dias, etiqueta in ((0, "LUNES — el dia que entrega el proyecto"),
                           (1, "MARTES — el dia de la colegiatura"),
                           (4, "VIERNES — termina el cuatrimestre"),
                           (7, "LUNES SIGUIENTE — la cita medica")):
        os.environ["HERMES_FECHA_SIMULADA"] = _fecha(dias, "07:30")
        with Libreta("simulacion") as lib:
            guion(lib, etiqueta)
            for c in lib.pendientes_de_avisar():
                lib.marcar_avisada(c["id"])
    os.environ.pop("HERMES_FECHA_SIMULADA", None)


if __name__ == "__main__":
    main()
