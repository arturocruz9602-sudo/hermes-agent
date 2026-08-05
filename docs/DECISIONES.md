# DECISIONES — memoria técnica permanente de Hermes (v1.1, 01 ago 2026)
**Regla: toda decisión aquí es FINAL salvo evidencia nueva escrita. Claude Code consulta este archivo
antes de proponer cambios de arquitectura. Reabrir una decisión cerrada sin evidencia nueva = falla de protocolo.
Formato: fecha · decisión · motivo · impacto. Append-only.**

---

**22 jul 2026 · Heurísticas de juicio → rúbrica evaluada por modelo (JSON), no listas de condiciones en
Python.** Motivo: whack-a-mole del 22 jul. Impacto: patrón vigente para todo gate nuevo.

**23 jul 2026 · Claude Code es el centro de trabajo diario; claude.ai es consultor eventual.** Impacto:
arranque autónomo; el chat de diseño no emite bloques sin ESTADO del día.

**27 jul 2026 · Editar skills es privilegio de quien pase la compuerta F2v2.** Impacto: `normal` de punta
a punta; `critico` solo diff.

**29 jul 2026 · Obsidian local base de conocimiento + espejo solo-lectura a Notion.** Impacto: escritura
solo en Obsidian; Notion nunca es fuente de verdad.

**30 jul 2026 · DeepSeek v4-flash llave principal de chat; Gemini en `chat-gratis` para lo automático.**
Motivo: 429 de Gemini; costo real ~8 MXN/mes. Impacto: "nunca DeepSeek automático" intacta vía alias.

**30 jul 2026 · max_turns=25 + hard_stop + reasoning_effort=none en chat-primary.** Motivo: 97.5% del
costo histórico fue de 5 sesiones desbocadas. Impacto: techo duro; ~45% menos razonamiento (6 muestras).

**30 jul 2026 · El router de modelos NO se crea de cero: se centraliza el existente** (`image_routing.py`,
`complexity_detector.py`, `turn_finalizer.py:978`). Impacto: refactor, no componente nuevo.

**31 jul 2026 · Se cancela la API de Google Classroom.** Motivo: los avisos llegan por correo. Impacto:
el frente escuela se cubre analizando correo.

**31 jul 2026 · Ningún dato personal de Arturo a APIs gratuitas** (Gemini free entrena con el contenido).
Impacto: personal → local o proveedor con términos verificados. Matiz de sensibilidad: ver entrada 01 ago.

**31 jul 2026 · Adaptador de correo APAGADO hasta blindarlo** (solo-lectura + EMAIL_ALLOWED_USERS;
jamás la bandeja histórica de 4,223).

**31 jul 2026 · Laboratorio Docker regla permanente (HAS §F11).** Impacto: toda migración de esquema se
prueba en lab antes de producción (F11-e); los 5 roles solo corren ahí (F11-d).

**03 ago 2026 · E14 (ventana de mantenimiento nocturna) reusa `cola_v2` como persistencia, no inventa
cola nueva.** Motivo: E14 ya declaraba `depende_de: F5-2` en `loop_cola.py`; la garantía dura de F5-2
(toda tarea termina `notificada` o `atorada`+aviso, nada se pierde en silencio, cada intento en
`task_queue_log`) cubre exactamente el requisito "ejecutar con evidencia" del bloque, con 11/11 pruebas
ya verdes. Impacto: `scripts/ventana_mantenimiento.py` solo aporta el gate horario 2:00-5:00 + gate
térmico (r.103) + las fuentes de candidatos (hoy: skills stale §F5/§E3); reportar/conteo se filtra por
`chat_id="ventana_mantenimiento"` para no mezclarse con otros usos reales de la misma tabla compartida.

**31 jul 2026 · Reset de memoria a cero** (orden explícita; respaldos pre-wipe en seagate). Confirmado
01 ago (r.94): NADA se restaura, todo desde cero. Memoria solo vía `memory_tool.py`.

**31 jul 2026 · YouTube Analytics por OAuth conectado a HERMES, no a Claude Code.** Avisar si el token
vence; nunca fallar en silencio.

**31 jul 2026 · Publicar en YouTube nunca automático.** Hermes prepara; Arturo da el "sí, súbelo".

**31 jul 2026 · Edición creativa autónoma NO se promete; render automático SÍ.** Primera skill de edición
aprende del proceso real de Arturo (ya capturado en r.49-50 del cuestionario).

**31 jul 2026 · Ollama en la HP solo lotes nocturnos** (i3 sin GPU, calor, gemma:2b reprobó). El músculo
local futuro es la M1 por Tailscale.

