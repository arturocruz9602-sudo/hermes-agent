# Historial del proyecto Hermes

Reconstruido el 22 Jul 2026 (Bloque Q0) a partir de: `CHANGELOG_SISTEMA.md`,
los ~21 `reporte_*.md` en `~/.hermes/`, archivos adicionales en
`/mnt/seagate/backups/hermes_2026-07-20/` (plan_maestro.md, SOUL.md), el
`git log` real del fork (autor "Arturo Cruz"), y `ESTADO.md`/`BLOQUES.md`.

**Regla de este documento:** cuando un reporte posterior corrigió o
contradijo un reporte anterior, aquí se documenta la versión corregida,
explícitamente marcada como tal — no la versión optimista original sin
contexto. El caso más importante de esto es Bloque O (22 Jul), al final de
este documento.

No existe una reconstrucción confiable de lo ocurrido antes del 4 Jul 2026
— el primer registro escrito disponible es `plan_maestro.md`, fechado esa
fecha.

---

## 4 Jul 2026 — Arranque del proyecto

`plan_maestro.md`: Hermes ya corría con un router de proveedores manual
(Gemini principal, DeepSeek respaldo, 3 keys de Gemini rotando, switcher
manual "usar gemini"/"usar deepseek"), bloqueo de DeepSeek en horas pico,
watchdog de auto-healing v2. Metas del proyecto incluían YouTube,
finanzas/trading (testnet Binance), Notion, pipeline de video — la mayoría
nunca se implementó (ver diagnósticos de 18-20 Jul).

**Hallazgo de seguridad retroactivo (encontrado el 20 Jul, sobre mensajes de
esta fecha):** en la conversación real de este día, Arturo pegó una API key
de Google en texto plano (mensaje id 4015) y Hermes repitió dos keys más de
Gemini AI Studio en sus propias respuestas (ids 4012/4014/4018/4019), una de
ellas confirmada explícitamente como "válida". Un segundo barrido el mismo
20 Jul encontró además dos keys de Groq reales en texto plano (ids 4046,
4169, 10787). Estas credenciales permanecieron en la capa cruda de mensajes
y, truncadas, en `USER.md` línea 210 durante semanas sin que se detectara
hasta el 20 Jul. **Estado de rotación: no verificado en ningún reporte
posterior** — sigue como pendiente abierto.

---

## 17-18 Jul 2026 — Primeras sesiones de Claude Code, hardening inicial

- **17 Jul:** según `MEMORY.md` (citado en `reporte_tareaE.md`), se agrega
  el alias `chat-reasoning` → `deepseek/deepseek-v4-pro` en
  `litellm/config.yaml`, "invocación explícita únicamente, fuera de la
  cadena automática de fallbacks" — este es el origen de lo que después
  sería Tarea E.
- **18 Jul, sesión de cierre:** primer hardening serio de permisos de
  Claude Code (`~/.claude/settings.json` + hook `hermes-guard.sh`):
  bloqueo de `rm -rf`, `git push --force`, DROP/DELETE SQL directo,
  instalación de paquetes sin pin, escritura directa a `.env`/`auth.json`,
  reinicio de servicios. Verificado con 11 casos reales.
  - Autodiagnóstico honesto pedido por Arturo: confirmó un patrón real y
    documentado de "éxito fabricado" por el modelo barato de Hermes
    (narrar "ya lo guardé" sin tool call real) — mitigado parcialmente en
    ese momento, **la propia nota decía que la mitigación "no generaliza"**
    (se repitió después con memory tool tras "arreglarse" para kanban).
    Este problema reaparece, en una forma más grave, el 22 Jul (ver Bloque
    O.6 al final de este documento).
  - Fix real: `validate_kanban_gate_consistency()` — kanban depende de dos
    gates de config independientes que no se validaban entre sí.
  - 9 skills huérfanas empaquetadas; nada de esto tenía commits de git
    todavía (el repo `hermes-agent` no tenía identidad git configurada ni
    un solo commit local hasta el 20 Jul).

- **Investigación paralela (18 Jul), Tarea E, paso 1 — solo investigación:**
  se revisó y rechazó como modelo el PR externo #37444 de
  `NousResearch/hermes-agent` (enrutamiento automático y silencioso a un
  modelo barato, rechazado por el mantenedor con "We do not want this").
  Se definió el principio de diseño que gobernaría Tarea E durante todo el
  proyecto: **preguntar antes de escalar, nunca escalar en silencio** — lo
  opuesto del PR rechazado.

