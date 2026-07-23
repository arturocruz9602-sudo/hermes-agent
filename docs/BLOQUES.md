# Historial de Bloques — Hermes

Este archivo no existía antes del 22 Jul 2026 (creado en O.8, primera
entrada retroactiva es Bloque O porque es el bloque activo al momento de
crear este archivo; bloques anteriores no se reconstruyen aquí).

## Sesión de mañana (23 Jul, ~10-11 AM) — Bloques AA-AD

Detalle completo con evidencia real en `ESTADO.md`. Resumen: causa raíz
real de por qué Groq nunca se intentaba anoche (cooldown interno stale
de litellm, no un fallo real -- resuelto reiniciando `litellm.service`,
Groq confirmado sano); confirmado con código que Tarea E depende de una
respuesta base Y de su propia autoevaluación, ambas necesitan Gemini, lo
que la deja en silencio justo cuando toda la escalera gratis está caída
(hallazgo de diseño, no arreglado, pendiente de decisión de Arturo);
**hallazgo grave nuevo sin arreglar**: fabricación real no bloqueada por
el guard de Tarea 1 pese a que el patrón sí hace match -- requiere
sesión de diagnóstico dedicada. 3 commits pusheados a `fork arturo/prod`
(verificado SHA). `docs/BITACORA_ARTURO.md` creado, regla permanente
agregada a `CLAUDE.md`.

## Sesión nocturna autónoma (23 Jul, madrugada) — Bloques Q/R/S/T/U/V/W/X/Y/Z

Continuación directa de Bloque Q (retomado en Q.2, ver su sección más
abajo). Orden real de ejecución de la noche: R2.1 → S (ya reportado) →
T → U.1 → diagnóstico de recall → W → V → X.5/X.6 → Y → este cierre.

**R2.1 (verificación de contenido O.1):** confirmado con una
reconstrucción en vivo (misma función, mismo mensaje, ~1 min después)
que O.1 SÍ inyectó datos reales de CoinGecko/Brave en el intento de ETH
de esa noche -- no vacío, no parcial. Aclarado explícitamente como
reconstrucción, no el valor histórico exacto capturado.

**Bloque T -- bóveda de credenciales cifrada:**
- `tools/vault_tool.py`: AES-256-GCM + scrypt (Python puro, `age`
  original de la orden no estaba instalado y requiere sudo). Registrada
  como toolset `vault` en `config.yaml` (`platform_toolsets.cli` y
  `.telegram`).
- T.4: `~/.hermes/scripts/raw_layer_export.py` redacta turnos de bóveda
  antes de escribir a la capa cruda (probado con una conversación
  sintética real).
- T.5: **NO viable** borrar mensajes que Arturo mismo manda (límite real
  de la API de Telegram, confirmado con la documentación del wrapper
  `delete_message()` ya existente en el adapter -- solo funciona para
  mensajes que el bot mismo mandó).
- T.6: escáner de salida en `turn_finalizer.py` + 5 patrones nuevos de
  **formato real** de llaves en `tools/threat_patterns.py` (Gemini,
  Google legacy, Groq, OpenRouter, OpenAI/DeepSeek-style) -- el patrón
  viejo (solo por palabra clave cercana) NO detectaba el incidente real
  del 4-jul ("la clave es: AQ.Ab8..."), verificado y corregido.
- **Hallazgo de seguridad real, encontrado probando en vivo con Arturo:**
  con una passphrase mal escrita, Hermes reveló la passphrase correcta
  -- la leyó de su propio historial de conversación, sin importar lo que
  devolvía la herramienta (que nunca la reveló). Corregido con una
  garantía de CÓDIGO, no solo instrucción: `hermes_state.py`
  (`_redact_vault_turns`, conectado en `get_messages_as_conversation`)
  ahora redacta automáticamente cualquier turno de bóveda (passphrase,
  valor, y la respuesta del modelo que lo repite) de la ventana de
  conversación que se manda al modelo en turnos futuros. Verificado con
  una simulación exacta de la conversación real de Arturo.
- T.7: bóveda de prueba aislada (sin tocar la real) -- guardar/recuperar
  coincide exacto, passphrase incorrecta no filtra el valor, grep en
  USER.md/MEMORY.md/memoria_estructurada/índice semántico/state.db: 0
  hits en todos.
- **Config.yaml, hallazgo aparte:** durante la noche, `config.yaml`
  perdió las entradas de `kanban`, `vault` y el proveedor `LiteLLM` (
  reemplazado por un proveedor Ollama local no relacionado). Repuesto y
  verificado (`_resolve_litellm_credentials()` vuelve a resolver
  correctamente). Sin esto, O.1/O.6 y la bóveda habrían dejado de
  funcionar en silencio.