**01 ago 2026 · Reestructura documental** (ESTADO ≤80 sobreescrito · BLOQUES índice · DECISIONES ·
archivo · tarea única con elección de impacto UNA vez al abrir sesión). Motivo: 550 KB de arranque
reproducían "Hola Hermes" en el propio flujo. Impacto: gate `wc -l ≤ 80` al cierre.

---
## Del cuestionario respondido (01 ago 2026) — la voz directa de Arturo

**01 ago · REGLA DE SIMULACIÓN (r.20) — la más importante del día.** Todo dato de fechas, pagos, citas,
eventos mencionado durante pruebas es SIMULADO salvo que Arturo marque explícitamente "dato real que va a
memoria permanente". Claude Code queda autorizado a inventar escenarios completos (fechas, gastos, viajes,
tareas) y a adelantar el reloj artificialmente — SOLO dentro del laboratorio. Nada simulado toca producción,
calendario real ni memoria permanente (ya era F11-f; ahora con autorización explícita ampliada). Impacto
inmediato: **la "colegiatura del 27 de abril" queda ANULADA como dato real** — era ejemplo. La captura
espontánea en producción sigue: siempre preguntar "¿lo agendo?" antes de crear nada (r.89).

**01 ago · Meta financiera nueva (r.28-31, 35) — INVALIDA los números de E10.** Objetivo: capital de
100,000 MXN (piso 90,000) para el 31 de Diciembre 2027. Saldo actual: 0. **Mac Mini DESCARTADA**; Mac
Studio se compraría DESDE el capital cuando él decida, con rastreo de precios/promos por Hermes. Moto:
futuro sin monto. Depósito objetivo 3,500 MXN/mes provisional, se recalibra con datos reales. Sin deudas;
sin fondo de emergencia separado (el capital es el fondo). Impacto: reescribir HAS §E10 (v1.7) con estos
números; el reporte de rieles pasa a SEMANAL (r.18).

**01 ago · Fuente de ingreso nueva: venta de refrescos (r.16).** Caja 328 MXN/24 pzas, venta 20 MXN/pza,
Coca-Cola y Yoli, patrón desconocido. Impacto: tabla `ingresos` la registra por separado; Hermes detecta
el patrón y reporta cuánto deja realmente.

**01 ago · Correo evoluciona (r.62-64, 67, 107-108).** Sigue solo-lectura, pero el destino aprobado es:
analizar → avisar prioritarios (banco, compras, eventos, TODO lo escolar con entrega) → sugerir qué hacer
→ (futuro F6) BORRADOR de respuesta + ejemplo + autorización explícita por correo, jamás envío automático.
Ruido definido: notificaciones de "alguien comentó/compartió". Pendiente: direcciones exactas de las 2 cuentas.

**01 ago · Gemini Live / modo llamada: DESCARTADO (r.99).** Motivo: ya no lo necesita; notas de voz bastan.
Sustituto: alertas críticas en iPhone vía Telegram (vibración tipo llamada) para emergencias y olvidos.
Impacto: OT-9.5 se archiva; se libera el proyecto de Google dedicado.

**01 ago · La M1 es PRESTADA (r.102).** Toda configuración nocturna (caffeinate para render) se aplica →
se usa → se REVIERTE antes de las 06:00 → se verifica revertida. La Mac queda exactamente como estaba.
Impacto: el script de render nocturno nace con reversión obligatoria y verificación.

**01 ago · Gate térmico de la HP (r.103).** Claude Code monitorea temperatura durante corridas de prueba
y PAUSA hasta que baje. Impacto: check de `sensors` antes y durante cada corrida del laboratorio.

**01 ago · Enrutamiento clarificado por Arturo (r.91).** DeepSeek comanda a Hermes; las llaves de Gemini
para VISIÓN y VOZ son intocables en su rol; las demás gratuitas (Gemini extra, Groq, OpenRouter) absorben
tareas repetitivas para no gastar DeepSeek. Matiz de privacidad PENDIENTE de su confirmación (propuesta
default: montos/tickets sí a gratis; correos completos, nombres y salud no).

**01 ago · Presupuesto de contexto como prueba permanente del arnés (preocupación P2 de Arturo).** Techo
de tokens de prompt por tipo de llamada (base 30 jul: 19.1k/vuelta); medición con ≥3 muestras en cada
corrida de laboratorio; exceder el techo = suite en rojo, mismo trato que un bug funcional. Impacto: la
eficiencia deja de ser optimización eventual y se vuelve regresión vigilada.

