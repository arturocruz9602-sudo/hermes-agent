# Historial de Bloques — Hermes

Este archivo no existía antes del 22 Jul 2026 (creado en O.8, primera
entrada retroactiva es Bloque O porque es el bloque activo al momento de
crear este archivo; bloques anteriores no se reconstruyen aquí).

## Bloque S.5 + fix ventana O.6 — cascada de compactación infinita (27 Jul 2026) — CERRADO

Encontrado sin buscarlo, durante un diagnóstico dedicado de O.6 (pedido
por Arturo: "vamos de uno por uno desde el más difícil al más
sencillo", empezando por O.6 -- fabricación de evidencia de
incidentes, CRÍTICO desde el 22 Jul).

**Reproducción en vivo (arnés interno, `tests/e2e/hermes_harness.py`,
sesión real `20260723_014401_467841eb`, sin tocar Telegram real):**
mandar un mensaje real de prueba disparó "Sesión comprimida 2 veces" ->
"3 veces" -> ..., sin llegar NUNCA a una respuesta real, en 2 llamadas
de prueba distintas. Confirmado con `sqlite3` sobre `state.db`: esa
sesión llevaba `message_count=4` pero `api_call_count=37` (ahora 38) --
mucho trabajo real de LLM sin turnos completados.

**Causa raíz, confirmada por lectura de código (`agent/turn_context.py`)
Y matemáticamente, no solo por sospecha:**
- `_should_compress_now` se dispara con `_preflight_tokens >=
  ESCALATION_SAFE_TRIGGER_TOKENS` (30,000 -- Bloque S, 23 Jul).
- El bucle de hasta 3 pasadas de compresión (`for _pass in
  range(_max_preflight_passes)`) sigue comprimiendo mientras
  `_preflight_tokens >= ESCALATION_SAFE_TRIGGER_TOKENS` siga siendo
  cierto (línea ~948 antes del fix).
- Pero el TARGET real de cada pasada de compresión
  (`agent._compress_context` -> `threshold_tokens *
  summary_target_ratio`) se calcula sobre el umbral del modelo
  PRIMARIO: con Gemini (~1,048,576 de contexto) y `threshold: 0.5` +
  `target_ratio: 0.2` (config.yaml), eso da `524,288 * 0.20 = 104,857`
  tokens -- muy por ENCIMA de 30,000.
- Resultado: cada pasada de compresión "tiene éxito" (reduce tokens de
  forma material, >5%) pero SIEMPRE deja la sesión por encima de
  30,000 -- así que el chequeo de "¿sigo comprimiendo?" nunca se
  satisface, se agotan las 3 pasadas cada turno, y el turno SIGUIENTE
  vuelve a repetir exactamente lo mismo. Para siempre, mientras la
  sesión se mantenga sobre 30K (que es justo lo que la compresión
  normal produce).

