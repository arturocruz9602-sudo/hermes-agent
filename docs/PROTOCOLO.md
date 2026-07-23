# PROTOCOLO DE COORDINACIÓN · v1.3.1
**Cambios v1.3.1 (23-jul):** C16 — presupuesto autónomo de pruebas ($100 MXN/mes con cortacircuitos), aprobado por Arturo.
**Cambios v1.3 (23-jul) — CORRECCIÓN DE ARQUITECTURA:** el centro de trabajo diario deja de ser el chat de diseño y pasa a ser **Claude Code**, que arranca solo leyendo `CLAUDE.md` + `ESTADO.md` y propone el siguiente paso sin que Arturo pegue nada. Arturo deja de ser el cable entre cajas. Nuevas reglas: §10 (arranque autónomo y consulta interna a otros modelos), C15 (permisos por allowlist), P6.1 (cuenta QA de Telegram), P7 (guion de pruebas del día completo y las 3 capas de verificación de memoria). El chat de diseño (claude.ai) pasa a rol de consultor eventual, no de eslabón diario.
**Cambios v1.2 (23-jul):** nueva sección 9 "La carga de Arturo" — regla suprema de este protocolo: los Claudes existen para quitarle trabajo a Arturo, no para convertirlo en mensajero ni en juez; economía de decisiones, versiones declaradas en ESTADO.md, y defaults con plazo.
**Cambios v1.1 (23-jul):** D7 (leer antes de preguntar — fallas L9/L15), D8 (muestra antes de construir — L16), C13-C14 (bitácora de Arturo y barrido TEMP-DIAG), P6 (arnés interno para pruebas de rutina), verificación git de ESTADO/BLOQUES (L11). Jurisprudencia completa: HAS §F9.
**Proyecto Hermes · 22-jul-2026 · Este documento vive en el contexto del Proyecto de claude.ai Y en el fork como `docs/PROTOCOLO.md`. Obliga a ambos Claudes y a Arturo por igual.**

## 0. El problema que este protocolo elimina

Caso real (22-jul): el chat de diseño emitió bloques de prueba sin conocer el resultado real de los bloques anteriores; Claude Code parchó heurísticas persiguiendo el último caso fallido (L → M → diagnóstico → regresión del guard); una prueba propuesta por el chat (short de ETH) contradecía el propio HAS (módulo spot, sin cortos); y las pruebas se corrieron con el gateway reiniciándose a media prueba. Resultado: incongruencias, gasto de tokens, y cero fases cerradas ese día. **Causa raíz: los dos Claudes no comparten el mismo estado del mundo.** Este protocolo crea ese estado compartido y las reglas para no volverlo a perder.

## 1. Jerarquía documental (quién manda sobre quién)

1. **`docs/HAS.md`** — QUÉ se construye y con qué reglas. Solo cambia con nota de versión.
2. **`docs/ESTADO.md`** — DÓNDE vamos (el puente, sección 2). Cambia en cada sesión.
3. **`docs/BLOQUES.md`** — registro de órdenes emitidas y su estado (sección 3).
4. Los prompts/bloques individuales — instrucciones desechables; si contradicen 1-3, pierden.

Regla de oro: **ninguna instrucción nueva puede contradecir al HAS sin antes modificar el HAS** (con nota de versión). Si el chat de diseño propone algo fuera del HAS (caso real: probar un short cuando el diseño es spot con lista blanca), cualquiera de los dos Claudes debe señalarlo antes de ejecutar, y Arturo decide: se ajusta la propuesta o se versiona el HAS.

## 2. ESTADO.md — el puente obligatorio

Archivo único, corto (máx ~80 líneas), en el fork. Es la memoria compartida entre sesiones y entre los dos Claudes.

**Formato fijo:**
```
# ESTADO — actualizado: <fecha hora> por <claude-code|arturo>
## Fases HAS: F0 ✅ | F1 ✅ | F2 🔄 (bloque X en curso) | F3+ ⬜
## Últimos 3 bloques cerrados: <letra: veredicto en 1 línea c/u>
## Bloque(s) EN CURSO ahora mismo: <letra + qué está haciendo, o "ninguno">
## Bugs abiertos: <lista corta con evidencia mínima>
## Decisiones pendientes de Arturo: <lista o "ninguna">
## No tocar / en cuarentena: <archivos a media cirugía, o "nada">
```

