"""
Tests para analizador_refrescos.py (F7-2: Ingresos refrescos).

Verifica que:
1. Se registren compras y ventas correctamente.
2. Se calcule costo unitario y margen correcto.
3. Se detecte patrón de venta realista.
4. Se proyecte ganancia sin errores.
"""

import pytest
from datetime import datetime, timedelta

from scripts.libreta import Libreta
from scripts.analizador_refrescos import AnalizadorRefrescos


@pytest.fixture
def lib_sim():
    """Libreta en entorno de simulación."""
    with Libreta("simulacion") as lib:
        # Limpiar datos previos de refrescos para test aislado
        lib.con.execute("DELETE FROM negocio_compras WHERE producto='refresco'")
        lib.con.execute("DELETE FROM negocio_ventas WHERE producto='refresco'")
        lib.con.commit()
        yield lib


def test_analizador_inicializacion(lib_sim):
    """Verificar que el analizador se inicializa con supuestos correctos."""
    analizador = AnalizadorRefrescos(lib_sim)
    assert analizador.REFRESCOS_POR_CAJA == 24
    assert analizador.COSTO_CAJA == 328.0
    assert analizador.PRECIO_UNITARIO == 20.0
    assert round(analizador.costo_unitario, 2) == 13.67
    assert round(analizador.margen_por_unidad, 2) == 6.33


def test_ganancia_por_venta_unitaria(lib_sim):
    """Verificar cálculo de ganancia por número de piezas."""
    analizador = AnalizadorRefrescos(lib_sim)
    # 1 pza: $20 - $13.67 = $6.33
    assert round(analizador.ganancia_por_venta(1), 2) == 6.33
    # 10 pzas: $6.333... × 10 = $63.33
    assert round(analizador.ganancia_por_venta(10), 2) == 63.33
    # 24 pzas (caja completa): $6.333... × 24 = $152.00
    assert round(analizador.ganancia_por_venta(24), 2) == 152.00


def test_registro_compra_y_venta(lib_sim):
    """Registrar una compra y una venta, verificar que se persisten."""
    # Comprar 1 caja
    compra_id = lib_sim.registrar_compra_negocio(328.0, "refresco", "reja", "2026-08-01")
    assert compra_id > 0

    # Vender 15 pzas
    venta_id = lib_sim.registrar_venta_negocio(15, 20.0, "refresco", "2026-08-01")
    assert venta_id > 0

    # Verificar en BD
    compra = lib_sim.con.execute(
        "SELECT * FROM negocio_compras WHERE id=?", (compra_id,)
    ).fetchone()
    assert dict(compra)['costo_mxn'] == 328.0

    venta = lib_sim.con.execute(
        "SELECT * FROM negocio_ventas WHERE id=?", (venta_id,)
    ).fetchone()
    assert dict(venta)['unidades'] == 15