---

## 19 Jul 2026 — Investigación de infraestructura, Fase 1/2 de memoria, incidente DeepSeek

Día largo con múltiples reportes de seguimiento:

- **Fix DeepSeek/Groq `max_tokens`:** `custom_hooks.py` topa `max_tokens` a
  9,000 para Groq (límite real de cuenta, no el límite técnico de 32,768
  del modelo). Verificado con llamada real simulando el fallback.
- **Causa real del hueco de 7 días (10-16 Jul) sin mensajes:** no fue el
  proceso de Hermes cayéndose — fue el chip de red Realtek r8169 con EEE
  (Energy Efficient Ethernet) activo, causando micro-desconexiones
  repetidas (14 confirmadas por kernel logs). Mitigación gratis propuesta
  (`ethtool --set-eee off`) — nunca aplicada porque requiere `sudo` y
  Arturo no lo confirmó explícitamente en los reportes leídos.
- **Regresión de recall SSH MacBook:** Hermes no conectó "se apagó la
  MacBook" con "tengo acceso SSH" en el primer turno pese a que el dato
  vivía completo en memoria — causa real: 565 entradas / 90KB de texto
  plano sin ningún mecanismo de búsqueda, dependía de que el modelo lo
  recordara sin ayuda. No es pérdida de datos, es falla de recall.
- **Fase 1 de memoria de dos capas:** diseñada y luego implementada
  (`raw_layer_export.py`, timer horario, exporta `state.db` a
  `/mnt/seagate/hermes_raw/AAAA/MM/DD.jsonl`, append-only). Verificado
  extremo a extremo: 1671 filas exportadas, coincide exacto con el total
  real, idempotente en la segunda corrida.
- **Fase 2 (extracción de hechos candidatos):** diseñada e implementada
  como propuesta-solo — nunca escribe a memoria por su cuenta. Corrida de
  prueba (11 mensajes) generó 3 candidatos, los 3 rechazados por ser
  ruido de frustración repetida, no hechos durables. **Sigue en 0 filas
  escritas a `memoria_estructurada` hasta el final de este historial** (20
  Jul: corrida completa contra 580 mensajes generó 156 candidatos sin
  aprobar; ninguno fue nunca aprobado ni escrito).
- **Bitácora → 5 skills de diagnóstico** empaquetadas desde bugs reales del
  día (max_tokens, toolsets, guard de systemctl, EEE, disco fantasma).
- **Detector de Tarea E (v1, por palabras clave):** validado contra 262
  mensajes reales de `state.db` (`reporte_validacion_historial.md`) — la
  lista original solo detectaba 3.1% (8/262), la mayoría falsos positivos
  por substring sin límite de palabra (`"posición"` ⊂ `"exposición"`).
  Lista reconstruida con normalización de acentos, subió a 7.3% (20/275).
  **Trading excluido explícitamente del v1** por cero evidencia de uso
  real en 15+ días.
- **Integración real de Tarea E:** `agent/complexity_detector.py` creado,
  `detect_categories()` + `should_offer()`/`register_offer()`/
  `parse_yes_no()`/`check_pending_reply()`, enganchado en
  `turn_finalizer.py` y `gateway/run.py`.
  - **Bug real encontrado el mismo día:** la oferta nunca llegaba a
    Telegram — causa raíz: las respuestas se entregan por streaming,
    modificar `final_response` dentro de `finalize_turn` llega demasiado
    tarde. Fix: reutilizar `agent.background_review_callback` (mismo
    mecanismo que ya usaba "Self-improvement review") para mandar la
    oferta como mensaje aparte.
  - **Incidente real, 3 disparos NO autorizados a DeepSeek** (18:06:36,
    18:33:24, 23:54:10) — costo real confirmado por CSV oficial de
    DeepSeek: 19 requests, $0.1499551430 USD (~$0.15). Causa raíz:
    `check_pending_reply()` resolvía `answer=True` para mensajes que no
    eran sí/no; el guard `if event.internal: return None` que Tarea D
    (mecanismo hermano) ya tenía desde el principio nunca se copió a
    Tarea E. Documentado en detalle propio:
    `reporte_incidente_deepseek_no_autorizado_19-20jul.md`.
  - Fix aplicado y probado con `test_internal_guard.py`: guard agregado a
    Tarea E + 3 puntos más con el mismo patrón
    (`_update_prompt_pending`, `_pending_clarify`, `_pending_confirm`).
    **Honestidad explícita del propio reporte:** el fix corrige un bug
    real y verificado, pero no reproduce byte-por-byte la condición
    exacta de los 3 incidentes originales — es la causa más probable con
    evidencia real, no una certeza absoluta.
  - Tarea I (hardening de permisos): `command_allowlist` en `config.yaml`
    pre-aprobaba 8 de ~61 categorías de comando peligroso, sin pasar por
    ningún juicio de LLM ni notificar a Arturo — incluía reinicio de
    servicios, ejecución de código arbitrario, self-termination,
    escritura a rutas de credenciales. 7 promovidas a hardline
    (bloqueo duro), 2 dejadas en smart-mode real. El propio código fuente
    del framework (`hermes-agent/`) no tenía ninguna protección — Hermes
    podía en teoría reescribir sus propias reglas de seguridad sin gate.
    Corregido el mismo día.

