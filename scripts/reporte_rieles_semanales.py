#!/usr/bin/env python3
"""
reporte_rieles_semanales.py — Reporte semanal de rieles financieros (bloque F7-3, r.18).

Genera un análisis completo del estado financiero: balance semanal, desglose de
ingresos, gastos, negocio de refrescos, meta de ahorro ($100k por 31-dic-2027).

USO
    python3 reporte_rieles_semanales.py [--entorno real|simulacion] [--dias N]

Por defecto genera el reporte de los últimos 7 días en entorno "real".
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from libreta import Libreta, hoy, ahora


def fecha_hace_n_dias(n: int, desde_fecha: str | None = None) -> str:
    """Fecha de N días atrás (incluye hoy si n=0)."""
    if desde_fecha:
        d = datetime.fromisoformat(desde_fecha).date()
    else:
        d = datetime.now().date()
    return str(d - timedelta(days=n))


def generar_reporte(lib: Libreta, dias: int = 7) -> str:
    """Genera el reporte semanal."""
    hoy_str = lib.hoy()
    hoy_dt = lib.ahora()
    hace_n = fecha_hace_n_dias(dias - 1, hoy_str)  # hace 6 días para tener 7 días incluido hoy

    lines = []
    lines.append("=" * 70)
    lines.append(f"REPORTE SEMANAL — RIELES FINANCIEROS")
    lines.append(f"Periodo: {hace_n} hasta {hoy_str} ({dias} días)")
    lines.append(f"Generado: {hoy_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    # 1. BALANCE SEMANAL
    bal = lib.balance(desde=hace_n, hasta=hoy_str)
    lines.append("📊 BALANCE SEMANAL")
    lines.append(f"  Ingresos:  ${bal['ingresos']:>10.2f}")
    lines.append(f"  Gastos:    ${bal['gastos']:>10.2f}")
    lines.append(f"  Saldo:     ${bal['saldo']:>10.2f}")
    lines.append("")

    # 2. DESGLOSE DE INGRESOS POR FUENTE
    ingresos_q = lib.con.execute(
        "SELECT fuente, SUM(monto_mxn) AS total, COUNT(*) AS n FROM ingresos "
        "WHERE fecha BETWEEN ? AND ? GROUP BY fuente ORDER BY total DESC",
        (hace_n, hoy_str),
    ).fetchall()
    if ingresos_q:
        lines.append("📈 INGRESOS POR FUENTE")
        for row in ingresos_q:
            lines.append(f"  {row[0]:<20} ${row[1]:>10.2f} ({row[2]} movs)")
        lines.append("")
    else:
        lines.append("📈 INGRESOS: sin registros esta semana")
        lines.append("")

    # 3. DESGLOSE DE GASTOS POR CATEGORÍA
    gastos_cat = lib.gastos_por_categoria(desde=hace_n, hasta=hoy_str)
    if gastos_cat:
        lines.append("💸 GASTOS POR CATEGORÍA")
        for row in gastos_cat:
            lines.append(f"  {row[0]:<20} ${row[1]:>10.2f} ({row[2]} movs)")
        lines.append("")
    else:
        lines.append("💸 GASTOS: sin registros esta semana")
        lines.append("")

    # 4. NEGOCIO DE REFRESCOS (si hay datos)
    margen = lib.margen_negocio(producto="refresco", desde=hace_n, hasta=hoy_str)
    if margen['rejas_compradas'] > 0 or margen['unidades_vendidas'] > 0:
        lines.append("🧊 NEGOCIO DE REFRESCOS (esta semana)")
        lines.append(f"  Rejas compradas:    {margen['rejas_compradas']}")
        lines.append(f"  Invertido:          ${margen['invertido']:>10.2f}")
        lines.append(f"  Unidades vendidas:  {margen['unidades_vendidas']}")
        lines.append(f"  Ingreso bruto:      ${margen['ingreso']:>10.2f}")
        lines.append(f"  Ganancia neta:      ${margen['ganancia']:>10.2f}")
        if margen['invertido'] > 0:
            roi = (margen['ganancia'] / margen['invertido']) * 100
            lines.append(f"  ROI:                {roi:>10.1f}%")
        lines.append("")

    # 5. META DE AHORRO ($100k por 31-dic-2027)
    meta_100k = lib.meta_ahorro("meta_capital_100k")
    lines.append("🎯 META DE AHORRO ($100,000 por 31-dic-2027)")
    if meta_100k:
        acumulado = meta_100k['acumulado_mxn']
        objetivo = meta_100k['objetivo_mxn'] or 100000
        piso = 90000
        lines.append(f"  Acumulado actual:   ${acumulado:>10.2f}")
        lines.append(f"  Objetivo:           ${objetivo:>10.2f}")
        lines.append(f"  Piso (minimo):      ${piso:>10.2f}")
        pct = (acumulado / objetivo * 100) if objetivo > 0 else 0
        lines.append(f"  Progreso:           {pct:>10.1f}%")
    else:
        lines.append("  [Meta no encontrada: crear con lib.meta_ahorro()]")
    lines.append("")

    # 6. DEPÓSITO OBJETIVO MENSUAL ($3,500/mes provisional, r.29)
    mes_actual = hoy_dt.strftime("%Y-%m")
    bal_mes = lib.balance(desde=f"{mes_actual}-01", hasta=hoy_str)
    deposito_objetivo = 3500
    dias_transcurridos = int(hoy_dt.day)
    deposito_prorrateado = (deposito_objetivo / 31) * dias_transcurridos
    lines.append(f"💰 DEPÓSITO MENSUAL (objetivo: ${deposito_objetivo:,.0f}/mes, r.29)")
    lines.append(f"  Días transcurridos: {dias_transcurridos}")
    lines.append(f"  Objetivo prorrateado: ${deposito_prorrateado:>10.2f}")
    lines.append(f"  Ingresos reales mes: ${bal_mes['ingresos']:>10.2f}")
    diferencia = bal_mes['ingresos'] - deposito_prorrateado
    lines.append(f"  Diferencia:         ${diferencia:>10.2f} {'✓' if diferencia >= 0 else '✗'}")
    lines.append("")

    # 7. PAGOS RECURRENTES (si hay)
    recurrentes = lib.con.execute(
        "SELECT nombre, monto_mxn, frecuencia_meses, dia_del_mes FROM pagos_recurrentes "
        "WHERE activo = 1 ORDER BY nombre"
    ).fetchall()
    if recurrentes:
        lines.append("📅 PAGOS RECURRENTES ACTIVOS")
        for r in recurrentes:
            lines.append(f"  {r[0]:<30} ${r[1]:>8.2f} (cada {r[2]}m, día {r[3]})")
        lines.append("")

    lines.append("=" * 70)
    lines.append("Reporte generado por reporte_rieles_semanales.py (F7-3, r.18)")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Reporte semanal de rieles financieros desde libreta.db"
    )
    parser.add_argument(
        "--entorno",
        choices=["real", "simulacion"],
        default="real",
        help="Entorno de la libreta (default: real)",
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=7,
        help="Número de días a reportar (default: 7)",
    )
    parser.add_argument(
        "--guardar",
        type=str,
        help="Guardar el reporte en un archivo",
    )
    args = parser.parse_args()

    try:
        with Libreta(args.entorno, solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=args.dias)
            print(reporte)

            if args.guardar:
                ruta = Path(args.guardar)
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text(reporte)
                print(f"\n✓ Reporte guardado en: {ruta}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