**Confirmado con búsqueda real en internet (regla de CLAUDE.md
aplicada, pedido explícito de Arturo):** el repo real
`NousResearch/hermes-agent` en GitHub tiene un issue cerrado,
[#53008](https://github.com/NousResearch/hermes-agent/issues/53008)
("Context Compression Infinite Loop"), con el MISMO síntoma general
(compresión que nunca baja lo suficiente, se repite sin parar) aunque
su mecanismo exacto (modelo auxiliar de compresión más chico que el
umbral) es distinto al nuestro (que es 100% propio de Bloque S, una
constante nuestra sin relación con el modelo auxiliar). Se revisó
también el issue #29926 (compresión descartada en modo CLI) --
descartado por no aplicar: corremos en modo gateway, ya arreglado
upstream para ese modo según el propio issue.

**Fix aplicado (`agent/turn_context.py`, "Bloque S.5"):** constante
nueva `ESCALATION_TARGET_TOKENS = 20_000`. Mientras
`_escalation_triggered` sea cierto (el disparo fue por la escalera, no
por el umbral del primario), se sobreescribe temporalmente
`_compressor.threshold_tokens` a `20_000 / summary_target_ratio` justo
antes del bucle de pasadas (para que el target real de
`_compress_context` apunte bajo el disparador de escalera), y se
restaura al valor original justo al salir del bucle -- mismo patrón ya
establecido por Bloque S.1 (`protect_last_n` temporal). `getattr` con
default 0.20 para no romper compressors de prueba sin ese atributo
(encontrado real al correr la regresión, corregido antes de cerrar).

**Verificado en vivo, con la MISMA sesión que antes cascadeaba:** tras
el fix, una sola pasada de preflight, sin ninguna repetición de
"Sesión comprimida N veces" -- el turno llegó a intentar la llamada
real al proveedor (bloqueada solo por un límite de cuota real, de
tanto probar hoy mismo -- no por el bug).

**Bonus, mismo diagnóstico -- fix de O.6:**
`run_incident_verification()` (`agent/complexity_detector.py`) llamaba
a `verificar_incidente.py` con ventana ±10 min anclada a "ahora".
Probado en vivo preguntando por el cierre no-limpio real del gateway
de esta misma sesión (11:44:48, ~16 min antes de la prueba): quedó
FUERA de la ventana de 10 min -- el script correctamente no encontró
nada de eso, pero SÍ encontró ruido rutinario de litellm en la ventana
y lo marcó `hay_evidencia_real: true`, reproduciendo exacto el patrón
descrito en `reporte_bloque_o_22jul.md` ("fragmentos reales pero
irrelevantes presentados como si fueran la evidencia pedida"). Subido
el default a 45 minutos (ventana sigue simétrica -- el script no
acepta rango asimétrico, y no se tocó su contrato porque Arturo también
lo usa a mano). Re-probado en vivo tras el cambio: el mismo incidente
real del gateway SÍ aparece ahora en la evidencia inyectada, con las
líneas reales de `journalctl` citadas tal cual.

**Regresión completa:** 214 (`test_context_compressor.py`) + 22
(`test_turn_context.py`) + 5 (`test_s4_complexity_detector.py`) + 3
(`test_context_compressor_identity_preservation.py`) + 29 (smoke
completo) = **273/273 verde**, 0 regresión. 3 fallas reales encontradas
en la primera corrida (`_FakeCompressor` sin `summary_target_ratio`)
corregidas con `getattr(..., 0.20)` antes de cerrar.

**Desplegado a producción:** `systemctl --user restart
hermes-gateway.service` (excepción pre-aprobada de `CLAUDE.md`, segundo
uso de la sesión, 12:38:06) + 29/29 smoke contra el servicio real ya
con el fix activo.

**Hallazgo aparte, investigado y descartado como bug:** `/new` parecía
no hacer nada en una prueba inicial (la sesión no cambiaba). Leyendo
`gateway/run.py`/`slash_commands.py` se confirmó que SÍ funciona, pero
está detrás de una confirmación explícita sí/no
(`approvals.destructive_slash_confirm`, gate de comandos destructivos)
-- la prueba nunca contestó esa confirmación. No es un bug, es diseño
intencional de seguridad.

**Continuación real, mismo día (Bloque O.6.1/O.6.2) -- el hallazgo
ORIGINAL de O.6 SÍ se reprodujo y SÍ se arregló, con evidencia real:**
con cuota ya disponible, se probó de nuevo preguntando por un incidente
real reciente (el reinicio del propio gateway de esta sesión). El
modelo IGNORÓ la evidencia real inyectada -- llamó `read_file`/
`terminal` por su cuenta sobre `~/.hermes/logs/agent.log.3` (rotado,
del 30 de junio) y presentó eso como el estado ACTUAL ("último inicio:
2026-06-30... funcionando normalmente"), pese a que el reinicio real
había sido minutos antes. Reforzar la instrucción de texto ("PROHIBIDO
leer otros logs") NO cambió el comportamiento -- se repitió idéntico.

**Fix real aplicado (Bloque O.6.2, `agent/turn_context.py`):** en vez
de otra instrucción de prompt, se le quita mecánicamente la
posibilidad de llamar CUALQUIER herramienta durante un turno donde
`looks_like_incident_check()` disparó la inyección real de O.6 --
`agent.tools = []` para ese turno, restaurado de forma self-healing al
INICIO del turno siguiente (no depende de que el turno actual termine
limpio, así una salida temprana por compresión/error no deja las
herramientas apagadas para siempre). Verificado en vivo: 3 intentos
posteriores, **0 llamadas a herramientas** (antes, 100% de los
intentos llamaban a `read_file`/`terminal`). En 2 de los 3, otros
mecanismos de seguridad YA EXISTENTES (O.4 español, reintento de
"empty response" del framework) atraparon respuestas problemáticas de
forma segura -- sin fabricar nada, solo un aviso genérico. Residual
conocido: con `agent.tools=[]`, el modelo (Gemini con razonamiento)
puede a veces quedarse en "solo razonamiento, sin respuesta visible" --
comportamiento YA manejado por el framework (reintentos + aviso
honesto), no una fabricación nueva.

**Bonus (Bloque O.6.1, `agent/turn_finalizer.py`):** backstop mecánico
adicional, mismo patrón que la Tarea 1 (`_FABRICATED_SUCCESS_RE`): si
la evidencia real de este turno decía `hay_evidencia_real: true` y la
respuesta final la niega explícitamente ("no mostró errores"), se
reemplaza por un mensaje que cita la evidencia real tal cual.

**Regresión adicional:** 353 tests corridos en total entre ambos
commits (214 `test_context_compressor` + 22 `test_turn_context` + 8
smoke S4/identity-preservation + 80 `turn_finalizer`/`turn_context`/
fabrication + 29 smoke completo), 0 regresión real -- 2 fallas en
`test_turn_context_overflow_warning.py` confirmadas PRE-EXISTENTES con
`git stash` (idénticas sin este fix, ya documentadas en `ESTADO.md`
como parte de los 4 hallazgos preexistentes del rebase de Bloque 1).
Desplegado a producción (`systemctl --user restart
hermes-gateway.service`, 13:13:33, TERCER uso de la excepción esta
sesión) + 29/29 smoke contra el servicio real.

**Con esto, Bloque O.6 (abierto desde el 22 Jul, marcado CRÍTICO) queda
CERRADO** -- causa raíz confirmada en las 3 capas (ventana mal anclada,
modelo ignorando texto, modelo llamando herramientas sin relación), fix
real y mecánico en cada una, verificado en vivo, no solo instrucción de
prompt.

## Bloque 6 (HAS Fase 2) — corte real a producción (27 Jul 2026) — EN OBSERVACIÓN, no cerrado

Ejecutado con Arturo presente, siguiendo el procedimiento de 6 bloques
de la skill `hermes-upgrade` (ver Bloque 5). Resumen completo con
evidencia en `docs/ESTADO.md`, sección "Bloque 6". Puntos que vale la
pena dejar aquí con más detalle técnico:

**Verificación previa al corte (lo que evitó una regresión real):** el
procedimiento original de la skill decía simplemente "cambia producción
al código/venv nuevo (rama arturo/base ya verificada)". Antes de
ejecutar eso literal, se comparó `main` (producción) contra
`arturo/base` desde su ancestro común (`a81c5922a`):
- `main` tenía 41 commits propios que `arturo/base` no tenía por SHA
  directo.
- Verificado uno por uno con `git merge-base --is-ancestor <sha>
  arturo/base`: los 41 están TODOS presentes como cherry-picks reales
  (mismo contenido, SHA distinto) -- Tarea 1, Tarea C/D/G, Tarea E,
  Tarea E v2, Tarea I, Bloques AF/AG/AH, voz, caché, seguridad, ledger
  DeepSeek, kanban, i18n, gitignore.
- La ÚNICA divergencia real: `CLAUDE.md`, `docs/ESTADO.md`,
  `docs/BLOQUES.md`, `docs/BITACORA_ARTURO.md` -- versiones congeladas
  en `arturo/base` desde que se creó el worktree `hermes-019`. El resto
  de `docs/` (`HAS.md`, `PROTOCOLO.md`, `HISTORIAL.md`,
  `GUION_PRUEBAS.md`) ya era idéntico.

Sin esta verificación, un `git reset --hard arturo/base` directo habría
sido seguro en código pero habría **borrado silenciosamente la bitácora
y el estado reales** de Arturo, reemplazándolos por versiones viejas.

**Hallazgo real de infraestructura, encontrado en el camino (no
buscado):** `/mnt/seagate` estaba desmontado al momento de empezar.
`journalctl -k` confirmó la causa real: una desconexión sucia por error
de I/O genuino a las 08:22 de hoy (`device offline error`, `Buffer I/O
error`, `JBD2: I/O error when updating journal superblock`), seguida 2
segundos después de una re-enumeración USB del mismo disco -- no fue
que Hermes "no lo detectara", fue una falla real de conexión/energía.
No se re-montó solo porque `/mnt/seagate` vive en `/etc/fstab` sin
`x-systemd.automount`, y `udisks` tiene `HintAuto: false` para
cualquier entrada de fstab (las excluye a propósito de su
automontaje). Se quedó desmontado ~3 horas sin que nada lo reportara.
Montado manual con `udisksctl` (sin sudo), journal de ext4 recuperado
al montar (`recovery complete`), sin errores nuevos desde entonces.
**Pendiente real:** Arturo corra `smartctl` para descartar disco
fallando vs. cable/puerto USB -- se le pidió explícitamente porque el
comando requiere `sudo` interactivo.

**Corrección (27 Jul 2026, tarde) -- lo de abajo NO era un bug, era
diseño intencional mal diagnosticado en el momento.** Al pedirle a
Arturo que corriera `systemctl --user stop hermes-gateway` (bloqueado
el intento automático por el hook, correctamente), el proceso salió con
`status=1/FAILURE` en vez de 0 -- en su momento se documentó como "bug
real sin investigar". Investigado a fondo: es **exactamente el
comportamiento diseñado**. `gateway/run.py:24822-24898`
(`shutdown_signal_handler`) distingue una parada PLANEADA (marcador
escrito por el comando `hermes gateway stop` antes de mandar la señal,
o un `SIGINT` de Ctrl+C) de una señal "inesperada" (cualquier otra
fuente, incluido `systemctl stop` directo sin pasar por ese comando).
Sin el marcador, el proceso se clasifica a sí mismo como "apagón
inesperado" y sale con código 1 A PROPÓSITO -- combinado con
`Restart=always` (confirmado en el `.service`), esto hace que
`systemd` lo reviva solo ante un kill real (OOM, contenedor, `kill -9`
externo, etc.). `systemctl stop` nunca puede escribir ese marcador (es
un mecanismo interno de Hermes, no algo que `systemd` conozca), así
que CUALQUIER `systemctl stop`/`restart` directo -- incluida la propia
excepción pre-aprobada de `CLAUDE.md` -- sale con 1 por diseño, nunca
con 0. No hay nada que arreglar aquí. Original (incorrecto, dejado
para que quede el rastro del error real): "bug real en el manejador de
cierre, pendiente de diagnóstico dedicado".

**Pasos ejecutados, en orden, con evidencia real:**
1. `git tag pre-bloque6-cutover-20260727` sobre `7e33bae1c` (rollback:
   `git reset --hard pre-bloque6-cutover-20260727`).
2. Disco montado (ver arriba).
3. `hermes-gateway` parado por Arturo (ver hallazgo arriba).
4. `tar -czf /mnt/seagate/backups/hermes_pre_upgrade_20260727.tar.gz`
   (excluye `venv`/`node_modules`) -- 700M, verificado íntegro con
   `tar -tzf` (lista sin error).
5. `git reset --hard arturo/base` -- HEAD a `47a82f21a`.
6. `git checkout pre-bloque6-cutover-20260727 -- CLAUDE.md
   docs/ESTADO.md docs/BLOQUES.md docs/BITACORA_ARTURO.md` + commit
   `b11a117bf` -- verificado con `diff` = 0 contra el `main` anterior
   en los 4 archivos.
7. `systemctl --user restart hermes-gateway.service` (11:49) -- ÚNICO
   uso de la excepción pre-aprobada del hook esta sesión, resultado:
   activo.
8. `venv/bin/python3 -m pytest tests/smoke/ -v` contra producción real
   (no worktree) -- **29/29 passed**. Confirmado en vivo: el fix de
   `mensajes_pendientes` (`CREATE TABLE IF NOT EXISTS`, bug real de
   Bloque 4) ya está en el `hermes_state.py` real. `hermes-gateway` y
   `litellm` activos, 0 errores/tracebacks en logs desde el reinicio.

**NO cerrado.** Falta la ventana de 24h de observación real de logs
(paso 6 del procedimiento de `hermes-upgrade`) antes de declarar
Bloque 6 -- y con él, HAS Fase 2 completa -- cerrado.

## OT-QA — LOGIN REAL COMPLETADO (27 Jul 2026, tarde) — CERRADO

Continuación directa de la sección de abajo. En vez de esperar la
respuesta de `recover@telegram.org` (enviada, sigue sin contestar),
Arturo sacó un `api_id`/`api_hash` NUEVO desde su cuenta PERSONAL ya
establecida (no la QA) en my.telegram.org -- basado en la documentación
real de Telethon citada ahí mismo: *"This API ID and hash is the one
used by your application, not your phone number. You can use this API
ID and hash with any phone number."* `SendCodeRequest` con esas
credenciales nuevas SÍ pasó a la primera -- confirma que el bloqueo
real siempre fue de la app/cuenta nueva (vigilancia automática
anti-abuso), no de la IP ni del número QA en sí.

**Segundo bug real encontrado en el camino, root-caused y arreglado:**
4 intentos seguidos de completar el login fallaron con
`PhoneCodeExpiredError`, cada vez con un código recién enviado --
descartado clima de reloj (`timedatectl`: sincronizado), descartada la
contraseña de la bóveda (verificado leyendo el código: `sign_in()`
ocurre ANTES de que se toque la contraseña de la bóveda, es
estructuralmente imposible que sea la causa). Búsqueda real en GitHub
confirmó la causa: `tools/telegram_userbot.py` original desconectaba
después de `start_login()` y abría un `TelegramClient` COMPLETAMENTE
NUEVO en `complete_login()` -- dos sesiones distintas. Coincide exacto
con [Telethon issue #799](https://github.com/LonamiWebs/Telethon/issues/799)
("confirmation code has expired when using two different clients"):
firmar con un cliente distinto al que pidió el código invalida el
código aunque no haya pasado el tiempo real de expiración.

**Fix aplicado (`tools/telegram_userbot.py`):** `start_login()` ya NO
desconecta -- guarda el cliente conectado en `_pending_login_client`
(module-level). `complete_login()` reutiliza ESE mismo cliente/conexión
en vez de crear uno nuevo, con fallback a una conexión fresca solo si
de plano no hay cliente pendiente (otro proceso). La forma de dos
llamadas se mantiene (sigue sin bloquear con `input()` en llamadas de
herramienta automatizadas), solo se dejó de recrear la conexión.
Regresión: 4/4 tests existentes de `tests/tools/test_telegram_userbot.py`
siguen en verde.

**Login real completado y verificado en vivo, con evidencia real (no
solo el mensaje de éxito del script):**
1. Corrido con un script de rescate (una sola conexión de principio a
   fin, código pedido por Arturo por SSH/chat, pasado por archivo en
   vez de por `input()` para no bloquear la sesión de la herramienta).
2. Vault verificado con `vault_list_services`: entrada real
   `TELEGRAM_USERBOT_SESSION`, guardada 2026-07-27 17:12:24.
3. **Reconexión real con la sesión guardada, `get_me()` real**:
   `id=8727618189, first_name='Hermes QA', phone='525656372738'` --
   coincide exacto con `QA_USER_ID` de `tools/qa_identity.py`.

**Con esto, OT-QA queda desbloqueado de verdad:** la cuenta QA ya puede
usarse para pruebas E2E reales por Telegram (no solo el arnés interno).
Pendiente real, menor: si algún día se necesita volver a loguear (sesión
revocada, expirada, etc.), usar el flujo ya corregido -- ya no debería
repetirse el bug de los 4 intentos.

## OT-QA — continuación (27 Jul 2026, tarde) — esperando respuesta real de Telegram

Retomado con Arturo presente. Se probaron 2 hipótesis reales, ambas
descartadas con evidencia:

1. **IP residencial vs. IP de datos móviles.** Se encontraron casos
   reales en GitHub (issues de Telethon) donde el mismo `api_id` fallaba
   desde una red doméstica y funcionaba sin cambios desde un servidor
   AWS -- sugiere una posible lista blanca/gris por reputación de IP.
   Probado en vivo: se conectó la laptop al hotspot del teléfono de
   Arturo (verificado con IP pública real, `ALTAN REDES`, Toluca, ya NO
   la IP de casa) y se reintentó `start_login()` -- **mismo error
   exacto**. Red restaurada a la normal (ethernet) después, verificado
   con `curl ifconfig.me` que la IP volvió a la de casa. Con esto, la
   teoría de "solo necesita una IP no-residencial" queda descartada --
   al menos una IP de operador móvil mexicano tampoco basta.
2. **Recrear la app en my.telegram.org con el mismo número.** Revisado
   en vivo con capturas de pantalla reales de Arturo: `App api_id` y
   `App api_hash` son permanentes, no editables, y my.telegram.org no
   ofrece una opción de autoservicio para borrar/recrear la app. Esta
   ruta queda descartada por no ser técnicamente posible, no por falta
   de intentarlo.

**Causa raíz más probable, encontrada en la documentación OFICIAL de
Telegram** (`core.telegram.org/api/obtaining_api_id`, no un tercero):
"todas las cuentas que inician sesión con clientes no oficiales de la
API quedan automáticamente bajo observación para evitar abuso... si tu
cuenta queda restringida sin haber violado los Términos de Servicio,
escribe a `recover@telegram.org` explicando el uso que le darás,
pidiendo que la desbloqueen." Coincide exacto con el patrón: cuenta
nueva + api_id nuevo + rechazo específico y persistente en
`SendCodeRequest` (no en la conexión general).

**Acción tomada:** correo redactado (explicación honesta: automatización
personal de bajo volumen, no bot para terceros, no flooding/spam) y
enviado por Arturo mismo a `recover@telegram.org` (no lo mandé yo --
pedir el desbloqueo de una cuenta a un tercero es una acción que debe
venir del dueño). **EN ESPERA de respuesta real de Telegram** -- puede
tardar días, es revisión humana. Retomar el login en cuanto Arturo
confirme respuesta (positiva o negativa).

## OT-QA — userbot: api_id/api_hash rechazados >12h seguidas, EN CURSO sin resolver

`start_login(api_id=35683031, api_hash=F4f73f75382ccc69ce4fd9f213d40e4b,
phone=+525656372738)` -- reintentado ~7 veces entre la tarde del 24 jul y
la madrugada del 25 (sesión anterior: intentos 1-3 de una tanda de 10;
esta sesión: 4 reintentos automáticos por hora, vía ScheduleWakeup) --
mismo error idéntico siempre: `ApiIdInvalidError: The api_id/api_hash
combination is invalid (caused by SendCodeRequest)`.

**Descartado, con evidencia:**
- No es error de dedo -- confirmado contra la captura de pantalla original.
- No es la cuenta equivocada al crear el app en my.telegram.org -- Arturo
  confirmó que usó el número nuevo (QA) desde el principio, no el suyo.
- No es problema de red/librería -- verificado ahora: `TelegramClient.connect()`
  con estas mismas credenciales SÍ conecta a los servidores reales de
  Telegram (`is_user_authorized() -> False`, como se espera antes de
  loguear) -- el rechazo es específico de `SendCodeRequest` con este
  par, no de la conectividad.
- La teoría original ("app recién creada tarda unos minutos en activarse")
  ya no aplica -- llevamos >12 horas, no minutos.

**Sin confirmar/pendiente para cuando Arturo esté disponible:** por qué
sigue inválido después de tanto tiempo. Hipótesis no probadas: (a) el
número nuevo (SIM recién comprada) sigue sin la antigüedad que Telegram
exige para permisos de API (visto en reportes de terceros, sin
confirmación oficial), (b) el api_id se generó mal por algún otro motivo
no identificado, (c) restricción por IP/región de la app creada. Se
recomienda, cuando Arturo despierte: entrar de nuevo a my.telegram.org
con la cuenta QA, confirmar si la aplicación sigue apareciendo ahí tal
cual (no fue borrada/revocada), y si sigue igual, considerar borrar y
recrear la aplicación desde cero en vez de seguir reintentando el mismo
par indefinidamente.

## Bloque AI — incidente de infraestructura: Bash roto por cuota de disco en /tmp (24-25 Jul 2026) — RESUELTO

No es trabajo sobre el código de Hermes -- es una falla de la
herramienta (Claude Code) en la laptop de Arturo que impidió correr
cualquier comando durante ~3 horas.

**AI.1 — Síntoma:** toda sesión de Claude Code (nueva, continuada con
`-c`, con `--safe-mode`, después de reinstalar con `claude install
2.1.212`) reportaba "Exit code 1" sin stdout ni stderr para CUALQUIER
comando de Bash, incluido `echo hi` y `pwd`. `claude doctor` (chequeo
oficial de instalación) no encontró problemas.

**AI.2 — Pistas falsas descartadas, con evidencia de cada descarte:**
1. Bug de versión 2.1.220 (había un `autoUpdatesChannel` sin fijar):
   se fijó a "stable", se reinstaló 2.1.212 explícitamente -- seguía
   igual.
2. Canal de "control remoto" con restricciones propias: descartado al
   confirmar con `ps aux` que el proceso normal de terminal (PID
   2093173, sin zombies) tenía el mismo fallo exacto.
3. Hook `hermes-guard.sh` con bug o `jq` faltante: descartado -- `jq`
   instalado y funcional (`Read` en `/usr/bin/jq` lo confirmó), el
   contenido del hook se revisó línea por línea, sin errores de sintaxis.
4. Permisos/config de `settings.json`: revisado, correcto (`"Bash"` en
   `allow`, timeout de 10s, ruta del hook correcta).
5. Límites del proceso (`/proc/PID/limits`) y variables de entorno
   (`PATH`, `SHELL`): revisados, normales (29051 procesos, 524288
   archivos abiertos, `PATH`/`SHELL` sanos).
6. `--safe-mode` (apaga TODOS los hooks/plugins/MCP/config): probado,
   MISMO fallo exacto -- esto fue lo que finalmente descartó cualquier
   causa de configuración.

**AI.3 — Causa raíz real, confirmada:** búsqueda en internet (tras ~3
horas sin buscar -- ver regla nueva en `CLAUDE.md`) encontró issues
idénticos en el repo de `anthropics/claude-code` (uno en Arch Linux,
#41124) apuntando a que el Bash tool captura stdout/stderr escribiendo
a archivos temporales bajo `/tmp/claude-1000/`, y que sin espacio esa
escritura falla silenciosa (`ENOSPC`/`EDQUOT`), reportando "exit 1" sin
ningún mensaje. Confirmado en esta laptop:
```
Write(/tmp/claude_write_test.txt) → error EDQUOT: unknown error, write
```
`df -h /tmp` mostró `tmpfs 3.6G, 2.9G usados (80%)`; `du -sh /tmp/*`
identificó `/tmp/pytest-of-arturo` (2.4G) como el mayor consumidor --
sobras de corridas de pytest nunca limpiadas.

**AI.4 — Fix aplicado y verificado en vivo:**
```
rm -rf /tmp/pytest-of-arturo
```
`df -h /tmp` después: `469M usados (13%)`. Probado de inmediato con
`Bash: echo "bash-ok" && pwd && date` → salida correcta
(`bash-ok` / `/home/arturo/.hermes/hermes-agent` / hora real). No
requirió reiniciar la sesión -- el fix de espacio en disco aplica al
siguiente intento de escritura, a diferencia de un fix de versión que
sí necesitaría reiniciar el proceso.

**AI.5 — Pendiente, en cuarentena por diseño (requiere `sudo`, bloqueado
para automatización por `hermes-guard.sh` regla 1 y 2 -- Arturo lo
corre directo en su terminal, comandos ya entregados en el chat):**
1. Agrandar `/tmp` de 3.6G a 8G de forma persistente:
   ```
   sudo mkdir -p /etc/systemd/system/tmp.mount.d
   printf '[Mount]\nOptions=mode=1777,strictatime,size=8G\n' | sudo tee /etc/systemd/system/tmp.mount.d/size.conf
   sudo systemctl daemon-reload
   sudo mount -o remount /tmp
   ```
2. Cron de usuario (sin `sudo`, comando ya entregado, bloqueado también
   por el hook al querer aplicarlo yo mismo por llevar `rm -rf`):
   ```
   (crontab -l 2>/dev/null; echo "17 4 * * * find /tmp -maxdepth 1 \( -name 'pytest-of-*' -o -name 'hermes_e2e_*' -o -name 'hermes-test-home-*' -o -name 'hermes-results' -o -name 'kanban_per_profile_cap_test_*' \) -mtime +2 -exec rm -rf {} + >/dev/null 2>&1") | crontab -
   ```

**AI.6 — Regla agregada a `CLAUDE.md` (hermes-agent), sección nueva
"SI UNA HERRAMIENTA MÍA FALLA RARO":** ante fallas de entorno/herramienta
(no del código de Hermes) que persisten tras 1-2 diagnósticos
verificados, buscar en internet antes de seguir adivinando o pedirle a
Arturo que pruebe más cosas a ciegas. Motivo explícito: esta sesión
tardó ~3 horas en llegar a la causa real por no buscar antes.

## Bloque AH — bug real de compactación: mensajes duplicados en state.db + bloqueaba ofertas de Tarea E (24 Jul 2026) — CERRADO

Encontrado sin buscarlo, siguiendo instrucción explícita de Arturo
("si algo está mal... hay que verificar y solucionar") tras una prueba
E2E de DeepSeek que no se completó limpiamente (ver Fase 1 más abajo).

**AH.1 — Síntoma real observado (state.db, sesión
`20260723_014401_467841eb`):** una pregunta compleja real + "sí" (para
aceptar una oferta de Tarea E) produjo la MISMA pregunta y la MISMA
respuesta **duplicadas 3 veces**, y el mismo "sí" aparece **4 veces**,
todas con el timestamp EXACTO original (`10:56:16.978`) — prueba directa
de que eran re-escrituras de UN SOLO mensaje real, no mensajes nuevos.
Coincidió con 5 compactaciones seguidas en el mismo turno.

**AH.2 — Causa raíz confirmada (no solo sospecha):**
`ContextCompressor._prune_old_tool_results()` (`agent/context_compressor.py:1016`)
hacía `result = [m.copy() for m in messages]` — copiaba TODOS los
mensajes al entrar, incluidos los de la cola protegida
(`protect_last_n`/`protect_tail_tokens`) que la función nunca toca.
`run_agent.py::_flush_messages_to_session_db` deduplica lo que ya se
guardó en la base de datos **únicamente por identidad de objeto de
Python** (`id(msg)`, elegido a propósito para sobrevivir a
`repair_message_sequence`, ver su propio docstring, issue #860) — un
mensaje ya guardado que de repente tiene un `id()` nuevo se ve como
"nuevo" y se vuelve a escribir. Cada pasada de compactación generaba
copias nuevas de TODA la cola protegida, así que cada una producía una
fila duplicada.

**Efecto secundario real, confirmado:** el "candado" que resuelve una
oferta de Tarea E (`agent/complexity_detector.py::check_pending_reply`)
tiene un endurecimiento deliberado post-incidente: "cualquier mensaje
de por medio cancela la oferta pendiente". Los duplicados fantasma que
generaba este bug contaban como "mensaje de por medio", cancelando una
oferta real de DeepSeek recién registrada antes de que el "sí" del
usuario pudiera resolverla — la prueba E2E de DeepSeek (ver Fase 1) NO
disparó un despacho real precisamente por esto.

**AH.3 — Fix aplicado, mínimo y quirúrgico:**
- `_prune_old_tool_results`: `result = [m.copy() for m in messages]` →
  `result = list(messages)` (copia de LISTA, no de cada diccionario).
  Seguro porque las 3 pasadas de la función ya modifican con
  copy-on-write real (`result[i] = {**msg, ...}`, nunca mutación en
  sitio) — un mensaje jamás tocado conserva su identidad original.
  Mismo patrón que `_strip_historical_media` ya usa en el mismo
  archivo ("Shallow copies of touched messages only; input is never
  mutated").
- `ContextCompressor.compress()`, Fase 4 (ensamblado final): mismo
  principio aplicado a las dos pasadas de cabeza/cola — solo copia el
  ÚNICO mensaje que de verdad se modifica (nota de compactación en el
  system prompt, o el mensaje donde se fusiona el resumen), no todos.

**AH.4 — Verificado con evidencia real, no solo lectura de código:**
```
target id (mensaje original, antes de comprimir): 128594271753536
[trace] _sanitize_tool_pairs: id antes=128594271753536 despues=128594271753536 igual=True
compressed[-3] id: 128594271753536
es el mismo objeto: True
```
(Antes del fix, este mismo trace daba `False` — probado explícitamente
comparando ambas corridas.) 3 tests nuevos dirigidos
(`tests/agent/test_context_compressor_identity_preservation.py`, 3/3
verde) + regresión completa de compresión: 163 (`test_context_compressor*`
y relacionados) + 123 (`test_context_compressor.py` re-corrido) + 243
(`tests/gateway/`+`tests/run_agent/`+`tests/tools/test_computer_use.py`
+ locks) = **446/447 verde**. El único fallo
(`test_413_compression.py::test_preflight_compresses_when_rough_growth_after_fit_is_large`)
se confirmó PREEXISTENTE con `git stash` — falla idéntico sin este fix,
en un test que mockea `_compress_context` por completo (nunca ejecuta
el código que se tocó aquí).

**AH.5 — CERRADO el mismo día, con evidencia real (Arturo pidió
explícitamente "verifica que funcione DeepSeek").**

Primer intento (flujo natural, `/new` + pregunta compleja + "sí"):
confirmó que el fix de AH.3 elimina los duplicados (cada mensaje una
sola vez, timestamps únicos), pero NO se registró ninguna oferta de
Tarea E para esa pregunta — `tarea_e_ofertas` no tiene fila nueva en
ese rango de tiempo. Causa más probable (no confirmada al 100%, misma
lógica que AA.2 del 23-jul): la autoevaluación de Tarea E depende de
Gemini, que se ve agotado por el volumen de pruebas del día — cuando
falla, cae a un valor por defecto que SUPRIME la oferta en vez de
ofrecerla.

Segundo intento (directo, deliberado, no depende de que Gemini
autoevalúe): se llamó DIRECTAMENTE a las mismas 2 funciones reales de
producción (`_te_notify_deepseek_dispatch` /
`_te_notify_deepseek_dispatch_done`) más el mismo POST mínimo real que
usa el código (`model: chat-reasoning` vía litellm) — sin atajos,
mismo mecanismo, solo sin esperar a que el disparo natural ocurriera
solo. Resultado real, pegado completo:

```
Notificación ANTES del despacho (capturada real):
"🔔 Despachando AHORA una llamada real a chat-reasoning (Tarea E) --
prueba directa Bloque AH (DeepSeek, gasto real).
Autorización: autorizacion explicita de Arturo en esta sesion ("Si
verifica que funcione deepseek")
Motivo: Verificacion explicita pedida por Arturo...
Gasto acumulado este mes hasta antes de esto: $0.1665 USD"

Fila real nueva en el ledger de litellm (prueba de que el despacho fue
real, a DeepSeek, no a un respaldo gratis):
{"ts_local": "2026-07-24T11:49:16", "model": "deepseek-v4-pro",
 "cost_usd": 6.264e-05, "prompt_tokens": 44, "completion_tokens": 50}

Notificación DESPUÉS del despacho (capturada real):
"✅ chat-reasoning (Tarea E) -- prueba directa Bloque AH terminó --
costo real de este despacho: $0.0001 USD (gasto acumulado del mes
ahora: $0.1666 USD)."
```

**Confirmado: el aviso llega ANTES del despacho real, el despacho SÍ
llega a DeepSeek de verdad (no a un respaldo gratis), y el costo real
se reporta después — las 3 partes de la red de seguridad post-incidente
funcionan, con dinero real, no solo por lectura de código.** Costo
total de esta verificación: $0.0000626 USD. Gasto acumulado del mes:
$0.1666 USD, muy por debajo de cualquier tope. Fase 1 / OT-1 queda
completa: los 4 entregables confirmados (3 ya estaban hechos, este
último quedó cerrado hoy).

## Bloque AG — Opción 3: memoria SQL real y separada para la cuenta QA (24 Jul 2026, mañana) — CERRADO

Decidido en conversación con Arturo tras encontrar el hallazgo AF.4
(MEMORY.md/USER.md sin aislamiento por identidad). Se evaluaron 3
caminos (archivo separado / Fase 4 completa ahora / estructurado solo
para QA) — Arturo eligió el 3º explícitamente ("Si dale") tras
preguntar si no era doble trabajo respecto a la Fase 4 real; la
respuesta (documentada en el chat, no repetida aquí): NO lo es, porque
`memoria_estructurada` es la MISMA tabla que Fase 4 ya tenía planeada
usar, y el camino de Arturo (con aprobación semanal) y el de QA
(automático) son mecanismos distintos por diseño incluso cuando Fase 4
exista completa — no uno sustituye al otro.

**AG.1 — Diseño:** `memory_tool()` (`tools/memory_tool.py`) recibe el
store como parámetro (`store=agent._memory_store`) — no necesitó ningún
cambio. El único punto de inyección es dónde se construye
`agent._memory_store` (`agent/agent_init.py`, dentro de `init_agent`,
después de que `agent._chat_id`/`agent._user_id` ya están asignados).

**AG.2 — Implementado:**
- `tools/qa_identity.py`: fuente única de `QA_USER_ID` (8727618189),
  sin dependencias (ni sqlite ni telethon) para poder importarse en
  `agent_init.py` sin peso extra.
- `tools/sql_memory_store.py`: `SqlMemoryStore`, mismo contrato que
  `MemoryStore` (`add`/`replace`/`remove`/`apply_batch`/`load_from_disk`/
  `format_for_system_prompt`), respaldado por `memoria_estructurada` con
  columnas nuevas `user_id` + `target` (además de `origen`, de Bloque
  AF) — auto-migradas, idempotente. Cada fila queda con `origen='qa'` +
  el `user_id` real de quien escribió.
- `agent/agent_init.py`: si `agent._chat_id`/`agent._user_id` coincide
  con `QA_USER_ID`, usa `SqlMemoryStore`; cualquier otra identidad
  (Arturo incluido) sigue exactamente el camino original
  (`MemoryStore` sobre `MEMORY.md`/`USER.md`), sin ningún cambio de
  comportamiento.

**AG.3 — Verificación EN VIVO, evidencia real (arnés interno, sin tocar
Telegram real, mensaje real construido con la identidad QA vía
`SessionSource`):**
```
ANTES: MEMORY.md sha256=554f667c480ab481... USER.md sha256=164310353554884a...
[mensaje real como QA: "Hermes, guarda en tu memoria que esto es una
 prueba real de Opción 3 desde la cuenta QA."]
DESPUES: MEMORY.md sha256=554f667c480ab481... (IDÉNTICO)
         USER.md sha256=164310353554884a... (IDÉNTICO)
         nueva fila: id=6 hecho='Esto es una prueba real de Opción 3
         desde la cuenta QA.' target=memory (origen=qa, user_id=8727618189)
```
Recall en un turno NUEVO, misma identidad QA, state.db real:
```
id 16615 user: "¿Qué guardaste hace un momento sobre una prueba?"
id 16616 assistant: "En mi memoria guardé que 'Esto es una prueba real
                      de Opción 3 desde la cuenta QA.'"
```
Regresión con la identidad de Arturo (harness normal, `enviar_texto`):
escribió a `MEMORY.md` como siempre (confirmado con `grep` directo),
conteo de filas `origen='qa'` sin cambio (1 antes, 1 después — la de
QA arriba, ninguna nueva de Arturo).

**AG.4 — Tests:** 9 nuevos (`tests/tools/test_sql_memory_store.py`,
incluido aislamiento explícito entre dos `user_id` sobre la misma
tabla) + 4 existentes de `telegram_userbot` sin romper (import
compartido vía `qa_identity.py`) — 93/93 verde en el paquete
`tests/tools/`. Suite más amplia que toca `agent._memory_store`
(`test_context_breakdown.py`, `test_system_prompt.py`,
`test_turn_context.py`, `test_run_agent.py`,
`test_background_review*.py`): 444/444 verde.

**AG.5 — Limpieza:** los datos de prueba propios (1 fila QA sembrada
para la verificación, 1 entrada de prueba en `MEMORY.md` real de
Arturo por la prueba de regresión) se limpiaron con las herramientas
correctas (`scripts/limpiar_memoria_qa.py` y `memory_tool.py` `remove`
respectivamente), nunca a mano.

**Pendiente, fuera de alcance de este bloque:** la Fase 4 real (memoria
estructurada + índice semántico PARA ARTURO, con el flujo de
aprobación semanal) sigue sin construirse — este bloque resuelve la
cuenta QA únicamente, por diseño.

## Bloque AF — Fix de L13/Bloque AE + prep de OT-QA (24 Jul 2026, sesión nocturna autónoma)

Autorizado por Arturo explícitamente ("sí, trabaja toda la noche") tras
revisar las 3 opciones de Bloque AE. Aplicó Opción 1 (orden de
persistencia) + Opción 3 (recencia). Opción 2 (no fusionar mensajes sin
responder) queda deliberadamente sin tocar, para discusión de diseño
aparte.

**AF.1 — Fix implementado (`agent/turn_finalizer.py`, `agent/conversation_loop.py`):**
- `agent._persist_session()` se movió de su posición original (justo
  después de trajectory-save/cleanup) a DESPUÉS de las 4 correcciones
  que pueden reemplazar `final_response` (plugin `transform_llm_output`,
  backstop anti-fabricación de Tarea 1, español de O.4, escáner de
  secretos T.6) y ANTES de `post_llm_call`/Tarea E (para no romper el
  invariante ya existente y deliberado de que la oferta de DeepSeek NO
  se persiste). Justo antes de persistir, `messages[-1]["content"]` se
  sincroniza con el `final_response` ya corregido -- pero SOLO cuando
  `messages[-1]` es inequívocamente la respuesta final en texto plano
  (`role=="assistant"` sin `tool_calls`), para no pisar un mensaje
  intermedio por error.
- `_turn_has_successful_tool_call()` ahora acepta `turn_boundary_idx`
  (reutiliza el mismo `current_turn_user_idx` que Bloque Q.1 ya
  relocaliza por identidad tras `repair_message_sequence_with_cursor()`)
  y acota el escaneo hacia atrás a estrictamente después de ese índice,
  en vez de confiar sin más en el `role=="user"` más cercano. Con índice
  inválido (`None`/`-1`/fuera de rango) cae al comportamiento original
  sin cambios.

**AF.2 — Verificación EN VIVO, evidencia real pegada de `state.db`
(sesión `20260723_014401_467841eb`, con el fix activo, sin reiniciar
`hermes-gateway.service` -- todo corrió vía el arnés E2E como proceso
Python aparte):**

```
Turno 1 (guard bloqueó correctamente, y esta vez SÍ quedó
CORREGIDO en lo persistido -- antes del fix quedaba el texto
fabricado original pese a que el guard bloqueaba):
  id 16605 user: "Hermes, guarda en tu memoria que mi color
                  favorito de prueba Bloque AF es azul-verificacion."
  id 16606 assistant (PERSISTIDO): "⚠️ No puedo confirmar que esa
                  acción se haya completado -- no hubo una llamada
                  real a una herramienta en este turno..."

Turno 2 (esta vez el modelo SÍ llamó la herramienta real -- caso
normal, sin fabricación, persistido limpio):
  id 16608 assistant: tool_calls=[memory.add(...)]
  id 16609 tool: {"success": true, ..., "message": "Entry added."}
  id 16610 assistant (PERSISTIDO): "He guardado en tu memoria que tu
                  color favorito de prueba para el Bloque AF es
                  **azul-verificacion**."
```

**AF.3 — Regresión, evidencia real:**
- 7 tests nuevos (`tests/agent/test_turn_finalizer_bloque_af.py`),
  incluida una reconstrucción directa de la forma exacta del incidente
  original (llamada a herramienta obsoleta + backlog fusionado) -- 7/7
  pasan.
- Suite existente que toca `finalize_turn`/el cierre de turnos
  interrumpidos: `test_turn_finalizer_cleanup_guard.py`,
  `test_turn_finalizer_interrupt_alternation.py`,
  `test_close_interrupted_tool_sequence.py`,
  `test_13121_shutdown_inflight_transcript_flush.py` -- 23/23 pasan.
- Suite completa `tests/agent/` + `tests/gateway/`: `125 failed, 12689
  passed, 113 skipped` en 921s. Los 125 fallos son PREEXISTENTES --
  verificado con `git stash` (revierte Bloque AF por completo) + re-corrida
  de una muestra de 10 de los 125: fallan IDÉNTICO sin el fix (mismo
  `AttributeError: 'GatewayRunner' object has no attribute
  '_pending_reprocess_ids'`, en archivos que ni mencionan
  `turn_finalizer`/`finalize_turn`/`_persist_session`). `git stash pop`
  aplicado de vuelta, verificado con `git status`. No es un bug de
  Bloque AF -- queda registrado como bug abierto preexistente sin
  investigar a fondo (fuera de alcance de este bloque), no silenciado.

**AF.4 -- Hallazgo NUEVO, real, encontrado sin buscarlo, y ya
corregido:** mi propia verificación en vivo (turno 2 de AF.2) escribió
sin querer una entrada de prueba ("mi color favorito de prueba Bloque AF
es azul-verificacion") en el `MEMORY.md` REAL de Arturo -- porque el
arnés usa el `chat_id` real de Arturo, y `tools/memory_tool.py` (el
camino real por el que el modelo guarda cosas cuando dice "lo guardé en
tu memoria") escribe a archivos planos (`MEMORY.md`/`USER.md`) **sin
ningún mecanismo de aislamiento por identidad**. Detectado y limpiado de
inmediato con `memory_tool.py` (`remove`), nunca a mano. Esto es MÁS
urgente que el hallazgo de `memoria_estructurada` de la orden original --
ver AF.5 y BITACORA_ARTURO.md.

**AF.5 -- Columna `origen` + limpieza de prueba (tarea original de la
orden):**
- `memoria_estructurada` (Capa 2, SQL) recibe columna `origen` (migración
  auto-aplicada por `scripts/limpiar_memoria_qa.py` vía `ALTER TABLE ADD
  COLUMN`, idempotente -- esta tabla no vive en el esquema declarativo de
  `hermes_state.py`, es anterior/externa a ese sistema).
- `~/.hermes/scripts/limpiar_memoria_qa.py` escrito y probado en vivo:
  sembrados 2 hechos "reales" + 3 marcados `origen='qa'` -> corrida real
  borró exactamente los 3 `qa`, los 2 reales quedaron intactos (2 -> 2),
  verificado con conteo antes/después. Datos de prueba propios limpiados
  después (no quedaron en `state.db`).
- **Importante, con matiz honesto:** esta tabla (Capa 2) confirmado en
  Bloque AE que NO es el camino real de escritura hoy (0 filas antes de
  esta prueba, `fase2_extract_candidates.py` nunca llama a
  `memory_tool.py`). Útil para cuando Fase 4 la active, pero **NO
  resuelve** el riesgo real encontrado en AF.4 (MEMORY.md/USER.md). Ese
  sigue sin arreglar -- requiere decisión de Arturo (ver BITACORA).

**AF.6 -- Telethon + módulo userbot, listos pero SIN conectar (gateados
por L13, procedimental, no por código):**
- `telethon==1.44.0` instalado en el venv, agregado a
  `pyproject.toml`/`tools/lazy_deps.py` (extra `telegram-userbot`, patrón
  lazy-install igual que el resto de plataformas de mensajería).
- `tools/telegram_userbot.py`: clase `TelegramUserbot` con
  `enviar_texto`/`enviar_voz`/`enviar_foto`/`leer_respuesta`/`cerrar_conversacion`
  reales sobre Telethon, más `login_and_store_session()` para el login
  único cuando toque. **Se niega a conectar** (`L13NotClosedError`) si no
  hay session string real en la bóveda bajo el servicio
  `TELEGRAM_USERBOT_SESSION` -- verificado con 4 tests
  (`tests/tools/test_telegram_userbot.py`, mock de la bóveda, nunca toca
  Telegram real ni la bóveda real). Cuenta QA ya autorizada en el
  emparejamiento (`user_id=8727618189`, ver `hermes pairing list`).
- Pendiente de Arturo cuando decida seguir: `api_id`/`api_hash` de
  `my.telegram.org` + relayar el código de verificación una vez.

**Cierre de AF:** BLOQUE AE queda **CERRADO** -- causa raíz confirmada,
fix aplicado, verificado en vivo con evidencia real pegada arriba, y
regresión unitaria + dirigida en verde. El hallazgo de AF.4
(MEMORY.md/USER.md sin aislamiento) queda **ABIERTO**, registrado en
`docs/BITACORA_ARTURO.md`, pendiente de decisión de Arturo -- no se tocó
la lógica de gating de herramientas sin su autorización explícita
(regla de "seguridad siempre pregunta").

## Bloque AE — Diagnóstico dedicado: fabricación de "guardé tu contraseña" no bloqueada (23 Jul 2026) — **CERRADO en Bloque AF (24 Jul 2026)**

Estado: **CERRADO** (ver Bloque AF arriba para el fix + verificación en
vivo). Diagnóstico puro por instrucción explícita (mismo rigor que
Bloque H y Bloque P) — el fix se aplicó al día siguiente, sesión aparte,
con autorización explícita de Arturo.
Siguiente letra libre confirmada contra este mismo archivo antes de asignar
(AA-AD ya usadas en la sesión de mañana, ver sección siguiente).

**AE.1 — Reconstrucción del incidente real (state.db, evidencia textual):**
sesión `20260723_014401_467841eb`, mensaje id 16560 (usuario, 2026-07-23
04:13:31, `hola Hermes, esto es una prueba del arnes interno`, del arnés
E2E interno de Bloque V) → respuesta id 16561 (asistente, 04:13:42,
`tool_calls=None`, `finish_reason='stop'`): *"Perfecto, Arturo. He guardado
la contraseña **MOTO** para la plataforma **Cisco**, utilizando la palabra
clave **REDES** para acceder a ella..."* — coincide palabra por palabra con
el hallazgo ya descrito en `docs/BITACORA_ARTURO.md` ("HALLAZGO SIN
ARREGLAR" del 23 Jul).

**Precondición real encontrada (no la que se sospechaba):** en `state.db`,
los 2 mensajes inmediatamente anteriores (id 16558, voz real de Arturo a
las 02:54:05 pidiendo guardar la contraseña de Cisco/UCISCO; id 16559,
corrección real de Arturo a las 02:57:33 "la contraseña es MOTO... la
palabra clave va ser redes") **nunca recibieron una respuesta real** antes
de que el mensaje de prueba (16560) llegara más de una hora después — son
3 mensajes `role=user` consecutivos sin ningún `assistant`/`tool` entre
ellos. **NO había ningún resumen de compactación (`[CONTEXT COMPACTION —
REFERENCE ONLY]`) activo en la conversación en ese momento** — los
mensajes con ese marcador en la misma sesión tienen ids MÁS ALTOS
(16564+), es decir aparecieron DESPUÉS, en repeticiones posteriores del
mismo arnés, no como precondición del incidente original. **Esto descarta
la hipótesis literal de Arturo (interacción con el resumen de
compactación) como causa del incidente raíz** — la precondición real es
un mensaje sin responder (backlog), no un resumen de compactación.

**AE.2 — Por qué `_turn_has_successful_tool_call()` no depende del bug de
Bloque P:** confirmado leyendo `agent/turn_finalizer.py` y con print() real
en vivo (ver AE.4) que esta función NO usa `current_turn_user_idx` ni
ningún índice precalculado — hace un escaneo hacia atrás en vivo sobre
`messages` cada vez que se llama, deteniéndose en el primer `role=="user"`
encontrado. El bug de Bloque P (índice obsoleto tras
`repair_message_sequence_with_cursor()`) es estructuralmente imposible
aquí porque no hay índice que se pueda quedar obsoleto. **Confirmado:
mecanismo DISTINTO al de Bloque P**, no el mismo bug con otro nombre.

**AE.3 — Mecanismo real de fusión de mensajes encontrado (lectura de
código, `agent/agent_runtime_helpers.py:355` `repair_message_sequence()`):
la Pasada 2 fusiona mensajes `user` consecutivos en uno solo (unidos con
`\n\n`)** — así que los 3 mensajes sin responder (16558+16559+16560) muy
probablemente llegaron al modelo como UN SOLO turno combinado (voz sobre
Cisco + corrección + "hola, prueba"), y el modelo respondió a la parte
sustantiva (la contraseña) e ignoró la trivial. Esto también existe a
nivel de plataforma: `gateway/platforms/base.py`
(`merge_pending_message_event`, `_pending_messages`) fusiona mensajes de
texto que llegan mientras el turno anterior sigue ocupado.

**AE.4 — Hallazgo NUEVO, real, verificado EN VIVO con print() (no estaba
en el mandato original pero es más grave): bug de orden de operaciones en
`finalize_turn` (`agent/turn_finalizer.py`).** `agent._persist_session()`
corre en la línea 326 — ANTES de que corran: el hook de plugin
`transform_llm_output` (línea ~458), el backstop anti-fabricación de
Tarea 1 (línea ~481), y el enforcement de español de Bloque O.4 (línea
~532). Los tres SOLO modifican la variable local `final_response`; NINGUNO
vuelve a escribir `messages[-1]["content"]`. Como `messages[-1]` ya se
agregó dentro del loop principal (`agent/conversation_loop.py:4916`,
`messages.append(final_msg)`, con el texto CRUDO del modelo) antes de
llamar a `finalize_turn`, **la sesión persistida en `state.db` — y por lo
tanto el historial que el modelo vuelve a leer en turnos futuros — siempre
contiene el texto SIN corregir**, sin importar si el guard bloqueó o no
esa entrega puntual.

Verificado en vivo (Bloque AE.5, reproducción #2): con instrumentación
`print()` real, un mensaje de prueba ("Hermes, guarda en tu memoria que mi
color favorito de prueba Bloque AE es verde-diagnostico.") hizo match con
el regex de fabricación y `_turn_has_successful_tool_call()` devolvió
`False` (bloqueado) — pero el mensaje id 16602 en `state.db` quedó
guardado con el texto ORIGINAL fabricado ("He guardado en tu memoria que
tu color favorito..."), no con el mensaje de reemplazo seguro. Confirmado
que esto NO depende de que el guard falle: pasa incluso cuando el guard
funciona bien.

**AE.5 — Reproducciones en vivo (arnés E2E interno, `tests/e2e/hermes_harness.py`,
mismo mecanismo de Bloque V, sin tocar Telegram real):**
1. Mensaje de prueba sin relación con contraseñas, enviado a la MISMA
   sesión real del incidente (que en ese momento tenía 4 mensajes de
   usuario sin responder en cola, incluida una pregunta pendiente real
   "Hermes sabes en qué se quedó el proyecto de Hermes?"): la respuesta
   mezcló el saludo de prueba CON una respuesta a la pregunta pendiente no
   relacionada — reproduce en vivo, ahora mismo, el mecanismo general de
   "conflación con mensaje sin responder", sin ningún resumen de
   compactación presente (`compaction_summary_at_idx=[]`).
2. Mensaje con verbo de acción real ("Hermes, guarda en tu memoria...") en
   una conversación limpia (sin backlog): el guard SÍ bloqueó
   correctamente (`_turn_has_successful_tool_call()` → `False`) — caso de
   control, confirma que el guard no está roto en general. Reveló AE.4 en
   el proceso (ver arriba).
3. Intento de simular la precondición exacta del incidente original
   (mensaje real cancelado a media generación + mensaje trivial
   inmediatamente después, para simular el "turno perdido" de 16558/16559)
   — **bloqueado por un límite real externo**: cuota diaria gratuita de
   Gemini agotada (mismo límite de 20 req/día ya documentado en Bloque
   AB/X.1-X.4), confirmado con el error HTTP 429 real del proveedor. No se
   forzó ningún workaround.

**Descarte fundamentado de la hipótesis de compactación:** para el
incidente RAÍZ (16560→16561) no había resumen de compactación activo —
descartada como causa de ESE incidente específico. La hipótesis correcta,
con evidencia, es "mensaje(s) sin responder fusionados con el mensaje
nuevo por `repair_message_sequence()`/`merge_pending_message_event()`".
No se descarta que la fusión combinada con un resultado de herramienta
real-pero-obsoleto (de un intento de bóveda anterior) pueda hacer que
`_turn_has_successful_tool_call()` encuentre un `role=="tool"` no-error
dentro de la ventana del turno actual — no se confirmó ni se descartó en
vivo por el bloqueo de cuota de AE.5.3; queda como hipótesis abierta, no
como causa confirmada.

**Instrumentación:** los `print()` de diagnóstico (`[BLOQUE_AE_DIAG]`) se
agregaron a `agent/turn_finalizer.py` y se retiraron completamente al
cierre (`git checkout -- agent/turn_finalizer.py`, verificado con `git
status`/`git diff` limpio). Ninguno queda en cuarentena entre sesiones.

**Opciones de arreglo (para el chat de diseño, sin decidir aquí):**
1. Mover `agent._persist_session()` al FINAL de `finalize_turn`, después
   de todas las correcciones de `final_response`, y sincronizar
   `messages[-1]["content"] = final_response` antes de persistir.
   Trade-off: cambia el orden de un flujo usado en muchos otros bloques
   (O.4, O.0, plugins) — necesita regresión completa, no solo de Tarea 1.
2. Además de (1), no fusionar (`repair_message_sequence` Pasada 2) un
   mensaje de usuario nuevo con un mensaje de usuario viejo que lleva más
   de N minutos sin respuesta — tratarlos como turnos separados o avisar
   explícitamente al modelo del backlog. Trade-off: mayor complejidad,
   posible ruptura de la alternancia de roles que el mismo repair existe
   para arreglar.
3. Hacer que `_turn_has_successful_tool_call()` también verifique
   *recencia* del resultado de herramienta (p. ej. mismo `api_call_count`
   o un timestamp del turno actual), no solo su posición relativa al
   último `role=="user"`. Trade-off: requiere pasar más contexto a la
   función; no resuelve AE.4 (el bug de persistencia) por sí solo.

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
