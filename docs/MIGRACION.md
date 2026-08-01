# MIGRACIÓN — reestructura documental (01 ago 2026)
**Esto se ejecuta UNA vez, en la próxima sesión de Claude Code (o Arturo lo corre a mano). ~5 minutos.**

## 1. Archivar lo viejo (nada se borra — el crudo es sagrado, F1.3)
```bash
cd ~/.hermes/hermes-agent   # o donde viva docs/
mkdir -p docs/archivo docs/bloques
git mv docs/ESTADO.md  docs/archivo/ESTADO_2026-07.md
git mv docs/BLOQUES.md docs/archivo/BLOQUES_2026-07.md
```

## 2. Colocar los archivos nuevos
Copiar a `docs/`: `ESTADO.md`, `BLOQUES.md`, `DECISIONES.md`, `LIBRETA_SEED.md` y
`CUESTIONARIO_MAESTRO.md` (respondido y pulido — ya viene en markdown, no hay PDF que convertir).
El cuestionario es la voz directa de Arturo, misma jerarquía que MANDATO; donde un documento viejo lo
contradiga, gana el cuestionario. `LIBRETA_SEED.md` NO se carga a state.db en este paso: espera al
Bloque AR (primero el laboratorio, F11-e).

## 3. Gate de cierre (agregar al script/checklist de cierre de sesión)
```bash
LINEAS=$(wc -l < docs/ESTADO.md)
if [ "$LINEAS" -gt 80 ]; then
  echo "❌ ESTADO.md tiene $LINEAS líneas (máx 80). La sesión NO terminó. Poda o archiva."
  exit 1
fi
grep -rn "TEMP-DIAG" --include="*.py" . && { echo "❌ TEMP-DIAG vivo"; exit 1; }
echo "✅ Gates de cierre en verde"
```

## 4. Parche a CLAUDE.md (pegar en la sección de arranque, reemplaza la lista de lectura actual)
```
ARRANQUE DE SESIÓN (ligero, en este orden, y NADA más por default):
1. Leer CLAUDE.md (este) + docs/MANDATO_ARTURO.md + docs/ESTADO.md. Fin de la lectura fija.
2. ESTADO.md dice qué documentos adicionales leer para la tarea activa. Leer SOLO esos.
   Leer HAS/PROTOCOLO/VIDA/archivo completos requiere escribir 1 línea de motivo antes.
3. Consultar docs/DECISIONES.md antes de proponer cualquier cambio de arquitectura.
   Reabrir una decisión cerrada sin evidencia nueva = falla de protocolo.

REGLA DE TAREA ÚNICA (concilia MANDATO §1 con el foco):
- La elección de la tarea de mayor impacto ocurre UNA sola vez, al abrir sesión.
- Elegida, queda BLOQUEADA hasta cerrarla: no refactorizar, no limpiar, no optimizar,
  no renombrar, no investigar otra cosa, no abrir frentes nuevos.
- Si a media sesión aparece algo más importante: se ANOTA en ESTADO.md como candidato
  para la siguiente sesión. No se cambia de caballo. Excepción única: producción caída.

CIERRE DE SESIÓN:
- ESTADO.md se SOBREESCRIBE (nunca append) con el formato vigente, ≤80 líneas (gate).
- Bloque cerrado → 1 línea en BLOQUES.md; narrativa larga (si amerita) → docs/archivo/.
- Decisión nueva → DECISIONES.md. Lo demás igual: commit, bitácora, TEMP-DIAG=0, push.
```

## 5. Actualizar PROTOCOLO (nota de versión v1.4, 3 líneas)
- §2 sin cambios de fondo — solo se AGREGA: "ESTADO.md incluye la sección 'Documentos a leer
  esta sesión'; se sobreescribe, nunca se appendea; gate wc -l ≤ 80 en el cierre."
- §3 se AGREGA: "la narrativa de cada bloque vive en docs/archivo/; BLOQUES.md es solo el índice."
- Nueva regla C17: tarea única (texto del punto 4).

## 6. Verificación de la migración (evidencia, F8)
```bash
wc -l docs/ESTADO.md   # ≤80 o la migración NO está cerrada
git ls-files docs/ESTADO.md docs/BLOQUES.md docs/DECISIONES.md docs/LIBRETA_SEED.md \
  docs/CUESTIONARIO_MAESTRO.md docs/archivo/   # los 5 + cuestionario, todos versionados
git log --oneline -1
```
Pegar la salida en el commit. Con eso la migración está cerrada y la siguiente sesión
arranca directo en el Bloque AQ (laboratorio) sin releer 550 KB.
