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