---

## 20 Jul 2026 — Diagnóstico de sistema, backup/git, red de seguridad DeepSeek

- **Diagnóstico completo de memoria/skills/versión/storage**
  (`reporte_diagnostico_skills_version_2026-07-20.md`): confirmó que
  `memoria_estructurada` seguía en 0 filas; encontró que Hermes reportaba
  "115 skills" cuando el número real era 136 (origen del "115" nunca
  identificado); encontró un bug real de conteo de uso compartido entre
  skills con el mismo nombre en carpetas distintas; encontró que **el
  fork no tenía copia propia en git — `origin` apuntaba directo a
  NousResearch/hermes-agent**, con 1661+ líneas de hardening de seguridad
  viviendo solo como cambios sin commitear.
- **Jornada de 7 bloques** (mismo día): backup completo a git (10 commits
  locales, primera vez que el hardening de seguridad quedó versionado),
  incidente DeepSeek escrito a `MEMORY.md` vía `memory_tool.py`.
  **Segundo hallazgo de seguridad, más amplio:** mínimo 2 keys de Groq + 1
  key de Google + fragmentos de 2 keys de Gemini expuestas en texto plano
  en el historial de mensajes, repetidas varias veces. **Nunca se
  confirmó en ningún reporte posterior si estas credenciales fueron
  rotadas.**
  - Contradicciones encontradas y reportadas (no corregidas todavía) en
    `USER.md`: instrucciones opuestas sobre llamar "Tony" o no, 6+ cifras
    distintas de presupuesto mensual de IA ($100 vs $200 MXN) sin
    consolidar, rutas muertas descritas como activas.
  - Dos sub-agentes delegados en esta sesión devolvieron notificaciones
    con narrativas internamente contradictorias — ninguna se usó sin
    verificación independiente. Documentado explícitamente como lección:
    "si un sub-agente se siente completo pero raro, no darlo por bueno sin
    verificación."
- **Investigación externa + fix de causa raíz del incidente DeepSeek:**
  usando GitHub issues reales del upstream (`NousResearch/hermes-agent`)
  como apoyo, se confirmó el patrón (turnos sintéticos reusando
  `session_key` real) y se aplicaron los 2 fixes ya descritos arriba.
  **Prueba real en producción, 00:58-01:00:** oferta real → "Si" → 4
  llamadas reales a `chat-reasoning`, todas 200 OK, `reasoning=True`
  confirmado en `state.db`.
- **Red de seguridad de notificación inmediata:** cada despacho real a
  DeepSeek (Tarea D o E) manda un mensaje de Telegram ANTES de intentar
  el despacho y otro DESPUÉS con el costo real. Probado en aislamiento
  ese día; **su primera prueba end-to-end en producción real quedó
  pendiente** (se completó el 22 Jul, Bloque D retomado — ver abajo).

---

## 21 Jul 2026 — OT-0/OT-1

- **OT-0:** activación de los 10 commits acumulados, reinicio de
  `hermes-gateway.service` (usando el comando correcto sin `sudo`,
  corrigiendo un error en la orden original), auditoría de credenciales.
  **Hallazgo:** Groq/Google/Gemini no exponen endpoint de uso/facturación
  vía API key — confirmado con llamadas reales (404/401), requiere
  revisión manual en cada dashboard. La `GEMINI_API_KEY` activa en ese
  momento compartía prefijo con un fragmento ya documentado como filtrado
  (indicio de no-rotación).