**Diagnóstico de recall de sesiones (fuera de los bloques con letra,
pedido directo de Arturo):** causa raíz real confirmada -- Hermes llamó
a `session_search` con `query="Hermes project"` (genérico, en inglés)
en vez de usar palabras específicas de la pregunta real en español. Se
verificó que la MISMA herramienta, con mejores términos, SÍ encuentra la
sesión correcta. Solución aplicada en Bloque U.1.

**Bloque U.1:** guía reforzada en `tools/session_search_tool.py`
(sección "QUERY QUALITY") -- usar palabras específicas del mensaje real,
en el mismo idioma, reintentar una vez con mejores términos antes de
rendirse. **U.2 (confirmación en vivo) PENDIENTE** -- cuota de Gemini
agotada (ver `ESTADO.md`).

**Bloque W -- confirmación antes de guardar por voz:**
- `tools/vault_tool.py`: `looks_like_voice_vault_save_request()`
  (detección determinística por regex, no LLM) + tabla
  `vault_pending_voice_confirm` (mismo patrón que `tarea_e_ofertas`).
- `agent/turn_context.py`: gate de dos turnos inyectado de forma forzada
  (mismo mecanismo que O.1/O.6) -- si el mensaje es de voz y parece
  pedir guardar una credencial, se prohíbe llamar a `vault(action=save)`
  ese mismo turno y se fuerza pedir confirmación explícita primero.
- W.3: lógica probada completa sin audio real (como pidió la orden) --
  6/6 casos del detector (incluida una variante en mayúsculas, una
  variante de "guárdame", y el caso negativo de texto normal sin ser de
  voz), y el ciclo completo registrar→confirmar sí→limpiar /
  registrar→confirmar no→limpiar, ambos verificados.
- **Verificación en vivo con el modelo real: PENDIENTE**, cuota de
  Gemini agotada. **Prueba con audio real de Arturo: pendiente para
  mañana**, como pidió la orden explícitamente.

**Bloque V -- arnés E2E interno:** `tests/e2e/hermes_harness.py`.
Construye un `GatewayRunner` REAL (config/session_store/state.db
reales) con un adaptador de captura en vez de conexión real a Telegram
-- cero riesgo de chocar con el `hermes-gateway.service` en vivo (nunca
intenta `getUpdates`). Usa el chat_id real de Arturo para pasar
autorización real. Confirmado: construcción limpia, autorización real
pasando, y un turno completo procesado de punta a punta contra la
conversación real (aunque el primer intento coincidió con el peor
momento de agotamiento de cuota).

**X.5:** 101 tests relevantes corriendo (incluidos los 4 nuevos de
Bloque S) -- todos pasan, sin duplicar nada.

**X.6:** estructura de `reply_markup` verificada programáticamente
(texto en español, `callback_data` dentro de 64 bytes). Verificación
VISUAL real pendiente para mañana.

**X.1-X.4, X.7, X.8: PENDIENTES.** Bloqueados por un límite real externo
encontrado y confirmado con evidencia (mensaje de error real de
Google): la cuota gratuita de Gemini es de **20 requests/día**, no por
hora. El volumen de pruebas de toda la noche muy probablemente ya la
agotó por el resto del día. Groq (fallback) respondió brevemente pero
su ventana de 128k no alcanza para la conversación real ya inflada;
OpenRouter (fallback3) también agotado (límite diario gratuito). No se
forzó ningún workaround -- se documenta como bloqueo real, como pide la
regla de esta sesión.

**Bloque Y -- limpieza de la bóveda:** la bóveda no existía antes de
esta sesión (la funcionalidad es nueva), así que TODAS sus entradas
fueron creadas esta noche por definición. Se eliminó la única entrada
real (`Cisco`, guardada por Arturo durante la prueba en vivo de T.7).
Verificado: `vault_list_services()` devuelve `entries: []` -- la bóveda
quedó exactamente como antes de que empezara la sesión (0 entradas). El
mecanismo en sí queda completo y listo para uso real.

---

## Bloque O — Tarea E v2 (22 Jul 2026) — **EN CURSO, NO CERRADO**

Estado: **EN CURSO**. No se cierra mientras el hallazgo crítico de O.6
(y su causa raíz identificada en Bloque P) siga sin resolver. Ver
Bloque P abajo.

Reemplaza las heurísticas de Bloques L y M por autoevaluación real vía
Gemini. Reporte completo: `~/.hermes/reporte_bloque_o_22jul.md`.
Commit: `d2f5edc47` (pusheado a `fork arturo/prod`).

