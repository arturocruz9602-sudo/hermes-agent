#!/usr/bin/env python3
"""
analizador_refrescos.py — Detecta patrón real de venta y ganancia en refrescos.

Arturo r.16: "Ese ingreso varía y aún no he detectado un patrón ni cálculos
de cuánto se gana ahí."

Este analizador:
1. Lee las compras de refrescos (cajas a $328 c/24 pzas).
2. Lee las ventas de refrescos (unidades individuales a $20 c/u).
3. Calcula ganancia neta = (precio_venta - costo_unitario) × unidades_vendidas.
4. Detecta patrón: promedio diario, desviación, mejor/peor día, pico semanal.
5. Proyecta rentabilidad mensual/anual basada en el patrón observado.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from collections import defaultdict

from scripts.libreta import Libreta


class AnalizadorRefrescos:
    """Analiza ventas de refrescos y detecta patrón de rentabilidad."""

    # Supuestos fijos (r.16)
    REFRESCOS_POR_CAJA = 24
    COSTO_CAJA = 328.0  # MXN, sube anualmente pero asumimos fijo para este análisis
    PRECIO_UNITARIO = 20.0  # MXN

    def __init__(self, libreta: Libreta):
        self.lib = libreta
        self.compras = []
        self.ventas = []
        self.costo_unitario = self.COSTO_CAJA / self.REFRESCOS_POR_CAJA
        self.margen_por_unidad = self.PRECIO_UNITARIO - self.costo_unitario

    def cargar_datos(self, desde: str | None = None, hasta: str | None = None) -> None:
        """Carga compras y ventas de refrescos del período."""
        desde = desde or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        hasta = hasta or datetime.now().strftime("%Y-%m-%d")

        # Compras
        cur = self.lib.con.execute(
            "SELECT fecha, costo_mxn, unidad, nota FROM negocio_compras "
            "WHERE producto='refresco' AND fecha BETWEEN ? AND ? ORDER BY fecha",
            (desde, hasta),
        )
        self.compras = [dict(row) for row in cur.fetchall()]

        # Ventas
        cur = self.lib.con.execute(
            "SELECT fecha, unidades, nota FROM negocio_ventas "
            "WHERE producto='refresco' AND fecha BETWEEN ? AND ? ORDER BY fecha",
            (desde, hasta),
        )
        self.ventas = [dict(row) for row in cur.fetchall()]

    def ganancia_por_venta(self, unidades: int) -> float:
        """Ganancia neta de N refrescos vendidos."""
        return self.margen_por_unidad * unidades

    def ganancia_total(self) -> float:
        """Total de ganancias en el período (ventas menos costo de compras)."""
        venta_bruta = sum(v['unidades'] * self.PRECIO_UNITARIO for v in self.ventas)
        costo_compras = sum(c['costo_mxn'] for c in self.compras)
        return venta_bruta - costo_compras

    def por_dia(self) -> dict[str, dict]:
        """Ventas agrupadas por día (fecha)."""
        por_dia = defaultdict(lambda: {"unidades": 0, "ganancia": 0.0})
        for v in self.ventas:
            unidades = v['unidades']
            por_dia[v['fecha']]['unidades'] += unidades
            por_dia[v['fecha']]['ganancia'] += self.ganancia_por_venta(unidades)
        return dict(por_dia)

    def estadisticas_diarias(self) -> dict:
        """Media, desv.est, min, max de unidades/día."""
        por_dia = self.por_dia()
        if not por_dia:
            return {
                "dias_con_venta": 0, "total_dias": 0,
                "promedio_unidades": 0.0, "desv_est_unidades": 0.0,
                "minimo_unidades": 0, "maximo_unidades": 0,
                "promedio_ganancia_diaria": 0.0,
            }

        valores = [d['unidades'] for d in por_dia.values()]
        ganancias = [d['ganancia'] for d in por_dia.values()]

        return {
            "dias_con_venta": len(por_dia),
            "total_dias": len(por_dia),
            "promedio_unidades": round(mean(valores), 1) if valores else 0,
            "desv_est_unidades": round(stdev(valores), 1) if len(valores) > 1 else 0,
            "minimo_unidades": min(valores) if valores else 0,
            "maximo_unidades": max(valores) if valores else 0,
            "promedio_ganancia_diaria": round(mean(ganancias), 2) if ganancias else 0.0,
        }

    def por_semana(self) -> dict[str, dict]:
        """Ventas agrupadas por semana (año-semana)."""
        por_semana = defaultdict(lambda: {"unidades": 0, "ganancia": 0.0, "dias": set()})
        for v in self.ventas:
            fecha_obj = datetime.strptime(v['fecha'], "%Y-%m-%d")
            semana_iso = fecha_obj.strftime("%Y-W%V")
            unidades = v['unidades']
            por_semana[semana_iso]['unidades'] += unidades
            por_semana[semana_iso]['ganancia'] += self.ganancia_por_venta(unidades)
            por_semana[semana_iso]['dias'].add(v['fecha'])

        # Convertir set a count
        return {
            k: {
                "unidades": v['unidades'],
                "ganancia": round(v['ganancia'], 2),
                "dias_activos": len(v['dias']),
            }
            for k, v in sorted(por_semana.items())
        }

    def reporte(self, desde: str | None = None, hasta: str | None = None) -> str:
        """Reporte legible del patrón y rentabilidad de refrescos."""
        self.cargar_datos(desde, hasta)

        if not self.ventas:
            return "Sin datos de venta de refrescos en este período."

        est = self.estadisticas_diarias()
        semanas = self.por_semana()
        ganancia_total = self.ganancia_total()

        # Construir reporte
        lineas = [
            "╔═══════════════════════════════════════════════════════════╗",
            "║        ANÁLISIS DE VENTA DE REFRESCOS (F7-2)             ║",
            "╚═══════════════════════════════════════════════════════════╝",
            "",
            f"Período: {desde or 'últimos 30 días'} a {hasta or 'hoy'}",
            f"Costo unitario: ${self.costo_unitario:.2f} (caja ${self.COSTO_CAJA}/24 pzas)",
            f"Precio venta: ${self.PRECIO_UNITARIO:.2f}/pza",
            f"Margen: ${self.margen_por_unidad:.2f}/pza ({self.margen_por_unidad/self.PRECIO_UNITARIO*100:.1f}%)",
            "",
            "📊 ESTADÍSTICAS DIARIAS:",
            f"  • Días con venta: {est['dias_con_venta']}",
            f"  • Promedio: {est['promedio_unidades']:.1f} pzas/día",
            f"  • Desviación: ±{est['desv_est_unidades']:.1f}",
            f"  • Rango: {est['minimo_unidades']}–{est['maximo_unidades']} pzas",
            f"  • Ganancia promedio diaria: ${est['promedio_ganancia_diaria']:.2f}",
            "",
            "📈 DESGLOSE POR SEMANA:",
        ]

        for semana, datos in semanas.items():
            lineas.append(
                f"  {semana}: {datos['unidades']} pzas "
                f"({datos['dias_activos']} días activos) → ${datos['ganancia']:.2f}"
            )

        lineas.extend([
            "",
            "💰 RENTABILIDAD TOTAL:",
            f"  • Ganancia neta: ${ganancia_total:.2f}",
            f"  • Unidades vendidas: {sum(v['unidades'] for v in self.ventas)}",
            f"  • Cajas compradas: {len(self.compras)}",
            "",
            "🎯 PROYECCIÓN (si continúa el patrón):",
        ])

        if est['dias_con_venta'] > 0:
            dias_mes = 30
            proyeccion_mes = est['promedio_ganancia_diaria'] * dias_mes
            proyeccion_ano = proyeccion_mes * 12
            lineas.extend([
                f"  • Mes (30 días): ${proyeccion_mes:.2f}",
                f"  • Año (12 meses): ${proyeccion_ano:.2f}",
            ])

        lineas.append("")
        return "\n".join(lineas)


def main():
    """Ejemplo de uso."""
    with Libreta("simulacion") as lib:
        analizador = AnalizadorRefrescos(lib)
        print(analizador.reporte())


if __name__ == "__main__":
    main()
