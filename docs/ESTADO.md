# Estado de Hermes — 22-25 Jul 2026

**Versiones vigentes: HAS v1.4 · PROTOCOLO v1.3.1**

## Bloque S.5 + fix de ventana O.6 — cascada de compactación infinita, CERRADO (27 Jul 2026)

Encontrado sin buscarlo, diagnosticando O.6 en vivo con el arnés interno
(mismo mecanismo de Bloque V, sesión real `20260723_014401_467841eb`,
sin tocar Telegram real): la sesión entró en compactaciones repetidas
(2, 3+ veces seguidas) sin completar nunca el turno.

**Causa raíz real, confirmada por lectura de código + reproducción en
vivo:** el target normal de compresión (`threshold_tokens *
summary_target_ratio`, ~104,857 tokens con Gemini) queda muy por encima
de `ESCALATION_SAFE_TRIGGER_TOKENS`/`HARD_CAP` (30K/40K, Bloque S del 23
Jul) -- una vez que una sesión cruza 30K tokens, cada turno vuelve a
disparar compresión de inmediato, para siempre, sin importar cuántas
veces se comprima. Búsqueda en el repo real de NousResearch/hermes-agent
en GitHub confirmó que este ES un patrón conocido de la familia
upstream ([#53008](https://github.com/NousResearch/hermes-agent/issues/53008),
infinite compression loop) aunque el mecanismo exacto aquí es propio de
Bloque S (constante propia de Hermes, no del upstream).

**Fix (Bloque S.5, `agent/turn_context.py`):** mientras el disparo sea
por la escalera de respaldo (no por el umbral del primario), el target
real de esa pasada apunta a `ESCALATION_TARGET_TOKENS` (20K) en vez del
20% del primario, restaurado al salir del bucle. Verificado en vivo:
la MISMA sesión que antes cascadeaba sin fin ahora completa en una sola
pasada (llegó a intentar la llamada real al modelo, bloqueada solo por
un límite de cuota real de tanto probar hoy -- no por el bug).

**Bonus, mismo diagnóstico:** `run_incident_verification()` (O.6) usaba
una ventana de ±10 min anclada a "ahora" -- un incidente real de hace 16
minutos (el propio cierre no-limpio del gateway de esta sesión, ver
Bloque 6 abajo) quedó fuera de la ventana. Subido a 45 min. Verificado
en vivo: el mismo incidente real ahora SÍ aparece en la evidencia
inyectada al modelo.

**Regresión:** 273 tests verdes (214 `test_context_compressor` + 22
`test_turn_context` + 5 smoke S4 + 3 identity-preservation + 29 smoke
completo), 0 fallas nuevas. Desplegado a producción con la excepción de
reinicio (12:38, segundo uso de la sesión) + 29/29 smoke contra el
servicio real.

**Hallazgo aparte, sin arreglar:** `/new` SÍ funciona (confirmado
leyendo `gateway/run.py`/`slash_commands.py`) pero requiere confirmación
explícita sí/no (`approvals.destructive_slash_confirm`) -- no es
instantáneo como parecía en una prueba inicial. No es un bug.

## OT-QA -- EN ESPERA de respuesta de Telegram (27 Jul 2026, tarde)

2 hipótesis reales probadas y descartadas hoy (IP residencial vs. móvil
-- probado en vivo con el hotspot del teléfono, mismo error; recrear la
app -- no es técnicamente posible, api_id/api_hash son permanentes).
Causa más probable, según la documentación OFICIAL de Telegram: cuentas
nuevas quedan bajo restricción automática anti-abuso, se resuelve
escribiendo a `recover@telegram.org`. Correo redactado y enviado por
Arturo mismo. **En espera de respuesta real, puede tardar días.**
Detalle completo en `docs/BLOQUES.md`.

## Bloque O.6 -- CERRADO (27 Jul 2026), el hallazgo CRÍTICO desde el 22 Jul

Con cuota real disponible, se reprodujo el hallazgo original ("el
modelo prioriza narrativa sobre instrucciones explícitas") y se
arregló de raíz. El modelo ignoraba la evidencia real inyectada Y una
instrucción reforzada de texto, llamando `read_file`/`terminal` sobre
un log rotado de hace un mes y presentándolo como el estado actual.
Fix real: se le quita mecánicamente el acceso a herramientas durante
ese turno (`agent.tools = []`, restaurado self-healing al turno
siguiente) -- no otra instrucción, sino quitarle la posibilidad real.
Verificado en vivo: 0 llamadas a herramientas en 3 intentos (antes,
100%). Backstop adicional (O.6.1): si la evidencia real dice que sí
hay evidencia y la respuesta la niega, se reemplaza citando la
evidencia real tal cual. 353 tests corridos, 0 regresión real (2
fallas confirmadas pre-existentes con `git stash`). Desplegado a
producción (13:13:33, tercer reinicio de la sesión). Detalle completo
con las 3 reproducciones reales en `docs/BLOQUES.md`.

## HAS Fase 2 — Bloque 6 (corte real a producción) — EN OBSERVACIÓN (27 Jul 2026)

Corte ejecutado con Arturo presente, siguiendo el procedimiento de la
skill `hermes-upgrade`. Antes de tocar nada, verificación real (no
asumida) de que `arturo/base` es superset del código de producción: los
41 commits propios que `main` tenía de más desde el ancestro común se
confirmaron uno por uno, con `git merge-base --is-ancestor`, como ya
cherry-pickeados en `arturo/base` (Tarea 1, Tarea E/E v2, Tarea I,
Bloques AF/AG/AH, voz, caché, etc.) -- salvo 4 archivos vivos
(`CLAUDE.md`, `docs/ESTADO.md`, `docs/BLOQUES.md`,
`docs/BITACORA_ARTURO.md`) que sí divergían (versiones congeladas desde
que se creó el worktree) y se restauraron a mano después del reset,
verificado con `diff` = 0 contra el `main` anterior.

**Pasos reales ejecutados, con evidencia:**
1. Tag de rollback `pre-bloque6-cutover-20260727` sobre `7e33bae1c`
   antes de tocar nada. Comando de vuelta atrás si algo falla:
   `git reset --hard pre-bloque6-cutover-20260727`.
2. `/mnt/seagate` encontrado desmontado -- causa real confirmada en
   `journalctl -k`: desconexión sucia por error de I/O real a las
   08:22 de hoy (`Buffer I/O error`, `JBD2 I/O error`), no algo que
   Hermes causara. Montado manual (`udisksctl`), journal de ext4
   recuperado al montar, sin errores nuevos desde entonces. Pendiente:
   Arturo corra `smartctl` para descartar disco fallando vs.
   cable/puerto USB.
3. `hermes-gateway` parado por Arturo mismo (el hook bloqueó
   correctamente el intento automático de `stop`, como debe ser).
   **Hallazgo real, no bloqueante:** el cierre no fue limpio
   (`SIGTERM` recibido, 8s de shutdown, `exit code 1` en vez de 0) --
   bug real en el manejador de cierre, pendiente de diagnóstico
   aparte.
4. Respaldo real, 700M, en
   `/mnt/seagate/backups/hermes_pre_upgrade_20260727.tar.gz` (excluye
   `venv`/`node_modules`, reproducibles) -- verificado íntegro con
   `tar -tzf`.
5. `git reset --hard arturo/base` + restauración de los 4 archivos
   vivos + commit `b11a117bf` con el detalle completo.
6. Reinicio con la ÚNICA excepción pre-aprobada del hook
   (`systemctl --user restart hermes-gateway.service`) -- 11:49,
   resultado: activo. Único uso de la excepción esta sesión.
7. **29/29 smoke tests pasan contra producción real** (no un worktree
   aislado). Confirmado en vivo: el fix de `mensajes_pendientes`
   (`CREATE TABLE IF NOT EXISTS`, bug real encontrado en Bloque 4) ya
   está en el `hermes_state.py` de producción. `hermes-gateway` y
   `litellm` activos, sin errores/tracebacks en logs desde el
   reinicio.

**NO cerrado todavía** -- falta la ventana de 24h de observación real
de logs (paso 6 del procedimiento) antes de declarar Bloque 6, y con
él HAS Fase 2 completa, cerrado. Revisar logs mañana (28 Jul) antes de
cualquier declaración de cierre.

## HAS Fase 2 (Blindaje y actualización) — Bloques 4 y 5 CERRADOS (27 Jul 2026)

Con Bloque 1 (rebase, arriba) ya cerrado, seguí con los entregables que
faltaban de Fase 2 según el HAS:

- **Bloque 4 — 10 smoke tests** (`~/hermes-019/tests/smoke/`): arranque
  CLI, arranque gateway (dry-run), slash commands, detector de
  complejidad, guardias de permisos, cola de mensajes, tick de curator,
  lectura de MEMORY/USER, pipeline de media, fallback de proveedores.
  **29/29 pasan.** De paso, otro hallazgo real: la tabla
  `mensajes_pendientes` existe en producción pero nunca tuvo
  `CREATE TABLE` en el código -- una instalación nueva jamás la habría
  tenido. Arreglado.
- **Bloque 5 — ensayo de actualización futura + skill `hermes-upgrade`**:
  678 commits nuevos ya en upstream (¡en lo que duró esta sesión!),
  ensayo real en rama desechable confirma que `plugins/platforms/
  telegram/adapter.py` es un punto caliente recurrente. Procedimiento
  completo de 6 bloques documentado en
  `~/hermes-019/skills/hermes-upgrade/SKILL.md`.

**Solo falta el Bloque 6 de Fase 2 (corte real a producción) -- por
diseño, ese requiere a Arturo presente, no se hace solo.** Detalle
completo en `~/hermes-019/docs/MIGRATION_LOG.md`.

## Bloque 1 (rebase a upstream 0.19.x, `hermes-019`/`arturo/base`) — CERRADO (26-27 Jul 2026)

Retomé donde quedó la sesión del rebase y cerré todo lo pendiente, con
evidencia real en cada paso, no solo "se ve bien":

1. **Los 8/8 fallos reproducibles eran regresión real, no contaminación.**
   `Bloque S.1` (tope duro absoluto, ya existía en producción) tenía su
   propio presupuesto fijo de 3 pasadas, sin coordinar con el nuevo tope
   configurable que unificó upstream -- se sumaban en vez de compartir.
   Arreglado (`39e05c32e`), los 8 pasan.
2. **El pendiente de `last_prompt_tokens` tras interrupción, resuelto.**
   El mecanismo de upstream (snapshot/rollback) ya estaba completo y
   correcto -- el problema real: `Bloque S` (escalada de compresión,
   propio de Hermes) dispara compresión real que 2 tests de upstream no
   contemplaban, dejando un sentinel `-1` que bloqueaba el rollback.
   Arreglado mockeando esos 2 tests igual que sus hermanos (`ad7a23ae9`).
3. **Los 3 cuelgues de `hermes_cli`, causa raíz encontrada y arreglada**
   con `faulthandler` (sin necesitar ptrace, bloqueado en este sandbox):
   `npm audit` real sin red (bloqueado en el guard de `conftest.py`),
   fetch real al catálogo de modelos de GitHub sin mockear (mockeado), y
   un candado sistémico nuevo (`_no_real_network`) que convierte
   cualquier otra llamada de red no mockeada en fallo rápido en vez de
   cuelgue silencioso (`702e55a7d`).
4. **Bonus:** una fuga de logging en un fixture de test causaba 2000+
   "Logging error" en cascada sobre pruebas sin relación -- arreglada
   (`6e82accb1`); explicaba 143 de los 147 fallos que parecían
   "contaminación" en corridas grandes.

**Resultado final, sin ningún cuelgue:** `tests/hermes_cli/` completo
(9,576 tests) -- 9,525 passed, 20 failed, 31 skipped, 0 timeouts.
`tests/run_agent/`+`tests/agent/`+`tests/tools/` -- de 147 fallos
combinados, solo 4 reales y preexistentes (sin relación con el rebase).
Detalle completo, commit por commit, en `~/hermes-019/docs/MIGRATION_LOG.md`.

**Todo pusheado a `fork:arturo/base` como respaldo.** Pendiente real
para el corte a producción (fuera de esta verificación): reconciliar
`tools/telegram_userbot.py` (versión vieja en este worktree, el fix real
solo está en producción) y decidir sobre los 19 fallos dispersos sin
investigar (OAuth dashboard, proveedores custom, CLI de suscripción).

## Incidente de infraestructura (24-25 Jul 2026, noche) — Bash roto por cuota de disco en /tmp, RESUELTO

No es un bloque de trabajo de Hermes -- es una falla de la herramienta
(Claude Code) que impidió trabajar ~3 horas. Se documenta aquí porque
consumió toda la sesión y dejó cambios de infraestructura reales.

**Síntoma:** Bash fallaba con "Exit code 1" sin ninguna salida (ni
stdout ni stderr) para CUALQUIER comando, hasta `echo hi`, en toda
sesión de Claude Code probada (nueva, continuada con `-c`, con
`--safe-mode`, tras reinstalar la versión con `claude install`).
`claude doctor` no reportó problemas de instalación.

**Diagnóstico real:** confirmado con la herramienta `Write` devolviendo
`EDQUOT` ("Disk quota exceeded") al escribir en `/tmp` -- la partición
`tmpfs` de `/tmp` (3.6G) estaba al 80% (2.9G usados), sobre todo por
`/tmp/pytest-of-arturo` (2.4G de sobras de pruebas viejas nunca
limpiadas). Bash captura la salida de cada comando escribiéndola a un
archivo temporal en `/tmp`; sin espacio, esa escritura fallaba
silenciosa y el comando se reportaba como "exit 1, sin salida" sin
importar qué tan trivial fuera. No tuvo nada que ver con la versión de
Claude Code, los hooks, los permisos, ni el canal de "control remoto"
-- todas esas fueron pistas falsas seguidas antes de encontrar la causa
real (~3 horas perdidas antes de buscar en internet, ver regla nueva
en `CLAUDE.md`).

**Fix aplicado, verificado en vivo:** borrado `/tmp/pytest-of-arturo`
-- `/tmp` bajó de 80% a 13% de uso, Bash volvió a funcionar de
inmediato, sin reiniciar la sesión.

**Ambos pendientes, CERRADOS (25 Jul 2026, madrugada), verificado en vivo:**
1. `/tmp` agrandado de 3.6G a 8G vía `systemd` (`tmp.mount.d/size.conf`
   + `mount -o remount,size=8G /tmp` -- el primer intento con
   `daemon-reload` + `remount` sin `size=` explícito no aplicó nada,
   corregido). `df -h /tmp` confirma `8,0G` tras el fix.
2. Cron de usuario instalado y confirmado con `crontab -l`: borra sola
   basura de pruebas (`pytest-of-*`, `hermes_e2e_*`, `hermes-test-home-*`,
   `kanban_per_profile_cap_test_*`) de más de 2 días, todos los días a
   las 4:17 am.

**Regla nueva agregada a `CLAUDE.md`:** ante fallas raras/silenciosas
de la herramienta (no del código de Hermes), buscar en internet antes
de seguir adivinando causas o pedirle a Arturo que pruebe cosas a
ciegas.

## Hallazgo de documentación — commit sin registrar (24 Jul 2026, mediodía)

`1c559f058` ("fix: telegram_userbot login como flujo de 2 pasos, no
bloqueante") se commiteó a las 12:12 pero nunca se documentó aquí -- la
sesión que lo hizo terminó (o fue interrumpida por el incidente de
arriba) antes de actualizar `ESTADO.md`/`BLOQUES.md`. Verificado ahora
(25 Jul, ya con Bash sano): `tests/tools/test_telegram_userbot.py` --
**4/4 tests pasan**. Sin evidencia de prueba en vivo contra Telegram
real de esa sesión (no estuve presente); el commit resuelve un bug real
y verificable por lectura de código: `client.start()` de Telethon
bloqueaba en `input()` esperando el código de verificación por teclado,
imposible desde una herramienta automatizada sin terminal interactiva
-- reemplazado por el flujo de 2 pasos `start_login()`/`complete_login()`
(mismo patrón que el emparejamiento por DM), con manejo explícito de
2FA (`TwoFactorPasswordNeeded`).

## Pendientes sueltos — CERRADO (27 Jul 2026)

Los 4 archivos de respaldo del 9 de julio (18 días sin tocarse) --
Arturo confirmó borrarlos. Eran sin rastrear (nunca entraron a git), así
que no hay commit de por medio, solo se eliminaron del disco.

## Bloque AH (24 Jul 2026, mañana) — bug real de duplicación por compactación, CERRADO

Encontrado siguiendo instrucción de Arturo de verificar y arreglar tras
una prueba E2E de DeepSeek que no completó limpiamente. Detalle
completo, evidencia real, en `BLOQUES.md` sección "Bloque AH". Resumen:
`ContextCompressor._prune_old_tool_results()` copiaba TODOS los
mensajes al entrar (incluida la cola protegida que nunca toca),
rompiendo la identidad de objeto de la que depende
`_flush_messages_to_session_db` para no duplicar filas en `state.db`.
Cada compactación producía una fila duplicada del último intercambio —
confirmado en vivo (mismo timestamp exacto repetido 3-4 veces en
`state.db`). Efecto secundario real: los duplicados fantasma cancelaban
ofertas reales de Tarea E antes de que el "sí" del usuario pudiera
resolverlas (el candado post-incidente "cualquier mensaje de por medio
cancela la oferta" las contaba como mensajes nuevos). Fix quirúrgico:
copiar solo lo que de verdad se modifica (copy-on-write), no todo por
adelantado — mismo patrón que `_strip_historical_media` ya usa en el
mismo archivo. 3 tests nuevos + 446/447 en la regresión completa de
compresión (el único fallo, preexistente, confirmado con `git stash`).
**Prueba E2E de DeepSeek — CERRADA, con dinero real (Arturo pidió
explícitamente "verifica que funcione DeepSeek"):** llamada directa a
las mismas 2 funciones reales de producción del aviso + el mismo POST
mínimo real (`model: chat-reasoning`) que usa el código. Confirmado con
evidencia real: aviso ANTES del despacho, fila nueva real en el ledger
de litellm (`model: deepseek-v4-pro`, no un respaldo gratis), aviso de
costo real DESPUÉS ($0.0000626 USD esta prueba, $0.1666 USD acumulado
el mes). Fase 1 / OT-1 completa — los 4 entregables confirmados.

## Bloque AG (24 Jul 2026, mañana) — memoria SQL real y separada para la cuenta QA, CERRADO

Resuelve el hallazgo AF.4 (memoria de Arturo y de QA mezcladas).
Detalle completo, evidencia real, en `BLOQUES.md` sección "Bloque AG".
Resumen: `agent/agent_init.py` ahora elige `SqlMemoryStore`
(`tools/sql_memory_store.py`, respaldado por `memoria_estructurada` con
`user_id`+`origen='qa'` reales) para la identidad QA
(`tools/qa_identity.py`, user_id=8727618189), y sigue exactamente igual
(`MemoryStore` sobre `MEMORY.md`/`USER.md`) para cualquier otra
identidad. Verificado en vivo con hash de archivo (MEMORY.md/USER.md
byte-idénticos antes/después de un escrito real desde QA) + recall real
en turno nuevo + regresión confirmando que Arturo sigue en su archivo
de siempre. 9 tests nuevos + 93/93 en `tests/tools/` + 444/444 en la
suite más amplia de `agent._memory_store`.

**Con esto, la cuenta QA ya puede usarse sin restricciones** — puede
chatear Y pedir que se recuerden cosas, sin riesgo a la memoria real de
Arturo. Pendiente real, fuera de alcance: Fase 4 de verdad (memoria
estructurada + índice semántico PARA Arturo) sigue sin construir.

## Bloque AF (24 Jul 2026, madrugada) — fix de L13/Bloque AE, CERRADO

Autorizado por Arturo ("sí, trabaja toda la noche") tras revisar las 3
opciones de Bloque AE. Detalle completo, evidencia real y prints en
`BLOQUES.md` sección "Bloque AF". Resumen:

1. **Fix aplicado:** `agent._persist_session()` movida a después de las
   4 correcciones de `final_response` (transform_llm_output, backstop
   anti-fabricación, español O.4, escáner de secretos T.6), con
   `messages[-1]` re-sincronizado antes de persistir. Más:
   `_turn_has_successful_tool_call()` ahora acota su escaneo al índice
   real de esta conversación (reutiliza el índice de Bloque Q.1) en vez
   de confiar sin más en el `role=="user"` más cercano.
2. **Verificado EN VIVO, dos veces, evidencia real en `state.db`:** un
   turno bloqueado por el guard quedó CORRECTAMENTE persistido con el
   mensaje de reemplazo (antes se quedaba con el texto fabricado pese al
   bloqueo); un turno normal con herramienta real persistió limpio.
3. **Regresión:** 7 tests nuevos dirigidos al bug exacto (7/7 verde) +
   23 tests existentes de `finalize_turn`/interrupt (23/23 verde) + suite
   completa `tests/agent/`+`tests/gateway/` (ver resultado real abajo).
4. **Hallazgo nuevo sin arreglar, más urgente que el original:** las
   pruebas en vivo escribieron por accidente una entrada de prueba en el
   `MEMORY.md` REAL de Arturo (limpiada de inmediato con
   `memory_tool.py`) — confirma que el camino real de escritura de
   memoria (archivos planos, no la tabla SQL) no tiene NINGÚN
   aislamiento por identidad. Ver `docs/BITACORA_ARTURO.md`. NO se tocó
   el gating de herramientas sin autorización explícita de Arturo.
5. Prep de OT-QA completada: `telethon` instalado, `tools/telegram_userbot.py`
   listo (rechaza conectar sin session string real en la bóveda —
   4 tests), columna `origen` + `~/.hermes/scripts/limpiar_memoria_qa.py`
   probado con datos sembrados (2 reales + 3 qa → borra exacto 3, reales
   intactos). Cuenta QA ya autorizada (`user_id=8727618189`).

**Resultado real de la suite completa `tests/agent/ tests/gateway/`:**
`125 failed, 12689 passed, 113 skipped, 260 warnings in 921.17s` (15
min). **Los 125 fallos son preexistentes, confirmados con `git stash` +
re-corrida de una muestra de 10 contra el código SIN Bloque AF: fallan
IDÉNTICO (mismo error, `AttributeError: 'GatewayRunner' object has no
attribute '_pending_reprocess_ids'`, sin relación con
`turn_finalizer.py`/`conversation_loop.py`) — no causados por este
bloque. No investigados a fondo (fuera de alcance de Bloque AF), quedan
registrados como bug abierto preexistente, no silenciados.

## Bloque AE (23 Jul 2026) — diagnóstico dedicado, CERRADO en Bloque AF

Diagnóstico puro del "HALLAZGO SIN ARREGLAR" de la sesión de mañana
(fabricación "he guardado tu contraseña" no bloqueada). Detalle completo
con evidencia textual y prints reales en `BLOQUES.md`, sección "Bloque
AE". Resumen:

1. **Causa raíz del incidente ORIGINAL:** no fue un resumen de
   compactación (no existía ninguno activo en ese momento, descartado con
   evidencia) — fue un backlog real de 2 mensajes de Arturo (voz +
   corrección sobre la contraseña de Cisco) que nunca recibieron
   respuesta durante más de una hora, y que `repair_message_sequence()`
   fusiona con el mensaje nuevo por ser 3 `user` consecutivos. El modelo
   respondió a la parte sustantiva (la contraseña) del turno fusionado.
2. **Hallazgo NUEVO más grave, verificado en vivo:** `finalize_turn`
   persiste la sesión a `state.db` (línea 326) ANTES de que corran las
   correcciones de `final_response` (anti-fabricación, español de O.4,
   plugin `transform_llm_output`) — ninguna de esas correcciones vuelve a
   escribir el mensaje ya guardado en `messages`. Confirmado en vivo:
   incluso cuando el guard SÍ bloquea correctamente, `state.db` se queda
   con el texto fabricado original. Esto afecta a las 3 correcciones, no
   solo a Tarea 1.
3. Reproducciones en vivo: 2 de 3 exitosas (arnés E2E interno, sin tocar
   Telegram real); la 3ª (simular la precondición exacta del incidente
   original) bloqueada por cuota diaria de Gemini agotada (límite externo
   real, mismo ya documentado en Bloque AB).
4. Sin fix aplicado — 3 opciones de arreglo con trade-offs en
   `BLOQUES.md`, pendientes de decisión de Arturo en el chat de diseño.
5. Instrumentación de diagnóstico retirada completamente al cierre
   (`git status`/`git diff` en `agent/turn_finalizer.py` limpio) — nada
   queda en cuarentena.

## Corrección de estado real — Fase 1 del HAS (24 Jul 2026, verificado contra código, no contra el documento)

El HAS v1.4 marca Fase 1 "PARCIAL" con 4 pendientes. Verificado contra
código real: **3 de los 4 ya estaban hechos**, el documento no se
actualizó cuando se completaron en sesiones anteriores:
- Whisper→gateway: conectado, 12 transcripciones reales ya en `state.db`.
- `cleanup_audio_cache()`: existe (`gateway/platforms/base.py`) y corre
  sola en el tick periódico junto a imagen/documento.
- `allowed_fails` (rate-limit vs error duro): existe bajo otro nombre,
  `agent/error_classifier.py` + `FailoverReason`, ya integrado.

**Único pendiente real confirmado:** la prueba E2E del aviso de
DeepSeek antes de un despacho real — intentada hoy, reveló el bug de
Bloque AH (ver arriba) en el camino, no completada limpiamente. Ver
Bloque AH para el detalle y el pendiente de re-probar con el fix puesto.

## Sesión de mañana (23 Jul, ~10-11 AM) — Bloques AA-AD

- **AA.1 (causa raíz del fallback caído anoche) — RESUELTO CON
  EVIDENCIA REAL:** Groq (`chat-fallback`) nunca aparece en los logs
  con un error propio porque litellm lo tenía en un **cooldown interno
  stale** (327s+ restantes) de algún fallo real de horas antes -- Groq
  en sí respondía 200 OK al llamarlo DIRECTO (sin litellm). Confirmado
  y resuelto: Arturo reinició `litellm.service`, Groq volvió a
  responder 200 OK a través de litellm inmediatamente después.
  OpenRouter (`chat-fallback3`) sí tiene un límite diario real agotado
  (confirmado con su propio error, no cooldown de litellm).
- **AA.2 (¿Tarea E depende de una respuesta base?) — CONFIRMADO CON
  CÓDIGO:** sí depende, pero de forma más sutil de lo esperado.
  `turn_finalizer.py:605` gatea la oferta en `final_response` truthy --
  y cuando fallan TODOS los proveedores, sí se genera un
  `final_response` (el texto de error mismo). Pero `self_assess_response()`
  hace su PROPIA llamada a `chat-primary` para autoevaluar -- si esa
  llamada TAMBIÉN falla (mismo Gemini agotado), cae al valor por
  defecto `resolvi_con_confianza=True`, que **suprime** la oferta.
  Resultado real: cuando toda la escalera gratis está caída, Tarea E
  se queda en silencio en vez de sugerir DeepSeek, justo cuando más
  ayudaría.
- **AA.3:** hallazgo de diseño reportado, NO arreglado -- pendiente de
  que Arturo decida si quiere un modo "todo gratis caído, ¿autorizo
  DeepSeek de todos modos?" como excepción explícita.
- **HALLAZGO NUEVO, GRAVE, SIN ARREGLAR:** fabricación real confirmada
  -- un mensaje de prueba sin relación con contraseñas recibió una
  respuesta que decía "he guardado tu contraseña..." sin ninguna
  llamada real a la herramienta (`tool_calls=None` en state.db,
  confirmado). El guard anti-fabricación (Tarea 1) SÍ detecta el patrón
  en el texto (regex probado, hace match), pero `_turn_has_successful_tool_call()`
  no bloqueó la respuesta -- causa raíz exacta no confirmada, sospecha
  de interacción con el límite de "última mensaje de usuario" cuando
  hay un resumen de compactación de por medio. Requiere sesión de
  diagnóstico dedicada (mismo nivel que Bloque H/O.6), NO un parche
  rápido. Documentado en `docs/BITACORA_ARTURO.md`.
- **AB (reintentos):** U.2 y otros casos con conversación real grande
  (~40k tokens) siguen fallando incluso después del fix de Groq --
  Gemini se re-agota casi de inmediato con requests reales (aunque
  responde 200 OK a peticiones mínimas de prueba). El arnés (Bloque V)
  tampoco completó turnos grandes limpiamente en 2 intentos --
  necesita más diagnóstico, posible bug propio del arnés, no
  necesariamente de Hermes.
- **AC:** 3 commits de esta sesión y la de anoche pusheados a
  `fork arturo/prod`, verificados con SHA local=remoto.
- **AD:** `docs/BITACORA_ARTURO.md` creado (registro permanente,
  orientado a Arturo, no técnico) + regla agregada a `CLAUDE.md` para
  mantenerlo actualizado en cada cierre de sesión.

## Sesión nocturna autónoma (23 Jul, madrugada) — EN CURSO / cerrada parcialmente

Arturo se fue a dormir tras confirmar W.1. Trabajo autónomo real hecho,
con evidencia, hasta este punto:

- **Q.1 fix confirmado en vivo:** el fix de `current_turn_user_idx`
  (Bloque Q) funcionó -- O.6 citó evidencia real de journalctl por
  primera vez en 3 intentos esa misma noche.
- **Bloque S (E11) completo y verificado en vivo** con la conversación
  real de 285k+ tokens.
- **Bloque T (bóveda) completo**, con un hallazgo de seguridad real
  encontrado y corregido en el camino (la passphrase se filtraba desde
  el propio historial de conversación -- ver `BLOQUES.md` para el
  detalle completo). Bóveda de producción real probada en vivo con
  Arturo (Cisco/blindar), luego limpiada (Bloque Y) a 0 entradas.
- **Bloque U.1 implementado** (guía reforzada de `session_search`) --
  **verificación en vivo (U.2) pendiente**, bloqueada por cuota real de
  Gemini agotada (ver abajo).
- **Bloque V (arnés E2E) construido y validado**:
  `tests/e2e/hermes_harness.py`, corre el pipeline real (config/state.db
  reales, agente real) sin tocar la red de Telegram. Confirmado:
  construcción real, autorización real con el chat_id de Arturo, y un
  turno real completo procesado de punta a punta.
- **Bloque W (confirmación de guardado por voz) implementado y probado
  a nivel de lógica** (detección determinística + máquina de estado de
  confirmación pendiente, mismo patrón que Tarea E) -- **verificación
  en vivo con el modelo real pendiente**, misma razón de cuota.
- **X.5 (regresión de tests existentes):** 101 tests relevantes
  pasando, sin duplicar nada.
- **X.6 (estructura de botones):** verificada programáticamente
  (`reply_markup` válido, texto en español, dentro del límite de 64
  bytes de Telegram). **Verificación VISUAL pendiente para mañana con
  Arturo** -- no se puede confirmar cómo se ve realmente en su
  teléfono desde aquí.
- **X.1-X.4, X.7, X.8: PENDIENTES**, bloqueados por un hallazgo real
  importante: **la cuota diaria gratuita de Gemini es de solo 20
  requests/día** (no por hora) -- confirmado con el mensaje de error
  real de Google. Con todo el volumen de pruebas de esta noche
  (docenas de turnos), es muy probable que esté agotada por el resto
  del día. Groq (fallback) respondió brevemente pero su ventana de
  contexto (128k) no alcanza para la conversación real ya inflada.
  OpenRouter (fallback3) también agotado (límite diario gratuito).
  **No es una falla de código -- es un límite real externo.**

Detalle completo de cada bloque, con evidencia, en `BLOQUES.md`.

---

# Estado de Hermes — 22 Jul 2026

Este archivo no existía antes de hoy (O.8, confirmado por búsqueda en
todo `~/.hermes`). Refleja el estado real conocido hoy, no un plan.

## En producción, funcionando

- Gateway Telegram (`hermes-gateway.service`) + LiteLLM proxy
  (`litellm.service`), ambos activos.
- Tarea E v2 (autoevaluación real vía Gemini, Bloque O): compuertas
  pre-respuesta (O.1) y post-respuesta (O.2) activas, formato de oferta
  fijo (O.3), enforcement de español (O.4), atajo urgente (O.5).
- Ledger de costo DeepSeek real (Bloque I): `~/.hermes/litellm/cost_ledger/`.
- Guard anti-fabricación (Tarea 1) sin el falso positivo de bloques de
  código (O.0).

## OT-0.5 — Emergencia de credenciales: CERRADA (22-23 Jul 2026)

Los 6 pasos tienen evidencia real (comandos + salidas, ver
`CHANGELOG_SISTEMA.md`). Resumen: 3 credenciales activas confirmadas
expuestas y nunca rotadas (GROQ_API_KEY, GEMINI_API_KEY,
GEMINI_CHAT_KEY2) -- las 2 primeras rotadas y verificadas (nueva 200 OK,
vieja 401/403 real), la tercera eliminada por no tener uso en el código
(ya estaba muerta). Cron muerto limpiado. Tar de 487MB sin commits
destruido. Barrido de 8 fragmentos de llaves viejas: limpiado en vivo y
en backups, 0 hits salvo `state.db` (residuo aceptado y documentado --
llaves ya muertas, tocar esa tabla violaría la regla de no DROP/DELETE
SQL directo de esta sesión).

**Extensión post-cierre (pedido directo de Arturo, "busca todas las apis
que tengo"):** encontró 3 fuentes de exposición fuera del alcance
original (`~/hermes_bot/` con el TELEGRAM_BOT_TOKEN activo duplicado,
ya eliminado; un tercer backup real con `.env` en texto plano, purgado;
`auth.json`, sin secretos crudos). Todas las 10 credenciales activas
restantes probadas en vivo: 8 funcionan, **ELEVENLABS_API_KEY autentica
pero le faltan todos los permisos que Hermes necesita** (hallazgo
operativo, no de seguridad, pendiente de revisar en el dashboard de
ElevenLabs).

## Bloque Q — RETOMADO en Q.2 (23 Jul 2026)

Q.0 y Q.1 hechos (fix de código aplicado, sin commitear). Q.2: segundo
intento en curso -- instrumentación de confirmación reactivada,
`hermes-gateway.service` reiniciado a las 00:38:38, esperando que
Arturo reenvíe los 2 mensajes de prueba (O.6 y ETH/O.1). Q.3-Q.5 sin
empezar. Detalle completo en `~/.hermes/hermes-agent` `BLOQUES.md`,
sección "Bloque Q". El fix de Q.1 sigue **no confirmado end-to-end**.

## Bugs abiertos, confirmados con evidencia real, SIN resolver

1. **CRÍTICO — Fabricación de evidencia de incidentes (O.6).** Pese a 3
   capas de defensa (skill, disparo automático forzado, guard de Tarea 1),
   Hermes sigue inventando líneas de log/timestamps al responder "verifica
   qué falló". Evidencia completa en `~/.hermes/reporte_bloque_o_22jul.md`
   y en la respuesta de O.7 (22 Jul). Falló 2 de 2 intentos reales.
   Requiere sesión de diagnóstico dedicada (estilo Bloque H, con `print()`
   en vez de `logger`, por el blind spot conocido de
   `agent.conversation_loop`).
2. **O.4 sin rastro de ejecución en un caso real.** Mensaje real 100% en
   inglés (id 15885, 22-jul 17:10:10) no generó ninguna línea de log de
   O.4 (ni éxito ni el except que sí loguea). No diagnosticado.
3. **Hueco arquitectónico en O.1 vs `web_search` nativo.** La regla de
   conflicto de precios de O.1 solo ve los datos que el propio código
   inyecta antes del turno (Brave/CoinGecko) -- no tiene visibilidad
   sobre los datos que el modelo obtiene por su cuenta llamando a
   `web_search` durante el turno. Confirmado con un caso real (ETH
   $1,917-1,929 vs $1,736.63 presentados sin aviso, mensaje 15885) donde
   el conflicto vino de 3 llamadas nativas a `web_search`, no de la
   inyección de O.1. No mitigado.
4. Cron roto apuntando a `~/.hermes/scripts/vigilar_hermes.sh`
   (inexistente) -- hallazgo de Bloque K, fuera de alcance, sin tocar.

## Cobertura de pruebas real (O.7, 22 Jul)

De 6 casos E2E definidos: 1 pasó limpio, 1 mostró evidencia real negativa
(nunca reintentado tras los fixes), 2 nunca se probaron bajo el
mecanismo nuevo, 1 nunca se envió, 1 falló las dos veces que se probó.
Detalle completo en la respuesta de O.7 (22 Jul) y en
`~/.hermes/reporte_bloque_o_22jul.md`.

## Sin contexto / no confirmado

- No tengo el detalle de qué encontró específicamente "Bloque N" (el
  atajo O.5 se implementó según la especificación recibida, sin poder
  confirmar que cubre exactamente lo que N.1 identificó).
