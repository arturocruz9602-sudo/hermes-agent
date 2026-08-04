#!/usr/bin/env python3
"""
Síntesis de voz local con Piper (es_MX) para alarmas y avisos hablados.
Reemplaza Gemini Live con TTS CPU-bound, funcional en HP mientras llega Mac Mini.

Fase: F11-1 / OT-11 / B5 · Respuesta 99 del cuestionario.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfiguracionVoz:
    """Configuración de síntesis de voz."""
    modelo: str = "es_MX-claude-high"
    velocidad: float = 1.0  # 1.0 = normal, <1.0 = lento, >1.0 = rápido
    volumen: float = 1.0  # 0.0-1.0
    cache_dir: str = "/tmp/piper-audio"
    piper_dir: str = "/home/arturo/.hermes/piper-voices"
    bin_piper: str = "/home/arturo/.hermes/hermes-agent/venv/bin/piper"


class NotificadorVoz:
    """Genera y reproduce notificaciones de voz para alarmas y avisos."""

    def __init__(self, config: Optional[ConfiguracionVoz] = None):
        self.config = config or ConfiguracionVoz()
        self._validar_piper()
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)

    def _validar_piper(self):
        """Verifica que Piper esté disponible."""
        if not Path(self.config.bin_piper).exists():
            raise FileNotFoundError(f"Piper no encontrado: {self.config.bin_piper}")

        modelo_path = Path(self.config.piper_dir) / f"{self.config.modelo}.onnx"
        if not modelo_path.exists():
            raise FileNotFoundError(f"Modelo no encontrado: {modelo_path}")

    def generar_audio(self, texto: str) -> str:
        """
        Genera archivo WAV a partir de texto.
        Retorna ruta al archivo generado.
        """
        modelo_path = Path(self.config.piper_dir) / f"{self.config.modelo}.onnx"

        try:
            result = subprocess.run(
                [
                    self.config.bin_piper,
                    "--model",
                    str(modelo_path),
                    "--output-dir",
                    self.config.cache_dir,
                    "--output-dir-naming",
                    "timestamp",
                    "--length-scale",
                    str(1.0 / self.config.velocidad),
                    "--volume",
                    str(self.config.volumen),
                ],
                input=texto.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Piper falló: {result.stderr.decode('utf-8', errors='ignore')}"
                )

            # Extrae ruta del output del stderr (INFO:__main__:Wrote /path/to/file.wav)
            stderr_text = result.stderr.decode("utf-8", errors="ignore")
            for line in stderr_text.split("\n"):
                if "Wrote" in line:
                    # Formato: INFO:__main__:Wrote /tmp/123456789.wav
                    partes = line.split("Wrote ")
                    if len(partes) > 1:
                        return partes[1].strip()

            raise RuntimeError(
                "No se pudo extraer ruta del archivo de salida de Piper"
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Piper tardó demasiado (timeout 30s)")

    def alarma(self, texto: str) -> str:
        """
        Crea alarma hablada.
        En iPhone: notificación con vibración de llamada.
        En lab: solo genera WAV.
        """
        # Garantiza claridad máxima para alarmas
        config_alarma = ConfiguracionVoz(
            **{
                **vars(self.config),
                "velocidad": 0.9,  # Ligeramente lento para claridad
                "volumen": 1.0,  # Volumen máximo
            }
        )
        notificador_alarma = NotificadorVoz(config_alarma)
        return notificador_alarma.generar_audio(texto)

    def aviso(self, texto: str) -> str:
        """
        Crea aviso hablado (velocidad normal).
        Ejemplo: recordatorio de tarea, pendiente de captura espontánea.
        """
        return self.generar_audio(texto)

    def recordatorio(self, tarea: str, tiempo_restante: str) -> str:
        """
        Recordatorio para tareas pendientes.
        Ejemplo: "Recordatorio: aún no has reportado ir al gym. Faltan 2 horas."
        """
        texto = f"Recordatorio: {tarea}. {tiempo_restante}."
        return self.aviso(texto)


if __name__ == "__main__":
    # Prueba básica
    notificador = NotificadorVoz()

    # Test 1: Alarma simple
    print("Generando alarma...")
    wav_alarma = notificador.alarma("Buenos días Arturo. Es hora de levantarse.")
    print(f"✓ Alarma generada: {wav_alarma}")
    assert Path(wav_alarma).exists(), "Archivo no existe"

    # Test 2: Aviso
    print("Generando aviso...")
    wav_aviso = notificador.aviso(
        "Tienes una reunión en 30 minutos con el equipo de trading."
    )
    print(f"✓ Aviso generado: {wav_aviso}")
    assert Path(wav_aviso).exists(), "Archivo no existe"

    # Test 3: Recordatorio
    print("Generando recordatorio...")
    wav_recordatorio = notificador.recordatorio(
        "aún no has registrado tus ingresos de la taquería", "Faltan 4 horas para cierre."
    )
    print(f"✓ Recordatorio generado: {wav_recordatorio}")
    assert Path(wav_recordatorio).exists(), "Archivo no existe"

    # Test 4: Cambio de configuración (velocidad)
    print("Probando diferentes velocidades...")
    config_rapida = ConfiguracionVoz(velocidad=1.3)
    notificador_rapida = NotificadorVoz(config_rapida)
    wav_rapida = notificador_rapida.aviso("Mensaje rápido.")
    print(f"✓ Voz rápida: {wav_rapida}")

    config_lenta = ConfiguracionVoz(velocidad=0.7)
    notificador_lenta = NotificadorVoz(config_lenta)
    wav_lenta = notificador_lenta.aviso("Mensaje lento.")
    print(f"✓ Voz lenta: {wav_lenta}")

    print("\n✅ Todos los tests pasaron.")
    print(f"Archivos en: {notificador.config.cache_dir}")
