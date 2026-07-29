# Estado de Hermes — actualizado 29 Jul 2026, tarde

**Versiones vigentes: HAS v1.5 · PROTOCOLO v1.3.1**

## Espejo Obsidian -> Notion, mejora visual (29 Jul 2026, tarde)

Arturo, tras ver el espejo funcionando: "que sea bonito el boceto, no
solo todo indexado" -- el diseño original aplastaba la nota completa en
una propiedad de texto de la tabla (`Resumen`), viéndose como una hoja
de cálculo. Rediseñado: el contenido real ahora vive en el CUERPO de la
página (bloques de párrafo reales, con un callout 📓 al inicio
apuntando de vuelta a la ruta en Obsidian), la tabla solo muestra un
extracto corto (~200 caracteres, sin cortar palabras a la mitad), y
cada página lleva ícono 🧠. Verificado en vivo releyendo la página
completa (ícono + propiedades + bloques) desde la API real -- se ve
como una nota de verdad, no como una fila de spreadsheet. Nota #1
recreada con el formato nuevo (la vieja archivada, no borrada). 7 tests
nuevos (16 total en `test_notion_mirror.py`), 0 fallas. Aplicado en vivo.

## Espejo Obsidian -> Notion, CERRADO y verificado en vivo (29 Jul 2026, tarde)

Decisión final de Arturo sobre la visualización de nodos: diferida
hasta la Mac Mini (tendrá su propio monitor). En su lugar, cada nota
que Hermes guarda en Obsidian ahora también crea una fila numerada en
Notion ("nota número N") para que Arturo la consulte ahí mientras tanto.

**Nota de seguridad real de esta sesión:** Arturo pegó su
`NOTION_API_KEY` real en texto plano en el chat (en vez de solo en
`.env`) -- se le explicó por qué evitarlo a futuro (queda en el
historial de la sesión). La llave es de alcance acotado (solo páginas
que él comparta con la integración), riesgo bajo, pero el hábito
importa. `.env` se editó con un `read -s` (no queda en pantalla ni en
historial de shell) porque ni Bash ni Edit pueden tocar `~/.hermes/.env`
desde esta sesión (bloqueado a propósito por permisos) -- Arturo lo
corrió él mismo, como siempre debe ser con credenciales reales.

**2 hallazgos reales de la API de Notion, encontrados contra la API
real (no simulados) y corregidos antes de dejarlo funcionando:**
1. El endpoint para CREAR una base de datos nueva en la versión
   2025-09-03 no es `POST /v1/data_sources` (como decía la skill de
   Notion consolidada hoy en la mañana) -- ese endpoint solo sirve para
   bases ya existentes. La creación real sigue siendo `POST
   /v1/databases`, pero `properties` va anidado bajo
   `initial_data_source`, y la API separa el "database" (contenedor) de
   su "data source" (los datos reales) -- las páginas se crean
   apuntando al `data_source_id` devuelto, no al `database_id`.
2. La resolución de la página raíz "Hermes" se simplificó de pedirle a
   Arturo un ID de página (copiado de una URL) a buscarla por título
   vía `/v1/search` -- un paso menos de configuración de su parte,
   verificado con el shape real de la respuesta.

**Verificado de punta a punta con datos reales, no mocks:**
`obsidian_note` ya crea el archivo en Obsidian Y la fila numerada en
Notion en una sola llamada -- probado con una nota real de Arturo (la
del video de "segundo cerebro"), confirmada leyendo la fila de vuelta
desde la API real de Notion (nota número 1, título/tags/ruta correctos).
Notas de prueba propias limpiadas (archivo + fila de Notion archivada +
contador reiniciado) para que la numeración de Arturo empiece limpia en
1. 4 tests nuevos/actualizados en `tests/tools/test_notion_mirror.py`
(11 total) + 12 de `test_obsidian_note_tool.py`, 0 fallas. Aplicado en
vivo con reinicio del servicio.

**Diseño (best-effort, nunca bloquea):** si Notion falla por cualquier
razón (sin llave, sin red, página no compartida), la nota en Obsidian
YA se guardó de todos modos -- el campo `notion_synced` en la
respuesta le dice al agente si debe mencionarle el número a Arturo o no.

## Obsidian, decisión de arquitectura tomada y construida (29 Jul 2026, mañana)

Arturo decidió (tras aclarar que quería evitar mudanza manual de
información y que confirmó que Obsidian la app es gratis siempre): el
vault vive SOLO en la HP, sin sync a la MacBook. Él le manda ideas/notas
a Hermes por chat, Hermes las guarda organizadas; para visualizar desde
su Mac, monta la carpeta por SFTP/Finder (confirmado: sshd activo en
esta HP, sin configuración adicional necesaria de su lado).

**Construido y verificado en vivo, no solo diseñado:**
1. `/mnt/seagate/obsidian/` -- vault real, creado por Arturo (`sudo
   mkdir` + `chown`, único paso con sudo que hizo falta).
2. `tools/obsidian_note_tool.py` (nuevo) -- tool `obsidian_note` que el
   agente puede llamar para guardar una nota de conocimiento. Nunca
   sobrescribe en silencio (cada llamada crea un archivo nuevo, con
   sufijo si el título colisiona el mismo día); pasa por el mismo
   escáner de secretos que memoria estructurada (`scope="strict"`)
   ANTES de escribir -- una nota con una credencial real se bloquea, no
   se guarda. Registrada en el toolset core + 3 perfiles más.
   12 tests nuevos (`tests/tools/test_obsidian_note_tool.py`) -- uno de
   ellos encontró un bug real (parámetro `titulo` vs `title` en la
   función de frontmatter) antes de llegar a producción.
