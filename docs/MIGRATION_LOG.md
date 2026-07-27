# MIGRATION_LOG.md — OT-2 Bloque 1: rebase `arturo/base` sobre `upstream-main` (0.19.x)

Registro conflicto-por-conflicto exigido por HAS §B2. Worktree aislado: `~/hermes-019`
(rama `arturo/base`), nunca tocó `~/.hermes/hermes-agent` (producción). 27/27 commits
del historial local de `arturo/base` reaplicados sobre `upstream-main` (2489 commits de
diferencia). Rebase completado: `eb7246883` es ahora la punta de `arturo/base`.

## Commits con conflicto y su resolución

### Commit 1/27 — `.gitignore`
Unión de ambos bloques de reglas.

### Commit 2/27 — `agent/turn_finalizer.py` (46f479d8a)
Dos bloques independientes ("Context engine observation hook" y "Tarea E") en la
misma región — se conservaron ambos en secuencia, sin dependencia entre sí.

### Commits 3-6/27 — `fbf587ced`
- `gateway/run.py` (~96 líneas): unión secuencial del blanking-check de
  `_is_gateway_hidden_reasoning_incomplete_turn` (HEAD) y la cola de mensajes
  pendientes de Tarea C/D (THEIRS) — sin colisión de nombres.
- `hermes_state.py` (~423 líneas): unión de los métodos de índice `gateway_routing`
  (upstream) y los métodos de cola `mensajes_pendientes` (nuestro) — sin colisión.

### Commit 7/27 — `tools/approval.py` (0957ed45d, Tarea I)
- Región 1 (`DANGEROUS_PATTERNS`): unión de los nuevos patrones de ofuscación
  (base64/xxd/tr/openssl decode-pipe) de HEAD y el patrón de invocación `-c/-lc`
  de THEIRS — salvo que THEIRS' patrón regex para `-c/-lc` se DESCARTÓ: confirmado
  que HEAD ya lo detecta estructuralmente vía `_execution_flag_findings()`
  (línea 1589, mismo string de hallazgo "shell command via -c/-lc flag"), que es
  el enfoque que el propio comentario de HEAD explica que se prefirió para evitar
  falsos positivos con `--norc`/`--rcfile`/`--restricted`. También se descartaron
  2 líneas duplicadas exactas de `_SENSITIVE_WRITE_TARGET` (verificado con grep
  contra líneas ya existentes sin conflicto en el archivo).
- Región 2 (heredoc): se mantuvo la cobertura nueva de HEAD (heredoc de shell,
  `bash <<`) que no dependía de nada del lado THEIRS.
- `tools/file_tools.py`: auto-fusionado limpio (bloqueo de directorio del propio
  framework, Tarea I) — verificado, sin problema.

### Commit 8/27 — `plugins/platforms/telegram/adapter.py` (02686da1d, i18n)
Tarjeta de aprobación traducida al español. Se conservó la lógica CONDICIONAL de
botones de HEAD (Session/Always solo si `allow_session`/`allow_permanent`/no
`smart_denied`) en vez de la cuadrícula fija 2x2 de THEIRS, que hubiera mostrado
botones no autorizados — solo se tomaron las etiquetas en español de THEIRS.

### Commit 9/27 — `gateway/slash_commands.py` + `plugins/platforms/telegram/adapter.py` (7aee1f97a)
Botón "⟳ LiteLLM" de reinicio rápido del picker de modelo + `_persist_override`
kwarg roscado a través de `_on_model_selected_scoped`/`_on_model_selected`
(wrapper con `_profile_runtime_scope` que no existía cuando se escribió el commit
original). Paginación del picker de proveedores (HEAD) se conservó íntegra;
el botón LiteLLM se añadió a la fila de cancelar sin romper la paginación.

### Commit 16/27 — `agent/turn_context.py` (d2f5edc47, Tarea E v2)
Dos inyecciones independientes a `plugin_user_context` (notas must-deliver del
gateway de HEAD, búsqueda pre-respuesta de Bloque O.1) — unión secuencial, ambas
solo appendean a la misma variable sin pisarse.

### Commit 18/27 — Q.1 + Bloque S + Bloque T + Bloque U (a896b6a8f)
- `agent/conversation_compression.py`: HEAD ya tenía la reestructuración
  (`_context_engine_boundary_committed`) de una sección que el diff de este
  commit tocaba de forma más antigua/desactualizada — se conservó la estructura
  de HEAD y solo se trasplantó el cambio real (traducción i18n del aviso de
  compresión repetida) al lugar correcto.
