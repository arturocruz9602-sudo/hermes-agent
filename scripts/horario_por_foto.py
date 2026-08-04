#!/usr/bin/env python3
"""
horario_por_foto.py -- BLOQUE 1 de OT-6 (tutor academico, F6-2): foto del
horario escolar -> tabla `horario` en la libreta.

Extractor de vision INYECTABLE (mismo patron que el transcriptor Whisper de
corte_silencios.py y el ejecutor SSH de edicion_m1.py) -- por defecto sigue
sin llamar red por su cuenta (el simulado de --simular).

EXCEPCION ACOTADA a r.91, confirmada por Arturo el 04 ago (ver DECISIONES.md):
el horario trae nombres reales de profesores, y la regla general dice "nunca
nombres a API gratis" -- GEMINI_VISION_KEY_NEW SI es tier gratis (confirmado
por Arturo, no supuesto). La excepcion es puntual para FOTOS DE HORARIO
ESCOLAR unicamente, no abre la puerta a nombres en general en ningun otro
flujo. `extractor_gemini_vision()` es el extractor REAL, activado con
--foto RUTA; usa el alias `vision` de LiteLLM (gemini-2.5-flash,
GEMINI_VISION_KEY_NEW, cuota propia sin compartir con chat/voz).

Doble candado antes de tocar la libreta real (mismo espiritu que
PublicadorYouTube.aprobado y r.89 "pregunta antes de crear"):
  1. `parsear_horario()` es puro: foto cruda -> filas -> propuesta LEGIBLE
     para que Arturo la corrija en chat (HAS 653-659: "confirmacion con
     Arturo de la tabla extraida... antes de alta").
  2. `aplicar_horario()` se NIEGA a escribir sin `confirmado=True` explicito.

Versionado por cuatrimestre (HAS 1157, regla F7): un horario nuevo ARCHIVA
(activo=0) las filas de escuela del cuatrimestre anterior, nunca las borra ni
las pisa -- el historial academico es memoria permanente. Reaplicar el mismo
cuatrimestre es idempotente (no duplica filas ya insertadas).

USO (CLI de prueba, no toca la libreta real salvo --aplicar):
  python3 horario_por_foto.py --simular              -> corre con foto/extractor
                                                          sinteticos, imprime la
                                                          propuesta, no escribe
  python3 horario_por_foto.py --foto RUTA.jpg         -> extractor REAL (Gemini
                                                          Vision), imprime la
                                                          propuesta, no escribe
                                                          salvo --aplicar
"""

import base64
import json
import os
import re
import sqlite3
import sys
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import RUTAS, entorno_activo  # noqa: E402

DIAS_NOMBRE = {
    1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves",
    5: "viernes", 6: "sábado", 7: "domingo",
}
_DIAS_TEXTO = {
    "lunes": 1, "lun": 1,
    "martes": 2, "mar": 2,
    "miercoles": 3, "miércoles": 3, "mier": 3, "mié": 3,
    "jueves": 4, "jue": 4,
    "viernes": 5, "vie": 5,
    "sabado": 6, "sábado": 6, "sab": 6, "sáb": 6,
    "domingo": 7, "dom": 7,
}
# Nombres largos sin acento, para el fallback "el texto es prefijo del
# nombre" (p.ej. "lu" -> "lunes"). Ojo: la comparación es texto-es-prefijo-
# de-nombre, NUNCA al revés -- "marciano" no debe colar como "martes".
_DIAS_LARGOS = {
    "lunes": 1, "martes": 2, "miercoles": 3, "jueves": 4,
    "viernes": 5, "sabado": 6, "domingo": 7,
}

# Filas crudas que devuelve el extractor de vision (aun no cableado a red).
FilaCruda = dict


class ExtraccionInvalida(ValueError):
    """Una fila cruda no se pudo normalizar (dia/hora ilegible)."""


class ConfirmacionRequerida(RuntimeError):
    """aplicar_horario() nunca escribe sin confirmado=True explicito."""


@dataclass
class EntradaHorario:
    dia_semana: int  # 1=lunes .. 7=domingo
    hora_inicio: str  # 'HH:MM' 24h
    hora_fin: Optional[str]
    materia: str
    aula: Optional[str] = None
    profesor: Optional[str] = None


# Firma del puerto inyectable: foto (bytes) -> filas crudas sin normalizar.
# La implementacion real (Gemini Vision de paga verificado, u Ollama local)
# esta PENDIENTE -- ver docstring del modulo.
ExtractorHorario = Callable[[bytes], list]


def normalizar_dia(texto: str) -> int:
    t = texto.strip().lower()
    if t in _DIAS_TEXTO:
        return _DIAS_TEXTO[t]
    if len(t) >= 2:
        for nombre, num in _DIAS_LARGOS.items():
            if nombre.startswith(t):
                return num
    raise ExtraccionInvalida(f"día no reconocido: {texto!r}")