**01 ago · Trading (r.36-43).** Laboratorio testnet arranca lo antes posible dentro de la ventana. Binance
verificada sin fondos; Bitso pendiente. Lista blanca BTC/ETH/USDT+SOL se mantiene salvo que el laboratorio
DEMUESTRE mejor con datos. Dinero real: sigue atado a los criterios de B4 (2 meses de papel medido) y a
propone-y-apruebas SIEMPRE — **las expectativas de rendimiento se calibran con los resultados reales del
laboratorio, no al revés** (ver nota de expectativas en el chat del 01 ago). Hermes reporta números reales,
nunca promete rendimientos. Apagado -3% diario: pendiente de confirmación tras explicación.

**01 ago · Pruebas masivas SOLO en Docker con la cuenta QA (r.119).** Producción y el Telegram real de
Arturo no reciben tráfico de prueba. Impacto: el arnés apunta al contenedor; la cuenta QA vive dentro del
flujo de laboratorio.

**01 ago · Laboratorio Docker OPERATIVO y respaldos VERIFICADOS (Bloque AQ).** Imagen `hermes-agent:latest`
construida; respaldo `20260731_040925` restaurado en volumen aislado con `integrity_check` = ok en state.db
y memoria_semantica.db; smoke del código real + arnés host 57/57. Motivo: F11 exigía la primera corrida real
(hasta hoy el lab nunca había corrido). Impacto: (1) toda migración de esquema de AR en adelante se prueba
aquí antes de producción (F11-e); (2) queda probado por primera vez que los respaldos de Arturo restauran;
(3) **gate térmico** se implementa leyendo `/sys/class/thermal/*/temp` (sin `sudo`; `lm-sensors` requeriría
sudo), umbral 85°C — pico real del build 59°C.

**01 ago · Privacidad RESUELTA (r.91, confirmada por Arturo).** A APIs gratis (Gemini-extra/Groq/OpenRouter)
SÍ pueden ir **montos y tickets** (números de dinero). **NUNCA a APIs gratis:** correos (contenido y
direcciones), **contraseñas**, nombres, datos de salud, y cualquier dato que vulnere su seguridad en la red.
Las contraseñas no se guardan en ningún lado (r.92). Impacto: cierra el matiz que quedó abierto el 31 jul; el
router puede mandar montos/tickets a gratis, lo demás va a modelo local o proveedor de paga con términos
verificados de no-entrenamiento.

**01 ago · Trading — dirección de ENTRENAMIENTO (r.36-43, ampliada por Arturo).** Simulación en testnet con
capital de hasta **5,000 MXN**, ciclos **SEMANALES**. Estrategia a entrenar: cruzar caída de precio con
señales de noticias/web — si una cripto cae pero las noticias apuntan a que sube en la semana, se arriesga
(buy-the-dip informado por sentimiento). Meta declarada **2,000 MXN/semana = OBJETIVO de entrenamiento, NO
promesa** (guardrail vigente: Hermes reporta números reales, jamás promete; las expectativas se calibran con
los resultados del laboratorio). Primero entrenar el modelo; incluye **investigar en la web las mejores
estrategias** (parte de AT). Freno **-3% diario**: sigue SIN confirmación explícita — coexiste con la
estrategia (protege el capital, no la contradice).

**01 ago · La libreta vive en `libreta.db`, no en state.db (Bloque AR).** Hallazgo: la libreta YA existía
(17 tablas, clase `Libreta` con separación real/simulación + reloj virtual, sistema de migraciones propio).
Corrige el SEED/ESTADO que decían "state.db". Migración **v4** reconció los datos con el cuestionario del
01 ago (gym 500, moto 550, recarga_telefono 230, +deepseek/+gasolina, **meta capital $100k** 31-dic-2027 Mac
Mini descartada, colegiatura $1,200 inflada como colchón por Arturo, peso 111.5, 6 hábitos). Validada en copia
aislada + contenedor F11-e, aplicada a producción con respaldo previo y aprobación de Arturo (F7.2). Impacto:
toda captura de vida de Arturo pasa por la clase `Libreta`; `state.db` no se toca.

**01 ago · `libreta.db` entra al respaldo (Bloque AR, bug de data-safety).** El respaldo nocturno solo cubría
state.db + memoria_semantica.db; la libreta (finanzas, peso, agenda de Arturo) corría sin red. Agregada a
`respaldar_memoria.py::DEFAULT_DB_NAMES`. Impacto: los datos de vida de Arturo ya se respaldan y verifican
(integrity + conteo) cada corrida.