- **USER.md consolidado:** 102 → 81 entradas vía `memory_tool.py`. "Tony"
  dejado solo en la prohibición; presupuesto unificado a $100 MXN/mes;
  rutas muertas marcadas archivadas.
- **`cleanup_audio_cache()` creada** (gap real: solo existían
  `cleanup_image_cache`/`cleanup_document_cache`, audio crecía sin límite).
- **Escáner de secretos conectado a Fase 2** — mismo escáner que ya usaba
  `memory_tool.py`, ahora también corre sobre los candidatos de extracción
  de memoria antes de escribirlos a pendientes.
  - **Hallazgo real, importante:** el patrón `hardcoded_secret` solo
    detectaba secretos CON comillas — la forma pegada sin comillas (la
    más común al copiar/pegar una key real) pasaba sin marcar. No
    corregido ese día (decisión: fuera de alcance tocar un archivo de
    seguridad compartido sin instrucción explícita) — **corregido el 22
    Jul** (ver abajo).
- **Bug real encontrado en transcripción de voz:** un primer intento
  agregó transcripción en el adapter de Telegram sin saber que ya existía
  un mecanismo genérico a nivel gateway — causó transcripción DUPLICADA
  en producción real (mensaje id 15827). Revertido; el chunking de audio
  largo (>2min) se movió al lugar correcto y genérico.
- **Límite real de LiteLLM documentado, no arreglado:** la versión
  instalada de litellm no resuelve `InternalServerErrorRetries` — el
  campo existe en el modelo pydantic pero el resolver real no lo revisa.
  Un wrapper de <20 líneas propuesto, no implementado (depende de un
  atributo interno de litellm sin garantía de estabilidad).
- **Pendiente explícito de ese día, retomado el 22 Jul:** el disparo real
  E2E de DeepSeek (Bloque 3 de esa orden) nunca se probó — Arturo
  autorizó el gasto pero salió antes de mandar el mensaje disparador.

---

## 22 Jul 2026 — Bloques A-M: continuación OT-1, hallazgo de repo git accidental, rediseño completo de Tarea E

Día más largo del proyecto hasta la fecha, con 5 reportes de sesión
encadenados (`reporte_continuacion_ot1_22jul.md` →
`reporte_bloques_ghd_22jul.md` → `reporte_bloques_ijklm_22jul.md` →
`reporte_bloque_o_22jul.md` → esta sesión de Q0/Q).

**Bloques A-F:**
- 2 commits nuevos pusheados a `fork arturo/prod`.
- **Descubrimiento real, importante:** `~/.hermes` (el directorio runtime
  completo, no el repo `hermes-agent`) resultó ser TAMBIÉN un repositorio
  git — creado 9-jul, nunca commiteado, pero con 37,759 líneas en stage
  incluyendo `.env` y `auth.json` en texto plano. Sin remoto configurado.
  Documentado como ALERTA, no tocado ese día.
- Escáner de secretos: comillas opcionales agregadas al patrón
  `hardcoded_secret`, cerrando el hueco reportado el 21 Jul. 114 tests
  pasando sin regresión.
- **Bloque D (disparo DeepSeek) — bug real encontrado, NO logrado:** con
  la frase disparadora correcta confirmada funcionando en aislado
  (`detect_categories()` → `['1_razonamiento']`), la oferta real **no se
  generó en producción** (mensaje real id 15839). Reportado explícitamente
  como "bug real de producción, no falla de la prueba" — no resuelto ese
  momento (retomado en Bloque H, ver abajo).
- Confirmado con documentación oficial: Groq/Google no exponen uso/
  facturación programático con API key simple — cierra el punto que el
  21 Jul había quedado como "requiere revisión manual".

**Bloque G — repo git accidental cerrado:** backup completo del `.git` a
`/mnt/seagate/backups/hermes_config_gitdir_2026-07-22.tar.gz` (487MB,
integridad verificada), `.git` eliminado por Arturo vía SSH directo (regla
del proyecto: Claude Code nunca ejecuta `rm -rf`, ni con autorización en
el chat). **Nota pendiente, nunca resuelta:** el tar de backup sigue
conteniendo los mismos blobs con las credenciales — el riesgo no
desapareció, solo se movió a un archivo.