**Línea exacta de derogación** (del mensaje de commit `d2f5edc47`, también
presente como comentario en `agent/complexity_detector.py` línea 118-121):

> Deroga los criterios (a)/(b)/(c) de Bloque L y el gate de Bloque M
> (código Python heurístico basado en regex) -- reemplazados por
> autoevaluación real vía llamadas baratas a Gemini con rúbrica JSON fija.

Y en el propio código (`agent/complexity_detector.py:118-122`):

```
# Bloque O (22 Jul 2026): deroga los criterios (a)/(b)/(c) de Bloque L y el
# gate de Bloque M como código Python heurístico -- ver assess_data_need()
# y self_assess_response() más abajo (autoevaluación real via Gemini).
# fetch_context_summary() sigue viva, reutilizada por O.1.
```

Sub-bloques: O.0 (fix falso positivo anti-fabricación) · O.1 (compuerta
pre-respuesta, datos reales) · O.2 (compuerta post-respuesta,
autoevaluación) · O.3 (formato de oferta) · O.4 (enforcement de español)
· O.5 (atajo urgente) · O.6 (verificación determinista de incidentes,
SIN resolver) · O.7 (pruebas E2E, cobertura parcial, ver ESTADO.md) ·
O.8 (este archivo + ESTADO.md).

Estado real hoy: ver `~/.hermes/ESTADO.md`.

## OT-0.5 — Emergencia de credenciales: CERRADA (22-23 Jul 2026)

Los 6 pasos con evidencia real. 3 credenciales activas confirmadas
expuestas y nunca rotadas (GROQ_API_KEY, GEMINI_API_KEY,
GEMINI_CHAT_KEY2) -- las 2 primeras rotadas y verificadas (llave nueva
200 OK, vieja 401/403 real contra la API del proveedor), la tercera
eliminada (ya estaba muerta, sin uso en el código). Cron muerto
limpiado, watchdog real (`hermes-watchdog.timer`) confirmado activo.
Tar de 487MB sin ningún commit destruido con `shred`. Barrido de
fragmentos limpió residuos reales en logs, volcados de sesión, índice
semántico, y 2 backups adicionales encontrados fuera del alcance
original (`~/hermes_bot/` -- prototipo muerto con el TELEGRAM_BOT_TOKEN
activo duplicado, directorio eliminado por Arturo; y
`~/hermes_backups/20260704.../`, `.env` purgado). De las 10
credenciales activas restantes, probadas en vivo: **8 funcionan
confirmadas** (BRAVE, GEMINI_API_KEY, GEMINI_CHAT_KEY,
GEMINI_VISION_KEY_NEW, GROQ, DEEPSEEK, OPENROUTER, TELEGRAM_BOT_TOKEN),
**1 no aplica** (LITELLM_MASTER_KEY, interna), **1 pendiente fuera de
alcance** (ELEVENLABS_API_KEY autentica pero le faltan todos los
permisos que Hermes necesita -- requiere configuración en el dashboard
de ElevenLabs, no algo que se arregle desde código). Único residuo
aceptado: `state.db` conserva las llaves viejas en texto plano (ya
muertas, no se tocó por la regla de no DROP/DELETE SQL directo).
Detalle completo en `CHANGELOG_SISTEMA.md`.

## Bloque Q — cierre real de Bloque O: fix + verificación completa — **RETOMADO en Q.2** (23 Jul 2026)

Estado exacto (para que la próxima sesión retome sin adivinar si esta
también se interrumpe):

- **Q.0 (verificar escalera de fallback completa) — HECHO.** Groq
  (`chat-fallback`) y OpenRouter (`chat-fallback3`) probados directo y
  aislado, ambos 200 OK. La cadena NO está caída — Gemini (`chat-primary`)
  tenía cuota diaria agotada (confirmado, 429 real), y el fallo real de
  ese turno fue tamaño de conversación (262,593 tokens) excediendo el
  límite de contexto de los proveedores de respaldo, no una caída de
  proveedores. No fue necesaria ninguna alerta inmediata.
- **Q.1 (aplicar el fix de P.4) — APLICADO EN CÓDIGO, NO VERIFICADO
  LIVE TODAVÍA.** `agent/conversation_loop.py`: `current_turn_user_idx`
  ahora se relocaliza por identidad de objeto después de
  `repair_message_sequence_with_cursor()`, con manejo explícito del caso
  borde donde el mensaje del turno actual se fusiona (cae a -1, la
  inyección se salta en vez de aterrizar en un mensaje equivocado).
  Cambio SIN commitear (`git status`: `M agent/conversation_loop.py`).