**01 ago · Trading: freno de emergencia -3% diario CONFIRMADO (r.40).** Arturo, textual: "que quede así -3%".
Si en un día el capital acumula -3% de pérdida, Hermes se detiene y avisa (con $2,000 reales = apagado al
perder $60). Impacto: es el circuit-breaker duro del laboratorio testnet (AT) y de cualquier operación real
futura; coexiste con la estrategia news-driven (esta busca ganar, el freno solo evita el día catastrófico).

**01 ago · La migración v4 NO se edita tras aplicarse; los tests se hicieron precisos (Bloque AR, /loop).**
v4 siembra datos base en toda BD migrada, lo que rompía 2 tests que contaban la tabla completa. En vez de
editar una migración ya aplicada (prohibido por el runner), los tests ahora verifican solo la fila que crean
(`WHERE nombre=...`) — que es exactamente lo que prueban ("no duplica por nombre"). 49/49 en verde.

**02 ago 2026 · Capa de confiabilidad para loop autónomo: chequeos de arranque como hook SessionStart +
cierre como skill `/cierre` (Bloque AV).** EXTIENDE la reestructura documental del 01 ago (arranque ligero),
no la reabre: mismo objetivo (menos contexto siempre-residente, menos "Hola Hermes"). Los chequeos
DETERMINISTAS del arranque (git, L11, TEMP-DIAG, salud, uptime/reboot, tmux, tapa, gate ESTADO≤80, temp HP)
pasan a `.claude/hooks/hermes-arranque.sh` (SessionStart, versionado en el repo, `exit 0` siempre, tolera
gsettings sin D-Bus); su stdout se inyecta como contexto y dispara también en `/clear`. El cierre de 6 pasos
pasa a la skill `.claude/skills/cierre`. Motivo: un loop autónomo AMPLIFICA el olvido (r.115 "lo peor:
olvidar y autosabotear") — estos pasos no pueden depender de que Claude los teclee. El juicio (leer
MANDATO/ESTADO, elegir tarea, saludar, qué escribir) sigue siendo de Claude; el hook solo junta datos. NO se
usan subagentes-por-modelo para trabajar: B10 sigue vigente (perfiles = skills, escritura en sesión
principal, subagentes solo lectura). Hallazgo corregido: la salud se mide en scope **`--user`** (gateway/
litellm son user-units); el `systemctl is-active` SIN `--user` de CLAUDE.md pt.5 reporta 'inactive' con
producción ENCENDIDA — el hook usa el scope correcto. Impacto: es la base del orquestador con ruteo de modelo
por dificultad (Sonnet simple / Opus complejo), siguiente paso del loop que Arturo mira por SSH+tmux.

**02 ago 2026 · Loop autónomo: los bloques corren con `--permission-mode bypassPermissions`; la
red es el hook `hermes-guard` (AUTORIZADO por Arturo, textual: "Si autorizo").** `orquestar.py` corre
cada bloque con `claude -p --model <X>` en bypassPermissions para trabajar sin trabarse pidiendo
confirmación en cada archivo/comando. La RED DE SEGURIDAD es el PreToolUse `~/.claude/hooks/hermes-guard.sh`
(hard-deny de rm -rf, git push --force, DROP/DELETE SQL directo, curl|bash, instalaciones sin versión
fija, escritura directa a credenciales), que se dispara SIN importar el modo de permisos. Ruteo por
dificultad con los 3 Claude (Haiku/Sonnet/Opus); la escalera gratis (Gemini/Groq/OpenRouter) es de
HERMES en runtime, NO del loop (r.91). Gasto medido por bloque en `scripts/loop_tokens.jsonl`; freno
manual `scripts/.loop_alto`; gate térmico r.103 (>85°C pausa); estado reanudable en `.loop_estado.json`.
Impacto: el loop puede construir el proyecto sin supervisión; Arturo lo mira por SSH+tmux y lo frena
cuando quiera. Costo medido: cada sesión anidada paga ~$0.03-0.04 solo por cargar el contexto (peaje a
optimizar). Verificado inocuamente antes de correr real (`orquestar.py probar`).

**02 ago · Trading AT — la señal es un CRUCE de 3, no dip a secas (r.36-43).** Investigación web (02 ago):
comprar la caída sola rinde mal (se queda invertido dentro de bear markets). Por eso la entrada de
`trading_entrenador.py` exige TRES condiciones juntas: (1) caída ≥umbral vs. referencia, (2) RSI<30
(agotamiento/sobreventa, confirma pullback y no caída libre), (3) score de sentimiento alcista (r.91: a
gratis solo van números, un score numérico es apto). El freno -3% diario (r.40) es un circuit-breaker
INDEPENDIENTE de la estrategia. Arquitectura: mercado y sentimiento son puertos INYECTABLES → el módulo no
toca red por sí mismo (r.119, host con creds de prod sin QA); el cliente `MercadoBinanceTestnet` (python-binance
testnet=True) queda cableado pero exige keys+laboratorio para correr en vivo. Capital simulado con tope duro
5000 MXN. Impacto: AT cierra como entrenador probado localmente; el dinero real sigue atado a B4 y propone-y-apruebas.