**Reglas de mantenimiento:**
- Claude Code lo actualiza como **último acto de cada sesión**, siempre (va en la cabecera común de sesión como regla 10).
- Arturo lo pega (o pega su contenido) como **primer mensaje de cada conversación nueva** en el Proyecto, junto con el último reporte de sesión de Claude Code.
- **El chat de diseño tiene PROHIBIDO emitir bloques nuevos si no tiene un ESTADO.md de hoy o el reporte de la última sesión.** Su primera respuesta en ese caso es pedirlo, no diseñar de memoria. Diseñar sin estado fue la causa raíz del 22-jul.

## 3. BLOQUES.md — registro de órdenes

Una línea por bloque emitido: `<letra> | <fecha> | <objetivo en 5-10 palabras> | estado: pendiente/en curso/cerrado ✅/cerrado ❌/DEROGADO por <letra>`.

- Las letras son consecutivas y únicas para todo el proyecto (no se reusan).
- Cuando un bloque nuevo reemplaza el enfoque de uno viejo (caso real: O derogó los criterios de L y el gate M), el viejo se marca DEROGADO explícitamente — así Claude Code nunca ejecuta lógica zombi ni el chat rediseña sobre algo que ya no existe.
- El chat de diseño consulta este registro (vía ESTADO.md o pidiéndolo) antes de asignar letra nueva.

## 4. Reglas del chat de diseño (Claude en claude.ai)

D1. **Nunca diseña de memoria:** todo bloque nuevo cita su evidencia — el reporte de sesión, el transcript de Telegram pegado, o la sección del HAS que implementa. Sin evidencia, pide la evidencia.
D2. **Un frente a la vez:** no emite un bloque nuevo sobre un área donde hay otro bloque en curso ("no le compitas instrucciones a media ejecución" — ya pasó y se salvó de milagro).
D3. **Verifica contra el HAS antes de proponer** pruebas o cambios (checklist mental: ¿respeta lista blanca, spot-only, español, presupuesto, aprobación explícita, reglas duras?).
D4. **Prefiere criterio sobre heurísticas:** si la solución propuesta es "otra lista de condiciones en Python" para un problema de juicio, la propuesta correcta suele ser una rúbrica evaluada por Gemini con salida JSON. El whack-a-mole de heurísticas del 22-jul no se repite.
D5. **Bloques con verificación E2E definida ANTES de ejecutar** (qué caso, qué resultado esperado) y con formato de reporte. Sin eso, el bloque está incompleto.
D6. **Escala a Fable/chat limpio solo** cuando hay un problema de arquitectura genuinamente atorado tras evidencia de 2 intentos — no como respuesta a la frustración del momento.
D7. **Leer antes de preguntar (v1.1 — nace de las fallas L9/L15 del HAS §F9, y obliga a las TRES partes: chat, Claude Code y subagentes).** La primera acción de toda sesión al recibir ESTADO.md, un reporte o un transcript es EXTRAER: restatear en 3-5 líneas los hechos relevantes a la tarea, citándolos. Toda pregunta posterior afirma implícitamente "esto no está en los documentos que tengo" — si la respuesta sí estaba textual, es una falla de protocolo y se registra en ESTADO.md como incidente (no se deja pasar con un "ah, cierto"). Un orquestador jamás emite un prompt sin haber citado primero el estado del que parte; un prompt generado de memoria con estado desactualizado se descarta completo aunque "se vea bien".
D8. **Muestra antes de construir (v1.1 — nace de L16).** Todo artefacto cuyo consumidor final es Arturo (bitácoras, tableros, formatos de reporte o de mensaje) se le presenta primero como borrador de UNA muestra ("¿así lo quieres ver?") y solo tras su visto bueno se construye completo. Diez minutos de muestra ahorran una sesión de rehacer.

## 5. Reglas de Claude Code (ya existentes + 3 nuevas)