3. `~/.hermes/scripts/memoria_indexador.py::index_obsidian()` --
   implementación real (ya no el stub que saltaba con aviso). Cursor
   incremental por mtime de archivo (JSON `{ruta: mtime}` en
   `index_cursor`) -- solo reindexa lo nuevo/modificado, borra chunks de
   notas eliminadas del vault.
4. **Verificado de punta a punta con una nota real:** se creó una nota
   de prueba con la tool, se corrió el indexador (la indexó,
   `obsidian=1` en el log), y se confirmó recuperable por
   `agent.memory_semantic.buscar()` (score 0.819, tercer lugar en la
   pregunta "qué es el segundo cerebro de Arturo"). El "gap real" de
   Obsidian que quedó documentado en el Bloque 2 de esta misma mañana
   ya no aplica -- se cerró en esta misma sesión, mismo día.

**Nota de seguridad aparte, no nueva de hoy:** el SSH de esta HP tiene
login por contraseña habilitado (hallazgo ya existente del audit de
arranque del gateway) -- no bloquea nada de lo construido, pero es
pendiente real si la laptop llega a estar expuesta a internet, no solo
en la red local.

## Hueco O.1 vs web_search + arranque de Fase 5, CERRADO parcial (29 Jul 2026, mañana)

**Bloque O.1.2 -- hueco de web_search nativo, CERRADO.** El único punto
que quedó genuinamente abierto de la auditoría del backlog del 22 Jul
(arriba) ya se arregló: `agent/turn_finalizer.py` gana un chequeo
POST-respuesta (mismo patrón que O.6.1) -- si el modelo llamó
`web_search` este turno y la respuesta final menciona una moneda
conocida + una cifra en dólares, se compara contra CoinGecko real
(misma función que ya usaba O.1 para el caso Brave) y se avisa si
difieren >5%. No reemplaza la respuesta (no sabemos cuál número está
mal, solo que hay conflicto) -- solo la marca. Verificado contra la API
real de CoinGecko (no mock): con un precio de BTC deliberadamente viejo
($10,000) detectó el conflicto contra el precio real ($63,699) y agregó
el aviso. 6 tests nuevos (`tests/agent/test_turn_finalizer_o1_2_web_search_price_conflict.py`)
+ 47 de regresión de `turn_finalizer`, 0 fallas.

**Fase 5, arranque -- consolidación de la skill de Notion, CERRADO.**
OT-5 Bloque 1 pedía "consolida en notion-api, archiva la bundled" --
pero verificando el contenido real (no solo el nombre) resultó ser al
revés de lo que el texto sugería: la skill "personal" (`notion-api`,
40 líneas) no tenía ninguna mecánica real de la API (ni token, ni CLI,
ni curl), solo la estructura de bases de datos de Arturo; la "bundled"
de comunidad (`productivity/notion/`, 456 líneas + referencia de tipos
de bloque) es la que de verdad implementa la integración completa.
Desviación documentada y aplicada: se conservó la comprensiva
(renombrada `notion-api` en su frontmatter, como pedía el HAS), se le
agregó una sección "Estructura de Arturo" con sus bases de datos reales
(Finanzas/Proyectos/Tareas académicas/Ideas) tomada de la delgada antes
de archivarla. `~/.hermes/scripts/skills_audit.py` confirma 0
duplicados/404 tras el cambio. De paso, la skill archivada tenía una
referencia a "Tony" (el trato prohibido desde OT-1) -- documentado en su
nota de archivado, no corregido porque se está retirando, no
manteniendo.

**Pendiente real, requiere acción de Arturo:** pegar `NOTION_API_KEY`
en `.env` (instrucciones dadas en el chat) antes de poder verificar la
integración con una escritura real, como pide el HAS. La migración de
`mensajes_pendientes` (Tarea C) a la tabla `task_queue` v2 (máquina de
estados + escalera de reintentos + watchdog, HAS §E5/OT-5 Bloque 3) NO
se tocó hoy -- es una migración de un mecanismo de entrega en
producción viva, se recomendó tratarla como sesión dedicada en vez de
apurarla al final de una sesión ya larga.

## Obsidian -- decisión de arquitectura pendiente de Arturo (29 Jul 2026, mañana)

Arturo preguntó cómo se imaginaba el acceso a su vault de Obsidian
(para el índice semántico, Fase 4 Bloque 2 -- ver sección de arriba) y
si podía usar la misma cuenta de Notion en HP+MacBook. Aclarado en el
chat: Notion (tablero de operación) y Obsidian (biblioteca de
conocimiento, nodos/enlaces, "segundo cerebro") son productos distintos
con roles distintos (HAS §B7) -- lo que él describe (ideas conectadas,
grafo, que Hermes las vea para dar ideas de vuelta) es Obsidian, no
Notion. Dos caminos presentados: (1) gratis -- job programado que copia
el vault de la Mac hacia la HP cada noche, solo de lectura para Hermes,
Arturo sigue trabajando 100% normal en su Mac sin tocar nada; (2)
Obsidian Sync oficial (~$4-8 USD/mes) -- sync en vivo en ambos
sentidos, pero es gasto nuevo recurrente que requiere su autorización
explícita (choca con "cero servicios de paga nuevos" por default).
Recomendé la opción 1. Esperando su respuesta antes de construir nada.

## Falso positivo de Tarea E (oferta de DeepSeek sobre respuesta ya completa), CERRADO (29 Jul 2026, mañana)