**02 ago 2026 · Pipeline de clips (AU-2): el clip ES un guion corto grabado.** El corto ≤2min
se registra en la MISMA tabla `guiones` de AU-1 (estado 'grabado'), no en una tabla nueva:
comparte ciclo (idea→guion→grabado→publicado) y evita duplicar esquema. El tope de 2 min (r.48)
se defiende en el DATO (`ClipCandidato` revienta si dura >120s), no solo en el extractor —
imposible que un clip fuera de norma llegue a programarse. Extracción: enumera todas las
ventanas de segmentos y prefiere la más COMPACTA a igual valor (un clip denso de 40s vale más
que uno de 120s con relleno). Horarios: pesos por día/hora anclados en investigación 2025-2026,
CRITERIO ajustable cuando llegue el Analytics real del canal (no gate ciego). OAuth vive en
HERMES (DECISIONES 31 jul); publicar exige `aprobado=True` explícito de Arturo (r.59) — el
cliente de red es inyectable y queda cableado pero pendiente del OAuth de 5 min.

**02 ago 2026 · Corte de silencios (AU-3): la verificación §E6 es parte del corte, no un extra.**
El fallo real de r.49 (la IA toma la cola de una consonante final por silencio y la recorta)
se modela explícitamente con `cola_ms` por palabra: el corte se ACEPTA solo tras verificar 0
palabras perdidas y WER≤2% (§E6); si falla, relaja umbral+3dB/padding+50ms (máx 3 iter) y, si
aun así falla, entrega el ORIGINAL con "no pude cortar sin riesgo" — nunca un corte que destruye
habla. El Whisper de verificación es INYECTABLE (oráculo determinista en el laboratorio, r.20).

**02 ago 2026 · La M1 prestada se protege con TRIPLE candado (AU-3, r.102), no con un flag.**
`SesionM1` garantiza que la Mac queda como estaba con: (a) reversión en `finally` — ocurre aunque
el trabajo lance a media noche; (b) verificación de que revirtió — si no, `ReversionError`, alarma
dura, nunca en silencio (regla 3); (c) auto-expiración del lado de la Mac (`caffeinate -t` con los
segundos hasta las 06:00) — si Hermes muere sin `__exit__`, la config igual se cae sola. La edición
de timeline es SIN render (proyecto abierto para revisión, OT-8); el render SÍ es automático (r.102)
pero solo dentro del envelope (con caffeinate) y en ventana — es el paso pesado que calienta la Mac.
Impacto: Hermes puede editar de noche en la Mac de Arturo sin riesgo de dejarla tocada o sin batería.

**03 ago 2026 · YouTube: SE OCUPAN LAS DOS llaves — resuelve la contradicción de la sesión 31 jul, sin
ambigüedad.** Hallazgo previo (subagente Explore, 03 ago): en la sesión `159c6f15-...` (31 jul) Claude
Code se contradijo a sí mismo — primero dijo que el OAuth (login de Arturo, conectado a HERMES) sustituía
por completo a la API key pública de YouTube Data API v3 (Google Cloud Console), 35 min después dijo que
hacían falta ambas, y quedó sin resolver en el código (`pipeline_clips.py` solo cablea un OAuth). Arturo
CONFIRMÓ explícitamente (03 ago): **se necesitan las DOS.** (1) **API key pública** (Google Cloud Console
→ APIs y servicios → Credenciales → Crear credenciales → Clave de API) — para datos de canales públicos.
(2) **OAuth** (login de Arturo, conectado a HERMES no a Claude Code, ya decisión previa) — para datos
privados del propio canal (vistas, monetización) y para publicar. Impacto: AU-2/`pipeline_clips.py` debe
cablear AMBAS credenciales, no solo el OAuth; pendiente de que Arturo las saque (~10 min, ver ESTADO.md).