def normalizar_hora(texto: str) -> str:
    t = texto.strip().lower().replace(".", "")
    m = re.match(r"^(\d{1,2}):?(\d{2})?\s*(am|pm)?$", t)
    if not m:
        raise ExtraccionInvalida(f"hora no reconocida: {texto!r}")
    h = int(m.group(1))
    mnt = int(m.group(2) or 0)
    ampm = m.group(3)
    if not (0 <= mnt <= 59):
        raise ExtraccionInvalida(f"hora no reconocida: {texto!r}")
    if ampm == "pm" and h != 12:
        h += 12
    elif ampm == "am" and h == 12:
        h = 0
    if not (0 <= h <= 23):
        raise ExtraccionInvalida(f"hora no reconocida: {texto!r}")
    return f"{h:02d}:{mnt:02d}"


def parsear_horario(filas: list) -> tuple:
    """filas crudas del extractor -> (entradas validas, errores legibles).

    Nunca revienta con una fila mala: la separa en `errores` para que la
    propuesta se la muestre a Arturo y el resto SÍ se pueda confirmar.
    """
    entradas: list = []
    errores: list = []
    for i, fila in enumerate(filas, start=1):
        try:
            materia = (fila.get("materia") or "").strip()
            if not materia:
                raise ExtraccionInvalida("falta materia")
            dia = normalizar_dia(str(fila.get("dia", "")))
            hi = normalizar_hora(str(fila.get("hora_inicio", "")))
            hf_raw = fila.get("hora_fin")
            hf = normalizar_hora(str(hf_raw)) if hf_raw else None
            entradas.append(EntradaHorario(
                dia_semana=dia, hora_inicio=hi, hora_fin=hf, materia=materia,
                aula=(fila.get("aula") or "").strip() or None,
                profesor=(fila.get("profesor") or "").strip() or None,
            ))
        except ExtraccionInvalida as e:
            errores.append(f"fila {i} ({fila}): {e}")
    return entradas, errores


def formatear_propuesta(entradas: list, errores: list, cuatrimestre: str) -> str:
    """Tabla legible para Telegram -- lo que Arturo corrige antes del 'sí'."""
    lineas = [f"📅 Horario detectado para {cuatrimestre} (aún NO aplicado):", ""]
    por_dia: dict = {}
    for e in entradas:
        por_dia.setdefault(e.dia_semana, []).append(e)
    for dia in sorted(por_dia):
        lineas.append(f"*{DIAS_NOMBRE[dia].capitalize()}*")
        for e in sorted(por_dia[dia], key=lambda x: x.hora_inicio):
            rango = e.hora_inicio + (f"-{e.hora_fin}" if e.hora_fin else "")
            extra = " · ".join(x for x in (e.aula, e.profesor) if x)
            lineas.append(f"  {rango}  {e.materia}" + (f"  ({extra})" if extra else ""))
    if errores:
        lineas.append("")
        lineas.append("⚠️ No entendí estas filas, corrígelas tú:")
        lineas.extend(f"  - {err}" for err in errores)
    lineas.append("")
    lineas.append("¿Lo doy de alta así? Responde sí, o corrige lo que falte.")
    return "\n".join(lineas)


def aplicar_horario(
    conn: sqlite3.Connection,
    entradas: list,
    cuatrimestre: str,
    confirmado: bool = False,
) -> int:
    """Archiva el cuatrimestre anterior de escuela e inserta el nuevo.

    Se niega sin confirmado=True (HAS: "confirmación con Arturo... antes de
    alta"). Idempotente: reaplicar el mismo cuatrimestre no duplica filas.
    Devuelve cuántas filas nuevas insertó.
    """
    if not confirmado:
        raise ConfirmacionRequerida(
            "aplicar_horario requiere confirmado=True explícito de Arturo"
        )
    if not entradas:
        raise ValueError("sin entradas que aplicar")
    with conn:
        conn.execute(
            "UPDATE horario SET activo=0 "
            "WHERE materia IS NOT NULL AND activo=1 "
            "AND (cuatrimestre IS NULL OR cuatrimestre != ?)",
            (cuatrimestre,),
        )
        insertadas = 0
        for e in entradas:
            existe = conn.execute(
                "SELECT 1 FROM horario WHERE materia=? AND dia_semana=? "
                "AND hora_inicio=? AND cuatrimestre=?",
                (e.materia, e.dia_semana, e.hora_inicio, cuatrimestre),
            ).fetchone()
            if existe:
                continue
            conn.execute(
                "INSERT INTO horario "
                "(dia_semana, hora_inicio, hora_fin, actividad, lugar, "
                " materia, profesor, cuatrimestre, activo) "
                "VALUES (?,?,?,?,?,?,?,?,1)",
                (e.dia_semana, e.hora_inicio, e.hora_fin, e.materia, e.aula,
                 e.materia, e.profesor, cuatrimestre),
            )
            insertadas += 1
    return insertadas


