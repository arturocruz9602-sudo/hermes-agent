# Estado de Hermes — 22-24 Jul 2026

**Versiones vigentes: HAS v1.4 · PROTOCOLO v1.3.1**

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