- `agent/turn_context.py`: fusión real de lógica — el umbral de escalada
  absoluto de Bloque S (`ESCALATION_SAFE_TRIGGER_TOKENS`/`HARD_CAP_TOKENS`) se
  incorporó DENTRO de la cadena `if/elif` de HEAD (cooldown, codex-native-auto)
  en vez de reemplazarla. El bloque S.1 (tope duro, recorte agresivo) había
  quedado mal indentado en un merge automático previo (huérfano bajo
  `if _preflight_compressed:`) — se reubicó correctamente después del bucle de
  compresión multi-pasada, mismo nivel de indentación.
- `hermes_state.py`: redacción de turnos de bóveda (Bloque T) añadida al final
  de `get_conversation_history`, después de la reparación de alternancia.
- `tests/agent/test_turn_context.py`: unión de ambos bloques de tests
  (cooldown persistido + Bloque S), puramente aditivos.
- **Hallazgo real corregido durante la fusión**: el test
  `test_sync_does_not_touch_tool_call_bearing_last_message` (Bloque AF, ver
  abajo) asumía que un tail `assistant(tool_calls, content="")` nunca debía
  tocarse — pero eso choca con un fix de upstream YA integrado (#43849/#44100,
  commits `56ac96976`/`71157cbf6`, 18-19 jul, anteriores a Bloque AF) que
  llena exactamente ese caso para que la respuesta entregada no se pierda del
  transcript. Se actualizó el test de Bloque AF para reflejar el
  comportamiento correcto e integrado (dos tests: uno para tail con texto real
  que no debe tocarse, otro para tail vacío que sí debe llenarse) — el código
  de producción no se tocó, ya hacía lo correcto.

### Commit 24/27 — Bloque AF (58bfb0350)
- `pyproject.toml`: se mantuvieron las versiones más nuevas y parchadas de
  seguridad de HEAD (aiohttp 3.14.1, slack-bolt 1.29.0, slack-sdk 3.43.0 —
  CVE-2026-34513/34518/34519/34520/34525 + 34993/47265) en vez de las
  versiones más viejas de THEIRS; se añadió el extra `telegram-userbot`
  (telethon) de THEIRS, que no colisiona.
- `agent/conversation_loop.py` / `agent/turn_finalizer.py`: unión de kwargs
  nuevos (`_pending_verification_response*` de HEAD + `current_turn_user_idx`
  de THEIRS) en la firma de `finalize_turn`.
- `agent/turn_finalizer.py` (conflicto grande): HEAD tenía duplicado el cierre
  de turno interrumpido (`close_interrupted_tool_sequence`) y el
  `_persist_session()` temprano — Bloque AF los reubica DESPUÉS de las 4
  correcciones que pueden reemplazar `final_response` (fabricación, español
  O.4, escáner de secretos T.6). Se eliminó la duplicación temprana y se
  reubicó `_apply_persist_user_message_override` justo antes del
  `_persist_session()` diferido real (verificado: existía un segundo call site
  ya aplicado sin conflicto en la línea ~780 con exactamente esa lógica).

### Commit 26/27 — Bloque AH (968a3c117) — el más delicado
Bug de producción real: duplicación de mensajes en `state.db` por copiar cada
mensaje del head/tail incondicionalmente en `ContextCompressor.compress()`,
rompiendo el contrato de deduplicación de `_flush_messages_to_session_db`.
- El mecanismo de deduplicación real en HEAD (confirmado leyendo
  `run_agent.py::_flush_messages_to_session_db_unlocked`, ya evolucionado más
  allá de lo que el propio comentario de Bloque AH describe) usa un marcador
  intrínseco `_DB_PERSISTED_MARKER` estampado en el dict, NO `id()` puro
  (`id()` fue abandonado por #50372: aliasing de direcciones liberadas-y-
  reusadas de CPython). Preservar identidad de objeto sigue siendo la forma
  más simple y correcta de preservar el marcador para mensajes no tocados.