def test_simulacion_30_dias_patron_realista(lib_sim):
    """Simula 30 días de venta con patrón realista."""
    # Patrón: de lunes a sábado vende entre 8 y 20 pzas, domingo descansa (Arturo descansa martes en taquería)
    # Pero en refrescos vende casi todos los días: 10-25 pzas en promedio
    analizador = AnalizadorRefrescos(lib_sim)

    inicio = datetime.strptime("2026-08-01", "%Y-%m-%d")

    # Comprar 2 cajas en la primera y tercera semana
    lib_sim.registrar_compra_negocio(328.0, "refresco", "reja", "2026-08-01")
    lib_sim.registrar_compra_negocio(328.0, "refresco", "reja", "2026-08-15")

    # Simular ventas diarias (patrón variable realista)
    patron_ventas = [
        15, 12, 18, 10, 14, 20,  # Semana 1 (lun-sab)
        0,  # Domingo descansa
        16, 11, 19, 9, 15, 22,   # Semana 2 (lun-sab)
        0,  # Domingo descansa
        14, 13, 17, 12, 16, 21,  # Semana 3 (lun-sab)
        0,  # Domingo descansa
        18, 10, 20, 8, 13, 19,   # Semana 4 (lun-sab)
        0,  # Domingo descansa
        12,  # Día 29
    ]

    for i, cantidad in enumerate(patron_ventas[:30]):
        fecha = (inicio + timedelta(days=i)).strftime("%Y-%m-%d")
        if cantidad > 0:
            lib_sim.registrar_venta_negocio(cantidad, 20.0, "refresco", fecha)

    analizador.cargar_datos("2026-08-01", "2026-08-30")

    # Verificaciones
    assert len(analizador.ventas) > 0, "Debe haber registros de venta"
    assert len(analizador.compras) == 2, "Debe haber 2 compras"

    # Estadísticas diarias
    est = analizador.estadisticas_diarias()
    assert est['dias_con_venta'] > 20, "Debe tener muchos días con venta"
    assert est['promedio_unidades'] > 10, "Promedio debe ser > 10 pzas/día"
    assert est['promedio_ganancia_diaria'] > 50, "Ganancia diaria debe ser > $50"

    # Ganancia total
    ganancia_total = analizador.ganancia_total()
    # Aproximado: si vendió ~420 pzas × $6.33 = ~$2,658, menos 2 cajas ($656) = ~$2,002
    assert ganancia_total > 1500, f"Ganancia total debe ser > $1,500, obtuvo {ganancia_total}"


def test_desglose_por_semana(lib_sim):
    """Verificar desglose correcto de ventas por semana."""
    lib_sim.registrar_venta_negocio(10, 20.0, "refresco", "2026-08-04")  # Lunes semana 32
    lib_sim.registrar_venta_negocio(15, 20.0, "refresco", "2026-08-05")  # Martes
    lib_sim.registrar_venta_negocio(12, 20.0, "refresco", "2026-08-11")  # Siguiente lunes, semana 33

    analizador = AnalizadorRefrescos(lib_sim)
    analizador.cargar_datos("2026-08-01", "2026-08-15")

    por_semana = analizador.por_semana()
    assert len(por_semana) >= 2, "Debe tener datos de múltiples semanas"
    # Semana 32 debe tener 25 pzas
    assert por_semana['2026-W32']['unidades'] == 25
    # Semana 33 debe tener 12 pzas
    assert por_semana['2026-W33']['unidades'] == 12


def test_reporte_sin_datos(lib_sim):
    """Reporte cuando no hay datos de venta."""
    analizador = AnalizadorRefrescos(lib_sim)
    reporte = analizador.reporte("2026-01-01", "2026-01-02")
    assert "Sin datos" in reporte


def test_reporte_generado_con_datos(lib_sim):
    """Verificar que el reporte se genera correctamente con datos."""
    lib_sim.registrar_compra_negocio(328.0, "refresco", "reja", "2026-08-01")
    lib_sim.registrar_venta_negocio(20, 20.0, "refresco", "2026-08-01")

    analizador = AnalizadorRefrescos(lib_sim)
    reporte = analizador.reporte("2026-08-01", "2026-08-01")

    assert "ANÁLISIS DE VENTA DE REFRESCOS" in reporte
    assert "$6.33/pza" in reporte  # Margen
    assert "20" in reporte or "20.0" in reporte  # Unidades o precio
    assert "$" in reporte  # Debe tener dinero


def test_proyeccion_mensual_y_anual(lib_sim):
    """Verificar que la proyección se calcula sin errores."""
    # Simular una semana típica: 100 pzas en 6 días
    for i in range(6):
        lib_sim.registrar_venta_negocio(17, 20.0, "refresco", f"2026-08-0{i+1}")

    analizador = AnalizadorRefrescos(lib_sim)
    analizador.cargar_datos("2026-08-01", "2026-08-10")

    est = analizador.estadisticas_diarias()
    # Debe poder proyectar sin crash
    if est['dias_con_venta'] > 0:
        proyeccion_mes = est['promedio_ganancia_diaria'] * 30
        assert proyeccion_mes > 0
        # ~17 pzas × $6.33 × 30 = ~$3,207
        assert 2000 < proyeccion_mes < 4000