**03 ago 2026 · Canal QA de Telegram: YA EXISTÍA — no era una cuenta nueva por crear.** Corrige el hallazgo
del 02 ago (que decía "sigue sin existir, bloquea AS-2/AT/docker_qa"). Arturo confirmó y Claude Code
verificó en `state.db::gateway_routing`: cuenta "Hermes QA De La Cruz", `chat_id=8727618189`, mismo bot
`@ArturoHermes_bot`, sesión registrada desde 2026-07-24T10:36:39 — once días antes de que se reportara
como faltante. Impacto: el candado r.119 que bloqueaba envío real en AS-2/AT/bloques `docker_qa` se
resuelve con `TELEGRAM_QA_CHANNEL=8727618189` en `.env` (pendiente de confirmación explícita de Arturo
para tocar ese archivo, regla dura de CLAUDE.md "tocar .env... siempre" pregunta). Lección: antes de
declarar "no existe" un recurso, buscar más a fondo en el propio sistema (aquí, `state.db`) antes de
asumir que hace falta crear algo nuevo.

**03 ago 2026 · Ítem 19 resuelto: `media_files`/`retention_class=permanent` NO existía — no había nada
que rehacer.** Verificado en este bloque (F7-1, OT-7): `~/.hermes/state.db` (la BD real del gateway)
tiene 27 tablas y ninguna se llama `media_files` ni tiene columna `retention_class`; el `state.db` en la
raíz del repo (plantilla) está vacío. Lo que HAS §Fase 1/E1 describía como "ya creado" nunca se
implementó para el uso personal de Arturo — es la misma clase de hallazgo que el canal QA de Telegram
arriba: verificar en disco antes de asumir. Impacto: F7-1 crea la tabla `archivos` (equivalente a
`media_files`, con `retention_class` desde el día uno) en `libreta.db` vía migración v6, NO en
`state.db` — sigue el mismo patrón que `gastos`/`horario`/etc: la vida de Arturo vive en la libreta,
`state.db` es del gateway y no se toca para esto (ver `libreta_migrar.py` docstring).

**04 ago 2026 · Criterio de alarma del watchdog: manda el PRINCIPAL, no la escalera gratuita.** A partir
del Bloque AN (30 jul) `chat-primary` es `deepseek-v4-flash` y Gemini/Groq/OpenRouter son RESPALDO. Por
tanto, un 429 en los logs de LiteLLM **ya no es evidencia de caída**: la escalera gratuita cayéndose es
el diseño funcionando. Regla cerrada (P3): el watchdog alerta a Arturo y marca pausa **solo si cae toda
la escalera, DeepSeek incluido**; si el principal responde (`is_deepseek_ok`), lo resuelve en silencio y
lo deja en su log. Vale para cualquier alarma futura de disponibilidad, no solo esta: la pregunta
correcta es "¿el principal responde?", no "¿algún proveedor devolvió 429?". Esto es aplicación directa
de la regla de Arturo "no quiero estar viendo problemas, yo me estreso; que solo siga resolviendo sin
que me entere" — la misma que originó el fix del 30 jul (ledger <240s). Corolario operativo: cuando
cambie el modelo principal, hay que revisar el watchdog en la misma sesión — es la segunda vez que se
queda con una idea vieja de quién es el principal.

**04 ago 2026 · Correo escolar: alerta de frescura (P5) SIN Telegram por default — mismo principio que
el watchdog.** La primera vez que la alerta de P5 disparó de verdad (buzón 4.1h sin tocarse) resultó ser
falsa: Thunderbird estaba vivo y conectado (socket IMAP establecido), simplemente no había correo nuevo.
Arturo, textual: "como tal no quiero avisos, lo único que quiero es que cuando llegue el correo me
avise". Aplica el MISMO principio ya documentado arriba (30 jul, watchdog): no quiere ver problemas de
infraestructura, solo resultados. Impacto: `AVISAR_FRESCURA_POR_TELEGRAM = False` en
`vigilar_correo_escuela.py` — la detección y el log siguen intactos (así se ve en diagnóstico si hace
falta), pero no se manda nada por Telegram. Interruptor documentado en el propio código para reabrir con
evidencia nueva si algún día vuelve a fallar en silencio varios días sin que Arturo lo note primero.
Además, Arturo especificó el FORMATO exacto que sí quiere para correos reales (no para salud): "te llegó
tal correo, es una tarea para hoy a las 11, ¿qué quieres que realice?" — analizar contenido + preguntar
acción, nunca asumir. Ya incorporado a la guía de F6-3 en `scripts/loop_cola.py`.

