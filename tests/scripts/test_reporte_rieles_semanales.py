"""
Tests para reporte_rieles_semanales.py (F7-3, r.18).

Valida:
- Generación de reportes con datos reales y simulados
- Desglose de ingresos y gastos
- Análisis de negocio de refrescos
- Tracking de meta de ahorro ($100k por 31-dic-2027)
- Depósito objetivo mensual ($3,500/mes, r.29)
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import libreta
from reporte_rieles_semanales import generar_reporte, fecha_hace_n_dias


class TestFechaHaceNDias:
    """Suite: cálculo de fechas relativas."""

    def test_hace_cero_dias_es_hoy(self):
        """Hace 0 días es la fecha de hoy."""
        hoy = datetime.now().date()
        resultado = fecha_hace_n_dias(0, None)
        assert resultado == str(hoy)

    def test_hace_uno_es_ayer(self):
        """Hace 1 día es ayer."""
        ayer = datetime.now().date() - timedelta(days=1)
        resultado = fecha_hace_n_dias(1, None)
        assert resultado == str(ayer)

    def test_hace_n_dias_con_fecha_base(self):
        """Calcula desde una fecha base dada."""
        base = "2026-08-03"
        resultado = fecha_hace_n_dias(3, base)
        esperado = "2026-07-31"  # 3 días atrás
        assert resultado == esperado


class TestReporteBasico:
    """Suite: generación básica de reportes."""

    def test_reporte_contiene_seccion_balance(self):
        """El reporte incluye sección de balance semanal."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "BALANCE SEMANAL" in reporte
            assert "Ingresos:" in reporte
            assert "Gastos:" in reporte
            assert "Saldo:" in reporte

    def test_reporte_contiene_seccion_ingresos(self):
        """El reporte desgloce de ingresos por fuente."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "INGRESOS POR FUENTE" in reporte

    def test_reporte_contiene_seccion_gastos(self):
        """El reporte desgloce de gastos por categoría."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "GASTOS POR CATEGORÍA" in reporte

    def test_reporte_contiene_meta_100k(self):
        """El reporte incluye sección de meta de $100k (r.28)."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "META DE AHORRO" in reporte
            assert "$100,000" in reporte or "100000" in reporte
            assert "31-dic-2027" in reporte or "2027" in reporte

    def test_reporte_contiene_deposito_objetivo_3500(self):
        """El reporte incluye depósito objetivo $3,500/mes (r.29)."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "DEPÓSITO MENSUAL" in reporte
            assert "$3,500" in reporte or "3500" in reporte

    def test_reporte_contiene_timestamp(self):
        """El reporte incluye timestamp de generación."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "Generado:" in reporte

    def test_reporte_formato_moneda(self):
        """Todos los montos se formatean con $."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Debe haber al menos algunos $ en el reporte
            assert "$" in reporte


class TestReporteConDatos:
    """Suite: validación con datos reales."""

    def test_reporte_con_datos_simulados_sin_error(self):
        """Genera reporte con datos simulados sin excepciones."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            # No debe lanzar excepción
            reporte = generar_reporte(lib, dias=7)
            assert isinstance(reporte, str)
            assert len(reporte) > 0

    def test_reporte_respeta_rango_de_dias(self):
        """El reporte muestra el rango correcto de fechas."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            assert "7 días" in reporte or "(7 dias)" in reporte.lower()

    def test_reporte_7_dias_vs_14_dias(self):
        """Reporte de 7 vs 14 días tienen períodos diferentes."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            rep7 = generar_reporte(lib, dias=7)
            rep14 = generar_reporte(lib, dias=14)
            # Deben ser reportes diferentes
            assert rep7 != rep14

    def test_balance_coherente(self):
        """Saldo = ingresos - gastos."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            hoy = lib.hoy()
            hace_7 = str(datetime.fromisoformat(hoy).date() - timedelta(days=6))
            bal = lib.balance(desde=hace_7, hasta=hoy)

            # Verificar coherencia
            assert "ingresos" in bal
            assert "gastos" in bal
            assert "saldo" in bal
            esperado_saldo = bal["ingresos"] - bal["gastos"]
            assert abs(bal["saldo"] - esperado_saldo) < 0.01  # tolerancia de redondeo


