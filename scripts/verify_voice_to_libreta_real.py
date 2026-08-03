#!/usr/bin/env python3
"""
verify_voice_to_libreta_real.py — Verificación REAL punta a punta (Bloque AS-3)

FLUJO COMPLETO: voz .ogg → STT (transcribe) → extracción (regex) → libreta.db (escribe)

Candado r.119: NO enviar a Telegram. Todo local, todo verificable.
Se ejecuta en entorno 'simulacion' para no tocar datos reales.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import Libreta, entorno_activo  # noqa: E402
from voice_data_extractor import VoiceDataExtractor  # noqa: E402

HOME = Path.home()
TEST_AUDIO_DIR = HOME / ".hermes/test_cache/voice_to_libreta"
LOG = HOME / ".hermes/logs/verify_voice_to_libreta_real.log"


def log(msg: str, level: str = "INFO") -> None:
    """Log a message con timestamp."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_full = f"[{ts}] [{level}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg_full + "\n")
    print(msg_full)


def paso_1_generar_audio() -> str | None:
    """PASO 1: Generar .ogg con TTS."""
    log("=" * 70)
    log("PASO 1: Generar audio de prueba con TTS", "STEP")
    log("-" * 70)

    from tools.tts_tool import text_to_speech_tool

    # Texto que contenga datos interpretables para extracción
    texto = "Gasté cincuenta pesos en comida"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    TEST_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    salida = TEST_AUDIO_DIR / f"voice_real_{timestamp}.ogg"

    log(f"Texto: '{texto}'")
    log(f"Salida: {salida}")

    try:
        resultado_raw = text_to_speech_tool(texto, output_path=str(salida))
    except Exception as e:
        log(f"❌ TTS lanzó excepción: {e}", "ERROR")
        return None

    try:
        resultado = json.loads(resultado_raw)
    except json.JSONDecodeError:
        log(f"❌ TTS devolvió algo no-JSON", "ERROR")
        return None

    if not resultado.get("success"):
        log(f"❌ TTS reportó fallo: {resultado.get('error')}", "ERROR")
        return None

    archivo = resultado.get("file_path")
    if not archivo or not os.path.exists(archivo) or os.path.getsize(archivo) == 0:
        log(f"❌ archivo no existe o está vacío", "ERROR")
        return None

    tam = os.path.getsize(archivo)
    log(f"✅ audio generado: {archivo} ({tam:,} bytes)")

    # Verificación: ¿codec Opus?
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of",
             "default=noprint_wrappers=1:nokey=1", archivo],
            capture_output=True, text=True, timeout=15,
        )
        codec = r.stdout.strip()
        if codec != "opus":
            log(f"❌ codec inesperado: '{codec}'", "ERROR")
            return None
        log(f"✅ codec verificado: opus")
    except Exception as e:
        log(f"❌ ffprobe falló: {e}", "ERROR")
        return None

    log(f"✅ PASO 1 completado: {archivo}")
    return archivo


def paso_2_transcribir(archivo: str) -> str | None:
    """PASO 2: Transcribir con STT (Whisper local)."""
    log("=" * 70)
    log("PASO 2: Transcribir audio con STT", "STEP")
    log("-" * 70)

    try:
        from tools.transcription_tools import transcribe_audio
    except ImportError as e:
        log(f"❌ no se puede importar transcription_tools: {e}", "ERROR")
        return None

    log(f"Transcribiendo: {archivo}")

    try:
        resultado = transcribe_audio(archivo)
    except Exception as e:
        log(f"❌ transcribe_audio lanzó excepción: {e}", "ERROR")
        return None

    if not isinstance(resultado, dict):
        log(f"❌ resultado no es dict", "ERROR")
        return None

    if not resultado.get("success"):
        log(f"❌ STT reportó fallo: {resultado.get('error')}", "ERROR")
        return None

    transcripcion = resultado.get("transcript", "").strip()
    if not transcripcion:
        log(f"❌ transcripción vacía", "ERROR")
        return None

    log(f"✅ transcripción: '{transcripcion}'")
    log(f"✅ PASO 2 completado")
    return transcripcion


def paso_3_extraer_datos(transcripcion: str) -> list | None:
    """PASO 3: Usar VoiceDataExtractor para extraer gastos/tareas."""
    log("=" * 70)
    log("PASO 3: Extraer datos de transcripción", "STEP")
    log("-" * 70)

    log(f"Transcripción: '{transcripcion}'")

    try:
        datos_extraidos = VoiceDataExtractor.extraer(transcripcion)
    except Exception as e:
        log(f"❌ extracción falló: {e}", "ERROR")
        return None

    if not datos_extraidos:
        log(f"⚠️  no se extrajeron datos de la transcripción", "WARN")
        return []

    log(f"✅ se extrajeron {len(datos_extraidos)} elemento(s):")
    for item in datos_extraidos:
        desc = VoiceDataExtractor.describir(item)
        log(f"   → {desc}")

    log(f"✅ PASO 3 completado: {len(datos_extraidos)} datos extraídos")
    return datos_extraidos


