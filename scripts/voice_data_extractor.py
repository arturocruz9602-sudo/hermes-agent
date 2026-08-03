#!/usr/bin/env python3
"""
voice_data_extractor.py — Extracción de datos desde transcripciones de voz

Paso 2 del Bloque AS-3: interpretación de transcripciones para guardar datos en libreta.

Este módulo reconoce patrones en el texto de STT y los convierte en acciones:
  - Gastos: "gasté/gasto X pesos/MXN en Y"
  - Tareas: "agregar tarea", "apuntar", etc.
  - Recordatorios, pagos, notas

Patrón: texto → regex → entidad (gasto, tarea, etc.) → libreta.guardar()
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipoExtraccion(Enum):
    """Tipos de datos que se pueden extraer de una transcripción."""
    GASTO = "gasto"
    TAREA = "tarea"
    RECORDATORIO = "recordatorio"
    PAGO = "pago"
    DESCONOCIDO = "desconocido"


@dataclass
class DatosExtraidos:
    """Resultado de la extracción de datos."""
    tipo: TipoExtraccion
    datos: dict  # contenido específico según el tipo
    transcripcion: str
    confianza: float  # 0.0-1.0


class VoiceDataExtractor:
    """
    Extractor de datos desde transcripciones de voz.

    Usa patrones regex para reconocer:
    - Gastos: "gasté 50 pesos en comida", "costo 100 MXN en gasolina"
    - Tareas: "apuntar que tengo escuela mañana", "tarea importante: estudiar"
    """

    # Patrones regex para gastos
    PATRON_GASTO = re.compile(
        r"""
        (?P<prefijo>gast[ée]|costo|costó|pagué|pagó|gasté|gasto)
        \s+
        (?P<cantidad>\d+(?:[.,]\d+)?)
        \s*
        (?:pesos?|MXN|mxn)?
        (?:\s+en\s+(?P<categoria>\w+(?:\s+\w+)?))?
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Patrones regex para tareas
    PATRON_TAREA = re.compile(
        r"""
        (?:agreg|apunt|apunt(?:ar)?|notar?|recordar?|tengo|hay|debo)
        \s+
        (?:que\s+)?
        (?P<tarea>.{5,100}?)
        (?:\.|,|$)
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    @classmethod
    def extraer_gastos(cls, texto: str) -> list[DatosExtraidos]:
        """Extrae gastos de un texto."""
        gastos = []
        for match in cls.PATRON_GASTO.finditer(texto):
            try:
                cantidad_str = match.group("cantidad").replace(",", ".")
                cantidad = float(cantidad_str)
                categoria = (match.group("categoria") or "otro").strip().lower()

                gastos.append(
                    DatosExtraidos(
                        tipo=TipoExtraccion.GASTO,
                        datos={
                            "cantidad": cantidad,
                            "categoria": categoria,
                            "descripcion": match.group(0),
                        },
                        transcripcion=texto,
                        confianza=0.95,
                    )
                )
            except (ValueError, AttributeError):
                pass
        return gastos

    @classmethod
    def extraer_tareas(cls, texto: str) -> list[DatosExtraidos]:
        """Extrae tareas de un texto."""
        tareas = []
        for match in cls.PATRON_TAREA.finditer(texto):
            try:
                tarea_texto = match.group("tarea").strip()
                # Limpiar puntuación
                tarea_texto = re.sub(r"[,.]$", "", tarea_texto)

                if len(tarea_texto) >= 3:
                    tareas.append(
                        DatosExtraidos(
                            tipo=TipoExtraccion.TAREA,
                            datos={
                                "titulo": tarea_texto,
                                "descripcion": match.group(0),
                            },
                            transcripcion=texto,
                            confianza=0.80,
                        )
                    )
            except AttributeError:
                pass
        return tareas

    @classmethod
    def extraer(cls, transcripcion: str) -> list[DatosExtraidos]:
        """
        Extrae todos los datos reconocidos de una transcripción.

        Returns:
            Lista de DatosExtraidos ordenados por confianza (mayor a menor).
        """
        if not transcripcion or not isinstance(transcripcion, str):
            return []

        # Normalizar
        texto = transcripcion.strip().lower()

        # Buscar en orden: gastos, tareas, etc.
        resultados: list[DatosExtraidos] = []

        # Gastos (mayor confianza)
        resultados.extend(cls.extraer_gastos(texto))

        # Tareas (confianza menor)
        resultados.extend(cls.extraer_tareas(texto))

        # Ordenar por confianza (mayor a menor)
        resultados.sort(key=lambda x: x.confianza, reverse=True)

        return resultados

    @classmethod
    def describir(cls, extraccion: DatosExtraidos) -> str:
        """Descripción legible de lo extraído."""
        if extraccion.tipo == TipoExtraccion.GASTO:
            return (
                f"💰 Gasto: ${extraccion.datos['cantidad']:.2f} "
                f"en {extraccion.datos['categoria']}"
            )
        elif extraccion.tipo == TipoExtraccion.TAREA:
            return f"📝 Tarea: {extraccion.datos['titulo']}"
        else:
            return f"❓ {extraccion.tipo.value}: {extraccion.datos}"


if __name__ == "__main__":
    # Ejemplos de prueba
    ejemplos = [
        "Gasté 50 pesos en comida",
        "costo 100 MXN en gasolina",
        "pagué 200 en la escuela",
        "tengo que estudiar mañana",
        "apuntar que debo hacer la tarea",
        "gasté 50 pesos en comida y tengo que ir a clase",
    ]

    print("Pruebas de extracción:\n")
    for ejemplo in ejemplos:
        print(f"Entrada: '{ejemplo}'")
        resultados = VoiceDataExtractor.extraer(ejemplo)
        if resultados:
            for r in resultados:
                print(f"  → {VoiceDataExtractor.describir(r)}")
        else:
            print("  → (nada extraído)")
        print()
