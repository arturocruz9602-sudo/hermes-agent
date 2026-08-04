"""
Integración de NotificadorVoz con el sistema de alertas de cola_v2.

Proporciona notificadores que:
1. Generan audio local con Piper (voz es_MX)
2. Se adaptan a la interfaz de cola_v2 (Callable[[chat_id, texto], None])
3. En producción, envían notificaciones Telegram + audio a iPhone

F11-1: Voz local interina mientras llega Mac Mini.
Respuesta 99: Alarmas/alertas que vibren el iPhone como llamada.
"""

import sys
from pathlib import Path
from typing import Callable, Optional

# Allow imports from scripts directory
sys.path.insert(0, str(Path(__file__).parent))

from notificaciones_voz import NotificadorVoz, ConfiguracionVoz


class NotificadorVozTelegram:
    """
    Notificador que combina síntesis de voz + envío Telegram.
    Adaptador para cola_v2.
    """

    def __init__(
        self,
        config_voz: Optional[ConfiguracionVoz] = None,
        telegram_send: Optional[Callable[[str, str], None]] = None,
        telegram_send_audio: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Args:
            config_voz: Configuración de Piper (velocidad, volumen, etc.)
            telegram_send: Función para enviar texto a Telegram.
                          Firma: send(chat_id: str, text: str) -> None
            telegram_send_audio: Función para enviar audio a Telegram.
                                Firma: send_audio(chat_id: str, audio_path: str) -> None
        """
        self.notificador_voz = NotificadorVoz(config_voz)
        self.telegram_send = telegram_send or self._dummy_send
        self.telegram_send_audio = telegram_send_audio or self._dummy_send_audio

    @staticmethod
    def _dummy_send(chat_id: str, text: str):
        """Placeholder para entorno de lab (sin Telegram real)."""
        print(f"[TELEGRAM-TEXT] {chat_id}: {text}")

    @staticmethod
    def _dummy_send_audio(chat_id: str, audio_path: str):
        """Placeholder para entorno de lab (sin Telegram real)."""
        print(f"[TELEGRAM-AUDIO] {chat_id}: {audio_path}")

    def __call__(self, chat_id: str, texto: str) -> None:
        """
        Interfaz para cola_v2: Callable[[str, str], None].
        Genera audio + envía notificación a Telegram.
        """
        try:
            # Genera audio local (Piper es_MX)
            wav_path = self.notificador_voz.aviso(texto)

            # Envía texto a Telegram
            self.telegram_send(chat_id, texto)

            # Envía audio a Telegram (o descarta en lab)
            if Path(wav_path).exists():
                self.telegram_send_audio(chat_id, wav_path)

        except Exception as e:
            # Fallback: envía solo texto si audio falla
            print(f"[ERROR AUDIO] {e}")
            self.telegram_send(chat_id, f"⚠️ {texto}")


class NotificadorAlarmaVoz:
    """
    Notificador especializado para alarmas.
    Uso: recordatorios urgentes, cambios de horario, alertas de pago.
    """

    def __init__(
        self,
        config_voz: Optional[ConfiguracionVoz] = None,
        telegram_send_audio: Optional[Callable[[str, str], None]] = None,
    ):
        self.notificador_voz = NotificadorVoz(config_voz)
        self.telegram_send_audio = telegram_send_audio or self._dummy_send_audio

    @staticmethod
    def _dummy_send_audio(chat_id: str, audio_path: str):
        """Placeholder para lab."""
        print(f"[ALARMA-AUDIO] {chat_id}: {audio_path}")

    def __call__(self, chat_id: str, texto: str) -> None:
        """
        Crea alarma hablada (velocidad lenta, volumen alto).
        Interfaz para cola_v2.
        """
        try:
            # Genera alarma (máxima claridad)
            wav_path = self.notificador_voz.alarma(texto)

            # Envía audio con prioridad de notificación urgente
            self.telegram_send_audio(chat_id, wav_path)

        except Exception as e:
            print(f"[ERROR ALARMA] {e}")


class NotificadorRecordatorioVoz:
    """
    Notificador para recordatorios con tiempo restante.
    Uso: "Te quedan 2 horas para la entrega", "Aún no has ido al gym".
    """

    def __init__(
        self,
        config_voz: Optional[ConfiguracionVoz] = None,
        telegram_send: Optional[Callable[[str, str], None]] = None,
    ):
        self.notificador_voz = NotificadorVoz(config_voz)
        self.telegram_send = telegram_send or self._dummy_send

    @staticmethod
    def _dummy_send(chat_id: str, text: str):
        """Placeholder para lab."""
        print(f"[RECORDATORIO-VOICE] {chat_id}: {text}")

    def __call__(self, chat_id: str, texto_recordatorio: str) -> None:
        """
        Genera recordatorio: formato "Tarea pendiente: XX. Tiempo: YY."
        Interfaz para cola_v2.
        """
        try:
            # Genera audio con velocidad normal
            wav_path = self.notificador_voz.recordatorio(
                tarea="recordatorio", tiempo_restante=texto_recordatorio
            )

            # Envía texto a Telegram
            self.telegram_send(chat_id, texto_recordatorio)

        except Exception as e:
            print(f"[ERROR RECORDATORIO] {e}")


# Factory functions para uso simple

def notificador_voz_simple() -> Callable[[str, str], None]:
    """
    Retorna un notificador listo para usar con cola_v2.
    Uso: cola.procesar_pendientes(notificador=notificador_voz_simple())
    """
    return NotificadorVozTelegram()


def notificador_alarma_simple() -> Callable[[str, str], None]:
    """
    Retorna notificador de alarmas.
    """
    return NotificadorAlarmaVoz()


def notificador_recordatorio_simple() -> Callable[[str, str], None]:
    """
    Retorna notificador de recordatorios.
    """
    return NotificadorRecordatorioVoz()


if __name__ == "__main__":
    # Demo: simular notificación en cola_v2

    # 1. Notificador simple
    notif = notificador_voz_simple()
    print("=== Test 1: Notificador simple ===")
    notif("8727618189", "Recordatorio: falta reportar los ingresos de la taquería.")

    # 2. Alarma
    alarma = notificador_alarma_simple()
    print("\n=== Test 2: Alarma ===")
    alarma("8727618189", "Es hora de levantarse para la escuela.")

    # 3. Recordatorio
    recordatorio = notificador_recordatorio_simple()
    print("\n=== Test 3: Recordatorio ===")
    recordatorio("8727618189", "Faltan 4 horas para tu clase de Algoritmos.")

    print("\n✅ Demo completado. Los notificadores están listos para cola_v2.")