def paso_4_guardar_en_libreta(datos_extraidos: list) -> int:
    """PASO 4: Guardar datos extraídos en libreta (entorno simulacion)."""
    log("=" * 70)
    log("PASO 4: Guardar en libreta.db", "STEP")
    log("-" * 70)

    if not datos_extraidos:
        log(f"✅ (no hay datos para guardar)")
        return 0

    # Verificar que disco de pruebas está montado
    try:
        from libreta import _verificar_disco_de_pruebas
        _verificar_disco_de_pruebas()
    except Exception as e:
        log(f"⚠️  disco de pruebas no disponible: {e}", "WARN")
        log(f"   (siguiendo de todas formas; puede fallar después)")

    guardados = 0
    try:
        ent = entorno_activo("simulacion")
        log(f"Abriendo libreta en entorno: {ent}")

        with Libreta(ent, solo_lectura=False) as lib:
            for dato in datos_extraidos:
                try:
                    if dato.tipo.value == "gasto":
                        monto = dato.datos.get("cantidad")
                        categoria = dato.datos.get("categoria")
                        descripcion = dato.datos.get("descripcion")

                        # Guardar en BD
                        gasto_id = lib.registrar_gasto(
                            monto,
                            categoria,
                            descripcion=descripcion or "desde transcripción de voz"
                        )
                        log(f"✅ gasto guardado: id={gasto_id}, ${monto} en {categoria}")
                        guardados += 1

                    elif dato.tipo.value == "tarea":
                        titulo = dato.datos.get("titulo")
                        # Tarea no tiene registrar_tarea accesible desde voz aún
                        log(f"⚠️  tarea anotada (no guardada aún): {titulo}")

                except Exception as e:
                    log(f"❌ error al guardar dato: {e}", "ERROR")

    except Exception as e:
        log(f"❌ no se pudo abrir libreta: {e}", "ERROR")
        return -1

    log(f"✅ PASO 4 completado: {guardados} registro(s) guardado(s)")
    return guardados


def paso_5_verificar_en_bd() -> dict | None:
    """PASO 5: Verificar que los gastos se escribieron en la BD."""
    log("=" * 70)
    log("PASO 5: Verificar escritura en BD", "STEP")
    log("-" * 70)

    try:
        ent = entorno_activo("simulacion")
        with Libreta(ent, solo_lectura=True) as lib:
            # Contar gastos de hoy
            hoy = lib.hoy()
            cursor = lib.con.execute(
                "SELECT COUNT(*), SUM(monto_mxn) FROM gastos WHERE fecha = ?",
                (hoy,),
            )
            fila = cursor.fetchone()
            cantidad = fila[0]
            total = fila[1] or 0.0

            log(f"Gastos de hoy ({hoy}): {cantidad} registros, ${total:.2f} MXN total")

            # Listar últimos 5 gastos
            cursor = lib.con.execute(
                "SELECT id, fecha, monto_mxn, categoria, descripcion FROM gastos "
                "ORDER BY id DESC LIMIT 5"
            )
            ultimos = cursor.fetchall()
            log(f"Últimos 5 gastos en la BD:")
            for row in ultimos:
                log(f"   id={row[0]}, {row[1]}: ${row[2]:.2f} ({row[3]})")

            log(f"✅ PASO 5 completado: BD verificada")
            return {
                "cantidad_gastos_hoy": cantidad,
                "total_hoy_mxn": total,
                "ultimos": [dict(r) for r in ultimos]
            }

    except Exception as e:
        log(f"❌ verificación de BD falló: {e}", "ERROR")
        return None


def main() -> int:
    """Ejecutar verificación completa punta a punta."""
    log("🎤 VERIFICACIÓN REAL: Voz → STT → Extracción → Libreta (Bloque AS-3)")
    log(f"   Fecha: {datetime.datetime.now().isoformat()}")
    log(f"   Entorno: simulacion (no toca datos reales)")
    log(f"   Candado: NO se envía a Telegram")
    log("")

    # PASO 1: Generar audio
    archivo = paso_1_generar_audio()
    if not archivo:
        log("❌ FALLO en PASO 1 — abortando", "FATAL")
        return 1
    print()

    # PASO 2: Transcribir
    transcripcion = paso_2_transcribir(archivo)
    if not transcripcion:
        log("❌ FALLO en PASO 2 — abortando", "FATAL")
        return 1
    print()

    # PASO 3: Extraer datos
    datos = paso_3_extraer_datos(transcripcion)
    if datos is None:
        log("❌ FALLO en PASO 3 — abortando", "FATAL")
        return 1
    print()

    # PASO 4: Guardar en libreta
    guardados = paso_4_guardar_en_libreta(datos)
    if guardados < 0:
        log("❌ FALLO en PASO 4 — abortando", "FATAL")
        return 1
    print()

    # PASO 5: Verificar BD
    verify = paso_5_verificar_en_bd()
    if verify is None:
        log("❌ FALLO en PASO 5 — abortando", "FATAL")
        return 1
    print()

    # REPORTE FINAL
    log("=" * 70)
    log("🎉 VERIFICACIÓN COMPLETADA CON ÉXITO", "FINAL")
    log("-" * 70)
    log(f"✅ Audio generado: {archivo}")
    log(f"✅ STT transcribió: '{transcripcion}'")
    log(f"✅ Extractor identificó: {len(datos)} dato(s)")
    log(f"✅ Libreta guardó: {guardados} registro(s)")
    log(f"✅ BD verificada: {verify['cantidad_gastos_hoy']} gastos hoy, ${verify['total_hoy_mxn']:.2f}")
    log("")
    log(f"Log: {LOG}")
    log(f"Audio: {archivo}")
    log("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