**04 ago 2026 · F6-3 — el seguimiento de r.64 (aviso antes/después de la hora límite) usa un JSON propio,
NO `cola_v2.py`.** El mapa de reuso del bloque sugería reusar `cola_v2` (garantía dura
encolada->resuelta->notificada) para no inventar "un sistema de recordatorios nuevo". Al implementarlo se
encontró que no encaja: `cola_v2.procesar_pendientes()`/`procesar_una()` toman una tarea `encolada` y la
resuelven YA, con una escalera de proveedores (solver inyectable) — no existe un campo "no antes de esta
hora" en su esquema ni en su máquina de estados, y agregarlo tocaría infraestructura compartida por otros
bloques (F9-2, E14) fuera del alcance de esta sesión. `cola_v2` es la herramienta correcta para "esto hay
que resolverlo YA con reintentos", no para "avisa en un momento futuro de reloj de pared". Se optó por un
JSON de pendientes en `scripts/vigilar_correo_escuela.py` (`SEGUIMIENTOS`), mismo patrón ya usado en ese
archivo para `SALUD`/`vistos` — sin nueva arquitectura, solo el patrón existente aplicado a un tercer
estado. Si en el futuro aparece más de un caso de "recordatorio a hora futura" (HAS §OT-9 ya menciona una
`tabla reglas_recordatorio` pendiente, sin construir), vale la pena evaluar un motor de recordatorios
programados compartido — hoy solo hay un consumidor real, no amerita esa inversión todavía.

**04 ago 2026 · Gotcha de IMAP "UID N:*" con N mayor al máximo real — filtrar SIEMPRE del lado del
cliente, nunca confiar en que el servidor respetó el rango (P7).** Hallazgo real (reportado por Arturo:
el mismo correo se avisó 3 veces) y reproducido en vivo contra Gmail: cuando `desde_uid` ya es el UID más
alto del buzón, `imap.uid("SEARCH", None, f"UID {desde_uid+1}:*")` NO regresa vacío — RFC 3501 define "*"
como el UID más grande que exista, así que el servidor regresa ese último correo de todos modos, sin
importar si el rango pedido lo excluye. Cualquier código futuro que use rangos `N:*` de IMAP (no solo
`vigilar_correo_personal.py`) debe filtrar los UIDs devueltos con `> desde_uid` del lado del cliente antes
de procesarlos — el servidor no es de fiar en este caso límite. Impacto: patrón a reusar si se agrega otro
vigilante de correo por IMAP en vivo (el escolar no aplica, usa un mbox local con set de "vistos", no UID
ranges).