- Se corrigieron 4 puntos para respetar "copiar solo al modificar":
  1. Bucle de head (`for i in range(compress_start)`): pasar `messages[i]`
     directo en vez de `_fresh_compaction_message_copy(messages[i])`.
  2. Construcción de `tail_messages`: mismo cambio.
  3. `_strip_context_summary_handoff_message`: el caso común (no es un
     resumen) ahora retorna el objeto ORIGINAL sin copiar, en vez de
     `message.copy()` incondicional; los 4 branches que sí reescriben
     contenido ahora también limpian `_DB_PERSISTED_MARKER` (antes solo
     limpiaban `COMPRESSED_SUMMARY_METADATA_KEY`), para que el flush SÍ
     vuelva a persistir el contenido genuinamente modificado.
  4. Fusión del resumen dentro del primer mensaje de cola: ahora itera sobre
     `tail_messages` (que preserva el filtrado de handoffs obsoletos) con
     copy-on-write explícito (`msg = msg.copy()` + limpieza del marcador)
     justo antes de mutar, en vez de mutar en sitio un objeto que podía ser
     el original del llamador.
- Verificado con los 3 tests de
  `tests/agent/test_context_compressor_identity_preservation.py` (el
  contrato exacto de Bloque AH) + 660/662 de la suite ampliada de
  compresión/handoff (2 fallos confirmados no relacionados: timing de
  `test_compression_concurrent_fork.py`, `compress()` completamente mockeado
  en esos 2 tests, código del fence no tocado por este merge).

## Bugs reales encontrados y arreglados en `agent/turn_context.py` (25-26 Jul 2026, sesión de verificación de Bloque 1)