Encontrado en vivo probando los dos fixes de arriba: tras una respuesta
buena y completa sobre el incidente de compresión (terminaba
correctamente preguntándole a Arturo "¿reiniciamos con `/new` o
seguimos así?" -- decisión que le corresponde a él, no a Hermes), llegó
una SEGUNDA oferta de Tarea E ("Mi respuesta se quedó corta en: una
decisión clara sobre el curso de acción... ¿Le entro con DeepSeek?").
Mismo patrón que ya aparecía descrito en el incidente original del 29
Jul madrugada -- preexistente, no causado por los fixes de hoy.

**Causa raíz confirmada:** `agent/complexity_detector.py::self_assess_response`
(Bloque O.2) evalúa la propia respuesta de Hermes con una llamada barata
a Gemini. La rúbrica vieja (`_SELF_ASSESS_RUBRIC`) marcaba
`resolvi_con_confianza=false` para cualquier respuesta que "presentara
opciones sin decidirse por una" -- sin distinguir entre "no supe
decidir" (sí amerita ofrecer razonamiento profundo) y "le devolví
correctamente la decisión al usuario porque es su preferencia personal,
no algo que Hermes deba decidir solo" (NO amerita ofrecer nada, ya
estaba completa).

**Fix:** rúbrica actualizada con una excepción explícita para el segundo
caso -- sin tocar `should_offer_v2()` ni la lógica de código, solo el
prompt. Verificado con el modelo barato REAL (no mock) contra 4 casos:
el caso real de Arturo (ya no ofrece), una respuesta genuinamente
insegura (sigue ofreciendo), una decisión multivariable con hueco real
sin resolver (sigue ofreciendo), y una respuesta trivial certera (no
ofrece, sin cambio). 5 tests nuevos
(`tests/agent/test_complexity_detector_self_assess.py`) + 57 tests de
regresión de `turn_finalizer`/`complexity_detector`, 0 fallas. Aplicado
en vivo con reinicio del servicio (09:23), sin errores nuevos.

## Respuesta rota en la cuenta real de Arturo (29 Jul 2026, ~1:31am) — DIAGNÓSTICO CONFIRMADO Y FIX APLICADO EN VIVO (29 Jul, mañana)

Causas raíz confirmadas por lectura de código real (no hipótesis) y
arregladas en la misma sesión. `hermes-gateway.service` ya reiniciado con
ambos fixes activos (verificado: servicio `active`, sin tracebacks nuevos
en `errors.log`/`agent.log`).

**Causa (a) — `read_file` trajo contenido de hace un mes, CONFIRMADA Y
ARREGLADA.** `tools/file_tools.py:1238` (`read_file_tool`) usa por
defecto `offset=1, limit=500` -- lee desde el INICIO del archivo, no el
final. `gateway.log` no había rotado desde el 30 jun (2.24MB, bajo el
límite de 5MB por tamaño) porque el tráfico es bajo -- cualquier
`read_file` sin argumentos explícitos sobre ese archivo traía la primera
página del archivo, literalmente `2026-06-30 01:47:16...`. Confirmado con
`head`/`wc -l` reales antes del fix.
Fix (`hermes_logging.py`, `_ManagedRotatingFileHandler` + `setup_logging`,
mode="gateway" únicamente): nuevo parámetro `max_age_days` -- al abrir el
handler, si la primera línea del archivo ya tiene más de N días (3 para
gateway.log), fuerza un rollover inmediato antes de seguir logueando. No
toca agent.log/errors.log/gui.log (sin `max_age_days`, comportamiento
idéntico a antes). Verificado con script aislado (log viejo simulado
rota, log reciente NO rota de más) + 6 tests nuevos en
`tests/test_hermes_logging.py::TestMaxAgeRollover`. Aplicado en vivo: el
reinicio de esta sesión ya rotó el `gateway.log` real (ahora
`gateway.log.1` tiene las 16038 líneas viejas, `gateway.log` arranca
limpio en `2026-07-29 09:07:13`).

**Causa (b) — sin dedup de `platform_update_id` para mensajes normales,
CONFIRMADA Y ARREGLADA.** El único mecanismo existente
(`_is_stale_restart_redelivery`, `gateway/run.py`) estaba acotado
EXCLUSIVAMENTE a `/restart` (invocado solo desde
`gateway/slash_commands.py::_handle_restart_command`). Un mensaje de
texto normal no tenía ninguna protección propia contra redelivery de
Telegram -- dependía 100% de que PTB no reenviara updates ya vistos, y el
propio comentario del código documenta el caso conocido: si el
`get_updates` de ACK final falla durante un shutdown (como pasó esa
noche con varios reinicios seguidos), Telegram reenvía los mismos updates
al arrancar. Para mensajes normales (a diferencia de `/restart`) nada
filtraba eso -- cada redelivery se procesó como turno nuevo e
independiente, explicando los 7 duplicados.
Fix (`gateway/run.py`): generalización del mismo patrón -- 2 métodos
nuevos, `_is_duplicate_update`/`_mark_update_processed`, con marcador
persistente `~/.hermes/.last_update_id.json` (mismo estilo que
`.restart_last_processed.json` pero para TODO mensaje, no solo
`/restart`). Se invoca al principio de `_handle_message`, antes de auth/
sesión/plugins -- una redelivery nunca llega a esas rutas. Solo aplica
cuando `platform_update_id` no es None (hoy, solo Telegram) -- otras
plataformas no se ven afectadas. Verificado con script aislado (mismo
update_id → duplicado; update_id nuevo → no duplicado; sin
platform_update_id → no-op) + 6 tests nuevos en
`tests/gateway/test_restart_redelivery_dedup.py`.

**Causa (c) — `_pending_reprocess_ids` (Bloque AF), DESCARTADA por
lectura de código.** Es un mecanismo totalmente distinto (cola
`mensajes_pendientes`/auto-watcher para reintentos de autorización de
DeepSeek, con el bug conocido preexistente de usar `id(event)` como
llave). Los 7 duplicados de esa noche llegaron por el canal en vivo de
Telegram (polling de PTB), no por esa cola -- no están relacionados. De
paso, corriendo la suite de regresión salió que el bug real afecta **5
tests**, no 2 como decía el registro anterior (mismo `AttributeError:
'GatewayRunner' object has no attribute '_pending_reprocess_ids'` en
`test_status_command.py` x3, `test_incomplete_gateway_turns.py`,
`test_telegram_topic_mode.py`) -- confirmado preexistente (reproducido
con `git stash` contra el código sin tocar), sigue sin arreglar, no era
el objetivo de esta sesión.

**Verificación de regresión antes de tocar el servicio real:** ~1600
tests de `tests/gateway/` + `tests/test_hermes_logging.py` corridos en
bloques (no de un solo golpe, por la regla del incidente del 24-25 jul).
0 fallas nuevas -- las 19 fallas totales que aparecieron (5+14, ver
arriba y Bloque AF) son idénticas antes y después del cambio, confirmado
comparando contra el código sin tocar vía `git stash`.

**Excepción del hook usada esta sesión:** `systemctl --user restart
hermes-gateway.service`, 29 Jul 09:07 -- resultado: servicio activo,
gateway.log rotado correctamente, sin errores nuevos. (Nota para la
próxima sesión: el comando debe mandarse SOLO, sin encadenar con `;`/`&&`
a otros comandos en la misma llamada de Bash -- el hook exige match
exacto contra el string completo y un compuesto lo tumba con el
hard-deny de la regla 6, aunque el comando real adentro sea el exacto
autorizado.)

## ESTADO ACTUAL — leer esto primero, antes que nada más abajo

**HALLAZGO CRÍTICO DE SEGURIDAD, CERRADO (29 Jul 2026, madrugada):** el
escáner de secretos (`tools/threat_patterns.py`) no detectaba
contraseñas humanas dichas en prosa en español (solo llaves de API con
formato reconocible). Se coló una contraseña real de prueba ("Cisco",
del test de la bóveda del 23 Jul -- confirmado por Arturo que NO es una
credencial real vigente) a un archivo de candidatos de memoria. Ya
contenida en cuarentena (`~/.hermes/cuarentena_credenciales_28jul/`,
permisos 600) y el escáner arreglado con 2 patrones nuevos (verificados
contra los 4 casos reales que se colaron + 11 frases benignas sin falsos
positivos + 484 tests de regresión, 0 fallas). Ver sección propia más
abajo, "Hallazgo de seguridad -- escáner de contraseñas en español".

**Fase 4 (Memoria que encuentra) — AUTORIZADA Y EN CURSO (28-29 Jul
2026, noche/madrugada).** Arturo autorizó explícitamente arrancarla tras
una sesión de contexto completo del proyecto. OT-4 Bloque 1 (aprobación
de candidatos) tiene avance real, incluido el resumen semanal
automático de los domingos (nuevo esta madrugada). Ver secciones propias
más abajo
("Fase 4 -- Bloque 1"). Bloques 2-3 (índice semántico, verificación
E2E) sin empezar.

## Hallazgo de seguridad -- escáner de contraseñas en español, CERRADO (29 Jul 2026, madrugada)

Probando el resumen semanal de memoria contra los candidatos reales
pendientes, la lista generada por Gemini incluyó 4 candidatos con
contraseñas REALES en texto plano ("La contraseña para Cisco es MOTO y
la palabra clave es redes", "la frase es silencio y la contraseña es
blindar", etc. -- del test en vivo de la bóveda del 23 Jul, Bloque T).
Arturo confirmó que no son credenciales reales vigentes (fue el ejemplo
usado para probar la bóveda entonces), pero el hallazgo del escáner es
real e independiente de eso.

**Causa raíz:** `tools/threat_patterns.py` línea 137 (patrón genérico de
secretos) exige la palabra en INGLÉS "password/token/secret/api_key" +
sintaxis `clave=valor` + un token de 20+ caracteres. Una contraseña
humana dicha en español natural ("la contraseña ... es MOTO") no cumple
ninguna de las 3 condiciones -- ni el idioma, ni la sintaxis, ni la
longitud (las palabras reales eran de 4-9 caracteres).

**Contención inmediata:** los 2 archivos `fase2_pendientes_*.json` con
las contraseñas movidos a `~/.hermes/cuarentena_credenciales_28jul/`
(permisos 600, fuera de la ruta que `/memoria`/el resumen semanal leen).
Confirmado que ningún otro candidato pendiente tiene contenido similar
(barrido completo con el escáner ya arreglado, 0 hits).

**Fix aplicado (`tools/threat_patterns.py`):** 2 patrones nuevos, scope
`strict`, deliberadamente NO genéricos -- anclados a "contraseñ*" y
"frase de paso" (palabras casi nunca ambiguas en español) seguidas de un
verbo de asignación con hasta 4 palabras de por medio. Se descartó a
propósito un patrón para "clave" sola por ser demasiado ambigua ("la
clave del éxito"). Verificado: los 4 casos reales que se colaron ahora
SÍ se detectan; 11 frases benignas de español normal ("la clave del
éxito", "cuál es la mejor frase", "mi contraseña favorita para explicar
el tema es esta analogía", etc.) NO generan falso positivo. Regresión:
484 tests (`test_threat_patterns`, `test_memory_tool`,
`test_turn_finalizer_*`, `test_prompt_builder`,
`test_tool_dispatch_helpers`, `test_cronjob_tools`, `tests/smoke/`), 0
fallas.

**Pendiente real, bajo riesgo, sin arreglar:** el mismo tipo de
contenido (contraseñas dichas en prosa) sigue en texto plano en
`state.db` y `/mnt/seagate/hermes_raw/` desde el 23 Jul -- por diseño
del proyecto ("el crudo es sagrado", nunca se borra/edita el historial
crudo), y porque Arturo confirmó que no es una credencial real vigente,
no se tocó. Si en el futuro aparece un caso real (credencial vigente),
el procedimiento es rotar la credencial (como en OT-0.5), no editar
`state.db`.

## Fase 4 -- OT-4 Bloque 1.3 (resumen semanal automático), CONSTRUIDO Y VERIFICADO (29 Jul 2026, madrugada)

Arturo pidió que la revisión de memoria no dependa de que él se acuerde
de escribir `/memoria` -- que Hermes le avise solo. Decisión de diseño
explícita, con su acuerdo: versión de TEXTO (Hermes manda un resumen
narrado los domingos 9pm y Arturo corre `/memoria` cuando quiera para
aprobar/rechazar con botones), no botones automáticos -- eso último
necesitaría un mecanismo de entrega con botones que hoy no existe en
ningún cron de Hermes, quedó anotado como upgrade futuro, no como parte
de este bloque.

**Excepción permanente y acotada autorizada por Arturo** (documentada en
`~/.hermes/CLAUDE.md`): SOLO para esta corrida semanal, si Gemini y Groq
fallan, se usa DeepSeek (`chat-reasoning` = `deepseek-v4-pro` en
litellm -- no existe una variante "flash" separada configurada hoy)
automáticamente, sin pedir autorización por llamada. No aplica a nada
más del proyecto.

**Construido:** `~/.hermes/scripts/memoria_resumen_semanal.py` -- pone
al día la extracción (bucle acotado a 10 rondas), junta los candidatos
reales pendientes, y le pide a un modelo que redacte el resumen
(escalera Gemini→Groq→DeepSeek). Stdout vacío si no hay candidatos
(corrida silenciosa, no molesta si no hay nada nuevo).

**Cron real creado** (`hermes cron create`, job `b0bc302007b0`,
schedule `0 21 * * 0`, `--no-agent`, `--deliver telegram:8899197004`).

**Bug real encontrado y diagnosticado en la verificación en vivo:**
`hermes cron run <id>` (para probar sin esperar al domingo) ejecuta el
script como proceso aparte del gateway (`source=direct` en
`executions.db`) -- el script corre bien, pero la entrega por Telegram
falla con timeout porque ese proceso no tiene la conexión viva del
adaptador. Confirmado leyendo el estado del job después:
`⚠ Delivery failed: delivery error: Telegram send failed: Timed out`.
**El mecanismo real (el tick interno del gateway, `source=builtin`) SÍ
funciona** -- verificado creando un job de prueba de un solo disparo
(`--repeat 1`) apuntado a la cuenta QA, dejando que el tick real del
gateway (cada 60s) lo disparara solo: llegó completo a Telegram (3
partes, por el límite de longitud), confirmado leyendo los mensajes
reales de la cuenta QA. Job de prueba autoeliminado tras dispararse
(`--repeat 1`). El job real de Arturo (domingo) no se tocó -- su
"Last run: failed" en el estado actual es de mi prueba fallida por CLI,
se sobreescribe solo con la corrida real del domingo.

**Pendiente real:** confirmar el domingo 2 de agosto que la entrega
real a la cuenta de Arturo funciona igual que la prueba con QA (misma
ruta de código, alta confianza, pero no verificado con su cuenta real
todavía -- decisión explícita de no volver a probar contra su cuenta
real tras el primer intento fallido).

**Fase 3 (Ciclo de vida de skills) -- CERRADA COMPLETA (28 Jul
2026), los 5 bloques de OT-3.** Después, Arturo pidió expandir la
limpieza más allá de OT-3 (11 skills nuevas/consolidadas, incluida la
ciberseguridad doméstica de E7 -- ver sección "Post-Fase 3" en
`docs/BLOQUES.md` y `~/.hermes/CHANGELOG_SISTEMA.md` para el detalle
completo). 142 skills activas al cierre, auditoría limpia (0
problemas reales).

## Fase 4 -- Bloque 1 (aprobación de candidatos), EN CURSO (28 Jul 2026, noche)

Arturo pidió arrancar Fase 4 tras compartir el contexto completo del
proyecto (visión de trading, estudio automatizado, segundo cerebro,
finanzas, y una propuesta externa sobre memoria por significado/dedup
de imágenes). Antes de tocar código se hizo el análisis comparativo:
casi todo lo que describió ya estaba especificado en las Fases 4-11 del
HAS -- no hubo que rediseñar nada, solo autorizar y ejecutar.

**Hallazgo real que cambió el plan de OT-4 1.2:** la premisa ("corre el
proceso con los 20 candidatos verificados existentes") estaba
desactualizada. En disco solo había 1 archivo con 3 candidatos (ya
descartados según `HISTORIAL.md`); la corrida de 156 candidatos del 20
Jul que el historial menciona no existe en ningún lado (ni
`/mnt/seagate`, ni respaldos). Corriendo la extracción real (3 lotes,
60 mensajes) se confirmó la causa raíz: `raw_layer_export.py` exportaba
**todos** los mensajes de `messages` sin filtrar por identidad --
mezclaba tráfico real de Arturo con el arnés E2E interno
(`user_id="u1"`), la cuenta QA, y sesiones cli/cron/subagent/webhook. De
~200 sesiones en `state.db`, solo 8 eran de la identidad real aprobada
de Arturo (`8899197004`, confirmado contra
`platforms/pairing/telegram-approved.json`).

**Fix aplicado y verificado en vivo:** `ARTURO_USER_ID` agregado como
filtro en `scripts/raw_layer_export.py` (JOIN contra `sessions.user_id`)
y `scripts/fase2_extract_candidates.py` (filtra por `session_id`
perteneciente a una sesión real de Arturo). Confirmado en vivo: una
corrida real descartó 28 mensajes de ruido y produjo candidatos
genuinos de conversación real. Quedan **8 candidatos reales pendientes
de revisión** (3 viejos del 19 Jul re-surgidos porque nada en disco los
marcaba revisados, más 5 limpios de conversación reciente real).

**Bloque 1.1 (interfaz de revisión) construido y verificado en vivo
contra Telegram real, no solo por código:**
- `tools/memoria_review.py` (nuevo): cola de candidatos con botones
  Aprobar/Rechazar, INSERT real a `memoria_estructurada` con escáner de
  secretos antes de escribir. v1 deliberadamente sin botón "Editar"
  (supuesto marcado -- un hecho mal redactado se rechaza y se dicta
  directo por chat).
- Comando `/memoria` (`gateway/run.py::_handle_memoria_command`,
  registrado en `hermes_cli/commands.py`, ruteado por `/hermes memoria`
  en Slack por el tope de 50 slots).
- **Aislamiento por identidad real, no solo por sesión:** la cola REAL
  de Arturo solo se sirve a `user_id=8899197004`. Cualquier otra
  identidad (QA, pruebas) recibe una cola sintética aislada
  (`build_test_queue`) -- mismo principio que Bloque AG (memoria QA
  separada por `origen`/`user_id` en la misma tabla). Esto se decidió
  DESPUÉS de notar que la implementación original hubiera dejado que la
  cuenta QA aprobara/rechazara los candidatos reales de Arturo sin que
  él lo supiera.
- **Bug real encontrado y arreglado durante la prueba en vivo:** el
  prefijo de callback `mr:` colisionaba con un catch-all ya existente
  del selector de modelos (`data.startswith(("mp:", ..., "mr"))` en
  `adapter.py:6102`, sin dos puntos) -- los botones nunca llegaban a mi
  código, respondían "Picker expired". Renombrado a `revm:`, verificado
  de nuevo en vivo.
- **Verificación E2E real, con la cuenta QA de Telegram** (`api_id`/
  `api_hash` de la app personal de Arturo en my.telegram.org + passphrase
  de la bóveda): `/memoria` real → candidato sandbox con botones →
  Aprobar → fila real insertada (`origen='qa'`, `user_id=8727618189`) →
  encadenó al siguiente candidato → Rechazar → cola vacía, mensaje de
  cierre correcto. Confirmado con SQL directo que los 8 candidatos
  reales de Arturo NO se tocaron. Fila de prueba limpiada con
  `limpiar_memoria_qa.py` (1 borrada, hechos reales antes/después: 0/0).
- Regresión: 256 tests en `tests/gateway/test_telegram_*` + `tests/smoke/`
  + `tests/hermes_cli/test_commands.py` + `tests/tools/test_slash_confirm.py`,
  0 fallas nuevas (2 preexistentes, confirmadas con `git stash`, mismo
  bug `_pending_reprocess_ids` de Bloque AF).
- Desplegado a producción 2 veces (fix de identidad + fix de colisión
  de callback), con la excepción de reinicio pre-aprobada
  (`systemctl --user restart hermes-gateway.service`), ambas veces
  confirmado `is-active` + logs limpios.

**Corte de luz real durante la sesión (~21:10-21:17):** el gateway
perdió conexión a Telegram (red completa, no solo Telegram, confirmado
con `ping`/`nmcli`) por ~7 minutos tras un reinicio que coincidió con el
apagón que reportó Arturo. Se reconectó solo al volver la red, sin
intervención, sin pérdida de datos.

**Pendiente real, sin arreglar:**
- Los **8 candidatos reales de Arturo siguen sin revisar** -- están
  listos, solo falta que él corra `/memoria` en su Telegram real.
- v1 de `/memoria` no tiene botón "Editar" ni fallback de texto para
  plataformas sin botones (supuesto marcado, ver arriba).
- `docs/BLOQUES.md` línea 706 tiene un `api_id`/`api_hash` de Telegram
  en texto plano committeado a git -- es el par viejo que Telegram
  rechazó (`ApiIdInvalidError`, ya muerto), pero sigue siendo una
  credencial expuesta en el historial del repo. Bajo riesgo (no
  funciona), no arreglado, pendiente de que Arturo decida si vale la
  pena reescribir esa parte del historial.
- OT-4 Bloque 1.3 (cron semanal de extracción) sin agendar.
- OT-4 Bloque 2 (índice semántico, sqlite-vec + e5-small) sin empezar.

Fases 0, 0.5, 1 y 2 del HAS quedaron CERRADAS de verdad
(27-28 Jul 2026), con evidencia real cada una, **incluido el Bloque 6**
(corte a producción) que hasta hoy seguía "EN OBSERVACIÓN" pese a que
el banner ya decía Fase 2 cerrada -- contradicción real detectada y
corregida hoy: ventana de 24h de logs revisada (23.3h limpias, 0
tracebacks, ver sección Bloque 6 más abajo), Bloque 6 cerrado, Fase 2
cerrada en sus 6 pasos, no solo de nombre.

**Fase 3 -- CERRADA COMPLETA (los 5 bloques de OT-3), 28 Jul 2026:**
- **Bloque 1:** respaldo, los 2 archivos-404 borrados, los 3 duplicados
  reales resueltos con verificación en vivo contra el código de
  producción. 141 → 136 skills activas.
- **Bloque 2:** `powerpoint`/`ocr-and-documents` reparados (la
  dependencia real que faltaba era `lxml`, no `validators` como decía
  el plan); `comfyui` archivado (confirmado `use_count: 0` real). 136 → 135.
- **Bloque 3, el más grande:** el bug de fondo de `.usage.json`
  (indexaba por nombre, no por ruta -- afectaba la resolución REAL de
  `skill_view()`, no solo el contador). Refactor real en 10 archivos de
  producción, autorizado explícitamente por Arturo tras exponerle el
  alcance verdadero (57 puntos de llamada). 1247/1247 tests en verde,
  desplegado con reinicio real del gateway (29/29 smoke, 0 errores en
  logs). De paso, una regresión propia del Bloque 1 (enlace roto en
  `superpowers/subagent-driven-development`) encontrada y corregida
  antes de que causara daño.
- **Bloque 4:** esquema de metadata E3 (`docs/HAS.md`) aplicado a las
  135 skills activas -- probado primero en una copia completa, no
  directo a producción. Pin real (no cosmético) en las 30 skills de
  desarrollo de software vía `.usage.json`.
- **Bloque 5:** `~/.hermes/scripts/skills_audit.py` -- 404s, duplicados
  por 2 mecánicas de resolución distintas, sintaxis rota, staleness,
  frontmatter incompleto. Corrido contra producción: 0 problemas
  reales nuevos.

Detalle técnico completo de los 5 bloques en `docs/BLOQUES.md` y
`~/.hermes/CHANGELOG_SISTEMA.md`.

**Hallazgos nuevos sin arreglar, fuera de alcance de OT-3 (anotados
para su propia sesión):**
- `tools/skill_manager_tool.py::_find_skill()` resuelve por nombre de
  carpeta, no por `name:` de frontmatter (inconsistente con
  `skill_usage._find_skill_dir()`). Confirmado con un caso real hoy
  (`notion` vs `productivity/notion`, 2 skills distintas que solo
  coinciden en nombre de carpeta -- ya planeada su consolidación en
  Fase 5, no es un bug nuevo).
- `tools/skills_tool.py::_find_all_skills()` deduplica por nombre en
  silencio -- una skill con nombre repetido desaparece de `hermes
  skills list`/`/api/skills` en vez de mostrarse. Dormido hoy (0
  colisiones por `name:` reales), pero resurgiría con la próxima skill
  duplicada.
- `thumbnail.py` de `powerpoint` necesita `sudo apt install
  libreoffice-impress` -- permiso denegado en sesión, pendiente de que
  Arturo lo corra él mismo o autorice explícitamente.
- `marker-pdf` (OCR pesado) instalado pero sin probar con un PDF real.
- Programar `skills_audit.py` semanalmente queda para Fase 5 (el propio
  OT-3 lo dice explícitamente), no es pendiente de Fase 3.
- `apple-shortcuts` y `chequeo-salud-macbook` (nuevas, post-Fase 3): no
  probadas en vivo -- sin sesión SSH activa a la MacBook. `apple-shortcuts`
  documenta un hallazgo real serio investigado con fuentes: `shortcuts
  run` necesita sesión gráfica activa, falla headless.
- `personal-operating-system` (235 líneas): mismo problema que ya se
  vio en `video-editing-pipeline` (ya archivada) -- mezcla hechos que
  pertenecen a memoria estructurada, notas técnicas obsoletas (LiteLLM/
  Groq, superadas por `hermes-provider-fallback`), y guía real vigente
  (permisos, comunicación, sprints). Requiere su propia sesión para
  separar sin perder lo vigente.

Pendientes reales sueltos, ninguno bloquea Fase 3:
- Disco Seagate: Arturo pendiente de correr `sudo smartctl -a /dev/sda`
  (hallazgo del 27 Jul, ver Bloque 6 más abajo) -- no urgente.
- `recover@telegram.org` puede contestar en cualquier momento (correo
  enviado el 27 Jul) -- irrelevante ya, OT-QA se resolvió por otra vía
  (ver sección OT-QA más abajo, cuenta QA ya autenticada y funcionando).

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

## HAS Fase 2 -- CERRADA DE VERDAD (27 Jul 2026, tarde)

El único criterio de verificación E2E que faltaba ("simular una
actualización futura y que el procedimiento la resuelva sin
intervención creativa") se cerró hoy mismo: rebase real completo sobre
761 commits nuevos de upstream (47 aplicables), en rama desechable
(`fase2-cierre-rebase`, nunca tocó `arturo/base` ni producción), un
solo conflicto real resuelto combinando ambos lados (no descartando
ninguno), 29/29 smoke + 26/26 de la prueba afectada en verde. Detalle
conflicto-por-conflicto en `~/hermes-019/docs/MIGRATION_LOG.md`,
sección "Bloque 6.1". Punto caliente de la skill `hermes-upgrade`
actualizado con el patrón real encontrado (van 3 rebases con conflicto
en el mismo archivo, `plugins/platforms/telegram/adapter.py`).

**Con esto, las Fases 0, 0.5, 1 y 2 del HAS quedan cerradas.** Fase 1
seguía marcada "parcial" en `docs/HAS.md` pese a estar cerrada desde
Bloque AH.5 -- corregir esa página queda pendiente (documento vive en
`~/hermes-019`, no en este repo). **Sigue: Fase 3 -- Ciclo de vida de
skills** (136 skills: borrar basura, resolver duplicados, arreglar
contador de uso, meterle metadata). Estimado 2 semanas. Roadmap
completo restante (Fases 3-11, sin la parte de voz que depende de
comprar la Mac Mini): ~25 semanas estimadas en `docs/HAS.md`.

## OT-QA -- LOGIN REAL COMPLETADO, CERRADO (27 Jul 2026, tarde)

En vez de esperar la respuesta de `recover@telegram.org` (enviada,
sigue sin contestar), se resolvió con un `api_id`/`api_hash` nuevo
sacado de la cuenta PERSONAL ya establecida de Arturo (no la QA) --
confirma que el bloqueo era de la app/cuenta nueva bajo vigilancia
anti-abuso, no de la IP. En el camino se encontró y arregló un segundo
bug real en `tools/telegram_userbot.py` (dos clientes de Telethon
distintos para pedir y confirmar el código -- causaba
`PhoneCodeExpiredError` real, 4 intentos fallidos, causa raíz
confirmada contra un issue real de Telethon). **Login verificado en
vivo con evidencia real**: sesión guardada en la bóveda, reconexión
real exitosa, `get_me()` confirma la identidad QA
(`id=8727618189, Hermes QA`). La cuenta QA ya puede usarse para
pruebas E2E reales por Telegram. Detalle completo en `docs/BLOQUES.md`.

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

## HAS Fase 2 — Bloque 6 (corte real a producción) — CERRADO (28 Jul 2026, verificado)

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
   Cierre con `exit code 1` en vez de 0 -- **investigado a fondo
   después (ver Bloque 6/OT-QA en `BLOQUES.md`), NO es un bug**: es
   diseño intencional (`gateway/run.py`, `shutdown_signal_handler`) --
   `systemctl stop` directo no puede escribir el marcador de "parada
   planeada" que solo pone `hermes gateway stop`, así que el proceso se
   trata a sí mismo como apagón inesperado y sale con 1 a propósito,
   para que `Restart=always` lo reviva solo ante un kill real. Corrige
   el hallazgo original de esta misma sesión.
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

**Ventana de 24h revisada (28 Jul 2026, ~12:30):** 23.3h reales desde el
reinicio de las 13:13:29 del 27 Jul (`journalctl --user -u
hermes-gateway.service --since "2026-07-27 13:13:29"`), 18 líneas de log
en total, 0 tracebacks/excepciones/CRITICAL -- las únicas 4 líneas de
WARNING son reconexiones de red transitorias de Telegram
(`httpx.ReadError`, attempt 1/10, reconectado en 5s cada vez, mismo
mecanismo de reintento ya existente, sin relación con el corte). `litellm.service`
en la misma ventana: 1 línea total, 0 errores. Con esto se cierra el
paso 6 pendiente del procedimiento -- **Bloque 6 cerrado, y con él HAS
Fase 2 queda cerrada de verdad en sus 6 pasos, no solo en el banner de
arriba** (esta sección contradecía al banner hasta ahora; corregido).

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

## Bugs abiertos del 22 Jul -- AUDITADOS de nuevo contra el código real (29 Jul 2026, mañana)

El registro de abajo databa del 22 Jul y nunca se había re-verificado
contra el código actual pese a que otras secciones de este mismo archivo
(fechadas 27-28 Jul) ya reportaban arreglos de al menos 2 de los 4
puntos -- contradicción real que se detectó pidiendo auditar este
backlog. Verificado uno por uno contra el código y el sistema real, no
repitiendo el texto viejo sin más:

1. **CRÍTICO -- Fabricación de evidencia de incidentes (O.6). CERRADO,
   confirmado.** La sección "Bloque O.6 -- CERRADO (27 Jul 2026)" de este
   mismo archivo ya lo documentaba; confirmado además leyendo el código
   real hoy: `agent/turn_context.py` (~línea 1306) le quita las tools al
   agente por completo (`agent.tools = []`) en el turno cuando detecta
   una pregunta de verificación de incidente, y `agent/turn_finalizer.py`
   (Bloque O.6.1) reemplaza la respuesta final si contradice evidencia
   real ya inyectada ese turno -- vi este segundo backstop dispararse EN
   VIVO hoy mismo durante la prueba de los fixes de redelivery/log (ver
   sección de arriba). Ya no es "sin resolver".
2. **O.4 sin rastro de ejecución -- probablemente ya no aplica, sin
   poder confirmar el caso original.** El código actual
   (`agent/turn_finalizer.py` líneas 685-729) envuelve TODO el bloque en
   un try/except que siempre deja rastro: si detecta inglés, loguea
   "regenerando"; si algo lanza, el except loguea "fallo el
   enforcement". El único camino sin log hoy es deliberado, no un bug:
   `response_looks_like_english()` (`agent/complexity_detector.py:824`)
   se sale sin marcar nada si la respuesta tiene menos de 20 palabras
   alfabéticas (para no disparar falsos positivos en respuestas cortas
   tipo "OK"). No tengo acceso al contenido original del mensaje 15885
   para confirmar si cayó en ese caso -- no repito el hallazgo viejo como
   vigente, pero tampoco lo cierro sin poder probarlo contra el caso
   real.
3. **Hueco arquitectónico en O.1 vs `web_search` nativo -- SIGUE
   ABIERTO, confirmado.** Búsqueda real en el código (`grep web_search`
   sobre `turn_finalizer.py`/`complexity_detector.py`): no existe ningún
   mecanismo de reconciliación posterior para precios que el modelo haya
   obtenido por su cuenta llamando a `web_search` durante el turno -- O.1
   sigue viendo solo lo que el propio código inyecta ANTES (Brave/
   CoinGecko). Nadie lo tocó desde el 22 Jul. Sigue siendo un hueco real.
4. **Cron roto apuntando a `vigilar_hermes.sh` -- CERRADO, confirmado.**
   `crontab -l` real hoy solo tiene la limpieza de `/tmp` (agregada tras
   el incidente del 24-25 Jul) -- ninguna entrada de `vigilar_hermes.sh`,
   y el script tampoco existe en disco. Coincide con la sospecha ya
   anotada en BLOQUES.md ("probable: lo reemplazó el watchdog real").

**Pendiente real que queda de este backlog:** solo el punto 3 (hueco
O.1 vs `web_search`) sigue genuinamente sin resolver -- no se tocó hoy,
fuera del alcance de esta auditoría (que era verificar, no arreglar).

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