**04 ago 2026 · CORRECCIÓN: `.env` línea 503 NO está corrupta — es el app password legítimo de Gmail;
NUNCA limpiarla.** El hallazgo del loop (03/04 ago: "línea 503 corrupta, escupe `zxei: orden no
encontrada`") fue un mal diagnóstico, señalado por Hermes y verificado directo en el archivo (sin
mostrar el valor): `EMAIL_PASSWORD`, 19 caracteres, forma `XXXX XXXX XXXX XXXX` — exactamente el formato
de un App Password de Google (16 caracteres en 4 grupos de 4). Causa real del error: `watchdog.sh` lee
`.env` con `source` SIN comillas; bash, al toparse con espacios dentro de un valor sin comillas, trata
cada palabra como un token nuevo — la primera palabra queda asignada a `EMAIL_PASSWORD`, pero las
siguientes palabras del password se intentan EJECUTAR como comandos, de ahí "orden no encontrada". El
dato nunca estuvo corrupto; el bug (si vale la pena arreglarlo) está en cómo `watchdog.sh` carga el
archivo, no en el archivo mismo. Impacto: (1) esta línea NUNCA se toca — borrarla rompería la
autenticación real del vigilante de correo personal (P6/P7); (2) si se quiere silenciar el ruido en
`watchdog.log`, la corrección correcta es citar la variable al hacer `source` (`set -a; source .env; set
+a` o exportar con comillas), no editar el valor. Lección (misma que ya dejó P3): un hallazgo de "dato
corrupto" reportado por un log de error necesita verificarse contra el archivo real antes de proponer
limpiarlo — un síntoma de parseo se puede confundir con datos corruptos.

**04 ago 2026 · EXCEPCIÓN ACOTADA a r.91: fotos de horario escolar SÍ pueden ir a Gemini Vision gratis
(nombres de profesores incluidos), confirmada por Arturo.** La regla general de r.91 sigue intacta en
todo lo demás: "NUNCA a APIs gratis: correos, contraseñas, **nombres**, salud". El horario trae nombres
reales de 7 profesores — Claude Code lo marcó como contradicción antes de actuar (no lo pasó por alto) y
preguntó explícitamente; Arturo confirmó la excepción con conciencia de la contradicción, eligiendo la
opción "(a) excepción puntual acotada" sobre "(b) mantener la regla, esperar tier de pago". Acotada al
string EXACTO del caso de uso: **fotos de horario escolar para `horario_por_foto.py`** — no es una puerta
abierta a nombres en general en ningún otro flujo (correo, tickets, etc. siguen bajo la regla original sin
cambio). Impacto: `extractor_gemini_vision()` en `scripts/horario_por_foto.py` queda cableado al alias
`vision` de LiteLLM (`gemini-2.5-flash`, `GEMINI_VISION_KEY_NEW`, cuota propia). Verificado en vivo contra
la foto real de Arturo (Grupo 301 DSM, UTRNG, mayo-agosto 2026): 18/18 clases extraídas correctamente,
nombres de profesores incluidos, sin tocar la libreta (`--foto` sin `--aplicar`).

**04 ago 2026 · Hallazgo de eficiencia: `thinking_config: {"thinking_budget": 0}` en llamadas de extracción
simple a Gemini 2.5 — sin esto, ~95% del presupuesto de tokens se va en "razonamiento" interno que no
hace falta.** Encontrado al cablear `extractor_gemini_vision()`: la primera llamada con `max_tokens=2000`
cortó el JSON a medias (`finish_reason=length`) — el desglose de `usage` mostró `reasoning_tokens=1917` de
2000 totales, dejando 79 para el texto visible. Es un modelo de "pensamiento" por default (gemini-2.5-flash),
y una tarea de puro OCR/transcripción de tabla no necesita razonar. Con `thinking_config.thinking_budget=0`
(parámetro ya soportado por `agent/gemini_native_adapter.py::_normalize_thinking_config`, vía `extra_body`
del lado del cliente o directo en el body del lado del proxy): 0 tokens de razonamiento, respuesta completa
en ~7s en vez de agotar el límite o expirar por timeout. Impacto: cualquier llamada FUTURA a un modelo
Gemini "thinking" para una tarea mecánica (extracción, clasificación, OCR — no las que sí necesitan
razonar) debe evaluar este parámetro antes de simplemente subir `max_tokens` a ciegas; subir el límite sin
apagar el razonamiento solo tapa el síntoma y es más lento/caro.

**04 ago 2026 · F11-2 (USB-llave) CORREGIDO: agente Go por Telegram/ntfy.sh, NO VeraCrypt+Tailscale+SSH
a equipos ajenos.** Hermes señaló que la implementación de F11-2 (`usb_llave/start-linux.sh`,
`scripts/registro_autorizacion_terceros.py`) se desvió del diseño aprobado en el skill
`hermes-portable-usb` (~/.hermes/skills/hermes-tools/hermes-portable-usb/SKILL.md +
references/arquitectura-final.md). Verificado ANTES de aceptar (no de fe): el skill existe con las 7
reglas exactas citadas, y el agente+gateway en Go YA estaban escritos y compilados desde julio (hallazgo:
vivían sin control de versiones en `~/Desktop/hermes_portable/`, tamaños de binario coincidentes con lo
reportado). Diseño real, confirmado por Arturo: la USB conecta Hermes a CUALQUIER PC/laptop/SO ajeno con
unos clics, dando órdenes desde Telegram — no es una bóveda que levanta Tailscale/SSH. Reglas duras: (1)
agente Go, binario único cross-compile Linux+Windows+macOS, sin dependencias externas; (2) transporte
Telegram Bot API (sin puertos) + ntfy.sh para señales máquina-a-máquina (Telegram bots NO pueden verse
entre sí por diseño de la API — esto invalidó un diseño anterior, ver `arquitectura-final.md`); (3)
memoria/contexto SIEMPRE en la HP, la USB nunca es el cerebro; (4) agente propone → botón inline en
Telegram → ejecuta, nunca comandos manuales; (5) **Tailscale limitado a HP+Mac+iPhone; equipos ajenos
SOLO por Telegram, sin SSH, sin Tailscale en la USB**; (6) al retirar USB: resumen+limpieza; al
reinsertar: recupera contexto por device_id; (7) passphrase memorizada, no derivada del token. Por esto
Arturo NO autorizó la llave SSH `hermes-portable` ni authkey Tailscale para la USB — no son necesarias en
el diseño correcto (eso es DISTINTO de `HERMES_EQUIPOS_PROPIOS`, que sigue usando SSH/Tailscale entre
HP↔MacBook, equipos propios, sin relación con F11-2). Impacto: código traído a `usb_llave/agente-go/`
(antes solo en Desktop); `usb_llave/start-linux.sh` queda marcado SUPERADO en su propio header, no
borrado (reversibilidad). Corrección adicional al reporte de Hermes: la lista negra de comandos peligrosos
(`evaluarComando`, 12 patrones regex) y el router multi-dispositivo por alias (`resolverAlias`) YA estaban
implementados en el código encontrado — no eran pendientes como decía el reporte inicial.