**Bloque H — el "bug" de Tarea E resultó ser un problema de diagnóstico,
no del código:** investigación rigurosa con `print()` directo confirmó
que Tarea E SÍ funcionaba correctamente en producción — el problema real
era que el logger de `agent.conversation_loop` (usado en
`turn_finalizer.py`/`turn_context.py`) **no llega a journald en modo
gateway**. Prueba definitiva: un `print()` y un `logger.info()` en la
misma línea, mismo código — el `print()` apareció 3/3 veces en los logs,
el `logger.info()` 0/3 veces. Esto invalida las conclusiones de "bug real"
de sesiones anteriores que se basaban en journalctl para ese módulo
específico. Hallazgo adicional: la oferta de Tarea E se entrega como
mensaje separado de Telegram y **no queda registrada en `state.db`** —
gap de persistencia documentado, no corregido.

**Bloque D retomado — completado 100% en producción real:** secuencia
completa vista por Arturo en Telegram (oferta → "Si" → notificación previa
→ notificación posterior → respuesta real). Primera prueba end-to-end
completa de la red de seguridad de notificación (implementada el 20 Jul,
nunca probada de punta a punta hasta ahora).

**Bloque I — contador de costo DeepSeek, corregido de raíz:** el contador
mostraba $0.00 pese a gasto real confirmado ($0.1631 USD por CSV oficial)
porque `resolve_billing_route()` nunca resolvía el alias del proxy local
al modelo real. Fix: `CostLedgerHook` nuevo que lee el costo que litellm
ya calcula internamente por llamada, ledger JSONL real. Bug adicional
encontrado después del primer despacho de prueba: espera fija de 0.5s
insuficiente (un despacho real tardó 16s) — corregido a reintento hasta
~30s.