Siguen vigentes las 9 reglas de la cabecera común del HAS §D. Se agregan:

C10. **Cierre de sesión = actualizar ESTADO.md y BLOQUES.md.** Una sesión que no los actualizó no terminó, aunque el código funcione.
C11. **Diagnósticos temporales se retiran antes de cerrar** (prints, logs extra, flags). Caso real: +11 líneas de diagnóstico en `turn_finalizer.py` causaron una regresión del guard anti-alucinación en producción. Si un diagnóstico debe quedarse entre sesiones, va en ESTADO.md bajo "en cuarentena".
C12. **Si una instrucción del chat contradice el HAS o el estado real del código, se detiene y lo reporta** en vez de ejecutarla ("el bloque pide X pero el HAS §B4 dice Y / esto ya se resolvió en el bloque K"). El chat de diseño puede equivocarse; el ejecutor es la segunda línea de defensa, en ambas direcciones.
C13. **Bitácora de Arturo (v1.1).** Si la sesión tocó algo visible para el usuario, el cierre incluye actualizar `docs/BITACORA_ARTURO.md`: qué cambió traducido a día-a-día + un mensaje de ejemplo que Arturo pueda mandar literal para probarlo. Las pruebas de rutina NO son de Arturo (ver P6); la bitácora es donde él verifica y experimenta por gusto, no por obligación.
C14. **Barrido de diagnósticos (v1.1 — nace de L4).** Todo diagnóstico temporal se marca `# TEMP-DIAG` al escribirse; el cierre de sesión corre `grep -rn "TEMP-DIAG"` sobre el árbol tocado y debe dar 0 resultados (o justificar en ESTADO.md, casilla "en cuarentena", cada uno que se queda). Además, al ABRIR sesión: `git ls-files docs/ESTADO.md docs/BLOQUES.md` debe devolver ambos; si no están versionados, se detiene todo y se corrige primero (L11).

## 6. Reglas de las pruebas (donde más se rompió el 22-jul)

P1. **Ventana limpia:** las pruebas E2E por Telegram se corren SIN ediciones ni reinicios del gateway en paralelo. Claude Code declara "ventana de pruebas abierta" / "cerrada"; entre ambas, no toca código. Cinco reinicios a media prueba invalidaron media tarde de resultados.
P2. **Toda prueba tiene resultado esperado escrito ANTES de correrla.** "A ver qué hace" no es una prueba.
P3. **La evidencia viaja completa:** Arturo pega el transcript real de Telegram (como hizo el 22-jul — eso estuvo bien y es lo que permitió encontrar los bugs). El chat analiza transcripts, no resúmenes de memoria.
P4. **Los casos de prueba respetan el diseño** (D3). Y tras la fase sintética, la validación fina se hace con el uso real de la semana de Arturo: anotar cuándo una oferta estorbó o cuándo faltó, y ajustar con esa evidencia.
P5. **Un fallo nuevo descubierto durante pruebas se registra en ESTADO.md como bug abierto** — no se parcha en caliente dentro de la misma ventana salvo que bloquee todo.
P6. **Arnés interno para la rutina (v1.1 — petición explícita de Arturo).** Las pruebas de rutina se corren por el arnés E2E interno (Bloque V), disparadas y leídas por Claude Code/Hermes sin intervención de Arturo. Telegram real se reserva para la evidencia final de cierre de un bloque y para los ejemplos de la bitácora. Toda evidencia se etiqueta `[arnés]` o `[E2E real]` — mezclarlas sin etiqueta invalida el reporte (L3). La ventana de pruebas se declara con timestamp en ESTADO.md; un reinicio dentro de ella invalida todos sus resultados sin rescate parcial (L8).

## 7. Flujo completo de un ciclo (el ritmo normal del día a día)

