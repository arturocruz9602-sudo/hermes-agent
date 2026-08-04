"""
Tests para síntesis de voz con Piper (F11-1).
Validación: generación de audio, configuración, manejo de errores.
"""

import pytest
import wave
from pathlib import Path
from scripts.notificaciones_voz import NotificadorVoz, ConfiguracionVoz


class TestNotificadorVoz:
    """Suite de pruebas para NotificadorVoz."""

    def test_inicializacion_default(self):
        """Inicialización con config por defecto."""
        notificador = NotificadorVoz()
        assert notificador.config.modelo == "es_MX-claude-high"
        assert notificador.config.velocidad == 1.0
        assert notificador.config.volumen == 1.0

    def test_inicializacion_custom(self):
        """Inicialización con configuración personalizada."""
        config = ConfiguracionVoz(velocidad=1.5, volumen=0.8)
        notificador = NotificadorVoz(config)
        assert notificador.config.velocidad == 1.5
        assert notificador.config.volumen == 0.8

    def test_generacion_audio_basica(self):
        """Genera audio y verifica que el archivo existe."""
        notificador = NotificadorVoz()
        wav_path = notificador.generar_audio("Texto de prueba.")
        assert Path(wav_path).exists()
        assert wav_path.endswith(".wav")

    def test_alarma(self):
        """Genera alarma con claridad máxima."""
        notificador = NotificadorVoz()
        wav_path = notificador.alarma("Alarm de prueba")
        assert Path(wav_path).exists()

    def test_aviso(self):
        """Genera aviso con velocidad normal."""
        notificador = NotificadorVoz()
        wav_path = notificador.aviso("Aviso de prueba")
        assert Path(wav_path).exists()

    def test_recordatorio(self):
        """Genera recordatorio formateado."""
        notificador = NotificadorVoz()
        wav_path = notificador.recordatorio("tarea pendiente", "2 horas restantes")
        assert Path(wav_path).exists()

    def test_archivo_wav_valido(self):
        """Verifica que el archivo WAV sea válido."""
        notificador = NotificadorVoz()
        wav_path = notificador.generar_audio("Prueba de audio WAV")

        # Intenta abrir como WAV
        with wave.open(wav_path, "rb") as wf:
            assert wf.getnchannels() in (1, 2)  # Mono o estéreo
            assert wf.getframerate() > 0
            assert wf.getnframes() > 0

    def test_velocidad_rapida(self):
        """Genera audio con velocidad aumentada."""
        config = ConfiguracionVoz(velocidad=1.5)
        notificador = NotificadorVoz(config)
        wav_path = notificador.generar_audio("Texto rápido")
        assert Path(wav_path).exists()

    def test_velocidad_lenta(self):
        """Genera audio con velocidad reducida."""
        config = ConfiguracionVoz(velocidad=0.7)
        notificador = NotificadorVoz(config)
        wav_path = notificador.generar_audio("Texto lento")
        assert Path(wav_path).exists()

    def test_volumen_bajo(self):
        """Genera audio con volumen reducido."""
        config = ConfiguracionVoz(volumen=0.5)
        notificador = NotificadorVoz(config)
        wav_path = notificador.generar_audio("Volumen bajo")
        assert Path(wav_path).exists()

    def test_volumen_maximo(self):
        """Genera audio con volumen máximo."""
        config = ConfiguracionVoz(volumen=1.0)
        notificador = NotificadorVoz(config)
        wav_path = notificador.generar_audio("Volumen máximo")
        assert Path(wav_path).exists()

    def test_texto_largo(self):
        """Genera audio para texto largo (múltiples oraciones)."""
        notificador = NotificadorVoz()
        texto_largo = """Buenos días Arturo. Este es un mensaje de prueba que contiene
        múltiples oraciones para validar que Piper puede procesar textos largos
        sin problemas. La síntesis de voz debe ser clara y natural."""

        wav_path = notificador.generar_audio(texto_largo)
        assert Path(wav_path).exists()

        # Verifica que el audio es más largo que uno corto
        with wave.open(wav_path, "rb") as wf:
            frames_largo = wf.getnframes()

        wav_corto = notificador.generar_audio("Hola.")
        with wave.open(wav_corto, "rb") as wf:
            frames_corto = wf.getnframes()

        assert frames_largo > frames_corto, "Texto largo debe producir más frames"

    def test_caracteres_especiales(self):
        """Maneja caracteres especiales en el texto."""
        notificador = NotificadorVoz()
        texto = "Hola, ¿cómo estás? ¡Muy bien! Números: 123, 456."
        wav_path = notificador.generar_audio(texto)
        assert Path(wav_path).exists()

    def test_directorio_cache_se_crea(self):
        """Verifica que el directorio de caché se crea automáticamente."""
        config = ConfiguracionVoz(cache_dir="/tmp/test-piper-cache-nuevoo")
        # Asegurar que no existe previamente
        if Path(config.cache_dir).exists():
            import shutil

            shutil.rmtree(config.cache_dir)

        notificador = NotificadorVoz(config)
        assert Path(config.cache_dir).exists()

    def test_piper_no_encontrado(self):
        """Lanza excepción si Piper no está instalado."""
        config = ConfiguracionVoz(bin_piper="/ruta/inexistente/piper")
        with pytest.raises(FileNotFoundError):
            NotificadorVoz(config)


class TestIntegracionAlarmas:
    """Tests de integración con el sistema de alarmas."""

    def test_alarma_diaria_diaria(self):
        """Simula alarma diaria: despertar a las 6:00."""
        notificador = NotificadorVoz()
        wav_path = notificador.alarma(
            "Son las seis de la mañana. Hora de levantarse para la escuela."
        )
        assert Path(wav_path).exists()

    def test_recordatorio_entrega(self):
        """Recordatorio de entrega de tarea con tiempo restante."""
        notificador = NotificadorVoz()
        wav_path = notificador.recordatorio(
            "tienes una entrega pendiente de Tecnologías de Información",
            "Faltan 4 horas para la fecha límite.",
        )
        assert Path(wav_path).exists()

    def test_aviso_pago(self):
        """Aviso de fecha de pago."""
        notificador = NotificadorVoz()
        wav_path = notificador.aviso(
            "Recordatorio: mañana es día de pago. Verifica tu depósito."
        )
        assert Path(wav_path).exists()

    def test_aviso_gym(self):
        """Recordatorio de asistencia al gym."""
        notificador = NotificadorVoz()
        wav_path = notificador.recordatorio(
            "aún no has ido al gym", "Se recomienda ir antes de las 18:00."
        )
        assert Path(wav_path).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