- **Q.2 (re-test en vivo de los 2 casos que fallaron en P.2) — EN
  CURSO, segundo intento.** Primer intento interrumpido (Arturo nunca
  mandó los mensajes antes de que la sesión se redirigiera a Bloque Q0 y
  luego a la pausa de Bloque R). Instrumentación de confirmación
  reactivada y servicio reiniciado a las 2026-07-23 00:38:38 (se había
  retirado al pausar, documentado en su momento). Esperando que Arturo
  reenvíe los 2 mensajes ("Revisa que error hubo hace un momento" para
  O.6, la pregunta de ETH para O.1/O.4). **El fix de Q.1 sigue sin
  confirmación end-to-end real.**
- **Q.3 (por qué el turno de ETH llegó a 262,593 tokens) — SIN EMPEZAR.**
- **Q.4 (completar los 3 casos de O.7 nunca probados: 2, 3, 5) — SIN
  EMPEZAR.**
- **Q.5 (cerrar Bloque O en BLOQUES.md si los 6 casos pasan) — SIN
  EMPEZAR.** Bloque O sigue "EN CURSO, NO CERRADO" (ver arriba).

**Decisión sobre la instrumentación de Q.2 (documentada por instrucción
de Arturo, Bloque R.2):** se retiraron los 2 `print()` de diagnóstico
(`BLOQUE_Q_DIAG`) y se dejó SOLO el fix real de Q.1 en el código, luego
se reinició el servicio. Razón: OT-0.5 (emergencia de credenciales)
implica múltiples reinicios y ediciones de `.env` -- tener prints de
depuración sueltos en producción durante esa ventana no aporta nada y
podía confundir logs de una tarea sensible sin relación. El fix de Q.1
en sí se dejó activo (no revertido) porque es una corrección real, no
instrumentación -- solo se activa cuando `repair_message_sequence_with_cursor`
de verdad recorta la lista, y en ese caso mejora el comportamiento
existente (roto) sin riesgo conocido de empeorarlo.

**Para retomar:** reactivar instrumentación equivalente si se quiere
confirmar Q.1 con evidencia fresca, o simplemente proceder directo a
Q.2 con una prueba en vivo (el `print()` no es estrictamente necesario
para confirmar el fix -- también se puede verificar revisando si O.1/O.6
llegan a citar datos reales en la respuesta entregada).

## Bloque P — Diagnóstico del punto ciego de inyección de contexto (22 Jul 2026)

Diagnóstico puro (sin fix aplicado, por instrucción explícita). Causa
raíz identificada con evidencia real de producción (`print()` directo,
mismo método que Bloque H): `current_turn_user_idx` se calcula una sola
vez en `agent/turn_context.py:303`, ANTES de que
`repair_message_sequence_with_cursor()` (llamada en
`agent/conversation_loop.py:753`, que por su propio docstring "merges/
drops messages in place, shrinking the list") potencialmente encoja la
lista `messages`. El índice nunca se recalcula después. Si el repair
recorta la lista, el índice queda apuntando fuera de rango o a un
mensaje que ya no es el turno actual -- y el bloque que inyecta
`plugin_user_context` (O.1 y O.6 comparten el mismo mecanismo) nunca
matchea, así que el contenido inyectado se descarta en silencio, sin
error, sin log.

Evidencia real capturada 22-jul, caso ETH (18:54-18:56): `repaired_seq=3,
len(messages) antes=323 despues=320, current_turn_user_idx=322` (fuera
de rango) en el primer intento; desalineado también en los 2 intentos
siguientes de la misma conversación. El contenido inyectado por O.1
(precios reales de CoinGecko + aviso de conflicto) nunca llegó al
mensaje final hacia la API en ninguno de los 3 intentos observados.
Detalle completo: respuesta de Bloque P en la sesión del 22 Jul.

No se aplicó ningún fix -- Arturo pidió diagnóstico primero, decisión
después.

## Bloques anteriores (no reconstruidos en detalle aquí)

Referencia únicamente por nombre, ya que no se reconstruyó su contenido
completo en este archivo (fuera de alcance de O.8):

- Bloque A-F, I-M: auditoría de despacho DeepSeek, contador de costo real,
  rediseño del disparador de Tarea E. Ver
  `~/.hermes/reporte_bloques_ijklm_22jul.md`.
- Bloque G: hallazgo de borrado accidental de repo git en `~/.hermes`.
  Ver `~/.hermes/CHANGELOG_SISTEMA.md`.
- Bloque H: diagnóstico del blind spot de logging de
  `agent.conversation_loop` (no llega a journald en modo gateway).
- Bloque N: contexto no disponible en esta sesión (ver SUPUESTOS en
  `~/.hermes/reporte_bloque_o_22jul.md`).