1. Arturo abre conversación en el Proyecto → pega ESTADO.md + último reporte (o dice "sin cambios desde ayer").
2. Chat de diseño analiza evidencia → emite UN bloque (o pide lo que falte).
3. Arturo lo pega en Claude Code → Claude Code verifica contra HAS/estado (C12) → ejecuta → reporta con el formato estándar → actualiza ESTADO.md y BLOQUES.md.
4. Arturo trae el reporte (y transcripts si hubo pruebas) al chat → se cierra el bloque en el registro → siguiente.
5. Los dos Claudes citan; ninguno recuerda. La memoria del proyecto son los tres archivos, no el contexto de nadie.

## 8. Arranque de este protocolo (una sola vez)

En la próxima sesión de Claude Code, antes de cualquier otro bloque:
- Crear `docs/PROTOCOLO.md` (este documento), `docs/ESTADO.md` (llenado con el estado real de HOY: qué fases/bloques están de verdad cerrados con evidencia, qué bugs quedaron abiertos del 22-jul — el guard, el idioma, las cifras contradictorias, el diagnóstico residual) y `docs/BLOQUES.md` (reconstruyendo el registro: bloques A…N con su estado real, L parcialmente DEROGADO, M DEROGADO, O pendiente/en curso).
- Commit de los tres al fork.
- Arturo sube este mismo documento al contexto del Proyecto en claude.ai (Project knowledge) para que el chat de diseño lo tenga siempre.

## 9. La carga de Arturo (v1.2 — regla suprema, manda sobre todo lo demás de este documento)

Si cumplir cualquier regla de este protocolo requiere que Arturo trabaje más, decida más o se estrese más, **la regla está mal aplicada.** El protocolo existe para coordinar Claudes entre sí; Arturo no es el bus de mensajes ni el árbitro de disputas de versiones.

**9.1 — Los únicos 4 trabajos de Arturo.** (1) Pegar ESTADO.md al abrir una conversación (un copy-paste); (2) contestar decisiones agrupadas (ver 9.3); (3) aprobar gastos y acciones irreversibles; (4) disfrutar la bitácora cuando quiera. TODO lo demás — verificar versiones, detectar duplicados, resolver qué documento manda, perseguir cierres — es trabajo de los Claudes. Una sesión que le pida a Arturo algo fuera de estos 4 debe primero agotar cómo resolverlo sola.

**9.2 — Versiones declaradas: fin de los interrogatorios.** La primera línea de ESTADO.md declara siempre: `Versiones vigentes: HAS vX.Y · PROTOCOLO vX.Y`. Toda sesión resuelve cualquier duda de versión contra esa línea, no preguntándole a Arturo. Si la copia del Project knowledge es más vieja que lo declarado: la sesión lo dice en UNA línea, pide solo las secciones cambiadas (o trabaja con ESTADO.md como resumen autoritativo si la tarea no depende del texto exacto), y sigue. Prohibido el cuestionario de sincronización dirigido a Arturo.

**9.3 — Economía de decisiones.** Máximo UNA petición de decisión por respuesta, siempre con recomendación incluida para que "ok" baste como respuesta. Las decisiones no urgentes NO se preguntan en el momento: se anotan en la casilla "Decisiones pendientes" de ESTADO.md con un default propuesto, y Arturo las revisa en lote cuando quiera (sugerido: domingo). **Si una decisión pendiente cumple 7 días sin respuesta, aplica el default propuesto** — excepto dinero, seguridad o acciones irreversibles, que siempre esperan su "sí" explícito sin plazo.

**9.4 — Las disputas entre Claudes las resuelven los Claudes.** Ante conflicto de documentos o de estado, la sesión resuelve citando la jerarquía (§1) y lo registra. Solo si es genuinamente irresoluble, se le presenta a Arturo como UNA pregunta con opciones a/b y recomendación — nunca como el problema crudo para que él lo desenrede.

**9.5 — Higiene de archivos del Proyecto.** Los archivos del Project knowledge conservan su nombre exacto entre versiones. Si aparece un duplicado renombrado (`archivo1.md`), la sesión que lo detecte lo reporta con la instrucción exacta de un paso ("borra X, conserva Y") — no con un análisis.

**9.6 — Termómetro.** Si Arturo expresa saturación o estrés por el proceso mismo, eso es un bug del protocolo con prioridad sobre cualquier bloque técnico: la sesión propone qué simplificar antes de continuar con lo que estaba.

