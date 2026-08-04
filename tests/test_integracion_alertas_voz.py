"""
Tests para integración de NotificadorVoz con cola_v2 (F11-1).
Valida: adaptadores Telegram, interfaces Callable, manejo de errores.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from scripts.integracion_alertas_voz import (
    NotificadorVozTelegram,
    NotificadorAlarmaVoz,
    NotificadorRecordatorioVoz,
    notificador_voz_simple,
    notificador_alarma_simple,
    notificador_recordatorio_simple,
)


class TestNotificadorVozTelegram:
    """Suite de pruebas para NotificadorVozTelegram."""

    def test_inicializacion_default(self):
        """Inicialización con valores por defecto."""
        notif = NotificadorVozTelegram()
        assert notif.notificador_voz is not None
        assert notif.telegram_send is not None
        assert notif.telegram_send_audio is not None

    def test_inicializacion_custom(self):
        """Inicialización con funciones Telegram personalizadas."""
        mock_send = Mock()
        mock_send_audio = Mock()
        notif = NotificadorVozTelegram(
            telegram_send=mock_send,
            telegram_send_audio=mock_send_audio
        )
        assert notif.telegram_send is mock_send
        assert notif.telegram_send_audio is mock_send_audio

    def test_callable_interface(self):
        """Verificar que el notificador implementa Callable[[str, str], None]."""
        notif = NotificadorVozTelegram()
        assert callable(notif)

    def test_notificacion_simple(self):
        """Envía notificación: texto + audio."""
        mock_send = Mock()
        mock_send_audio = Mock()
        notif = NotificadorVozTelegram(
            telegram_send=mock_send,
            telegram_send_audio=mock_send_audio
        )

        chat_id = "8727618189"
        texto = "Test de notificación"

        notif(chat_id, texto)

        # Verifica que se llamó telegram_send
        mock_send.assert_called_once_with(chat_id, texto)
        # Verifica que se intentó enviar audio
        mock_send_audio.assert_called_once()
        call_args = mock_send_audio.call_args
        assert call_args[0][0] == chat_id

    def test_fallback_si_audio_falla(self):
        """Si la síntesis falla, envía solo texto."""
        mock_send = Mock()
        mock_send_audio = Mock()

        # Simular que la síntesis de voz falla
        with patch('scripts.integracion_alertas_voz.NotificadorVoz') as MockNotificador:
            mock_notif_instance = Mock()
            mock_notif_instance.aviso.side_effect = RuntimeError("Piper error")
            MockNotificador.return_value = mock_notif_instance

            notif = NotificadorVozTelegram(
                telegram_send=mock_send,
                telegram_send_audio=mock_send_audio
            )

            chat_id = "8727618189"
            texto = "Test fallback"

            # No debe lanzar excepción
            notif(chat_id, texto)

            # Debe haber intentado enviar el texto con advertencia
            mock_send.assert_called()

    def test_dummy_send_en_lab(self):
        """Verifica dummy_send imprime en lab."""
        notif = NotificadorVozTelegram()

        with patch('builtins.print') as mock_print:
            notif._dummy_send("123", "Hello")
            mock_print.assert_called_with("[TELEGRAM-TEXT] 123: Hello")

    def test_dummy_send_audio_en_lab(self):
        """Verifica dummy_send_audio imprime en lab."""
        notif = NotificadorVozTelegram()

        with patch('builtins.print') as mock_print:
            notif._dummy_send_audio("123", "/path/to/audio.wav")
            mock_print.assert_called_with("[TELEGRAM-AUDIO] 123: /path/to/audio.wav")


class TestNotificadorAlarmaVoz:
    """Suite de pruebas para NotificadorAlarmaVoz."""

    def test_inicializacion_default(self):
        """Inicialización con valores por defecto."""
        alarma = NotificadorAlarmaVoz()
        assert alarma.notificador_voz is not None
        assert alarma.telegram_send_audio is not None

    def test_inicializacion_custom(self):
        """Inicialización con función personalizada."""
        mock_send_audio = Mock()
        alarma = NotificadorAlarmaVoz(telegram_send_audio=mock_send_audio)
        assert alarma.telegram_send_audio is mock_send_audio

    def test_callable_interface(self):
        """Verifica que implementa Callable."""
        alarma = NotificadorAlarmaVoz()
        assert callable(alarma)

    def test_genera_alarma(self):
        """Genera alarma y envía audio."""
        mock_send_audio = Mock()
        alarma = NotificadorAlarmaVoz(telegram_send_audio=mock_send_audio)

        chat_id = "8727618189"
        texto = "Hora de levantarse"

        alarma(chat_id, texto)

        # Debe haber llamado telegram_send_audio
        mock_send_audio.assert_called_once()
        assert mock_send_audio.call_args[0][0] == chat_id

    def test_manejo_error_alarma(self):
        """Maneja error en generación de alarma."""
        mock_send_audio = Mock()

        with patch('scripts.integracion_alertas_voz.NotificadorVoz') as MockNotificador:
            mock_notif_instance = Mock()
            mock_notif_instance.alarma.side_effect = RuntimeError("Piper error")
            MockNotificador.return_value = mock_notif_instance

            alarma = NotificadorAlarmaVoz(telegram_send_audio=mock_send_audio)

            with patch('builtins.print') as mock_print:
                alarma("123", "Error test")
                # Debe imprimir error, no lanzar excepción
                mock_print.assert_called()


class TestNotificadorRecordatorioVoz:
    """Suite de pruebas para NotificadorRecordatorioVoz."""

    def test_inicializacion_default(self):
        """Inicialización con valores por defecto."""
        record = NotificadorRecordatorioVoz()
        assert record.notificador_voz is not None
        assert record.telegram_send is not None

    def test_inicializacion_custom(self):
        """Inicialización con función personalizada."""
        mock_send = Mock()
        record = NotificadorRecordatorioVoz(telegram_send=mock_send)
        assert record.telegram_send is mock_send

    def test_callable_interface(self):
        """Verifica que implementa Callable."""
        record = NotificadorRecordatorioVoz()
        assert callable(record)

    def test_genera_recordatorio(self):
        """Genera recordatorio y envía texto."""
        mock_send = Mock()
        record = NotificadorRecordatorioVoz(telegram_send=mock_send)

        chat_id = "8727618189"
        texto = "Faltan 4 horas para la entrega"

        record(chat_id, texto)

        # Debe haber llamado telegram_send
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == chat_id

    def test_manejo_error_recordatorio(self):
        """Maneja error en recordatorio."""
        mock_send = Mock()

        with patch('scripts.integracion_alertas_voz.NotificadorVoz') as MockNotificador:
            mock_notif_instance = Mock()
            mock_notif_instance.recordatorio.side_effect = RuntimeError("Piper error")
            MockNotificador.return_value = mock_notif_instance

            record = NotificadorRecordatorioVoz(telegram_send=mock_send)

            with patch('builtins.print') as mock_print:
                record("123", "Error test")
                # Debe imprimir error, no lanzar excepción
                mock_print.assert_called()


class TestFactoryFunctions:
    """Tests para factory functions."""

    def test_notificador_voz_simple(self):
        """Factory retorna notificador simple."""
        notif = notificador_voz_simple()
        assert callable(notif)
        assert isinstance(notif, NotificadorVozTelegram)

    def test_notificador_alarma_simple(self):
        """Factory retorna notificador de alarmas."""
        alarma = notificador_alarma_simple()
        assert callable(alarma)
        assert isinstance(alarma, NotificadorAlarmaVoz)

    def test_notificador_recordatorio_simple(self):
        """Factory retorna notificador de recordatorios."""
        record = notificador_recordatorio_simple()
        assert callable(record)
        assert isinstance(record, NotificadorRecordatorioVoz)


class TestIntegracionCola:
    """Tests de integración con cola_v2."""

    def test_notificador_como_callback_cola(self):
        """Notificador funciona como callback de cola_v2."""
        mock_send = Mock()
        mock_send_audio = Mock()

        notif = NotificadorVozTelegram(
            telegram_send=mock_send,
            telegram_send_audio=mock_send_audio
        )

        # Simula cómo cola_v2 usaría el notificador
        callback = notif
        callback("8727618189", "Tarea completada")

        mock_send.assert_called()

    def test_alarma_como_callback_cola(self):
        """Notificador de alarma funciona como callback."""
        mock_send_audio = Mock()

        alarma = NotificadorAlarmaVoz(telegram_send_audio=mock_send_audio)

        # Simula cómo cola_v2 usaría la alarma
        callback = alarma
        callback("8727618189", "Alarma urgente")

        mock_send_audio.assert_called()

    def test_recordatorio_como_callback_cola(self):
        """Notificador de recordatorio funciona como callback."""
        mock_send = Mock()

        record = NotificadorRecordatorioVoz(telegram_send=mock_send)

        # Simula cómo cola_v2 usaría el recordatorio
        callback = record
        callback("8727618189", "Recordatorio de tarea")

        mock_send.assert_called()


class TestCasosRealesF11:
    """Tests con casos de uso reales de Hermes."""

    def test_recordatorio_reporte_ingresos_taqueria(self):
        """Caso real: recordatorio de reportar ingresos."""
        mock_send = Mock()
        notif = NotificadorVozTelegram(telegram_send=mock_send)

        notif("8727618189", "Recordatorio: falta reportar los ingresos de la taquería.")

        mock_send.assert_called()

    def test_alarma_escuela_manana(self):
        """Caso real: alarma para ir a la escuela."""
        mock_send_audio = Mock()
        alarma = NotificadorAlarmaVoz(telegram_send_audio=mock_send_audio)

        alarma("8727618189", "Es hora de levantarse para la escuela.")

        mock_send_audio.assert_called()

    def test_recordatorio_clase_algoritmos(self):
        """Caso real: recordatorio de clase de Algoritmos."""
        mock_send = Mock()
        record = NotificadorRecordatorioVoz(telegram_send=mock_send)

        record("8727618189", "Faltan 4 horas para tu clase de Algoritmos.")

        mock_send.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
