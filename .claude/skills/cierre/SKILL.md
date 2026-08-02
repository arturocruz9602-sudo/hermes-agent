---
name: cierre
description: Cierre de sesión de Hermes — camina el checklist obligatorio de 6 pasos (commit, ESTADO ≤80, BLOQUES, DECISIONES, BITÁCORA, TEMP-DIAG, temperatura, push a arturo/prod). Invócala al terminar, antes de un /clear, o cada 30 min de trabajo continuo. "Una sesión sin push no terminó."
---

# Cierre de sesión de Hermes

Vigente al 01 ago 2026 (CLAUDE.md v1.3, PROTOCOLO v1.4). El **qué escribir** en cada
doc es juicio tuyo; esta skill es la lista que garantiza que no se salta ningún paso.
Es el complemento del hook de arranque: si el arranque junta el estado, el cierre lo deja
guardado y empujado para que Arturo lo vea desde su terminal (`git log`, ESTADO, BLOQUES).

## Regla de oro

**Una sesión que no hizo push NO terminó, aunque el código funcione.** Y nunca digas
"ya quedó guardado" sin pegar la evidencia (commit/diff real) en el mismo mensaje.

## Los 6 pasos (en orden)

1. **Commit de avance** — aunque sea WIP. No dejes trabajo sin versionar.

2. **`docs/ESTADO.md` se SOBREESCRIBE** (nunca append) con el formato vigente.
   - Primera línea: versiones vigentes (`HAS vX.Y · PROTOCOLO vX.Y`).
   - **Gate duro:** `wc -l docs/ESTADO.md` debe dar **≤ 80**. Si se pasa: poda o manda
     lo viejo a `docs/archivo/`. No se cierra con ESTADO > 80.

3. **Bloque cerrado → 1 línea en `docs/BLOQUES.md`** (es solo el índice).
   La narrativa larga, si amerita, va a `docs/archivo/`.
   **Decisión de arquitectura nueva → `docs/DECISIONES.md`** (append-only; consúltalo
   también ANTES de reabrir cualquier cosa: reabrir una decisión cerrada sin evidencia
   nueva es falla de protocolo).

4. **`docs/BITACORA_ARTURO.md`** — solo si la sesión tocó algo visible para Arturo:
   qué cambió traducido a su día a día (antes/ahora concreto) + un mensaje de ejemplo
   que él pueda mandar literal para probarlo. Incluye también hallazgos reales sin
   arreglar que le afecten.

5. **`grep -rn "TEMP-DIAG"` = 0** en el árbol tocado (o justificar cada uno que se queda
   en ESTADO.md, casilla "en cuarentena"). Y **temperatura HP normal**
   (`/sys/class/thermal/*/temp`, umbral 85°C).

6. **`git push fork HEAD:arturo/prod`** — NUNCA `git push fork main` (esa rama espeja el
   upstream de NousResearch y diverge sin relación con el trabajo real).

## Gate de verificación (pega esta evidencia, no la resumas)

Corre esto y pega la salida real en el mensaje de cierre:

```bash
cd /home/arturo/.hermes/hermes-agent
echo "--- wc ESTADO (gate <=80) ---"; wc -l docs/ESTADO.md
echo "--- TEMP-DIAG (debe ser 0) ---"; grep -rn --include='*.py' 'TEMP-DIAG' . | grep -v '/.venv/' | grep -c . || true
echo "--- L11 versionados ---"; git ls-files docs/ESTADO.md docs/BLOQUES.md docs/DECISIONES.md docs/CUESTIONARIO_MAESTRO.md
echo "--- estado del arbol ---"; git status --short
echo "--- ultimo commit ---"; git log -1 --oneline
```

Después del push, confirma que salió:

```bash
git push fork HEAD:arturo/prod && git log fork/arturo/prod -1 --oneline
```

## Lo que este cierre NO hace

- No decide POR ti qué escribir en ESTADO/BLOQUES/DECISIONES — eso es juicio.
- No toca memoria (`.md` de memoria solo vía `memory_tool.py`).
- No reinicia servicios ni corre pruebas grandes (eso es de sus propias skills).
