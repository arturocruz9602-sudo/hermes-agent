#!/usr/bin/env python3
"""Batería de verificación del clasificador de dificultad del loop (Bloque AV, fase 2).

NO es un test unitario mockeado: llama al modelo GRATIS real (chat-gratis/Gemini)
con 9 bloques etiquetados a mano por Arturo/Claude para medir cuántos rutea bien
ANTES de conectar el lanzador de tmux. Es el artefacto de evidencia que pide el
auto-cuestionamiento ("LO VERIFICO CON: batería de bloques etiquetados").

Tres niveles (corrección de Arturo 02 ago): trivial->Haiku, medio->Sonnet,
complejo->Opus. Cada llamada es gratis y sin datos personales (solo descripciones
genéricas de tareas de ingeniería), así que puede correrse cuantas veces haga falta.

Uso:  python3 scripts/loop_clasificador_bateria.py
Sale con código 0 si el acierto es total; 1 en cualquier otro caso.
"""
from __future__ import annotations

import sys

from loop_orquestador import clasificar_dificultad  # mismo directorio

# (título, descripción, dificultad_esperada)
CASOS = [
    # --- triviales (mecánico, sin juicio, un paso obvio) ---
    ("Correr la suite de tests de libreta y reportar",
     "Ejecutar pytest sobre tests/test_libreta.py y pegar cuántos pasan/fallan.",
     "trivial"),
    ("Correr el índice de skills que ya existe",
     "Ejecutar build_skills_index.py tal cual y guardar su salida.",
     "trivial"),
    ("Reportar cuántas líneas tiene ESTADO.md",
     "Correr wc -l sobre docs/ESTADO.md y decir el número.",
     "trivial"),
    # --- medios (acotado, algo de trabajo, sin arquitectura) ---
    ("Actualizar BITACORA_ARTURO.md con el brief matutino",
     "Agregar una entrada nueva describiendo el brief de 6:30 en el formato existente.",
     "medio"),
    ("Renombrar la variable modelo_barato a modelo_gratis",
     "Cambio de nombre en un solo archivo, ajustando sus usos, sin cambiar comportamiento.",
     "medio"),
    ("Generar el reporte semanal desde la plantilla",
     "Rellenar la plantilla de reporte con los datos del ledger ya calculados.",
     "medio"),
    # --- complejos (juicio, multi-archivo, riesgo) ---
    ("Diseñar el lanzador de tmux del orquestador",
     "Decidir cómo se abre una ventana visible por bloque, cómo se pasa el prompt "
     "y cómo se mide el gasto de tokens de cada sesión de claude.",
     "complejo"),
    ("Depurar por qué el brief matutino manda el clima equivocado",
     "El timer corre pero la temperatura no cuadra con Open-Meteo; encontrar la causa raíz.",
     "complejo"),
    ("Aplicar la migración v5 de la libreta a producción",
     "Migración de esquema de state.db/libreta.db con datos reales de Arturo; "
     "requiere respaldo previo y validación en el laboratorio Docker.",
     "complejo"),
]


def main() -> int:
    aciertos = 0
    print(f"{'esperado':10} {'obtenido':10} {'modelo':8} {'fb':3}  título")
    print("-" * 78)
    for titulo, descripcion, esperado in CASOS:
        c = clasificar_dificultad(titulo, descripcion)
        ok = c.dificultad == esperado
        aciertos += ok
        marca = "OK " if ok else "XX "
        fb = "fb" if c.es_fallback else "-"
        print(f"{marca}{esperado:7} {c.dificultad:10} {c.modelo:8} {fb:3}  {titulo}")
        if not ok or c.es_fallback:
            print(f"        └─ razón: {c.razon}")

    total = len(CASOS)
    print("-" * 78)
    print(f"aciertos: {aciertos}/{total}")
    return 0 if aciertos == total else 1


if __name__ == "__main__":
    sys.exit(main())