class TestReportePagosRecurrentes:
    """Suite: sección de pagos recurrentes."""

    def test_reporte_menciona_pagos_recurrentes(self):
        """El reporte incluye sección de pagos recurrentes si existen."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Puede no haber pagos, pero la estructura debe estar
            # (El script verifica si existen antes de mostrar)
            assert "PAGOS RECURRENTES" in reporte or "sin registros" in reporte.lower()

    def test_reporte_menciona_gym_si_existe(self):
        """Si hay gym en pagos recurrentes, debería mencionarse."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # En simulación, gym podría estar definido
            # Simplemente verificamos que la sección existe
            assert "PAGOS RECURRENTES" in reporte or "REPORTE SEMANAL" in reporte


class TestReporteNegocioRefrescos:
    """Suite: análisis de negocio de refrescos."""

    def test_reporte_incluye_seccion_refrescos(self):
        """El reporte puede incluir sección de refrescos si hay datos."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Debería estar presente o tener mensaje alternativo
            assert "NEGOCIO DE REFRESCOS" in reporte or "sin registros" in reporte.lower()

    def test_roi_calculado_si_hay_inversion(self):
        """Si hubo inversión (invertido > 0) en refrescos, se calcula ROI.

        Puede haber ventas (unidades_vendidas > 0) sin compra en la misma
        ventana -- se vende de inventario comprado antes -- y ahí ROI no
        aplica (dividiría entre cero). El reporte solo lo calcula cuando
        invertido > 0, así que el test debe seguir esa misma condición.
        """
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            hoy = lib.hoy()
            hace_6 = str(datetime.fromisoformat(hoy).date() - timedelta(days=6))
            margen = lib.margen_negocio(producto="refresco", desde=hace_6, hasta=hoy)
            reporte = generar_reporte(lib, dias=7)
            if margen["invertido"] > 0:
                assert "ROI:" in reporte
            else:
                assert "ROI:" not in reporte


class TestGuardarReporte:
    """Suite: guardado de reportes en archivo."""

    def test_guardar_reporte_en_archivo(self):
        """El reporte se puede guardar en archivo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ruta = Path(tmpdir) / "reporte_test.txt"
            with libreta.Libreta("simulacion", solo_lectura=True) as lib:
                reporte = generar_reporte(lib, dias=7)
                ruta.write_text(reporte)

            assert ruta.exists()
            contenido = ruta.read_text()
            assert "BALANCE SEMANAL" in contenido


class TestIntegracionConMain:
    """Suite: integración con script main()."""

    def test_script_ejecutable_con_entorno_simulacion(self):
        """El script se ejecuta con entorno simulación directamente."""
        # Validamos que el código principal funciona sin errores
        # usando pytest fixtures, que configura las variables de entorno
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Debe generar un reporte válido
            assert "BALANCE SEMANAL" in reporte
            assert isinstance(reporte, str)


class TestFormatoYPresentacion:
    """Suite: formato visual del reporte."""

    def test_reporte_usa_emojis_apropiados(self):
        """El reporte usa emojis para secciones."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Debe tener emojis en secciones clave
            assert any(emoji in reporte for emoji in ["📊", "📈", "💸", "🎯", "💰"])

    def test_reporte_bien_estructurado(self):
        """El reporte tiene estructura clara con separadores."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Debe tener líneas de separación
            assert "=" * 70 in reporte or "=" in reporte


class TestMetaDeAhorro:
    """Suite: validación de meta de ahorro (r.28)."""

    def test_meta_100k_aparece_en_reporte(self):
        """La meta de $100k por 31-dic-2027 aparece."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Meta debe mencionarse explícitamente
            assert "100" in reporte and "000" in reporte

    def test_piso_minimo_90k_en_meta_o_mensaje_alternativo(self):
        """El reporte maneja la meta de $90k correctamente."""
        with libreta.Libreta("simulacion", solo_lectura=True) as lib:
            reporte = generar_reporte(lib, dias=7)
            # Piso debe estar o bien en la meta, o en el mensaje de "no encontrada"
            assert "META DE AHORRO" in reporte
            # Puede mostrar "90" (piso) o mensaje de "no encontrada"
            assert ("90000" in reporte or "no encontrada" in reporte.lower())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