---

## 10. Arquitectura de trabajo (v1.3 — corrige el flujo, no solo las reglas)

**10.1 El centro es Claude Code.** Su día a día: Arturo abre sesión (o da `/clear` y saluda) → Claude Code ya leyó `CLAUDE.md`, `ESTADO.md`, `BLOQUES.md` y git → saluda proponiendo el siguiente paso → Arturo aprueba o redirige. **Arturo no pega ESTADO, no resume la sesión pasada, no traslada mensajes entre herramientas.** Si un flujo requiere que Arturo sea mensajero, el flujo está mal (§9.1).

**10.2 El chat de diseño es consultor, no eslabón.** Se usa para replanteos grandes de arquitectura, cada varias semanas. Si Claude Code se atora en algo de diseño tras 2 intentos verificados, **él mismo despacha la consulta** al modelo más capaz disponible (LiteLLM), con el problema destilado — y le presenta a Arturo la conclusión, no el ida y vuelta. Cuando sí haga falta un chat de claude.ai, Claude Code prepara el texto listo para pegar.

**10.3 Regla del contexto congelado.** Los archivos del Project knowledge son una foto tomada al nacer la conversación: actualizar el proyecto NO refresca chats abiertos. Por eso: **si se actualizó un documento, se abre chat nuevo — las conversaciones viejas se cierran, no se reeducan.** Y ninguna sesión interroga a Arturo sobre versiones: se resuelve contra la primera línea de `ESTADO.md` (§9.2).

**C15. Permisos por allowlist (v1.3).** Claude Code opera con una allowlist en `.claude/settings.json` (git, tests, lectura, python del venv, systemctl de las units de Hermes, journalctl, arnés de pruebas) y un `sudoers.d` acotado a NOPASSWD solo para esas units. Deny permanente: sudo genérico, `rm -rf`, `push --force`, DROP/DELETE, edición de `.env`. **La allowlist crece con evidencia** (comando pedido ≥3 veces sin incidente → candidato, se registra), nunca por comodidad del momento. Objetivo: que Arturo no vuelva a teclear en terminal para tareas de rutina.

**P6.1 Cuenta QA de Telegram (v1.3, condicionada a L13).** Cuenta de usuario dedicada sobre chip propio, controlada por Claude Code vía userbot. (a) No se automatiza hasta cerrar L13 y su session string vive solo en la bóveda verificada; (b) la cuenta madura ≥5 días con uso manual y mantiene volumen bajo; (c) recarga bimestral registrada en E10; (d) reparto: arnés = rutina, cuenta QA = evidencia `[E2E real]`, Arturo = solo bitácora.

**C16. Presupuesto autónomo de pruebas (v1.3.1).** Claude Code gasta hasta **$100 MXN/mes** de DeepSeek en pruebas sin pedir permiso, con cortacircuitos: máx $10 MXN/día, alto y reporte si una corrida pasa de $3 MXN, aviso al llegar a $80 MXN. Gasto etiquetado `test`, separado del uso real en el ledger y en la vista de finanzas. Fuera de pruebas, DeepSeek sigue requiriendo "sí" explícito de Arturo.

**P7. Guion de pruebas y verificación de memoria (v1.3).** Toda validación grande se corre contra `docs/GUION_PRUEBAS.md` (el día completo de Arturo, de despertar a dormir, incluyendo cambio de cuatrimestre, audios, mala redacción, credenciales, caídas y casos límite). La memoria se verifica en **tres capas**: A) mecanismo, con la cuenta QA (persistencia, cruce de sesión, supervivencia a compactación, contradicciones, **aislamiento de identidad obligatorio**); B) inspección de solo-lectura sobre la memoria real de Arturo, sin escribir en ella; C) el juicio de Arturo en la bitácora, que vale más que A y B juntas. La simulación del día completo corre semanal y su resultado (X/6 criterios) va a ESTADO.md junto al % de `has_progress.py`.

---

*Sobre todo lo demás: la sección 9. Y sobre el flujo diario: la sección 10 — si Arturo está haciendo de mensajero, algo se está aplicando mal.*