def _extractor_simulado(foto: bytes) -> list:
    """Extractor de PRUEBA (r.20: escenario simulado, solo laboratorio).
    Se usa con --simular; el real está pendiente de decidir el proveedor."""
    return [
        {"dia": "Lunes", "hora_inicio": "8:00", "hora_fin": "9:30",
         "materia": "Programación Web", "aula": "B-204", "profesor": "Ing. Ríos"},
        {"dia": "Lunes", "hora_inicio": "9:30", "hora_fin": "11:00",
         "materia": "Bases de Datos", "aula": "B-204", "profesor": "Ing. Solís"},
        {"dia": "Miércoles", "hora_inicio": "8:00", "hora_fin": "9:30",
         "materia": "Programación Web", "aula": "B-204", "profesor": "Ing. Ríos"},
    ]


_PROMPT_VISION = """Extrae la tabla de horario escolar de esta imagen. Devuelve
SOLO un array JSON, sin texto extra, sin markdown, con esta forma exacta por
cada clase (una fila por bloque de horario; si varias horas seguidas son la
misma materia, es UN bloque con hora_inicio/hora_fin, no lo repitas):
[{{"dia": "lunes", "hora_inicio": "8:00", "hora_fin": "10:00", "materia": "...",
"profesor": "...", "aula": null}}]
dia en minusculas sin acento (lunes/martes/miercoles/jueves/viernes/sabado).
hora en formato H:MM o HH:MM, 24 horas. Si no hay profesor o aula visibles en
esa celda, usa null. No inventes clases que no veas en la imagen."""


def extractor_gemini_vision(foto: bytes) -> list:
    """Extractor REAL vía Gemini Vision (alias `vision` en LiteLLM,
    GEMINI_VISION_KEY_NEW, cuota propia, no comparte con chat/voz).

    EXCEPCIÓN ACOTADA a r.91 (DECISIONES.md 04 ago, confirmada por Arturo):
    ver docstring del módulo. Solo para fotos de horario escolar.

    Nunca lanza: cualquier fallo devuelve [] y se loguea a stderr (HAS
    regla 3, el silencio no es un estado válido de fallo) -- parsear_horario
    ya sabe convertir una lista vacía en "0 entradas, revisa la foto"."""
    try:
        from agent.complexity_detector import _resolve_litellm_credentials
        base_url, api_key = _resolve_litellm_credentials()
        b64 = base64.b64encode(foto).decode("ascii")
        payload = {
            "model": "vision",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT_VISION},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
            "max_tokens": 3000,
            "temperature": 0,
            # sin esto, gemini-2.5-flash gasta ~1900 de 2000 tokens en
            # "razonamiento" interno para una tarea de puro OCR/transcripcion
            # -- se corta el JSON a medias (hallazgo real, 04 ago: probado
            # contra la foto real, finish_reason="length" con solo esto
            # apagado se resuelve). thinking_budget=0 -> respuesta directa,
            # ~6-7s en vez de timeout, cero tokens desperdiciados en pensar
            # una extraccion de tabla.
            "thinking_config": {"thinking_budget": 0},
        }
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        raw = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
        filas = json.loads(raw)
        if not isinstance(filas, list):
            raise ValueError(f"esperaba una lista JSON, llegó {type(filas).__name__}")
        return filas
    except Exception as e:
        print(f"[horario_por_foto] extractor de visión falló: {e}", file=sys.stderr)
        return []


def main():
    if "--simular" in sys.argv:
        filas = _extractor_simulado(b"")
        cuatrimestre = "2026-SIMULADO"
    elif "--foto" in sys.argv:
        idx = sys.argv.index("--foto")
        if idx + 1 >= len(sys.argv):
            print("uso: python3 horario_por_foto.py --foto RUTA.jpg [--aplicar]")
            sys.exit(2)
        with open(sys.argv[idx + 1], "rb") as f:
            foto_bytes = f.read()
        filas = extractor_gemini_vision(foto_bytes)
        cuatrimestre = "detectado (confirma con Arturo antes de aplicar)"
    else:
        print("uso: python3 horario_por_foto.py --simular|--foto RUTA.jpg [--aplicar]")
        sys.exit(2)

    entorno = entorno_activo("simulacion")
    entradas, errores = parsear_horario(filas)
    print(formatear_propuesta(entradas, errores, cuatrimestre))
    if "--aplicar" in sys.argv:
        conn = sqlite3.connect(str(RUTAS[entorno]))
        n = aplicar_horario(conn, entradas, cuatrimestre, confirmado=True)
        print(f"\n✅ {n} filas insertadas en {entorno}")
        conn.close()


if __name__ == "__main__":
    main()