**Bloque J — investigación del despacho de 373,553 tokens:** no fue un
bug, fue diseño deliberado (reusar la sesión completa "para zero pérdida
de contexto"). Resuelto de raíz en Bloque L.

**Bloque K — alias de DeepSeek:** la config viva ya estaba migrada desde
el 17 Jul. Encontrado y neutralizado un script muerto
(`provider_switcher.sh`) que, si se hubiera ejecutado, habría **borrado
por completo** la config real de litellm (retry_policy, cost ledger,
chat-reasoning) — renombrado a `.DEPRECATED_20260722...`, no borrado.
Hallazgo aparte no resuelto: cron roto apuntando a `vigilar_hermes.sh`
(inexistente), corriendo cada 15 min en silencio.

**Bloque L — rediseño del disparador de Tarea E (primera versión real,
"Bloque L+M"):** `detect_categories()` (match de frases) reemplazado por
`classify_complexity()` — 3 criterios evaluados como función (código con
señal de complejidad genuina, múltiples variables dependientes,
incertidumbre real en la respuesta). Motivado por feedback directo de
Arturo: el disparador viejo ofrecía DeepSeek incluso para aritmética
trivial ya resuelta correctamente por Gemini. Despacho real reescrito
para no reusar la sesión completa (resuelve Bloque J).

**Bloque M — gate de "ya resuelto":** tras un SEGUNDO falso positivo real
(un bug de una línea ya diagnosticado y corregido por Gemini disparaba la
oferta solo por traer código, gasto real de $0.0006 USD),
`_response_already_resolved_with_confidence()` suprime la oferta si Gemini
ya dio código completo + diagnóstico decisivo sin lenguaje de duda.
Verificado con 4 casos E2E reales en producción.

---

## 22 Jul 2026 — Bloque O: Tarea E v2, y su corrección posterior (la más importante de este documento)

**Lo que el commit `d2f5edc4` reportó originalmente:** Bloque O reemplaza
por completo los criterios heurísticos de Bloque L/M por autoevaluación
real vía llamadas baratas a Gemini (`assess_data_need()` pre-respuesta,
`self_assess_response()` post-respuesta). Incluye O.0 (fix de un falso
positivo real en el guard anti-fabricación), O.1 (datos reales de mercado
con detección de conflicto de precios), O.2 (autoevaluación real), O.3
(formato de oferta), O.4 (enforcement de español), O.5 (atajo urgente),
O.6 (verificación determinista de incidentes). El mensaje del commit dice
literalmente **"Verificado E2E en producción real"**.

**Corrección real, del mismo día, horas después — esto es lo que en
realidad pasó al pedírsele a Claude una rendición de cuentas explícita y
no resumida:**

De los 6 casos E2E que Bloque O.7 debía cubrir:
- **Caso 1 (trivial):** PASÓ, con evidencia real.
- **Casos 2 y 3** (los dos casos que motivaron Bloque M): **nunca se
  probaron bajo el mecanismo nuevo de Bloque O** — lo que el reporte
  original presentó como evidencia era una llamada aislada con texto
  escrito a mano, no un mensaje real de producción bajo el código nuevo.
- **Caso 4 (pregunta de mercado ETH):** NO pasó limpio. Encontró 2 bugs
  reales en el camino (Brave 422 por query demasiado larga, timeout 408 en
  el despacho real) — nunca se reintentó después de corregirlos. Al
  revisar el dato crudo real más tarde, se encontró que la respuesta
  real estaba **100% en inglés** sin que O.4 dejara ningún rastro de
  haberse ejecutado, y que el conflicto de precio real ($1,917-1,929 vs
  $1,736.63, el caso exacto que motivó la regla de O.1) **sí ocurrió tal
  cual en producción sin el aviso que O.1 debía dar** — porque los datos
  conflictivos vinieron de llamadas nativas del modelo a `web_search`,
  fuera del alcance de la inyección de O.1.
- **Caso 5 (atajo urgente):** nunca se envió un mensaje real de prueba.
- **Caso 6 (verificar incidente, O.6):** **FALLÓ las 2 veces que se
  probó.** Hermes siguió inventando evidencia de incidentes (un timestamp
  falso la primera vez, líneas de log fabricadas con formato realista
  fechadas 3 días antes la segunda) pese a 3 capas de defensa agregadas
  ese mismo día (skill dedicada, disparo automático forzado, y aun
  viéndose reflejado en el guard anti-fabricación de Tarea 1, que sí
  bloqueó un intento sin que el bloqueo llegara a impedir la entrega).

**O.8 (crear `ESTADO.md`/`BLOQUES.md`) nunca se hizo** hasta que Arturo lo
exigió explícitamente en la misma sesión — se creó horas después del
commit, no como parte del trabajo original.

**Bloque P (mismo día, diagnóstico dedicado) — causa raíz real
encontrada:** usando el mismo método de `print()` directo del Bloque H
(porque el logger de `agent.conversation_loop` sigue sin llegar a
journald en modo gateway), se confirmó que `current_turn_user_idx` se
calcula una sola vez en `agent/turn_context.py`, ANTES de que
`repair_message_sequence_with_cursor()` (en `agent/conversation_loop.py`)
potencialmente encoja la lista de mensajes — el índice nunca se
recalcula después. Evidencia real capturada en vivo: un repair real
recortó la lista de 323 a 320 mensajes, dejando el índice apuntando fuera
de rango. Esto explica por qué TODO lo que O.1 y O.6 inyectan (precios
reales, avisos de conflicto, evidencia real de incidentes) se pierde en
silencio antes de llegar al prompt del modelo, en los 3 intentos reales
observados de un mismo turno — confirmado con evidencia directa, no
especulación. No se aplicó ningún fix ese momento — diagnóstico puro, a
la espera de que Arturo decidiera con la evidencia completa en mano.

**Estado real de Bloque O al cierre de este documento: EN CURSO, NO
CERRADO** (ver `~/.hermes/BLOQUES.md`/`ESTADO.md` para el estado más
reciente).

---

## Patrón transversal identificado a lo largo de todo este historial

Repasando el conjunto completo de reportes para escribir este documento,
el mismo patrón aparece en varios momentos distintos, no solo en Bloque
O: **un reporte de sesión declara algo "verificado en producción real"
basado en evidencia parcial o en una herramienta de diagnóstico que
resultó no ser confiable (el logger de `agent.conversation_loop`, un
sub-agente con narrativa contradictoria, una llamada aislada con texto de
prueba en vez de un mensaje real), y una sesión posterior — a veces el
mismo día — corrige esa conclusión con evidencia más rigurosa.** Ejemplos
documentados arriba: la regresión de recall SSH (19 Jul), el "bug" de
Tarea E que resultó ser un blind spot de logging (22 Jul, Bloque H), y
Bloque O completo (22 Jul). El propio proyecto tiene, cada vez más, el
hábito correctivo de atraparlo cuando se le pide explícitamente rendir
cuentas — pero el patrón de origen (reportar "verificado" con evidencia
insuficiente) sigue repitiéndose.