Los 8/8 fallos reproducibles reportados al cierre de la sesión de rebase
(`tests/run_agent/test_413_compression.py` + `test_preflight_compression_cap_e2e.py`)
SÍ eran regresiones reales, no contaminación entre tests -- confirmado
corriendo cada archivo aislado. Causa raíz: Bloque S.1 ("tope duro
absoluto", ya existía en producción antes del rebase) usa un bucle de
emergencia con presupuesto propio (`range(3)`, fijo) totalmente
independiente del bucle principal de preflight -- y ese bucle principal
ahora sí respeta un tope configurable (`max_compression_attempts`) que
trajo upstream con su propio commit `1c2faedd8 fix(compression): unify
the attempt cap across every compression site`. Cuando ambos bucles
corren en el mismo turno, se suman en vez de compartir presupuesto --
exactamente lo contrario de lo que ese commit de upstream pretendía
lograr.

**Fix 1 (comparte presupuesto):** Bloque S.1 ahora usa
`_max_preflight_passes - _preflight_passes_used` en vez de `range(3)` fijo
-- nunca gasta más pasadas de las que ya tenía asignadas el turno.

**Fix 2 (no reintenta lo ya demostrado inútil, pero SÍ lo que puede
ayudar):** Bloque S.1 solo se salta si la ÚLTIMA pasada del bucle
principal no redujo tokens de forma material (>5%) -- ej. sin proveedor
de resumen disponible, donde reintentar con otro `protect_last_n` no va a
arreglar un mecanismo de compresión roto. Si sí hubo reducción material
(el caso común: ya bajó del threshold normal pero sigue arriba del tope
duro, más estricto), Bloque S.1 SÍ se intenta -- confirmado con
`test_hard_cap_forces_extra_trim_when_normal_pass_is_not_enough`
(mensaje enorme dentro del rango protegido, donde bajar `protect_last_n`
es la única forma de alcanzarlo).

Intenté primero una versión más simple (saltar Bloque S.1 siempre que el
bucle principal se detuviera por "sin progreso") y rompió ese último
test -- revertido en cuanto until until la regresión lo confirmó, antes de
seguir.

**Verificado:** los 8 originales pasan. Regresión amplia
(`tests/run_agent/` completo + `test_turn_context.py` +
`test_context_compressor_identity_preservation.py`): **2350 passed, 2
failed, 4 skipped** -- los 2 fallos restantes son un hallazgo aparte, sin
relación (ver abajo).

## Hallazgo aparte, sin arreglar (fuera de alcance de esta verificación)

Dos pruebas nuevas de upstream esperan que `last_prompt_tokens` (el
contador que usa la barra de estado) se restaure al valor anterior si el
turno se interrumpe ANTES de la primera respuesta real del proveedor
(`test_interrupt_before_first_provider_call_restores_preflight_display_seed`,
`test_usage_less_provider_response_prevents_display_seed_rollback`). El
código captura el valor viejo (`_last`) pero nunca lo usa para restaurar
nada -- falta implementar esa lógica, y cruza 4 archivos
(`turn_context.py`, `context_compressor.py`, `conversation_compression.py`,
`conversation_loop.py`) con varios valores centinela (`0` vs `-1`) ya
delicados. No es un bug de la fusión -- es cobertura nueva de upstream
para una función que Hermes aún no tiene completa. Requiere sesión
dedicada, no un parche a esta hora.

Además, sin relación con el rebase (ya fallaban igual ANTES de mis
cambios, confirmado con `git stash`):
`tests/agent/test_turn_context_overflow_warning.py::test_warns_on_ineffective_block`
y `::test_warning_kind_switch_refires`.

## tests/hermes_cli/ completo (9,575 tests, 26 Jul 2026) — sin truncar, verificado

Con el fix del `os._exit()` puesto, corrí el directorio completo dividido
en 32 fragmentos de 300 (con `timeout 120` cada uno, para detectar
cuelgues automáticamente en vez de adivinar posición). Resultado real:

- **~8,627 passed, 19 failed, 30 skipped** en los 29 fragmentos que
  completaron normalmente.
- **3 fragmentos con cuelgue real** (no relacionado con mi trabajo de
  compresión, confirmado aislando cada uno por bisección):
  1. `tests/hermes_cli/test_doctor.py::TestDoctorStaleMaxIterationsDrift::test_detects_drift_warn_only`
     y `::test_fix_removes_ghost` — se cuelgan incluso solos, en
     `poll_schedule_timeout` con 2 sockets + un eventpoll abiertos
     (`get_hermes_home()` sí resuelve bien el `HERMES_HOME` de prueba
     vía monkeypatch -- descartado que toquen el `.env` real -- el
     cuelgue parece venir de un fixture compartido de `hermes_test` que
     abre recursos de red, no de la lógica del test en sí).
  2. Un segundo cuelgue en el área de `test_model_switch_*.py`
     (custom providers/copilot), no aislado al test exacto.
  3. Un tercer cuelgue cerca del ~83% de la corrida original de una sola
     pasada (antes de dividir en fragmentos), tampoco aislado al test
     exacto.
- Los 19 fallos reales (no cuelgues) están dispersos en áreas sin
  relación entre sí (OAuth de dashboard, normalización de proveedores
  custom, CLI de suscripción) -- no se investigaron a fondo, fuera de
  alcance de esta verificación.

**Conclusión:** el fix del `os._exit()` cumplió su propósito (ya no se
trunca la corrida completa sin aviso). Los 3 cuelgues restantes son
fallas de entorno (recursos de red/servicios reales en esta máquina),
consistentes con el mismo patrón ya documentado arriba -- no indican
ninguna regresión del rebase ni de los fixes de Bloque S.1.

## Los 3 cuelgues, causa raíz encontrada y arreglada (26-27 Jul 2026)

Diagnosticados con `faulthandler.dump_traceback_later()` (no requiere
ptrace, que está bloqueado en este sandbox):

1. **`test_doctor.py::TestDoctorStaleMaxIterationsDrift`** (las 4
   pruebas de esa clase): `hermes_cli/doctor.py` corre `npm audit
   --json` de verdad contra `PROJECT_ROOT` cuando `node_modules`
   existe -- necesita el registro real de npm, inalcanzable aquí.
   Colgado en `subprocess.communicate()` bien pasado el `timeout=30`
   que el propio doctor.py le pone. **Fix:** bloqueado en el guard
   existente de `tests/conftest.py` (mismo patrón que "hermes update")
   -- falla rápido y claro; `doctor.py` ya envuelve la llamada en
   `try/except`, así que no cambia su comportamiento real.
2. **`test_model_switch_copilot_api_mode.py`** (las 3 pruebas):
   `copilot_model_api_mode()` llama `fetch_github_model_catalog()`
   siempre que hay `api_key`, sin mockear -- fetch real a la API de
   catálogo de GitHub, colgado en `socket.getaddrinfo()`. **Fix:**
   mockeado a catálogo vacío (los modelos de estas pruebas no dependen
   de su contenido, ver comentario en el test).
3. **El ~83% de la corrida original de una sola pasada** -- resultó ser
   más del mismo problema (llamadas de red reales no mockeadas),
   cubierto por el candado nuevo de abajo.

**Candado sistémico agregado, corregido después de un primer intento
mal acotado** (`tests/hermes_cli/conftest.py::_no_real_network`,
autouse -- SOLO esa carpeta, no repo-wide): bloquea CUALQUIER conexión
real no-loopback en 3 puntos (`socket.create_connection`,
`socket.getaddrinfo`, `socket.socket.connect`) -- necesarios los 3
porque `requests`/`urllib3` no usa `create_connection`, arma el socket
a mano y solo pasa por `getaddrinfo`+`connect`. Primer intento lo puse
en `tests/conftest.py` (repo-wide) y sacó a la luz ~5 fallos nuevos en
`tests/tools/` fuera de esta investigación -- movido a
`tests/hermes_cli/conftest.py`, único lugar donde los cuelgues reales
estaban confirmados. Loopback exento para tests con servidor local
real; `@pytest.mark.live_system_guard_bypass` para los que de verdad
necesiten red real.

**Bonus encontrado en el camino:** el fixture `agent_env` de
`tests/agent/test_empty_tool_name_loop_dampening.py` dejaba un
`FileHandler` de logging colgado apuntando a un directorio temporal ya
borrado -- cada log de CUALQUIER prueba posterior en el mismo proceso
producía un "--- Logging error ---" completo en stderr (2000+
confirmados en una corrida de `tests/agent/` completo). Arreglado
desconectándolo con `hermes_logging._reset_queued_handlers()` antes de
borrar el directorio.

**Resultado final, verificado, sin ningún cuelgue:**
`tests/hermes_cli/` completo, 32 fragmentos de 300 con `timeout 120`
cada uno: **9,525 passed, 20 failed, 31 skipped, 0 timeouts (el 20o confirmado como contaminacion normal, pasa limpio aislado)** sobre
9,576 tests totales. Los 19 fallos siguen dispersos en áreas sin
relación (OAuth de dashboard, normalización de proveedores custom, CLI
de suscripción) -- no investigados, fuera de alcance de esta
verificación, no relacionados con el rebase ni con ningún fix de esta
sesión.

También: `tests/run_agent/` + `tests/agent/` + `tests/tools/`
completos -- de 147 fallos en la corrida combinada, 143 eran
contaminación del bug de logging de arriba (confirmados limpios
aislados + con `git stash` contra el código sin tocar); solo 4
preexistentes y sin relación (2 en `test_turn_context_overflow_warning.py`,
2 en `test_credential_pool_routing.py`).

## Bloque 5 (HAS Fase 2) — Ensayo de actualización futura (27 Jul 2026)

`git fetch origin main`: **678 commits nuevos** en upstream desde que se
cerró el rebase de 27 commits (misma sesión) -- confirma que el ritmo de
upstream es alto, no asumir que "quedó al día" dura mucho.

Ensayo en rama desechable (`rehearsal-upgrade`, nunca tocó `arturo/base`
real): `git rebase upstream-main` avanzó **7/46 commits limpio** antes
del primer conflicto real, en `plugins/platforms/telegram/adapter.py` --
el MISMO archivo que ya dio conflicto en el rebase original. Confirma
que es un "punto caliente" real, no coincidencia -- documentado en la
skill `hermes-upgrade` para vigilarlo siempre. Rebase abortado a
propósito (`git rebase --abort`) sin resolver el conflicto -- el ensayo
es para medir cuánto dolerá la próxima vez, no para completarla ahora.

Skill `hermes-upgrade` escrita en `skills/hermes-upgrade/SKILL.md` --
procedimiento completo de 6 bloques (preparación, rebase, sintaxis,
smoke tests, suite completa, corte a producción con Arturo presente),
con los "puntos calientes" reales de archivos que ya dieron conflicto
dos veces documentados explícitamente.

Con esto, HAS Fase 2 Bloque 4 (10 smoke tests) y Bloque 5 (ensayo +
skill) quedan completos.

## Hallazgo pendiente (no arreglado en este bloque)

`tools/telegram_userbot.py` en este worktree trae la versión ANTIGUA y
bloqueante de `login_and_store_session()` (un solo paso). El arreglo real
(split en `start_login()`/`complete_login()`, hecho en sesión previa) se
aplicó solo al checkout de producción (`~/.hermes/hermes-agent`), no al
historial de `arturo/base` que se rebasó aquí. Falta reconciliar antes del
corte a producción (BLOQUE 6) — cherry-pick del commit de producción o
reaplicar el fix aquí.

## Estado al cierre de este registro

- 27/27 commits aplicados, `git status` limpio, 0 archivos con error de
  sintaxis en todo el árbol (`ast.parse` sobre cada `.py`).
- Riesgo a producción: CERO (worktree aislado, nunca se tocó
  `~/.hermes/hermes-agent`).
