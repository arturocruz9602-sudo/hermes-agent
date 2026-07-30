# Historial de Bloques — Hermes

Este archivo no existía antes del 22 Jul 2026 (creado en O.8, primera
entrada retroactiva es Bloque O porque es el bloque activo al momento de
crear este archivo; bloques anteriores no se reconstruyen aquí).

## Bloque AH — El watchdog revertía la config por un "401" dentro del session_id (30 Jul 2026, `/loop`) — **CERRADO, causa raíz de AG**

Responde el pendiente que dejó AG. `~/.hermes/scripts/watchdog.sh` traía
`grep -qi "...\|401\|..."` con el **`401` suelto**, sin delimitadores.
Hacía match con el session_id de Arturo — `20260723_0144`**`01`**`_…` —
así que **restauraba `config.yaml.known-good` (4 jul) y reiniciaba el
gateway porque el ID de la sesión contiene esos tres dígitos.**

Evidencia textual (`~/.hermes/logs/watchdog.log:25279`):
`[jue 30 jul 2026 11:45:23 CST] 🔴 Auth error detectado` +
`✅ Restaurado known-good` — mismo segundo que el `mtime` de config.yaml.
Corroborado por duración: las corridas duran ~6s; la de 11:45:17 duró 19s.

**15 veces desde el 4 jul**, dos de ellas el 23 jul justo después de que
naciera esa sesión. Cada una devolvía la config a la forma que mata
Tarea E (Bloque AG) sin que nada se viera roto por fuera.

**Lección de jurisprudencia (la más cara del día):** un mecanismo de
*auto-curación* con un patrón de detección demasiado laxo no es una red
de seguridad — es una fuente de fallas periódicas que además borra la
evidencia de sí misma. Al escribir cualquier `grep` de detección sobre
logs, los números sueltos (códigos HTTP, PIDs, puertos) **deben ir
delimitados**: los IDs de sesión, hashes y timestamps del propio sistema
son texto adversario en la práctica.

**Cierre:** `\b401\b` + vocabulario de autenticación en la misma línea;
12/12 en casos reales (7 positivos legítimos, 5 falsos rechazados);
simulación contra los logs del incidente → no dispara; corrida real
13:03:21 `Result=success`. Aditivo: respaldo de la config vigente antes
de sobrescribir + log de la línea que disparó la detección.

**Deja abierto:** `~/.hermes/scripts/` (26 scripts de producción) no está
versionado ni cubierto por el respaldo nocturno — recomendación:
extender `scripts/respaldar_skills_y_sistema.py`. Y el known-good sigue
siendo el del 4 jul (decisión de Arturo: regenerarlo desde la config
vigente verificada).

## Bloque AG — Tarea E muerta en silencio: credenciales de LiteLLM (30 Jul 2026, `/loop`) — **CERRADO con evidencia real**

Nace del pendiente "Bloque O completo -- buscar OTROS huecos parecidos en
el rubro" de `ESTADO.md`. El hueco no estaba en el rubro.

**Síntoma que lo delató:** sonda de 8 casos límite con llamada REAL
devolvió el default **byte-idéntico** en los 8, incluido un caso
abiertamente multivariable. Ocho respuestas iguales = el rubro nunca
corrió.

**Causa raíz:** `_resolve_litellm_credentials()` solo leía
`custom_providers['LiteLLM']`. A las 11:45:23 se restauró
`config.yaml.known-good` (4 jul, `md5 c8910c8c…`, byte-idéntico al
vigente), que guarda las mismas credenciales bajo `model:`. La función
lanzaba; `_call_cheap_model_json` lo tragaba con `except: return None`
sin log; todo llamador caía a su default fail-safe. LiteLLM sano todo el
tiempo (`{"ok": true}` vía `model.base_url`).

**Jurisprudencia:** es L6/L14 del HAS en producción — el silencio como
estado de fallo. La lección nueva y accionable: **un default fail-safe
sin log es indistinguible de un éxito**, y ahí es donde esta familia de
fallas se esconde. Un `except` que devuelve default DEBE loggear.

**Cierre (commit `8ec8bfe4f`):** función canónica que lee ambas formas de
`config.yaml`; log obligatorio en el fallo; deduplicados los 2 lookups a
mano de `gateway/run.py` (Tarea D y E) que tenían el mismo defecto
(`grep` = 0 residuos); EXCEPCIÓN 1 del rubro ampliada a mensajes que solo
Arturo puede concretar. Verificación real 8/8 (incluye control negativo:
`"logs?"` sigue ofreciendo, no se sobreajustó). Pruebas 18/18 + 18/1skip
en gateway. Desplegado 12:05:19, gateway `active` PID 528048.

**Deja abierto:** (1) qué proceso restauró `config.yaml` y reinició el
gateway a las 11:45:23 — decisión de Arturo, se cruza con el hallazgo de
gobernanza de Hermes leyendo su propio código fuente ~11:47am;
(2) ~~barrer el árbol~~ → hecho en AG.2.

### AG.2 — barrido de fallos mudos (commit `efd421c93`) — **CERRADO**

385 handlers silenciosos en los 50 `.py` propios → 25 en líneas que
Hermes agregó → 10 en `complexity_detector.py`. Nueve arreglados con el
mensaje nombrando la consecuencia real; comportamiento fail-safe intacto.
Los dos de mayor riesgo no eran los obvios: `offers_today_count` (su
`return 0` deja el tope diario anti-spam **sin efecto** — presupuesto) y
`parse_yes_no` (ruta por la que Arturo autoriza gasto).

**Método que vale la pena repetir:** AST + cruce con `git diff
origin/main...HEAD`. Grep solo daba 385 resultados indistinguibles entre
código propio y heredado del fork; el cruce los bajó a 25 accionables.

**Prueba de mutación** como control de calidad del guard: al quitar un
log a propósito, 2 tests fallan. Un guard que no se prueba rompiéndolo es
otro silencio disfrazado. 31/31. Desplegado 12:34:57, PID 531722.

**Quedan 15** handlers mudos en código propio fuera de Tarea E
(`gateway/run.py` ×3, `hermes_logging.py`, `memory_semantic.py` ×2,
`obsidian_note_tool.py` ×2, `vault_tool.py` ×3, …) — menos críticos.

## Sesión de tarde con Arturo presente (30 Jul 2026) -- fix en vivo + auditoría "desde el inicio" pedida

Arturo vio en vivo, por Telegram, la misma familia de falla ya
documentada varias veces (Bloques H/P/Q/AE/AF): Tarea E ofreció DeepSeek
sobre un saludo trivial ("Hermes" -> "Buenas noches. ¿En qué puedo
ayudarte?"). Se hartó explícitamente ("siempre son las mismas fallas de
la investigación... estoy arto") y pidió repasar **desde el inicio del
proyecto** y corregir de verdad el patrón, no solo documentarlo --
confirmado en vivo. Detalle completo y punch list del repaso pendiente
en `docs/ESTADO.md`, sección "PRIORIDAD MÁXIMA".

**Cerrado esta tarde, con evidencia real:**
- Fix del hueco encontrado: `_SELF_ASSESS_RUBRIC` (Tarea E, Bloque O) sin
  excepción para saludos/mensajes sin pregunta real -- agregada
  "EXCEPCIÓN 2". Verificado con llamada REAL al modelo reproduciendo el
  caso exacto (ver ESTADO.md para el output). Test de regresión agregado.
  `tests/agent/test_complexity_detector_self_assess.py` +
  `tests/smoke/test_s4_complexity_detector.py`: 11/11 pasan.
- 15 filas duplicadas de reflexión del 30 jul (residuo de anoche,
  Bloque 3) -- limpiadas con respaldo real verificado primero. Detalle
  en ESTADO.md.
- Links de Google Cloud Console/Classroom entregados a Arturo.
- Aclaraciones a Arturo sobre Binance (solo papel, sin Bitso todavía),
  CoinGecko (para qué sirve, web-only), Docker (comando sudo pendiente
  de que Arturo lo pegue), Notion (biografías de TikTok son pieza del
  proyecto de YouTube, pendiente que Arturo comparta esa base).
- Corrección propia: **OT-9.5** (modo llamada interino, Gemini Live API,
  no depende de Mac Mini) existe desde el 21-jul y nunca se construyó --
  se me había pasado por alto al asumir que toda la voz esperaba a la
  Mac Mini. Pendiente decidir con Arturo si va antes o junto con
  Bloque 10.

**Sin cerrar, para la siguiente sesión (`/loop` tras `/clear` de Arturo):**
repaso real con evidencia de Bloques H/P/Q/AE/AF/O/L17 (lista exacta en
ESTADO.md) antes de continuar con el plan de 24h -- Arturo lo puso como
prioridad sobre ese plan, no en paralelo.

## Cierre de la sesión nocturna + Plan de 24 horas armado (30 Jul 2026, mañana)

Arturo despertó (8:58am), revisó lo de la cuenta `hermes_test` (creada
y borrada la misma mañana -- pedido explícito de no repetir ese patrón,
usar la cuenta QA ya autenticada en su lugar) y pidió una jornada larga
nueva: 24 horas, ~60 puntos entre bloques/fases/pendientes, con
investigación real antes de cada pieza, uso de la cuenta QA para
pruebas, y verificación explícita contra su cuenta principal (motivo:
pruebas externas previas nunca se implementaron ahí y eso ya causó
fracasos que no quiere repetir). Plan completo, priorizado y auditado
contra evidencia real (no contra el documento maestro solo), escrito en
`docs/ESTADO.md` bajo "PLAN DE 24 HORAS" -- arrancar ahí en la próxima
sesión. Resuelto de paso el Bloque 10 pendiente de anoche (SÍ ofrecer
DeepSeek automático si cae la escalera gratuita completa), con
investigación real: los alias `deepseek-chat`/`deepseek-reasoner` se
retiraron el 24 jul 2026, pero `litellm/config.yaml` ya usa los nombres
correctos (`deepseek-v4-flash`/`deepseek-v4-pro`), sin breakage real.

## Corrida autónoma de `/loop` (30 Jul 2026, madrugada) -- corrige la hipótesis del Bloque 1 del plan nocturno, cierra Bloque 6

Arturo dormido; corrida sin supervisión siguiendo el PLAN NOCTURNO ya
dejado en `ESTADO.md`. Detalle completo de la evidencia real (log +
`state.db`) en `ESTADO.md`, sección "Avance autónomo de la madrugada".
Resumen para este registro:

- **Bloque 1 (diagnóstico del "bug de reinicio a media conversación"):
  hipótesis de anoche descartada con evidencia real.** No fue un turno
  interrumpido a media conversación (ya arreglado en Bloques Q/AF sobre
  esta misma sesión). Fue el modelo re-narrando, sin que se lo pidieran,
  un incidente real de 13h antes que seguía en su ventana de contexto
  activa, al recibir un mensaje de bajo contenido ("Hermes buenas
  noches"). El guardia anti-fabricación (Tarea 1) bloqueó la mentira
  antes de llegar a Arturo -- funcionó como se diseñó -- pero el mensaje
  de rechazo genérico es un non-sequitur para un saludo. Deliberadamente
  NO se implementó ningún fix del comportamiento del guardia esta noche
  (riesgo de otra hipótesis no probada sin Arturo despierto para
  verificar en vivo, mismo patrón que ya costó sesiones completas en
  Bloques H/P/Q/AE/AF) -- queda como decisión pendiente de Arturo
  (¿regeneración condicionada con costo/latencia extra, sí o no?). R.11
  de `GUION_PRUEBAS.md` sigue sin escribir -- el escenario original no
  es el que de verdad pasó.
- **Bloque 6 -- CERRADO.** `has_progress.py --quiet` (invocado
  literalmente por el arranque de sesión de `CLAUDE.md`) no existía.
  Agregado con respaldo previo, verificado en vivo en ambos modos
  (silencioso en corrida limpia, sigue mostrando `[FAIL]`/resumen
  siempre -- HAS L14). Hallazgo colateral sin investigar: el check
  `tarea_i_allowlist_cleared` falla (`command_allowlist` no está vacío
  en `config.yaml` pese a que Tarea I decía haberlo dejado así) --
  posible regresión real o check desactualizado, ninguno de los dos
  confirmado todavía.
- **Bloque 7 -- paso 1 (verificación urgente) completado, sin sudo ni
  consola de Google.** La llave Gemini en uso sigue funcionando después
  del corte de API-restriction del 19 jun -- confirmado con tráfico de
  producción real de esta misma noche (22:46:08), no una prueba
  sintética. Descarta la hipótesis más barata del bloque. La rotación de
  credenciales de la fuga vieja (el resto de Bloque 7) sigue pendiente,
  requiere a Arturo o probar las llaves viejas en vivo.
- **Bloque 2, paso 1/5 -- CERRADO, mismo tick de `/loop`.** Los 2
  comandos `sudo` pendientes ya estaban corridos. Construido
  `scripts/respaldar_memoria.py` (respaldo de `state.db` +
  `memoria_semantica.db` vía Backup API de sqlite3, nunca `cp`) con 5
  pruebas nuevas (`tests/scripts/test_respaldar_memoria.py`), incluida
  una que simula escritura concurrente real durante el respaldo.
  Corrida real contra las DBs de producción en vivo, con el gateway
  activo: ambas DBs respaldadas y verificadas (`integrity_check` +
  conteo de filas por tabla, 24 + 12 tablas todas OK) en
  `/mnt/seagate/hermes_backups/20260729_235806/` -- primer archivo real
  que existe ahí desde el 4 de julio. Hallazgo real durante la
  construcción: `memoria_semantica.db` usa la tabla virtual `vec0`
  (extensión `sqlite-vec`) que una conexión simple no puede leer -- se
  corrigió cargando la extensión con el mismo patrón que ya usa
  `agent/memory_semantic.py::_connect`. Pasos 2-5 de HAS §E13 (bóveda
  `age`, skills/índices/timers, ensamblar `restaurar_hermes.sh`
  completo, prueba de restauración real) siguen sin empezar -- ver
  `ESTADO.md` para el detalle. Sin timer automático configurado todavía
  (deliberado, corrida manual de esta noche).

- **Bloque 2, paso 2/5 -- CERRADO, mismo `/loop`, tick siguiente.**
  `scripts/bovedar_secretos.py` (cifrar/descifrar con `age -p`), 4
  pruebas. Hallazgo real: `age -p` exige `/dev/tty`, no acepta
  passphrase por pipe -- confirmado con un experimento real antes de
  escribir el script (`age -p ... <<< "x"` falla con `/dev/tty is not
  available`). El script hereda stdio del proceso que lo invoca en vez
  de redirigir nada, para que el prompt llegue a la terminal real; las
  pruebas manejan el CLI dentro de un `pty` para automatizar el prompt
  sin cambiar el mecanismo de producción. Deliberadamente sin tocar el
  `.env` real ni ninguna credencial real -- solo contenido sintético de
  prueba, por la regla dura de `CLAUDE.md` de siempre preguntar antes
  de tocar credenciales reales.

- **Bloque 2, paso 3/5 -- CERRADO.** `scripts/respaldar_skills_y_sistema.py`
  (rsync de skills + copia de unidades systemd de Hermes), 5 pruebas,
  corrida real: 1431/1431 archivos de skills + 14 unidades/overrides
  systemd, verificado. Hallazgo real importante: ya existe un vault
  distinto y en producción (`~/.hermes/boveda/entries.json.enc` vía
  `tools/vault_tool.py`, Bloque T) para credenciales que Arturo pide a
  Hermes recordar en conversación -- NO se tocó ni se mezcló con el
  `bovedar_secretos.py` del paso 2 (ese es para `.env`/credenciales del
  sistema, un propósito distinto). Queda pendiente para una sesión con
  Arturo: ¿migrar `vault_tool.py` a `age` ahora que ya está instalado?
  Bloque 2 va 3/5 -- faltan paso 4 (ensamblar `restaurar_hermes.sh`) y
  paso 5 (prueba de restauración real).

- **Bloque 2, paso 4/5 -- CERRADO.** `scripts/restaurar_hermes.sh`
  orquesta los 3 pasos anteriores con un solo timestamp compartido
  (`respaldar` implementado y probado en vivo; `restaurar` sale con
  "SIN IMPLEMENTAR" a propósito, en vez de fingir). `docs/
  RECUPERACION.md` -- runbook humano completo, honesto sobre que hoy
  son pasos manuales. 33 pruebas en `tests/scripts/`, todas pasan.
  Corrida real completa contra producción (sin tocar `.env`): memoria +
  skills + systemd, un solo directorio, exit 0. Bloque 2 va 4/5 -- falta
  la prueba de restauración real en máquina limpia (necesita sudo/VM,
  queda para sesión con Arturo presente).

- **Bloque 3 -- CERRADO.** Ventana de mantenimiento nocturna (HAS E14):
  2 timers systemd nuevos (`hermes-memoria-reflexion-nocturna`,
  reflexión diaria vía `--dias` nuevo en `memoria_diario_reflexion.py`;
  `hermes-respaldo-total`, corre `restaurar_hermes.sh respaldar` cada
  noche) + `RandomizedDelaySec` en los 2 timers existentes que chocaban
  a las 03:00:00 exacto. Detalle completo, incluido un hallazgo real
  sobre `Persistent=true` disparando una corrida fuera de horario al
  cambiar mal la hora base de un timer (ya corregido), en
  `~/.hermes/CHANGELOG_SISTEMA.md` y `docs/ESTADO.md`. Fuera del repo
  (config de sistema + script en `~/.hermes/scripts/`), sin commit de
  código en `arturo/prod` para este bloque.

- **Bloque 4 -- CERRADO (B9, reglas de comportamiento aprendidas).**
  `detectar_patrones_repetidos()` en `fase2_extract_candidates.py`
  (fuera del repo): 3+ apariciones de la misma corrección exacta
  normalizada → candidato nuevo "regla_comportamiento", mismo flujo de
  aprobación de siempre, mapeado a "meta" en
  `tools/memoria_review.py::_CATEGORIA_MAP` (dentro del repo).
  Reutiliza infraestructura existente, alcance chico a propósito.
  Verificado con datos sintéticos (positivo y negativo). 3 pruebas
  nuevas en el repo, todas pasan. Detalle completo con limitaciones
  conocidas en `~/.hermes/CHANGELOG_SISTEMA.md` y `docs/ESTADO.md`.

- **Bloque 9 -- CERRADO, no era un bug.** `sessions.message_count`
  cuenta `messages WHERE active=1` (la ventana de contexto en vivo que
  se manda a la API), no el total de filas -- las filas `compacted=1`
  son historial preservado, nunca borrado. Verificado en vivo sobre la
  misma sesión del hallazgo original: coincidencia EXACTA
  (`message_count=16` = `COUNT(*) WHERE active=1`). Sin fix necesario.
- **Bloque 8 -- REEVALUADO, cerrado parcial a propósito.** Hallazgo
  importante que corrige la nota original del plan: el arnés E2E
  (`tests/e2e/hermes_harness.py`) maneja mensajes REALES contra el
  pipeline REAL de producción (state.db compartido con el gateway
  vivo, costo real de LLM) -- no es una sandbox segura. R.8 (ráfaga) y
  S.8 (inyección adversarial) se difirieron a propósito a una sesión
  con Arturo despierto, en vez de correrlos solo a las 3am. Sí se hizo,
  seguro: `pyfakefs==6.2.0` agregado como dependencia dev, 2 pruebas
  nuevas fijan con precisión el umbral de `_probe_disk()` (antes
  aceptaba "ok o degraded" sin controlar el uso real de disco).
  Hallazgo de diseño sin resolver: `_probe_disk()` es de solo lectura,
  R.10 pide un guard ACTIVO antes de escribir que no existe hoy --
  queda para que Arturo decida prioridad. R.9 no automatizado --
  resuelto con evidencia real ya existente (el hallazgo de
  `Persistent=true` del Bloque 3, más relevante que una simulación).

- **Bloque 5 -- PARCIAL.** `tools/notion_avance_has.py`: primera de 6
  vistas de Fase 5/OT-5 Bloque 2, sync cada 15 min a una página "Avance
  HAS" en Notion (reemplaza contenido, no acumula). Verificado en vivo
  dos veces contra la API real + confirmado vía el timer systemd real.
  Hallazgo real que bloquea el resto: ninguna de las bases de datos
  personales de Arturo (Finanzas/Proyectos/Tareas académicas/Ideas)
  está compartida con la integración -- Finanzas/Escuela necesitan que
  Arturo las comparta; Kanban espejo/Cola de tareas necesitan que
  decida base nueva vs. reusar "Proyectos".

**Commits:** ver `git log` de esta fecha en `arturo/prod` (docs +
`has_progress.py`/`fase2_extract_candidates.py` viven fuera del repo,
respaldo en `~/.hermes/backups/scripts/`;
`scripts/respaldar_memoria.py`, `scripts/bovedar_secretos.py`,
`scripts/respaldar_skills_y_sistema.py`, `scripts/restaurar_hermes.sh`,
`docs/RECUPERACION.md`, `tools/memoria_review.py`,
`tools/notion_avance_has.py` y las pruebas sí viven dentro del repo).

## Triaje de propuestas externas de arquitectura (HAS v1.6), CERRADO (29 Jul 2026, noche)

Arturo consultó 3 documentos de análisis externos sobre HAS (arquitectura
general, resiliencia/pruebas, y filosofía de trabajo para Claude Code) y
pidió evaluarlos contra el código y el estado real del proyecto, no contra
el documento HAS solo. Proceso: verificar cada afirmación de "esto falta"
contra disco/código antes de aceptarla o descartarla (mismo principio que
el resto de esta sesión).

**Adoptado en HAS v1.6** (detalle completo en `docs/HAS.md`, changelog de
versión y secciones nuevas):
1. **E13 "Recuperación total"** — verificado que `/mnt/seagate/
   hermes_backups/` está vacío desde su creación (4 jul); hueco real, no
   hipotético. `restaurar_hermes.sh` + prueba de restauración obligatoria
   cada 3 meses + `docs/RECUPERACION.md`. Queda agendado como **siguiente
   prioridad real** (por encima del tablero de Notion que venía pendiente).
2. **B9 extendida** — diario de reflexión pasa de semanal a nocturno;
   nuevo mecanismo de "reglas de comportamiento aprendidas" con el mismo
   candado de aprobación que los hechos normales (nunca auto-adopta),
   diseñado explícitamente después de la contaminación de memoria
   encontrada esta misma noche.
3. **E14 "Ventana de mantenimiento nocturna 2:00-5:00"** — numerada
   aparte de E9 (que ya usa "ventana de mantenimiento" para el ciclo de
   suscripción de Claude Pro; son conceptos distintos, se dejó explícito
   para no confundirlos).
4. **`GUION_PRUEBAS.md`** — regla de oro de crecimiento orgánico (todo
   bug real se vuelve prueba permanente la misma semana) + casos R.8
   (ráfaga de 20 entradas simultáneas) y R.9 (reloj del sistema y
   suspensión).

**Rechazado explícitamente por sobredimensión** respecto a la escala real
del proyecto (una laptop, un usuario, $100 MXN/mes): volumen de
2,400-4,000 pruebas formales y "100 pruebas por skill" (el principio de
cobertura ya lo cumple la matriz combinatoria de `GUION_PRUEBAS.md` + la
regla 3a de crecimiento orgánico); diseñar cada decisión pensando en un
horizonte de 5 años o "500 skills" hipotéticas (se distinguió entre
holgura ARQUITECTÓNICA -- esquemas, contratos entre módulos -- que sí vale
la pena pensar hacia adelante, vs. holgura de FUNCIONES/capacidad
construida para un uso que no existe todavía, que no); y re-arquitecturas
de mecanismos que ya funcionan bien (sistema de eventos -- Hermes ya corre
por timers, no por polling constante; framework de skills -- ya son 141
activas, más que las "40-60" sugeridas; motor de decisiones de proveedor
-- ya existe en la escalera Groq→Gemini→OpenRouter de Cola v2).

**Dos hallazgos propios de esta sesión, no incluidos en el triaje original,
sumados con autorización de Arturo** ("mientras no afecte el proyecto y
sea mejora hacia adelante, adelante"): (a) **R.10** — disco lleno (no
hipotética: ya pasó de verdad el 24-25 jul, `/tmp` lleno tumbó Bash 3
horas); (b) **S.8** — resistencia de `memoria_hecho_tool.py` (la
herramienta de borrado construida esta noche) a un intento de
inyección/suplantación, dado que ya quedó viva en el gateway real. Se
ubicó como caso de SEGURIDAD (bloque S., no R.) por ser la clasificación
correcta -- borrado no autorizado vía manipulación de contenido, no una
falla de infraestructura.

## Fix de /memoria (candado de concurrencia + filtro diagnóstico + dedup), CERRADO (29 Jul 2026, noche)

Nueva sesión, fuera de las 4 tareas de hoy. Arturo estaba probando
`/memoria` en su cuenta real, 49 candidatos pendientes acumulados.
Detalle completo en `docs/ESTADO.md`. Resumen: revisé los 49, casi todos
ruido (duplicados por corrida concurrente del extractor + texto de
prueba/diagnóstico de sesiones reales de Arturo probando el propio
pipeline) -- Arturo rechazó los 49 siguiendo la recomendación. Arreglé
la causa raíz: candado `fcntl.flock` en `fase2_extract_candidates.py`
(fuera del repo) contra la condición de carrera, filtro de contenido
`_DIAGNOSTIC_MARKERS` contra texto de prueba que el filtro de sesión no
podía distinguir (sí era de Arturo, solo que era texto de prueba), y
dedup exacto en `tools/memoria_review.py::_load_queue()` (dentro del
repo) como red de seguridad. Verificado con datos sintéticos y con una
corrida real en vivo del extractor ya arreglado (15 mensajes nuevos,
1 candidato limpio). Hallazgo sin tocar, reportado a Arturo: el primer
candidato que ya había aprobado antes del fix es una instrucción
puntual de DeepSeek de una sesión vieja, no una preferencia duradera --
pendiente su confirmación para borrar/editar esa fila.

**Commits:** `fe4fcb5a0` (repo), pusheado a `fork/arturo/prod`. Fix del
extractor fuera del repo, respaldado antes de tocarlo.

## SSH restringido a Tailscale + sin contraseña, CERRADO (29 Jul 2026, tarde-noche)

Tercera de las 4 tareas de hoy. Hallazgo del audit de seguridad de
arranque (ya existente). Investigado en internet antes de aplicar
(pedido explícito de Arturo) -- restringir SSH a la interfaz de
Tailscale es más fuerte que solo deshabilitar contraseña, y coincide
con el diseño ya previsto en HAS Fase 11 (USB portable: túnel de
Tailscale antes que SSH). Cambio de sistema (`/etc/ssh/sshd_config`),
corrido por Arturo mismo vía sudo -- sin commit en este repo. Verificado
en vivo: la sesión de Arturo (conectada por Tailscale desde su iPhone
vía la app de Claude) siguió funcionando sin interrupción durante y
después del `systemctl reload`. Detalle completo en `docs/ESTADO.md`.

## Cola v2 (HAS §E5, OT-5 Bloque 3), CERRADA (29 Jul 2026, tarde)

Primera de las 4 tareas que Arturo pidió completar hoy, empezando por
la más compleja. Detalle completo en `docs/ESTADO.md`. Resumen: NO se
migró Tarea C/`mensajes_pendientes` (decisión de alcance documentada,
sigue viva en producción sin tocar) -- se construyó `task_queue` como
mecanismo GENERAL nuevo (`hermes_state.py` esquema + `gateway/
task_queue.py` mixin), corriendo dentro del proceso vivo del gateway a
propósito (evita el bug de entrega ya confirmado esta mañana en cron
externo). Escalera Groq→Gemini→OpenRouter, watchdog de huérfanos,
garantía de notificación por compare-and-swap. Verificado con una tarea
real contra la cuenta QA (nunca la real de Arturo) -- resuelta,
entregada, notificada, confirmado leyendo `state.db`. Bug real
encontrado y arreglado en esa verificación: `proveedor_actual` nunca se
guardaba. 26 tests nuevos incluida la E2E de 15 tareas sintéticas con
proveedor primario deshabilitado que pide HAS, 0 fallas.

**Commits:** pendiente de commit al cierre de esta sesión (ver git log).

## Espejo Obsidian -> Notion, CERRADO (29 Jul 2026, tarde)

Cierre de la misma sesión larga. Arturo difirió la visualización de
nodos hasta la Mac Mini y pidió en su lugar que cada nota de Obsidian
también se numere en Notion. Detalle completo en `docs/ESTADO.md`.

`tools/notion_mirror.py` (nuevo) conectado a `obsidian_note_tool.py` --
best-effort, nunca bloquea el guardado real en Obsidian. 2 hallazgos
reales de la API de Notion 2025-09-03 (endpoint de creación de bases
distinto al documentado en la skill; `data_source_id` != `database_id`
para crear páginas) encontrados y corregidos contra la API real, no
simulados. Verificado de punta a punta con la nota real de Arturo,
confirmada leyendo la fila de vuelta de Notion. 11 tests en
`test_notion_mirror.py` + 12 en `test_obsidian_note_tool.py`, 0 fallas.

Incidente menor de manejo de credenciales: Arturo pegó su
`NOTION_API_KEY` real en el chat en vez de solo en `.env` -- corregido
en el momento (aviso + `.env` editado por él mismo vía `read -s`, ni
Bash ni Edit pueden tocar ese archivo desde esta sesión por permisos).

**Commits:** pendiente de commit al cierre de esta sesión (ver git log).

## Obsidian local + tool de notas, CERRADO (29 Jul 2026, mañana)

Continuación de la misma sesión larga. Arturo aclaró su visión real
("segundo cerebro" que Hermes construye desde lo que él le manda por
chat, sin mudanza manual de información) y decidió: vault SOLO en la
HP, sin sync a la Mac (visualización vía SFTP/Finder cuando quiera).
Detalle completo en `docs/ESTADO.md`.

Construido: `/mnt/seagate/obsidian/` (Arturo corrió el único `sudo`
necesario), `tools/obsidian_note_tool.py` (tool nueva, escaneada por
secretos antes de escribir, nunca sobrescribe en silencio, 12 tests --
1 bug real encontrado y arreglado por los tests antes de producción),
e `index_obsidian()` real en el indexador externo (cursor incremental
por mtime, ya no el stub que saltaba). Verificado de punta a punta: nota
real creada -> indexada -> recuperable por búsqueda semántica (score
0.819). El gap de Obsidian documentado en el Bloque 2 de esta misma
mañana queda cerrado en la misma sesión.

**Commits:** pendiente de commit al cierre de esta sesión (ver git log).

## Bloque O.1.2 (hueco web_search) + arranque Fase 5, CERRADO parcial (29 Jul 2026, mañana)

Continuación de la misma sesión, tras cerrar las 4 tareas de arriba.
Arturo pidió arreglar el único pendiente real de la auditoría (hueco
O.1 vs `web_search`) y arrancar Fase 5. Detalle completo en
`docs/ESTADO.md`.

1. **O.1.2:** `agent/turn_finalizer.py` -- chequeo POST-respuesta que
   detecta si se llamó `web_search` este turno (`messages` con
   `role="tool", name="web_search"`) y compara cualquier precio
   mencionado en la respuesta final contra CoinGecko real, mismo
   umbral >5% que O.1. Verificado contra la API real (no mock) con un
   caso de conflicto deliberado. 6 tests nuevos + 47 de regresión de
   `turn_finalizer`, 0 fallas.
2. **Notion, OT-5 Bloque 1:** consolidación con una desviación
   documentada del texto literal de la orden -- el contenido real
   estaba al revés de lo que el nombre sugería (la skill "personal" no
   tenía mecánica de API real, la "bundled" de comunidad sí). Se
   conservó `productivity/notion/` (renombrada `notion-api`), con una
   sección nueva "Estructura de Arturo" fusionada desde la delgada
   antes de archivarla en `.archive/notion-personal-thin/`
   (`ARCHIVADO.md` con la justificación completa, incluyendo que la
   archivada tenía una referencia a "Tony" sin corregir desde OT-1).
   `skills_audit.py` confirma 0 duplicados/404 tras el cambio.
3. **Cola v2 (Tarea C -> task_queue), NO iniciada a propósito.**
   Es una migración de un mecanismo de entrega en producción viva
   (`mensajes_pendientes`, usado hoy por el auto-watcher y la
   autorización manual de DeepSeek) a un esquema y máquina de estados
   nuevos con escalera de reintentos y watchdog -- se recomendó a
   Arturo tratarla como sesión dedicada en vez de apurarla al final de
   una sesión ya larga con 6 piezas de trabajo distintas.
4. **Obsidian: decisión de arquitectura presentada, no resuelta.**
   Arturo preguntó por el diseño real; se le explicó la separación
   Notion (operación) / Obsidian (conocimiento, HAS §B7) y se le dieron
   2 caminos (sync gratis por job programado vs. Obsidian Sync de
   pago) -- queda esperando su decisión antes de construir el canal de
   sync hacia el HP.

**Commits:** pendiente de commit al cierre de esta sesión (ver git log).

## HAS Fase 4, Bloques 2-3 (índice semántico de memoria) + limpieza de deuda pendiente, CERRADO (29 Jul 2026, mañana)

Pedido explícito de Arturo: "todo de una vez pero inicia con lo más
difícil" -- 4 tareas en una sesión. Detalle completo en `docs/ESTADO.md`.

**1. Índice semántico de memoria (HAS §B9/§E4, lo más difícil).**
`agent/memory_semantic.py` nuevo -- esquema `memoria_semantica.db`
(chunks + FTS5 + sqlite-vec), embeddings locales
(`intfloat/multilingual-e5-small`, 384 dim) + retrieval híbrido
(FTS5 top-20 + vector top-20, re-rankeado 0.5·similitud + 0.3·recencia +
0.2·importancia, exacto a HAS §E4). Dependencias nuevas
(`sqlite-vec==0.1.9`, `sentence-transformers==5.6.1`) via el patrón
lazy-install del proyecto (`tools/lazy_deps.py`, extra
`memory-semantic`), no eager -- mismo tratamiento que supermemory/mem0.

- **2 bugs reales encontrados y arreglados durante la verificación
  contra el modelo real** (no en el diseño en papel): (a) sintaxis de
  sqlite-vec -- `k=` y `LIMIT` juntos truena ("Only LIMIT or k=? can be
  provided"); (b) FTS5 sin filtrar palabras funcionales del español
  ("la", "por", "me", "como") hacía match contra CUALQUIER chunk que las
  compartiera, rankeando contenido sin relación real por encima de un
  match semántico genuino -- confirmado con el propio caso de prueba
  ("SSH a la MacBook") antes de arreglarlo.
- **Indexador** (`~/.hermes/scripts/memoria_indexador.py`, fuera del
  repo, mismo patrón que `fase2_extract_candidates.py`): backfill real
  corrido en vivo -- 282 chunks de `hermes_raw` (2,814 mensajes reales),
  2 hechos de `memoria_estructurada`, 142 skills activas (de 153
  totales). RAM pico medida: 1.68GB de 7.1GB totales -- muy por debajo
  del umbral de degradación del HAS (85% del sistema), sin necesidad de
  bajar a `paraphrase-multilingual-MiniLM-L12-v2`. Tiempo: 2:25 min
  (dominado por la carga única del modelo, no por el volumen real).
  Incremental verificado (segunda corrida: "nada nuevo" en raw/hechos).
- **Obsidian NO indexado -- gap real, documentado, no fabricado:** el
  vault vive en la MacBook remota: no hay canal de sync (ni rsync ni
  montaje) hacia esta HP. La prueba E2E literal del HAS ("SSH a la
  MacBook, 565 notas") no se pudo correr por esto -- se avisa en el log
  del indexador cada corrida, nunca en silencio.
- **Diario de reflexión** (`~/.hermes/scripts/memoria_diario_reflexion.py`):
  corrida real en vivo -- Gemini (chat-primary, nunca DeepSeek) leyó 200
  mensajes reales de los últimos 7 días y escribió 5 observaciones
  reales (verificadas a mano, sin alucinación evidente), indexadas con
  importancia=0.9.
- **Tool `memory_search`** (`tools/memory_search_tool.py`) registrada en
  el toolset core (`toolsets.py`, `_HERMES_CORE_TOOLS` + 3 perfiles más)
  -- búsqueda explícita del agente, umbral bajo (0.35). Además,
  **inyección automática** en `agent/turn_context.py` (mismo patrón que
  Bloque O.1) con umbral más alto (0.6, SUPUESTO marcado en el código --
  sin caso real todavía para calibrar).
- **Bug de rendimiento encontrado y arreglado antes de que llegara a
  producción:** conectar la inyección automática a `build_turn_context`
  hacía que CUALQUIER test que ejercitara esa función real (no solo los
  de memoria) cargara el modelo de embeddings -- `test_turn_context.py`
  pasó de 2.4s a 14.4s. Fix: `buscar()` ahora sale temprano
  (`SELECT 1 FROM chunks LIMIT 1`) si el índice está vacío, antes de
  tocar el modelo -- correcto también en producción (un índice recién
  instalado no debe intentar embeddings sin nada que comparar).
- **Verificación real de retrieval** (no sintética) contra el corpus
  real ya indexado: "como actualizo Hermes a una version nueva sin
  romper nada" -> `hermes-upgrade/SKILL.md` en el top-1 (score 0.803);
  "en que ha estado trabajando Arturo esta semana" -> observación de
  reflexión real en el top-1 (score 0.911).
- **Systemd timers reales, armados y confirmados con
  `systemctl --user list-timers`:** `hermes-memoria-index.timer` (diario
  3am) y `hermes-memoria-reflexion.timer` (domingos 8am), ambos
  `Persistent=true` (recuperan si la laptop estaba apagada/con la tapa
  cerrada a esa hora).
- **21 tests nuevos** (`tests/agent/test_memory_semantic.py`,
  `tests/tools/test_memory_search_tool.py`, 3 en
  `tests/agent/test_turn_context.py`) + toda la suite de
  `tests/agent/`, `tests/tools/`, `tests/test_toolsets.py`,
  `tests/test_toolset_distributions.py`, `tests/test_project_metadata.py`
  corrida sin fallas nuevas.
- **Pendiente real para otra sesión:** confirmar 3 noches seguidas de
  reindexado automático sin intervención (criterio literal de HAS §OT-4
  Bloque 3.3) -- el timer se armó hoy, necesita tiempo real de calendario
  para confirmarse, no se puede simular.

**2. Bug `_pending_reprocess_ids` (Bloque AF), CERRADO -- resultó ser
más grande de lo registrado.** El registro decía "2 tests fallando";
la corrida real de toda la suite de `tests/gateway/` mostró **15 tests**
con el mismo `AttributeError: 'GatewayRunner' object has no attribute
'_pending_reprocess_ids'` (10 de ellos solo en `test_session_hygiene.py`,
nunca contados antes). Causa: varios fixtures de test construyen
`GatewayRunner` vía `object.__new__()` (saltándose `__init__`, patrón ya
documentado en el propio archivo), así que nunca inicializan ese dict.
Fix de una línea en `gateway/run.py` (~línea 14795): `getattr(self,
"_pending_reprocess_ids", {})` en vez de acceso directo -- correcto
también en producción (un runner real siempre tiene el dict via
`__init__`; el fallback a `{}` es el comportamiento correcto para un
runner al que nunca se le registró nada pendiente). Los 15 tests pasan;
~1,600 tests de regresión de `tests/gateway/` sin fallas nuevas
(comparado contra el código sin tocar vía `git stash`).

**3. Auditoría del backlog del 22 Jul, CERRADO.** El registro de "4
bugs abiertos sin resolver" nunca se había re-verificado contra el
código actual, pese a que otras secciones de este mismo `ESTADO.md`
(27-28 Jul) ya reportaban 2 de los 4 arreglados -- contradicción real.
Verificado uno por uno contra código/sistema real (no repitiendo el
texto viejo): (1) fabricación de evidencia O.6 -- CERRADO, confirmado
en código Y visto disparar en vivo hoy mismo; (2) O.4 sin rastro de
ejecución -- probablemente ya no aplica (el código actual siempre deja
rastro salvo un caso deliberado de diseño), sin poder confirmar el caso
original sin el mensaje real; (3) hueco O.1 vs `web_search` nativo --
SIGUE ABIERTO, confirmado por grep real, nadie lo tocó; (4) cron roto de
`vigilar_hermes.sh` -- CERRADO, confirmado con `crontab -l` real (0
entradas, script no existe). Detalle en `docs/ESTADO.md`.

**Commits:** pendiente de commit al cierre de esta sesión (ver git log).

## Falso positivo de Tarea E sobre respuesta ya completa, CERRADO (29 Jul 2026, mañana)

Encontrado probando en vivo los fixes del bloque de abajo. Detalle
completo en `docs/ESTADO.md`. Resumen: `agent/complexity_detector.py::
self_assess_response` (Bloque O.2) conflaba "no supe decidir" con
"le devolví correctamente la decisión al usuario" -- una respuesta
completa que terminaba preguntándole a Arturo si reiniciar su sesión o
no disparaba una oferta de DeepSeek de todos modos. Fix: rúbrica
(`_SELF_ASSESS_RUBRIC`) con excepción explícita para decisiones que le
corresponden al usuario; sin tocar lógica de código. Verificado con el
modelo barato real (no mock) contra el caso real de Arturo + 3 casos de
control (insegura, multivariable con hueco real, trivial certera) + 5
tests nuevos + 57 de regresión, 0 fallas. Aplicado en vivo (reinicio
09:23).

## Diagnóstico y fix de la respuesta rota del 29 Jul madrugada, CERRADO (29 Jul 2026, mañana)

Detalle completo en `docs/ESTADO.md` (sección "Respuesta rota en la
cuenta real de Arturo"). Resumen: se confirmaron por código las 2 causas
reales del incidente de esa madrugada (7 mensajes duplicados por
redelivery de Telegram sin dedup general, y `read_file` trayendo
`gateway.log` de hace un mes por defecto), se descartó una tercera
hipótesis (`_pending_reprocess_ids`, subsistema distinto), y se
arreglaron ambas causas confirmadas:

1. `hermes_logging.py`: `_ManagedRotatingFileHandler` gana
   `max_age_days` -- fuerza rollover al abrir si la primera línea del
   archivo ya es más vieja que N días. Aplicado solo a `gateway.log`
   (`max_age_days=3` en `setup_logging(mode="gateway")`); agent.log/
   errors.log/gui.log sin cambios.
2. `gateway/run.py`: `_is_duplicate_update`/`_mark_update_processed`,
   generalización de `_is_stale_restart_redelivery` (que solo cubría
   `/restart`) a cualquier mensaje -- marcador
   `~/.hermes/.last_update_id.json`, chequeo al inicio de
   `_handle_message` antes de auth/sesión/plugins.
3. 12 tests nuevos (`tests/gateway/test_restart_redelivery_dedup.py`,
   `tests/test_hermes_logging.py::TestMaxAgeRollover`) + ~1600 tests de
   regresión corridos en bloques chicos (no de un solo golpe). 0 fallas
   nuevas -- las 19 fallas preexistentes (bug real de
   `_pending_reprocess_ids`, Bloque AF, ahora confirmado en 5 tests no 2)
   se reproducen idénticas con `git stash` contra el código sin tocar.
4. Aplicado en vivo: `systemctl --user restart hermes-gateway.service`
   (excepción permanente del hook, 29 Jul 09:07) -- servicio activo,
   `gateway.log` rotado (el viejo de 16038 líneas ahora es
   `gateway.log.1`), sin tracebacks nuevos.

**Commits:** pendiente de commit al cierre de esta sesión (ver git log).

## Hallazgo crítico + OT-4 Bloque 1.3, CERRADO (29 Jul 2026, madrugada)

Continuación directa de la sesión de Fase 4 de esta misma noche. Detalle
completo en `docs/ESTADO.md` (secciones "Hallazgo de seguridad --
escáner de contraseñas en español" y "OT-4 Bloque 1.3"). Resumen:

1. **Hallazgo real, contenido:** el escáner de secretos
   (`tools/threat_patterns.py`) no cubría contraseñas humanas dichas en
   prosa en español -- dejó pasar 4 candidatos con contraseñas reales de
   una prueba de bóveda del 23 Jul (confirmado por Arturo: no vigentes).
   Cuarentena inmediata de los 2 archivos afectados
   (`~/.hermes/cuarentena_credenciales_28jul/`, permisos 600). Fix: 2
   patrones nuevos anclados a "contraseñ*"/"frase de paso" (no a "clave"
   sola, por ambigüedad). Verificado contra los 4 casos reales + 11
   frases benignas (0 falsos positivos) + 484 tests de regresión, 0
   fallas nuevas.
2. **OT-4 Bloque 1.3 construido:** `~/.hermes/scripts/memoria_resumen_semanal.py`
   (fuera del repo, backup post-fix en `~/.hermes/backups/scripts/`) +
   cron real domingos 9pm (`hermes cron create`, job `b0bc302007b0`,
   `--no-agent --deliver telegram:8899197004`). Excepción permanente y
   acotada de DeepSeek automático para esta corrida documentada en
   `~/.hermes/CLAUDE.md` (autorizada por Arturo, sin techo de gasto
   aparte, sigue contando contra el presupuesto real de $100 MXN/mes).
3. **Bug real encontrado en la verificación en vivo:** `hermes cron run`
   ejecuta fuera del proceso del gateway (`source=direct`) y no logra
   entregar por Telegram (timeout, sin adaptador vivo). El mecanismo real
   (`source=builtin`, el tick interno del gateway) SÍ entrega -- probado
   con un job desechable (`--repeat 1`) dirigido a la cuenta QA,
   confirmado leyendo los 3 mensajes reales recibidos. El job real de
   Arturo (domingo 2 de agosto) queda sin verificación end-to-end contra
   su cuenta real -- se decidió no reintentar contra su cuenta después
   del primer intento fallido, para no seguir mandándole ruido de
   pruebas.

**Commits:** `2831838f9` (feature `/memoria` + fix de identidad,
sesión anterior) + fix de `tools/threat_patterns.py` de esta sección
(pendiente de commit al cierre).

## Fase 4 — OT-4 Bloque 1 (aprobación de candidatos), EN CURSO (28 Jul 2026, noche)

Autorizada por Arturo tras compartir el contexto completo del proyecto
(visión de trading/estudio/segundo cerebro/finanzas + una propuesta
externa de memoria por significado). Comparado contra `docs/HAS.md`
completo: casi todo lo pedido ya estaba especificado en Fases 4-11, sin
necesidad de rediseño.

**Hallazgo real (invalida la premisa de OT-4 1.2):** "los 20 candidatos
verificados existentes" no existen -- solo hay 1 archivo en disco con 3
candidatos ya descartados (`HISTORIAL.md`). La corrida de 156
candidatos del 20 Jul que el historial cita no está en ningún lado
(verificado: `/mnt/seagate/backups/`, disco actual, nada). Corriendo
`fase2_extract_candidates.py` en vivo (3 lotes reales, 60 mensajes,
venv correcto tras un primer fallo por `ModuleNotFoundError: dotenv`
usando el intérprete de sistema) salieron 14 candidatos, casi todos
ruido de depuración de código de prueba ("la función suma debería
devolver 4", "¿5 es primo?").

**Causa raíz confirmada por SQL directo:** `raw_layer_export.py`
exportaba TODA la tabla `messages` sin filtrar por identidad. Consulta
real contra `sessions` (`GROUP BY user_id, chat_id, source`): de ~200
sesiones, 120 son el arnés E2E interno (`user_id="u1", chat_id="123"`,
`tests/e2e/hermes_harness.py`), 32 son `source=cli`, y solo **8 son la
identidad real aprobada de Arturo** (`8899197004`, confirmado contra
`platforms/pairing/telegram-approved.json`). La cuenta QA
(`8727618189`) aparece 1 vez.

**Fix, en 2 scripts (`~/.hermes/scripts/`, fuera del repo):**
- `ARTURO_USER_ID = "8899197004"` agregado como constante (mismo patrón
  que `tools/qa_identity.py::QA_USER_ID` y
  `tests/e2e/hermes_harness.py::_ARTURO_USER_ID`).
- `raw_layer_export.py`: `JOIN sessions` + `WHERE s.source='telegram'
  AND s.user_id=?` en la query de exportación -- la capa cruda deja de
  mezclar identidades desde ahora (verificado en vivo, `exit 0`, sin
  mensajes nuevos que exportar porque ya estaba al día en 16780).
- `fase2_extract_candidates.py`: `_real_arturo_session_ids()` consulta
  `sessions` una vez por corrida y filtra `read_new_user_messages()` por
  esa lista antes de mandar nada al modelo. Verificado en vivo: la
  siguiente corrida real descartó 28 mensajes de ruido y solo mandó
  mensajes de sesiones reales de Arturo al extractor -- los candidatos
  resultantes ya no son ruido sintético (aunque sí son sobre desarrollo
  de Hermes, porque es de lo que Arturo habla actualmente por Telegram).
- 3 archivos `fase2_pendientes_*.json` generados durante el diagnóstico
  ANTES del fix (contaminados con el arnés E2E) se borraron -- no eran
  candidatos reales, eran artefacto de la investigación.
- **Resultado: 8 candidatos reales pendientes** (3 viejos del 19 Jul
  re-surgidos porque nada en disco los marcaba revisados + 5 limpios
  nuevos), listos para que Arturo los revise con `/memoria`.

**OT-4 Bloque 1.1 (interfaz interactiva) construida y verificada
E2E contra Telegram real:**

1. `tools/memoria_review.py` (nuevo, ~230 líneas) -- mismo patrón de
   estado que `tools/slash_confirm.py` (dict a nivel de módulo, keyed
   por `session_key`) pero con una COLA en vez de una sola confirmación.
   `_insert_fact()` corre `scan_for_threats(scope="strict")` antes de
   cualquier INSERT real a `memoria_estructurada`. Mapeo documentado
   (supuesto marcado) entre las categorías del extractor
   (preferencia/dato_dispositivo/proyecto_en_curso/correccion/decision)
   y el `CHECK` constraint real de la tabla
   (personal/académico/técnico/financiero/meta) -- son ejes distintos,
   no hay equivalencia exacta.
2. `plugins/platforms/telegram/adapter.py`: `send_memoria_review()`
   (calcado de `send_slash_confirm`, 2 botones en vez de 3) +
   `_memoria_review_state` dict + rama de callback dedicada.
3. `gateway/run.py`: `_handle_memoria_command()` +
   dispatch `if canonical == "memoria"`.
4. `hermes_cli/commands.py`: `CommandDef("memoria", ...)` agregado al
   `COMMAND_REGISTRY`. Rompió `test_telegram_parity` al principio --
   causa real: el registro ya estaba exactamente en el tope de 50 slots
   de Slack (comentario preexistente lo documentaba), cualquier comando
   nuevo desplaza a otro fuera de la lista nativa. Arreglado agregando
   `"memoria"` a `_SLACK_VIA_HERMES_ONLY` (mismo mecanismo ya usado para
   `topup`/`moa`/`debug`/`egress`) -- reachable vía `/hermes memoria` en
   Slack, nativo en Telegram/CLI/Discord.

**Aislamiento por identidad real (decisión tomada a medio camino, no
estaba en el diseño original):** la primera versión servía la cola de
`~/.hermes/fase2_pendientes_*.json` a QUIEN SEA que mandara `/memoria`,
sin verificar identidad -- hubiera dejado que la cuenta QA
aprobara/rechazara los candidatos REALES de Arturo sin que él se
enterara, justo cuando lo estaba por usar para probar el mecanismo.
Corregido antes de la primera prueba real: `_handle_memoria_command`
ahora compara `source.user_id` contra `ARTURO_USER_ID`; solo esa
identidad ve `build_queue()` (la cola real); cualquier otra
(`build_test_queue()`) recibe 2 candidatos sintéticos
("PRUEBA QA: ..."), nunca toca los archivos reales. `register()`/
`resolve()`/`_insert_fact()` llevan `actor_user_id`/`origen` explícitos
en vez de asumir Arturo -- mismo principio de aislamiento que Bloque AG
(memoria QA por `origen`/`user_id` en la misma tabla).

**Bug real encontrado y arreglado EN LA PRUEBA EN VIVO (no en código
estático):** primer intento con la cuenta QA -- botones se veían bien,
pero al hacer clic la respuesta fue "Picker expired — use /model
again." en vez de mi mensaje. Causa raíz leída en el código:
`adapter.py:6102` tiene `data.startswith(("mp:", "mpg:", "mpv:", "mm:",
"mc:", "mb", "mx", "mg:", "mr"))` como catch-all del selector de
modelos -- el prefijo `"mr"` (sin dos puntos) que yo había elegido para
memoria-review coincidía como prefijo de CUALQUIER string que empezara
con esas 2 letras, incluido mi propio `"mr:aprobar:..."`. Los callbacks
nunca llegaban a mi código. Renombrado a `revm:` (no colisiona con
ningún prefijo existente), verificado con una segunda corrida completa.

**Verificación E2E real, con la cuenta QA de Telegram (no solo
simulación local):** credenciales (`api_id`/`api_hash` REDACTADOS aquí a
propósito, de la app personal de Arturo en my.telegram.org, provistas
por Arturo en esta sesión, sesión ya en la bóveda desde
el 27 Jul, passphrase provista por Arturo en esta sesión) usadas para
conectar `tools/telegram_userbot.py` de verdad. Secuencia real,
confirmada mensaje por mensaje:
1. `/memoria` real → bot respondió con el candidato SANDBOX (confirma
   el aislamiento por identidad funcionando en producción, no solo en
   simulación).
2. Click real en "Aprobar" (`message.click(0)`) → respuesta
   `"✅ Aprobado"` → mensaje de confirmación → encadenó automáticamente
   al segundo candidato con sus propios botones.
3. Click real en "Rechazar" → `"❌ Rechazado"` → "Listo, no quedan más
   candidatos por revisar."
4. Confirmado con SQL directo: la fila aprobada quedó con
   `origen='qa', user_id=8727618189` (nunca `arturo_revision_telegram`);
   los 8 candidatos reales de Arturo siguieron en 8, sin tocar.
5. Limpieza con `~/.hermes/scripts/limpiar_memoria_qa.py`: 1 fila `qa`
   borrada, hechos reales antes/después: 0/0.

**Regresión, en 2 pasadas (antes y después del fix de `revm:`):**
`tests/gateway/test_telegram_*.py` (1518 tests) + `tests/smoke/` (221) +
`tests/hermes_cli/test_commands.py` + `tests/tools/test_slash_confirm.py`
-- 0 fallas nuevas en ambas pasadas. Las 2 fallas presentes en ambas
(`TestTelegramExecApproval::test_smart_deny_owner_override_only_offers_once_and_deny`,
`test_non_smart_allow_permanent_false_keeps_session`) confirmadas
preexistentes con `git stash` (mismo `AttributeError:
'_pending_reprocess_ids'` de Bloque AF, sin relación con este trabajo).
Desplegado a producción 2 veces con la excepción de reinicio
pre-aprobada, ambas verificadas con `is-active` + logs limpios.

**Corte de luz real durante la sesión:** ~21:10-21:17, coincidiendo con
un reinicio del gateway -- confirmado con `ping`/`nmcli` que fue caída
de red completa (no solo Telegram), se recuperó sola en ~7 min sin
intervención ni pérdida de datos.

**Hallazgo de seguridad, sin arreglar, bajo riesgo:** `docs/BLOQUES.md`
(este mismo archivo, línea ~706 en la versión de hoy) tiene un
`api_id`/`api_hash` de Telegram REAL en texto plano, committeado a git
-- es el par que Telegram rechazó (`ApiIdInvalidError`, muerto, no el
que funciona hoy). Bajo riesgo porque ya no es válido, pero sigue
siendo una credencial expuesta en el historial del repo. Pendiente de
que Arturo decida si vale reescribir esa parte del historial de git.

**Pendiente real, ninguno bloquea seguir:**
- Los 8 candidatos reales de Arturo, sin revisar -- listos para que él
  corra `/memoria`.
- `/memoria` v1: sin botón "Editar", sin fallback de texto (supuesto
  marcado, documentado en `tools/memoria_review.py`).
- OT-4 Bloque 1.3 (cron semanal de `fase2_extract_candidates.py`) sin
  agendar.
- OT-4 Bloque 2 (índice semántico `memoria_semantica.db`, sqlite-vec +
  e5-small) sin empezar -- HAS advierte medir RAM en el i3 antes de
  comprometerse al modelo de embeddings grande.

## Post-Fase 3 — 11 skills nuevas/consolidadas por pedido directo de Arturo, CERRADO (28 Jul 2026, noche)

Tras cerrar Fase 3 completa, Arturo pidió expandir la limpieza de
skills más allá de OT-3: revisó huecos reales contra cómo piensa usar
Hermes (entrenamiento, trabajo, proyectos, control de dispositivos,
navegación web, reparación de la HP/MacBook) y contra la sección E7 del
HAS (ciberseguridad doméstica, ya diseñada pero nunca empaquetada).
Pidió ir en orden de más a menos complejo, "que todo quede
solucionado". Detalle técnico completo de cada uno, con las 5
preguntas de F2v2 donde aplica, en `~/.hermes/CHANGELOG_SISTEMA.md`
(11 entradas fechadas 28 Jul). Resumen:

1. **`browser`** (nueva) — la herramienta (`tools/browser_tool.py`,
   10 funciones reales, `agent-browser` CLI) ya existía completa en el
   código; solo faltaba la skill. Verificado en vivo: navegar, leer
   snapshot y hacer click reales contra `example.com`.
2. **DaVinci/video (4→1)** — consolidadas en `media/davinci-resolve-automation`.
   De paso, investigación real (pedido de Arturo): la IA nativa de
   DaVinci (IntelliScript, etc.) NO es invocable por API y trabaja al
   revés de lo que se pedía -- documentado con fuentes en la skill.
3. **Ciberseguridad doméstica, E7 del HAS (5 skills nuevas)** —
   `red-inventario`, `router-checkup`, `higiene-credenciales`,
   `anomalias-equipo`, `wifi-intrusos`. 2 bugs reales encontrados y
   corregidos durante las pruebas en vivo contra la HP real (detección
   de sockets rota por `resolve()` vs `readlink()`; lista blanca de
   servicios systemd generando ~45 falsos positivos, rediseñada a
   línea base + diff).
4. **"Unificar dispositivos" (revisión de 3)** — 1 duplicado real
   (`jarvis-ecosistema`) archivado, 2 legítimas sin cambios. Hallazgo
   nuevo, fuera de alcance: `personal-operating-system` tiene el mismo
   problema de contenido mezclado/obsoleto que ya se vio en
   `video-editing-pipeline` -- pendiente su propia sesión.
5. **`hermes-database-maintenance`** (nueva) — respaldo real (API
   online de SQLite, no `cp` de archivo) + integridad, verificado
   contra las 4 SQLite reales de producción sin detener el gateway.
6. **Trading (2→1)** — consolidadas en `software-development/trading-automation`
   (tenía script real, `trading_entrenador.py`, confirmado en disco).
7. **`apple-shortcuts`** (nueva, reconstruida desde cero -- la anterior
   era la basura-404 borrada en Bloque 1) — hallazgo real serio,
   investigado con fuentes: `shortcuts run` requiere sesión gráfica
   activa en la Mac, falla headless.
8. **`chequeo-salud-macbook`** (nueva) — bug real encontrado: `platforms:
   [macos]` bloqueaba la skill al consultarla desde la HP (Linux, quien
   la invoca); corregido a `[linux, macos]`.
9. **`chequeo-salud-hp`** (nueva) — verificada en vivo contra la HP real.
10. **`entrenamiento`** (nueva, salud/gym) — registro local real
    (JSONL), probado en vivo (`NOTION_API_KEY` sigue sin configurar).
11. **`resumen-del-dia`** (nueva, implementa B11 del HAS) — cruza el
    kanban real de Arturo, verificado con datos reales.

**Auditoría final:** `skills_audit.py` sobre las 142 skills activas
resultantes -- 0 archivos-404, 0 duplicados por `name:`, 0 scripts con
sintaxis rota, 0 sin uso no pinneadas, 0 frontmatter incompleto (el
único "duplicado por carpeta" reportado, `notion`, ya está explicado y
resuelto para Fase 5). `tests/smoke/` -- 29/29 en verde tras todo el
trabajo.

**Pendiente real para retomar:**
- Autorizar `sudo apt install libreoffice-impress` (miniaturas de
  powerpoint) y `marker-pdf` sin probar con un PDF real.
- `apple-shortcuts` y `chequeo-salud-macbook` no probadas en vivo --
  sin sesión SSH activa a la MacBook esta sesión.
- `personal-operating-system`: separar hechos (memoria)/contenido
  obsoleto (LiteLLM/Groq)/guía vigente -- su propia sesión.
- `tools/skill_manager_tool.py::_find_skill()` resuelve por nombre de
  carpeta, no por `name:` -- inconsistente con `skill_usage._find_skill_dir()`.

## HAS Fase 3 — CERRADA COMPLETA (Bloques 1-5 de OT-3), 28 Jul 2026

Los 5 bloques de OT-3 cerrados en la misma sesión, autorizados por
Arturo ("comienzas con la fase 3" → "sí, continúa con esos"). Detalle
técnico completo de cada uno, con las 5 preguntas de F2v2 donde aplica,
en `~/.hermes/CHANGELOG_SISTEMA.md`. Resumen:

- **Bloque 1:** respaldo + 2 archivos-404 borrados + 3 duplicados
  reales resueltos (colisión confirmada contra el código de
  producción). 141 → 136 skills activas.
- **Bloque 2:** powerpoint/ocr-and-documents reparados (dependencia
  real era `lxml`, no `validators` como decía el plan); comfyui
  archivado (`use_count: 0` real confirmado). 136 → 135.
- **Bloque 3, el más grande:** bug de fondo de `.usage.json` (indexaba
  por nombre -- afectaba la resolución REAL de `skill_view()`, no solo
  el contador). Refactor de 10 archivos de producción, 1247/1247 tests,
  desplegado con reinicio real del gateway, 29/29 smoke. **Regresión
  propia encontrada y corregida en el camino:** un enlace real roto en
  `superpowers/subagent-driven-development` (consecuencia del Bloque 1,
  detectado por el propio checker de humo antes de que causara daño).
- **Bloque 4:** esquema de metadata E3 aplicado a las 135 skills
  (script idempotente, probado primero en una copia completa antes de
  tocar producción). Pin real (`.usage.json`, no solo cosmético) en las
  30 skills de desarrollo de software -- confirmado que no existen hoy
  categorías propias de bases de datos/redes/ciberseguridad para
  pinnear (solo coincidencias débiles, no forzadas).
- **Bloque 5:** `~/.hermes/scripts/skills_audit.py` (404s, duplicados
  por 2 mecánicas de resolución distintas, sintaxis rota, staleness,
  frontmatter incompleto). Corrido contra producción: 0 problemas
  reales nuevos -- el único "duplicado por carpeta" (`notion`) ya
  estaba planeado para consolidarse en Fase 5, no es un bug.

**Verificación E2E que pedía el HAS para Fase 3** ("dos skills
homónimas registran contadores independientes tras usarse una vez cada
una"): confirmada en vivo hoy contra `skill_view()`/`bump_use()` reales
(ver Bloque 3) -- no quedan skills homónimas activas para repetir la
prueba con 2 reales, pero el mecanismo que lo garantiza (indexado por
ruta) está probado y desplegado.

**Pendiente real para retomar, ninguno bloquea seguir con Fase 4:**
- `sudo apt install libreoffice-impress` -- pendiente de Arturo (miniaturas de powerpoint).
- Probar `marker-pdf` con un PDF real (instalado, sin probar).
- `tools/skill_manager_tool.py::_find_skill()` resuelve por nombre de
  carpeta (no por `name:`), inconsistente con `skill_usage._find_skill_dir()`.
- `tools/skills_tool.py::_find_all_skills()` deduplica por nombre en silencio.
- Programar `skills_audit.py` semanalmente -- explícitamente tarea de Fase 5, no de Fase 3.

## HAS Fase 3 (OT-3 Bloque 2) — reparar powerpoint/ocr, archivar comfyui, CERRADO (28 Jul 2026, tarde)

**powerpoint/ocr-and-documents:** el plan de OT-3 asumía que faltaba
`pip install validators marker-pdf`. Falso en el caso de `validators`
-- investigado el error real (`ModuleNotFoundError`) y resultó ser
`lxml`, no el paquete `validators` (que además es un paquete de PyPI
totalmente distinto y sin relación; `office/validators/` es un
subpaquete LOCAL de la skill, no algo que se instale). Instalado
`lxml` + `markitdown[pptx]` (system ya tenía `Pillow`/`defusedxml`,
`soffice`, `pdftoppm`). Probado con archivos reales generados con
`python-pptx`: `add_slide.py`, `clean.py`, `office/validate.py`
(`PASSED` en las 15 validaciones) -- **3 de 4 scripts funcionan**.
`thumbnail.py` (necesita renderizar a imagen vía LibreOffice) sigue
bloqueado: `libreoffice-impress` no está instalado (`dpkg -l` solo
muestra Writer/Math/Base), confirmado con un `.txt→pdf` real
(funciona) vs `.pptx→pdf` real (falla con "source file could not be
loaded", mismo error con o sin el wrapper `run_soffice`). `sudo apt
install libreoffice-impress` -- permiso denegado en la sesión, no se
reintentó. `ocr-and-documents`: `extract_pymupdf.py` ya funcionaba
(probado con texto/markdown/metadata reales); `marker-pdf` instalado
(paquete pesado, PyTorch, corrido en segundo plano ~15 min) -- pendiente
de probarlo con un PDF real en la próxima sesión.

**comfyui:** archivada. Confirmado con datos reales (`.usage.json`:
`use_count: 0`, `last_used_at: null` desde su creación el 5 jul) que
Arturo nunca la usó -- coincide con el supuesto del HAS. Nota dejada en
`.archive/comfyui/ARCHIVADO.md`: la skill YA soporta Comfy Cloud (sin
necesitar torch local), así que reactivarla no requiere esperar a la
Mac Mini si Arturo quiere generar imágenes antes.

## HAS Fase 3 (OT-3 Bloque 3) — fix real de fondo de .usage.json, CERRADO (28 Jul 2026, tarde)

Autorizado por Arturo ("refactor completo ahora") tras presentarle el
alcance real (57 puntos de llamada por nombre en 6 archivos, no solo un
archivo de un plan de una línea). Detalle técnico completo, con las 5
preguntas de F2v2, en `~/.hermes/CHANGELOG_SISTEMA.md`, entrada del 28
Jul "fix real del bug de fondo de .usage.json".

**Resumen:** `.usage.json` indexaba por `name:` de frontmatter -- 2
skills que compartan nombre compartían un solo contador Y (hallazgo más
grave, confirmado leyendo `tools/skills_tool.py::skill_view()` real)
`skill_view()` ya se NIEGA a resolver el nombre ambiguo con >1
candidato. Cambiada la llave a la ruta del `SKILL.md` relativa a
`~/.hermes/skills` (idéntica al campo `"path"` que `skill_view()` ya
expone). 10 archivos de producción tocados, 9 call sites reales
actualizados para pasar el directorio ya resuelto en vez de solo el
nombre. `archive_skill`/`restore_skill` ahora re-asignan el registro a
su nueva ruta al mover la carpeta (antes se habría perdido en
silencio).

**Regresión dirigida: 1247/1247 tests en verde** (9 tests corregidos
para reflejar el esquema correcto -- no revertidos, documentado caso
por caso en el diff). **Verificado en vivo contra el código real de
producción, dos veces:** `_skill_view_with_bump({"name":
"systematic-debugging"})` subió su contador real de 4 a 5 sin tocar
ninguna otra skill; `hermes curator status` corrió limpio contra los
datos ya migrados (87 skills agent-created, cifras coherentes).

**Migración real de producción:** `.usage.json` real, 103 entradas →
103 (0 perdidas): 98 migradas a su ruta activa, 2 resueltas en
`.archive/` (comfyui, memory-and-context-recovery), 3 mantenidas con
la llave vieja por no tener ya ninguna carpeta en ningún lado (huérfanas
reales, no re-creadas). Respaldo previo del `.usage.json` real en
`/mnt/seagate/backups/usage_json_pre_migracion_20260728.json`.

**Desplegado a producción:** `systemctl --user restart
hermes-gateway.service` (excepción pre-aprobada de `CLAUDE.md`, único
uso de la sesión — primer intento encadenado con `&&` fue bloqueado
correctamente por el hook, que exige el comando exacto sin encadenar;
corregido). 29/29 smoke tests pasan contra el servicio real ya
reiniciado (14:23:12). Logs reales desde el reinicio: 16 líneas
totales, 0 errores/tracebacks.

**Pendiente real, NO arreglado hoy (hallazgo nuevo, fuera de alcance):**
`tools/skill_manager_tool.py::_find_skill()` resuelve por nombre de
CARPETA (no por `name:` de frontmatter, a diferencia de
`skill_usage._find_skill_dir()`), y `tools/skills_tool.py::_find_all_skills()`
sigue deduplicando por nombre en silencio (una skill con nombre
repetido simplemente desaparece de `hermes skills list`/`/api/skills`
en vez de mostrarse). Con 0 colisiones reales hoy esto queda dormido,
pero es un bug latente independiente -- requiere su propia sesión.

## HAS Fase 3 (OT-3 Bloque 1) — limpieza inicial de skills (28 Jul 2026) — CERRADO

Autorizado por Arturo en sesión ("comienzas con la fase 3"). Primer bloque
de OT-3 completo, con evidencia real en cada paso:

**1.1 Respaldo:** `tar -czf /mnt/seagate/backups/hermes_skills_pre_fase3_20260728.tar.gz -C ~/.hermes skills` antes de tocar nada. Verificado con `tar -tzf` (1911 archivos, sin error).

**1.2 Los 2 archivos-404:** `smart-home/ha-automation/SKILL.md` y `hermes-tools/apple-shortcuts/SKILL.md` no eran skills reales -- byte a byte, la página 404 de `skills.sh` (10,220 bytes, sha256 idéntico `62ad1463...`, contenido literal `<h1>404</h1>`). Un intento de descarga guardó el error en vez del contenido. Borrados (archivo + `rmdir`, sin `rm -rf` -- bloqueado correctamente por el hook, resuelto sin necesitar la excepción).

**1.3 Los 3 duplicados** (`test-driven-development`, `systematic-debugging`, `requesting-code-review`, cada uno en `superpowers/` Y `software-development/`): causaban colisión real -- `tools/skills_tool.py` se niega a resolver el nombre con >1 candidato, confirmado con el código real (`skill_view()` devolvía error antes del arreglo). La suposición de OT-3 ("superpowers/ ⊇ software-development/, conservar superpowers/") resultó falsa en los 3 casos al leer el contenido completo, no solo el diff -- `software-development/` ya tenía una sección real "Hermes Agent Integration" (`delegate_task`, herramientas reales del runtime) y contenido metodológico más completo en 2 de 3. Se investigó el repo real `github.com/obra/superpowers` (v6.2.0 actual) para no decidir a ciegas: se rescataron 2 técnicas genuinamente nuevas (`condition-based-waiting.md`, `find-polluter.sh`) hacia la versión canónica antes de archivar la vainilla. `software-development/` se conserva como canónica en los 3 casos (desviación de OT-3 documentada con evidencia); `superpowers/<nombre>/` archivado a `.archive/<nombre>/` con nota explicando la decisión.

**Compuerta F2v2 aplicada:** creado `~/.hermes/scripts/skill_smoke_check.py` (valida frontmatter + que cada link relativo del SKILL.md resuelva a un archivo real) + `tests/smoke.sh` en las 3 skills canónicas -- `OK` antes y después del único cambio de contenido real (`systematic-debugging` v1.1.0→v1.2.0). Las 5 preguntas de F2v2 respondidas en `~/.hermes/CHANGELOG_SISTEMA.md`.

**Verificado en vivo con el código real de producción** (no solo el smoke test): `tools.skills_tool.skill_view()` contra los 3 nombres -- las 3 devuelven `success` ahora, antes del arreglo dos de tres habrían devuelto el error de colisión.

**Resultado:** 141 skills activas → 136 (coincide con el número que cita `docs/HAS.md`). Confirma que "136" no era una cifra vieja del documento -- es el número correcto una vez limpiada la basura real.

**Pendiente real para continuar Fase 3 (Bloque 2-5 de OT-3, no hecho hoy):** reinstalar deps de `powerpoint`/`ocr-and-documents` y probarlas con un archivo real; decidir comfyui (archivar, HAS ya lo recomienda); el bug de fondo de `.usage.json` (indexa por `name:`, no por ruta -- resuelto de facto para estos 3 nombres al quedar 1 solo archivo cada uno, pero el bug de diseño sigue latente); esquema de metadata + `nivel_riesgo` en las 136; comando `hermes skills audit`.

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

## Bloque 6 (HAS Fase 2) — corte real a producción (27-28 Jul 2026) — CERRADO

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

**Paso 6 cerrado (28 Jul 2026, ~12:30), con evidencia real:**
```
$ journalctl --user -u hermes-gateway.service --since "2026-07-27 13:13:29" | grep -iE "error|traceback|exception|critical" | grep -v "error_classifier|FailoverReason|ErrorClass"
jul 27 16:51:36 ... WARNING [Telegram] Telegram network error (attempt 1/10), reconnecting in 5s. Error: httpx.ReadError:
jul 27 20:21:11 ... WARNING [Telegram] Telegram network error (attempt 1/10), reconnecting in 5s. Error: httpx.ReadError:
(2 pares repetidos = 4 líneas WARNING en total, 0 tracebacks/CRITICAL)

$ journalctl --user -u hermes-gateway.service --since "2026-07-27 13:13:29" | wc -l
18
$ journalctl --user -u litellm.service --since "2026-07-27 13:13:29" | wc -l
1
```
23.3 horas reales desde el reinicio (`ActiveEnterTimestamp=Mon
2026-07-27 13:13:29`), 18 líneas de log en total en `hermes-gateway`,
1 en `litellm`, 0 tracebacks/excepciones no manejadas. Las 4 líneas
WARNING son reconexiones de red transitorias de Telegram
(`httpx.ReadError`), mecanismo de reintento ya existente que se
resuelve solo en 5s -- no un síntoma del corte. **Con esto, Bloque 6
cerrado y con él HAS Fase 2 completa, cerrada de verdad.**

## HAS v1.5 — resuelve la incoherencia sobre quién puede editar skills (27 Jul 2026, tarde-noche)

Después de cerrar Fase 2, expliqué el reparto de trabajo del HAS
(B3: "las mejoras sustantivas las hace Claude") como si Hermes nunca
pudiera tocar código de una skill. Arturo señaló que eso no era lo que
había pedido, y que además el propio documento ya se contradice: E9
regla 5 dice "si toca código, es de Claude", pero E9 regla 7 (v1.1, más
reciente) dice que Claude solo está disponible **un mes cada ~4 meses**
y que "entre ventanas, Hermes debe ser autosuficiente" -- si Hermes no
puede tocar código nunca, las skills no podrían mejorar 3 de cada 4
meses. Pedido explícito: verificar la incoherencia con evidencia real,
no de memoria.

**Verificación real, contra los 4 documentos que gobiernan el
proyecto** (no solo `HAS.md`): confirmado que `~/.hermes/CLAUDE.md`
(el archivo más antiguo y permanente) no restringe esto a Claude -- su
regla sobre skills es genérica ("antes de modificar cualquier skill:
respaldo, comparar, validar, versionar") y su objetivo central
declarado es "minimizar el consumo de APIs de pago mediante
reutilización de conocimiento". `PROTOCOLO.md` no toca el tema.
`hermes-agent/CLAUDE.md` tampoco. La incoherencia real estaba
específicamente en 3 puntos de `HAS.md` (E9 regla 5 vs regla 7 vs F2).

**Decisión de Arturo (texto completo suyo, aplicado literal en su
mayoría) -- HAS sube a v1.5:**

1. **E9 regla 5 reescrita**: reparto por capacidad (qué puede pasar
   la compuerta), no por prohibición de agente. Hermes hace TODO lo
   que pueda demostrar con la compuerta de F2v2, incluida edición de
   skills. Claude se reserva: arquitectura del framework, código del
   core, cambios al propio HAS, y lo que Hermes intentó 2 veces sin
   pasar la compuerta.
2. **F2 → F2v2** ("Compuerta de mejora de skills, anti-retroceso,
   agnóstica al agente"): (a) toda skill activa necesita una prueba de
   humo ejecutable -- sin prueba, nadie la edita, ni Claude; entregable
   de Fase 3. (b) Flujo único para cualquier agente: respaldo →
   investigar (Brave permitido y recomendado) → editar en staging →
   probar versión vieja Y nueva → solo se acepta si iguala o mejora →
   semver + changelog con las 5 preguntas de F2 respondidas → si falla,
   reversión automática. (c) Campo nuevo `nivel_riesgo` (normal/crítico)
   en el frontmatter de E3 -- crítico (seguridad, credenciales,
   permisos, dinero) Hermes solo propone, nunca aplica solo.
   Clasificar las 136 skills es entregable de Fase 3. (d) El curator
   sigue igual, poda, jamás edita.
3. **Nueva sección F10 "RECETARIO"**: biblioteca de soluciones real en
   `docs/recetario/` (ya creada, con `README.md` explicando el formato
   y 2 recetas reales de esta misma sesión como primer uso real de la
   regla: `telethon-signin-cliente-distinto-al-que-pidio-codigo.md` y
   `compactacion-en-cascada-target-mayor-al-disparador.md`). Claude
   tiene obligación de cierre (toda sesión que resuelva algo no trivial
   escribe su receta); Hermes la consulta antes de razonar desde cero y
   también escribe receta cuando resuelve algo solo. Métrica mensual: %
   de problemas resueltos sin tocar a Claude.
4. **B3 actualizada** en 2 puntos (el segundo no estaba en la lista
   explícita de Arturo, lo agregué por consistencia y se lo confirmé
   antes de aplicar): ya no dice "solo Claude edita", y la línea
   siguiente ("Hermes solo detecta, nunca edita... sesión mensual de
   mantenimiento") también corregida -- contradecía lo de arriba y
   citaba la cadencia vieja.

**Verificado, diff completo mostrado a Arturo antes de commitear (regla
D8 del PROTOCOLO: mostrar antes de construir), confirmado por él
explícitamente antes de aplicar.** Espejo aplicado también a
`~/hermes-019` (rama `arturo/base`), donde vive la copia de trabajo del
rebase -- ambas copias de `HAS.md` quedan idénticas otra vez.

## HAS Fase 2 — cierre real de la verificación E2E (27 Jul 2026, tarde) — CERRADA

Pedido explícito de Arturo: "Termina de cerrar la fase dos y de ahí ya
nos vamos a la 3". El criterio de verificación de Fase 2
(`docs/HAS.md`) pide simular una actualización FUTURA y que el
procedimiento la resuelva "sin intervención creativa" -- el ensayo del
Bloque 5 (mismo día) midió el dolor pero abortó a propósito en el
primer conflicto real, sin completarlo. Esta sesión cerró esa vuelta
pendiente de verdad.

**Ejecución:** worktree `~/hermes-019`, rama desechable nueva
`fase2-cierre-rebase` (creada sobre `arturo/base`, que ya estaba en
producción desde el corte de Bloque 6 -- nunca se volvió a tocar
producción). `git fetch origin main`: 761 commits nuevos desde el corte
de hoy, 47 aplicables por delante de `arturo/base`.

**El único conflicto real, resuelto siguiendo el procedimiento (no
"tomando lo que parecía más nuevo"):** commit 8/47, mismo archivo punto
caliente de siempre, `plugins/platforms/telegram/adapter.py`, contra el
propio commit `b64e6b9ac` (i18n español de los botones de aprobación).
Upstream reorganizaba el layout (2x2 en vez de fila única, arregla
truncamiento en móvil); el commit propio traducía las etiquetas al
español. **No competían** -- se combinaron los dos: layout de upstream
+ texto en español, ningún arreglo se perdió. Efecto real en pruebas:
`tests/gateway/test_telegram_approval_buttons.py` tenía 5 aserciones
con las etiquetas viejas en inglés de upstream -- actualizadas a las
etiquetas reales en español (mismo criterio que el propio commit de
i18n ya establecía). Detalle completo, con el análisis de qué hacía
cada lado, en `~/hermes-019/docs/MIGRATION_LOG.md`.

**Resultado:** 47/47 commits aplicados, un solo conflicto real, 0
errores de sintaxis en todo el árbol, 29/29 smoke tests, 26/26 de la
prueba afectada tras el ajuste. Riesgo a producción: CERO -- rama
desechable, nunca se tocó `arturo/base` ni `~/.hermes/hermes-agent`.
Adoptar estos 47 commits a producción queda como decisión FUTURA
separada (no requerida para cerrar la verificación -- el criterio es
que el PROCEDIMIENTO funcione de punta a punta, no mantenerse siempre
al día).

**Con esto, HAS Fase 2 (Blindaje y actualización) queda CERRADA por
completo** -- los 5 entregables de `docs/HAS.md` (migración por
archivo, venv paralelo + rebase, 10 smoke tests, skill
`hermes-upgrade`, producción cambiada con rollback listo) y los 2
criterios de verificación E2E (smoke tests en el venv nuevo; una
actualización futura simulada resuelta sin intervención creativa)
confirmados con evidencia real. Actualizado también el punto caliente
de la skill `hermes-upgrade` con el patrón real encontrado (3er rebase
con conflicto en el mismo archivo, ahora con la resolución ya
documentada para la próxima vez).

**Con Fase 2 cerrada, sigue Fase 3 — Ciclo de vida de skills** (136
skills, ~2 semanas estimadas), por pedido explícito de Arturo.

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

## Bloques AI/AJ/AK/AL/AM — jornada de rendimiento (30 Jul 2026) — **CERRADOS**

Peaje fijo por vuelta del agente: **~65,000 → ~19,100 tokens (71% menos)**.

**Hallazgo central, y es el que hay que recordar:** el costo fijo del
prompt NO se paga una vez por mensaje — se paga **una vez por iteración**.
Un "Hola Hermes" con voz dio 3 vueltas de ~70k = 219,930 tokens = 88% del
límite por minuto de Gemini free tier. Cualquier optimización del prompt
se multiplica por el número de vueltas; cualquier derroche también.

- **AI** — recorte de herramientas en turnos triviales (44 → 4).
- **AJ** — la hora local entró al prompt. No existía herramienta de tiempo
  en la instalación, pese a que el comentario de upstream asume que sí.
- **AK** — MEMORY.md como índice (25,475 → 848 tok) + `memoria_indexador.py`
  ahora indexa MEMORY.md/USER.md por secciones (`source='memory_md'`).
- **AL** — USER.md como índice (usa separadores `§`, no `##`); fuera
  `browser`/`computer_use`/`delegation` de Telegram tras consultar el HAS
  (cero menciones) y el uso real (0 de 1,125 llamadas).
- **AM** — toolsets ocasionales bajo demanda. `kanban` NO se elimina: el
  HAS lo pone como pieza central de Fase 5.

**Método que vale repetir:** todo se midió contra datos reales antes de
tocar nada — `sessions.system_prompt` en `state.db` para el peso real del
prompt, el `cost_ledger` para tokens por llamada, y `messages.tool_calls`
para saber qué herramientas usa Arturo de verdad (1,125 llamadas: 21
herramientas distintas de 44 cargadas). Tres hipótesis mías murieron en
el camino por medirlas: los archivos de contexto (1,151 tok, no 60,000),
la memoria del `MemoryManager` (0 tok) y el caché de prefijos (sí se usa:
7.4M tokens de hit — por eso la hora se puso en la parte volátil y no
arriba).

**Regla de diseño que sale de aquí:** al recortar herramientas el riesgo
es **asimétrico**. Gastar tokens de más es molesto; dejar a Hermes sin una
herramienta que necesitaba le rompe la tarea a Arturo. Todo recorte va
con disparadores generosos y "ante duda, mandar todo".
