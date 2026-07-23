# HERMES ARCHITECTURE STANDARD (HAS) — ENTREGA COMPLETA · v1.1
**Fecha:** 21 de julio de 2026 · **Para:** Arturo De la Cruz Román · **Ejecutores posteriores:** Claude Code (Sonnet) + Hermes (Gemini/Groq)

**Cambios v1.1 (aprobados por Arturo el 21-jul-2026):** (1) nuevo modo llamada interino por Gemini Live API (OT-9.5) con proyecto de Google dedicado; "Hermes en la oreja todo el día" formalmente diferido a Mac Mini. (2) Trading rediseñado: Binance como piso de operación y entrenamiento (testnet spot), Bitso como puerta regulada de pesos, laboratorio de papel **diario y permanente** + decisiones reales **semanales**, lista blanca BTC/ETH/USDT(+SOL satélite). (3) Nueva sección E10: plan financiero personal con los tres rieles de ingreso, CETES, y las metas Mac Mini → Mac Studio con números reales. (4) Estrategia de tokens adaptada al modelo "Claude un mes cada 4 meses" (ventanas de mantenimiento). (5) Nueva regla F7: evolución de esquema y versionado por cuatrimestre.

**Cambios v1.2 (22-jul-2026, sincronización con `docs/HISTORIAL.md` — el historial real reconstruido del 4 al 22 de julio):** (1) **Nueva OT-0.5 "Emergencia de credenciales", máxima prioridad del proyecto**: dos incidentes de llaves expuestas (4-jul y 20-jul) cuya rotación NUNCA se confirmó, más un tar de respaldo que aún contiene `.env`/`auth.json` en texto plano, más un cron silencioso roto. (2) Fase 0 marcada **COMPLETADA** con evidencia (fork `arturo/prod`, SHA `6e2a26a3` verificado local=remoto; 16 commits reales, no 10). (3) OT-1 marcada **parcial** (USER.md consolidado 102→81; escáner de secretos corregido el 22-jul). (4) Nueva regla F8: "cerrado solo con evidencia pegada" — respuesta directa al patrón transversal documentado de reportes que declaran "verificado en producción" sobre evidencia parcial. (5) Nueva especificación E11: higiene de tamaño de conversación en el gateway (una conversación de 262,593 tokens rompió toda la escalera de fallback — hallazgo Q.0). (6) `docs/HISTORIAL.md` se incorpora a la jerarquía documental como memoria histórica de solo-lectura.

**Cambios v1.4 (23-jul-2026 — corrección de arquitectura de trabajo):** (1) El centro de operación diario deja de ser el chat de diseño y pasa a **Claude Code**, que arranca solo leyendo `CLAUDE.md` (nuevo, raíz del repo) y propone el siguiente paso; el chat de claude.ai queda como consultor eventual. (2) Nuevo `docs/GUION_PRUEBAS.md`: el día completo de Arturo simulado, con matriz combinatoria (~1,600 combinaciones), memoria verificada en 3 capas, entrada sucia, seguridad adversarial y resiliencia. (3) Nueva **OT-P** (permisos: allowlist + sudoers acotado, para que Arturo no vuelva a teclear en terminal por rutina). (4) Nueva **OT-QA** (cuenta QA de Telegram sobre chip propio, condicionada a cerrar L13). (5) Nueva **E12**: presupuesto autónomo de pruebas ($100 MXN/mes con cortacircuitos) y metodología de verificación de memoria.

**Cambios v1.3 (23-jul-2026, lecciones de la sesión de ejecución 22-23 jul):** (1) Nueva sección **F9 "Lecciones permanentes"**: las 17 fallas reales de esa sesión convertidas en reglas citables (F8 queda intacta como principio; F9 es su jurisprudencia). (2) Resolución de la falla 17 con supuesto marcado: en caída total de la escalera gratuita, Hermes nunca calla ni despacha solo — avisa modo degradado y ofrece DeepSeek con costo. (3) `docs/BITACORA_ARTURO.md` se incorpora al cierre de sesión como entregable obligatorio para cambios visibles al usuario. (4) El PROTOCOLO sube a v1.1 en paralelo (D7 "leer antes de preguntar", D8 "muestra antes de construir", P6 "arnés interno para pruebas de rutina", C13-C14).

> **Corrección de nombres de modelos (importante para las órdenes de trabajo):** el documento maestro menciona "Claude Sonnet 5". Ese modelo no existe hoy. La línea actual de Anthropic es: **Claude Fable 5** (tope), **Claude Opus 4.8**, **Claude Sonnet 4.6** (el default de Claude Code) y **Claude Haiku 4.5**. Donde el maestro decía "Sonnet 5", léase **Sonnet 4.6**. Las reglas de escalamiento de la sección de tokens usan estos nombres reales. Verifica versiones vigentes en https://docs.claude.com si esto se ejecuta meses después.

---

# A. RESUMEN EJECUTIVO (para Arturo, sin tecnicismos)

Jefe, piensa en Hermes como una casa que ya tiene cimientos buenos pero con tres problemas: **(1)** las mejoras que le hiciste están escritas sobre las paredes originales — si el constructor original (Nous Research) te manda paredes nuevas, pierdes todo lo tuyo; **(2)** la casa tiene cuartos llenos de cajas sin etiquetar (memoria, skills, archivos) — la información existe pero no la encuentras cuando la necesitas; y **(3)** quieres agregarle pisos nuevos (tutor, voz, trading, video) antes de reforzar los cimientos.

**El orden de esta entrega es: primero asegurar lo construido, luego hacer que la memoria funcione de verdad, y solo entonces construir los pisos nuevos.** ¿Por qué ese orden? Porque cada módulo nuevo (tutor académico, finanzas, video) depende de dos cosas: que Hermes **recuerde** (memoria con búsqueda real) y que Hermes **no se rompa** al actualizarse (blindaje). Construir el tutor sobre la memoria actual sería como escribir apuntes en hojas sueltas que se vuelan.

**Las 12 fases, en una línea cada una:**

- **Fase 0 — Caja fuerte.** Resolver la anomalía de git, crear tu rama en tu fork, y subir tus 2,016 líneas a GitHub. Media sesión. Sin esto, un accidente borra meses de trabajo.
- **Fase 1 — Fugas urgentes.** Limpiar `USER.md` (las contradicciones te están afectando HOY en cada mensaje), escribir `cleanup_audio_cache()`, probar la alerta de DeepSeek de punta a punta, escáner de secretos en Fase 2, y **conectar Whisper al gateway** — porque la captura de ideas por voz es tu problema raíz y la pieza ya está instalada, solo desconectada.
- **Fase 2 — Blindaje.** Migrar lo migrable a plugins, dejar el resto como parches con procedimiento de rebase, y actualizar a 0.19.x de forma controlada.
- **Fase 3 — Skills sanas.** Borrar las 2 basura-404, resolver los 3 duplicados, arreglar el bug del contador de uso, reparar los 4 scripts rotos, y establecer el esquema de metadata.
- **Fase 4 — Memoria que encuentra.** Aprobar los 20 hechos candidatos (proceso, no a ciegas), activar el flujo de aprobación semanal, y construir la **búsqueda semántica local** — el índice que hace que "SSH a la MacBook" aparezca cuando lo preguntes.
- **Fase 5 — Tablero y cola.** Notion como el único lugar donde ves todo, y la cola de tareas con garantía "encolada → resuelta → notificada, sin excepción".
- **Fase 6 — Tutor académico.** Horario por foto, pizarrón por materia, repaso proactivo, Classroom. Llega justo antes de tu nuevo cuatrimestre.
- **Fase 7 — Archivo y finanzas.** Caché efímero vs biblioteca permanente; tickets con evidencia; fotos familiares a la HP.
- **Fase 8 — Producción de video.** Setup semiautomático, corte de silencios que no destruye habla (con verificación automática), edición en la línea de tiempo de DaVinci vía SSH a la M1.
- **Fase 9 — Proactividad.** Reglas explícitas + detección espontánea con periodo de entrenamiento "¿la anoto?".
- **Fase 10 — Trading en papel.** Dos meses de simulación medida antes de un solo peso real. Con dinero real, Hermes propone y tú apruebas — **siempre**.
- **Fase 11 — Voz y portabilidad (Mac Mini).** La voz cálida local de verdad y el "USB llave" se terminan cuando llegue la Mac Mini; mientras, hay versiones intermedias gratis.

**Analogía del USB, porque cambia respecto a lo que imaginabas:** el USB no va a ser una copia de Hermes (eso es cargar la casa entera en una mochila). Va a ser **la llave de tu casa**: la conectas en cualquier computadora, abre un túnel seguro a tu HP, y Hermes — que nunca salió de casa — trabaja a través de ese túnel con todas sus memorias intactas. Es más seguro, más barato, y funciona en los 3 sistemas operativos de verdad.

---

# B. DECISIONES DE ARQUITECTURA

Formato: **Problema → Opciones → Decisión → Por qué.**

## B1. Anomalía de git y fork: ¿ahora o después?

**Problema.** El 19 Jul el diagnóstico reportó 13,222 commits solo-locales con tip `a7d7c02cb`; el 20 Jul un fetch fresco dio 0 solo-locales, 2,327 commits nuevos y `a7d7c02cb` ya no es ancestro. Tus 10 commits (2,016 líneas) solo existen en un disco.

**Opciones.** (a) Investigar la anomalía hasta el fondo antes de tocar nada; (b) subir al fork ya y diagnosticar después; (c) ignorar y seguir sin fork.

**Decisión: (b) con diagnóstico acotado.** Subir la rama al fork es una operación de **solo escritura hacia afuera** — no puede empeorar nada local, y convierte el único punto de fallo (el SSD de la HP) en dos. El diagnóstico de la anomalía se hace en la misma sesión pero *después* del push, con un procedimiento cerrado (Orden de Trabajo 0). La explicación más probable, dada la evidencia: **el "13,222 solo-locales" del 19 Jul fue un artefacto de un fetch fallido o de refs remotas viejas/corruptas** (si `origin/main` local estaba desactualizado o dañado, todo upstream aparece como "local"), y el fetch del 20 Jul simplemente trajo la realidad. Que `a7d7c02cb` no sea ancestro es consistente con que upstream haya hecho *force-push/rebase de main* — Nous Research reescribiendo historia es plausible en un repo de investigación. La OT-0 discrimina entre ambas hipótesis con evidencia (fechas de commits vía API de GitHub). **Regla dura: prohibido `pip install -U` o `git pull` sobre producción hasta cerrar la Fase 2.**

## B2. Blindaje de las 2,016 líneas: ¿plugins, parches, o mezcla?

**Problema.** Todo el hardening vive dentro del código del framework. Upstream va 2,327 commits adelante; ya salió 0.19.0.

**Opciones.** (a) Todo a plugins/hooks; (b) todo como parches con rebase; (c) híbrido archivo por archivo.

**Decisión: (c) híbrido, con este veredicto por archivo:**

| Archivo | Destino | Justificación |
|---|---|---|
| `agent/complexity_detector.py` (332 líneas, nuevo) | **Plugin** (`plugins/arturo/complexity/`) | Es archivo nuevo, autocontenido; solo necesita un hook de pre-turno. Riesgo de migración: bajo. |
| `plugins/platforms/telegram/adapter.py` | **Plugin propio derivado** o parche pequeño | Ya vive en zona de plugins; si los cambios son hooks de mensaje, extraer a subclase. |
| `gateway/slash_commands.py` | **Plugin** si el registro de comandos es extensible en 0.19; si no, **parche** | Verificar en OT-2 si 0.19 permite registrar comandos desde plugin (probable: el framework presume extensibilidad). |
| `tools/approval.py`, `tools/file_tools.py`, `hermes_cli/context_switch_guard.py`, `hermes_cli/toolset_validation.py` | **Parche permanente** | Son las reglas de seguridad; modifican comportamiento del núcleo a propósito. Un plugin que "envuelve" seguridad puede ser saltado por el core — la seguridad se parcha en el core, punto. |
| `agent/conversation_loop.py`, `agent/prompt_builder.py`, `agent/turn_finalizer.py`, `gateway/run.py` (898 líneas), `hermes_state.py`, `hermes_cli/config.py` | **Parche con rebase controlado** | Núcleo caliente del framework; upstream los toca seguido. Se mantienen como serie de parches pequeños y temáticos (los 10 commits ya están organizados por área — eso es exactamente una quilt series). |
| `tests/`, `.gitignore` | **Rama propia, sin conflicto esperado** | Aditivos. |

**Estructura de ramas en el fork `arturocruz9602-sudo/hermes-agent`:**
- `upstream-main` — espejo limpio de NousResearch/main. Nunca se toca a mano.
- `arturo/base` — upstream-main + parches de seguridad (los que son "parche permanente").
- `arturo/prod` — lo que corre en la HP. = `arturo/base` + plugins (los plugins viven en `~/.hermes/plugins/` fuera del repo del framework cuando el framework lo permita; si no, en el repo).
- **Procedimiento de actualización** (se documenta como skill `hermes-upgrade`): fetch upstream → actualizar `upstream-main` → `git rebase upstream-main` sobre `arturo/base` → correr suite de tests propios → smoke test de gateway en un venv paralelo → solo entonces tocar producción. Nunca actualizar por pip: **la instalación de producción pasa a ser editable (`pip install -e`) desde el fork.**

## B3. Curator nativo vs Claude para robustecer skills

**Problema.** Hermes ya se auto-mejora (curator + `/learn`). Arturo pregunta qué es más confiable para robustecer skills: el curator o pedírselo a Claude con evidencia.

**Decisión: los dos, con roles distintos y frontera dura.**
- **El curator es el conserje, no el editor.** Se queda como está: poda determinística activa, consolidación por LLM **apagada permanentemente**. Evidencia: 3 corridas, 0 cambios — es seguro precisamente porque es inerte. Un LLM barato editando skills sin supervisión viola la restricción dura #4 (verificación E2E) y #9 (validar contra historial real).
- **Las mejoras sustantivas las hace Claude en sesiones dedicadas, bajo el "Protocolo de Mejora de Skill" (sección F2)**, que implementa las preguntas previas del documento fundacional: respaldo → diff → validación → versión → historial. Claude tiene lo que el curator no: criterio, conocimiento fresco, y capacidad de probar el script de la skill de verdad.
- **Hermes (Gemini) hace el trabajo de detección, no de edición:** barrido semanal que *reporta* duplicados, skills sin uso, scripts rotos, docs incompletas — y llena la cola de candidatos que Claude atiende en la sesión mensual de mantenimiento. Detección barata, edición cara pero supervisada.

**Por qué gana esta división:** tu propia observación — "con skill escrita, Hermes razona menos y gasta menos" — significa que **la calidad de la skill es apalancamiento de tokens**. El apalancamiento justifica gastar tokens caros (Claude) en escribirlas bien una vez, y prohíbe que un modelo barato las degrade gratis.

## B4. Trading: ¿"lo dejo trabajando solo" o "propone y yo apruebo"?

**Problema.** Arturo dijo ambas cosas. El diseño original decía "nunca ejecuta solo".

**Decisión: la autonomía depende del tipo de dinero, no de la confianza acumulada.**
- **Dinero de papel (simulación): autonomía total.** Hermes opera solo, 24/7, registrando cada decisión con razonamiento. Aquí "lo dejo trabajando solo" es literal y es donde se aprende.
- **Dinero real: propone-y-apruebas, PERMANENTE.** Hermes detecta la oportunidad, arma la orden completa (entrada, stop-loss, take-profit como OCO), te la manda por Telegram con su razonamiento y el gasto/exposición acumulados, y **no ejecuta sin tu "sí" explícito**. Lo que gradúa con la consistencia no es la autonomía: es el **tamaño de posición permitido** y la **frecuencia de propuestas**.
- **Criterios numéricos de graduación papel→real:** ≥2 meses corridos Y ≥60 operaciones simuladas Y expectativa positiva neta de comisiones Y drawdown máximo <15% Y calibración de confianza medida (cuando el sistema dice "70% seguro", acierta ~70%). Si falla cualquiera, otro mes de papel.
- **Apagados automáticos con dinero real:** pérdida diaria ≥3% del capital o semanal ≥6% → el módulo se desactiva solo y avisa; reactivación manual.

**Por qué:** con $1,000 MXN el upside de la autonomía total es de pesos; el downside de un bug (ya viviste el incidente DeepSeek: 3 disparos no autorizados) es perder el capital y la confianza en todo el sistema. El flujo que tú mismo describiste — "yo verifico si hay alguna noticia y lo apruebo" — es además tu ventaja: el humano filtra el contexto de noticias que un sistema de $100/mes no puede monitorear bien. **Nota obligatoria: ni Claude ni Hermes ni ningún modelo de este stack son asesores financieros licenciados. El sistema analiza, registra y ejecuta reglas que tú defines; las decisiones y las pérdidas son tuyas.** El mercado elegido se mantiene en cripto, con arquitectura híbrida decidida (v1.1, ya no es supuesto):

- **Binance = piso de operación y entrenamiento.** Comisiones spot ~0.1% por operación (~0.2% el ciclo completo, contra ~1–1.3% en Bitso) y **testnet de spot con la API real**, donde el laboratorio corre contra infraestructura idéntica a producción. Llaves de API restringidas: solo-trade, **sin permiso de retiro**, whitelist de IP apuntando a la HP.
- **Bitso = puerta regulada de pesos.** Entrada y salida garantizada vía SPEI (Bitso tiene licencia bajo la Ley Fintech; Binance opera en México sin figura regulada local y su retiro SPEI directo depende de un partner de pagos que a veces no está activo — cuando funcione, es un atajo válido, pero la ruta que siempre funciona es Binance → USDT → Bitso → venta → SPEI a tu banco). **Toda ganancia realizada que apruebes se transfiere a Bitso/banco; nada vive permanentemente en Binance.**
- **Lista blanca de monedas:** núcleo **BTC y ETH** (máxima liquidez, spreads mínimos, menor manipulabilidad), **USDT como posición de efectivo**, y **SOL como satélite opcional con tamaño reducido** solo si el laboratorio demuestra que aporta. Hermes analiza y elige *dentro* de la lista; operar fuera de ella requiere modificar este documento, no una decisión de sesión.
- **Doble ciclo permanente:** el laboratorio de papel en el testnet corre **diario, para siempre** (no solo los 2 meses de graduación); las decisiones con dinero real son **semanales** (swing, 1–3 propuestas/semana por Telegram). Cada domingo el sistema compara lo propuesto en real contra lo que hizo el laboratorio, y esa comparación alimenta la mejora de la estrategia. Los 2 meses con criterios de B4 son la barrera de entrada al dinero real; el laboratorio nunca se apaga.
- **Contexto obligatorio del módulo:** las señales salen de reglas deterministas versionadas; el LLM (vía alias `trading-analista` en LiteLLM, agnóstico al proveedor) solo hace trabajo blando — resumir noticias, vetar operaciones por contexto de mercado. El sistema no depende de qué modelo conteste hoy.

## B5. Prioridad de la voz: ¿antes o después de la base?

**Decisión: después de la base técnica (Fase 11), con dos excepciones que se adelantan porque son baratas y atacan el problema raíz:**
1. **Whisper→gateway se conecta en Fase 1.** Ya está instalado; conectarlo es horas, no semanas; y desbloquea la captura de ideas por voz — literalmente el motivo por el que existe el proyecto.
2. **TTS local interino gratis en Fase 9:** **Piper** (voz `es_MX`, corre en la HP con CPU, latencia baja) para alarmas y avisos hablados. No es "cálida tipo Gemini" — es funcional. La voz de calidad sigue siendo Gemini Zephyr mientras sea gratis.

**La voz conversacional de verdad (femenina, cálida, con interrupciones) se difiere a la Mac Mini.** Honestidad técnica: en la M1 de 8GB puedes *correr inferencia* de TTS modernos ligeros (Piper, Kokoro-82M — calidad sorprendentemente buena, licencia Apache, CPU-friendly; XTTS-v2 corre pero justo y su licencia Coqui es no-comercial — para uso personal está bien), pero **entrenar/fine-tunear una voz en 8GB unificados compartidos con el sistema es marginal**: se puede con Piper (entrenamiento de voz con dataset con licencia, días de cómputo, la Mac inutilizable mientras), y no vale la pena antes de la Mac Mini. **Prohibido clonar la voz de Scarlett Johansson o de cualquier persona identificable sin consentimiento** — se diseña sobre voces sintéticas con licencia (datasets como LJSpeech-style en español con licencia libre, o las voces ya empaquetadas de Piper/Kokoro). El modo "llamada fluida con interrupciones" requiere full-duplex con VAD y cancelación de eco — viable en Mac Mini con pipeline local (Whisper streaming + LLM + Kokoro), no viable con calidad en la HP i3. **Alexa: solo como bocina Bluetooth para alarmas si tu Echo soporta modo BT (la mayoría sí); cero integración de micrófono (Amazon no lo expone — confirmado por tu propia prueba).** Hardware dedicado de recámara (Raspberry Pi 5 + mic array + bocina ≈ $2,800–3,500 MXN) se evalúa después de la Mac Mini, no antes: competiría con ella por dinero.

## B6. Apple Watch vs iPhone

**Decisión: no comprar el Watch.** Los $3,575–4,674 MXN van a la Mac Mini. Justificación numérica: el Watch resuelve *un* canal de alerta (muñeca) que el iPhone ya cubre al 90% (notificaciones críticas de Telegram con sonido personalizado + modo "notificaciones urgentes" que atraviesan No Molestar). La Mac Mini desbloquea *cuatro* frentes completos (voz local, modelos locales, entrenamiento, render). Se reevalúa solo si tras 2 meses de proactividad activa hay evidencia registrada de ≥5 alertas críticas perdidas por no traer el teléfono.

## B7. Frontera Notion ↔ Obsidian

**Decisión:** **Notion = tablero de operación** (estado del día, % de avance, kanban espejo, finanzas del mes, cola de tareas, horario). Se alimenta **automáticamente** desde Hermes vía API; lo único manual es palomear y reordenar prioridades. **Obsidian = biblioteca de conocimiento** (biografías, guiones, apuntes profundos, nodos relacionados). Hermes escribe en Obsidian solo notas de conocimiento (apuntes de clase procesados, investigación para guiones), nunca estado operativo. Regla anti-mantenimiento: **si un dato requiere edición manual recurrente en Notion, ese dato no va en Notion** — se automatiza o se elimina de la vista.

## B8. USB portable: la llave, no el cerebro

**Problema.** Hermes completo en USB multi-OS con llaves adentro: si se pierde el USB, se pierden 11 credenciales; mantener 3 entornos Python (Linux/macOS/Windows) en un stick es frágil; y el framework no está diseñado para eso.

**Decisión: arquitectura "USB-llave".** El USB contiene:
1. **Bóveda cifrada** (VeraCrypt, multiplataforma real en los 3 OS) con: llave SSH dedicada `hermes-portable` (revocable independientemente), auth key de Tailscale efímera/re-generable, y un archivo de contactos de emergencia. **Nada de las 11 API keys viaja en el USB.**
2. **Lanzadores por OS** (`start-linux.sh`, `start-macos.command`, `start-windows.bat`) que: instalan/ejecutan el binario portable de Tailscale, levantan el túnel a la HP, y abren una terminal SSH contra Hermes CLI en la HP. Dos o tres clics reales.
3. **Toolkit de diagnóstico portable** (binarios estáticos multi-OS: herramientas de red, escaneo AV con ClamAV portable, scripts de inventario de hardware) que Hermes **dirige** por la sesión SSH inversa: el script corre local en la máquina prestada, su salida viaja a Hermes, Hermes razona y responde. Así "Hermes está dentro" sin que Hermes viva ahí.
4. **Registro de autorización de terceros:** antes de tocar una máquina ajena, el lanzador muestra un texto de consentimiento; Hermes registra en `state.db` quién autorizó, fecha, alcance, y se niega a ejecutar acciones fuera del alcance registrado. En equipo propio no aplica.
5. **Sincronización de contexto:** todo pasa por Hermes-en-la-HP, así que el contexto **nunca sale de casa** — no hay nada que sincronizar de vuelta. Archivos grandes de la máquina prestada: SSH/SCP directo a `/mnt/seagate` si hay internet; sin internet, el toolkit los copia al propio USB (partición de intercambio sin cifrar) y al llegar a casa un script los ingiere. El flujo "mándalo por Telegram y recuérdame bajarlo" queda como respaldo para archivos <2GB (límite de Telegram).
6. **Puente a la MacBook:** como todo corre vía Tailscale, desde la máquina prestada Hermes puede saltar a `macbook` con la misma llave — el guion que describiste funciona tal cual.

**Qué es fantasía y se dice de frente:** Hermes corriendo *offline* completo en una máquina prestada sin internet no es viable (sus modelos son APIs en la nube; sin internet no hay cerebro). El modo sin internet se limita al toolkit de diagnóstico con reportes diferidos.

## B9. Memoria: arquitectura de tres capas + índice

**Decisión.** Se conserva el principio rector — **nunca comprimir destruyendo; el crudo es sagrado, solo se comprime el índice** — y se completa así:
- **Capa 1 (cruda, existe):** `/mnt/seagate/hermes_raw/` sigue igual. Es el disco duro de los hechos.
- **Capa 2 (hechos aprobados, existe con 0 filas):** se activa con el proceso de aprobación semanal (OT-4). Cada hecho lleva `fuente` verificable contra la capa cruda. El escáner de secretos de `memory_tool.py` se inserta en el pipeline **antes** de que un candidato llegue a revisión.
- **Capa 3 (índice semántico, nueva):** embeddings locales con **`intfloat/multilingual-e5-small`** (~470MB en disco, ~600MB RAM en inferencia, CPU-viable en el i3; excelente en español) + **`sqlite-vec`** como almacén (cero servicios nuevos, mismo SQLite que ya usa Hermes). Indexa: mensajes de la capa cruda (por chunks de ~10 mensajes), hechos de capa 2, frontmatter+resumen de cada skill, y notas de Obsidian. Reindexado incremental nocturno vía timer systemd. Búsqueda: híbrida — FTS5 (keyword) + vectorial, unión re-rankeada. Esto resuelve directamente el fallo real "el dato existía (SSH a la MacBook, 565 notas) y no lo encontró".
- **Traducción de la literatura a decisiones:** de **MemGPT/Letta** se toma la idea de memoria de trabajo editable (eso ya es `USER.md`, que la sección F3 convierte en consolidable); de **Generative Agents** se toma el *memory stream* con recencia+relevancia+importancia como fórmula de ranking del retrieval (implementable en 30 líneas sobre sqlite-vec); de **RAPTOR** se toma la idea de resúmenes jerárquicos — **diferida a Mac Mini** (generar el árbol de resúmenes cuesta LLM; en la HP el presupuesto no da); de **A-MEM/Zettelkasten** se toma que las notas enlazadas viven en **Obsidian**, no en una base paralela; **HippoRAG** (grafo de entidades) se descarta por complejidad/beneficio en un corpus de una sola persona. **Método experimental que sí vale la pena** (Arturo los pidió): "diario de reflexión" — una vez por semana Hermes (Gemini, gratis) escribe 5 observaciones de alto nivel sobre la semana y las indexa como memorias de importancia alta; es la parte de "reflexión" de Generative Agents y es barata.
- **Degradación con gracia:** si la HP no aguanta e5-small (medir: si el reindexado nocturno tarda >2h o la RAM pasa de 85%), degradar a `paraphrase-multilingual-MiniLM-L12-v2` (mitad de tamaño) y chunks más grandes. En Mac Mini: subir a `multilingual-e5-base` y agregar RAPTOR.

## B10. Subagentes: contrato de verificación

**Problema.** Dos fallos reales: subagentes que reportaron trabajo no hecho o estado contradictorio.

**Decisión: "un subagente no reporta éxito; entrega evidencia".** Regla permanente para Claude Code y para Hermes: toda delegación define **antes de lanzarse** (a) el artefacto verificable que debe existir al terminar (archivo, fila en DB, salida de test), y (b) el comando de verificación que el orquestador corre él mismo. Si el artefacto no pasa la verificación, el resultado se descarta completo — no se "rescata parcialmente" texto del subagente. En Claude Code: subagentes en background **solo** para tareas de lectura/investigación (donde el fallo es barato); toda escritura de código va en la sesión principal. El router por complejidad (Tarea E) se conserva tal cual; los "perfiles por dominio" del maestro original se implementan como **skills**, no como subagentes — es más barato y aprovecha tu observación de que las skills reducen razonamiento.

## B11. Checklist diario: manual, generado

**Decisión: se mantiene el palomeo manual, pero la lista la genera Hermes cada mañana** (cruzando kanban + horario + metas) y la publica en Notion y Telegram. Palomear a mano tiene valor conductual real (compromiso, revisión consciente); lo que se automatiza es la *generación* y la *recolección* (lo palomeado alimenta la métrica de avance). Automatizar el palomeo destruiría la señal: Hermes marcando sus propias tareas como hechas es exactamente el patrón de auto-reporte no confiable de B10.

---

# C. PLAN POR FASES

Cada fase: **Objetivo · Dependencias · Entregables · Verificación E2E · Esfuerzo** (en sesiones de Claude Code de ~2h con Sonnet 4.6; "S" = sesión).

### Fase 0 — Caja fuerte (git + fork) — ✅ COMPLETADA (verificada 22-jul)
- **Evidencia de cierre:** fork `arturocruz9602-sudo/hermes-agent`, rama `arturo/prod`, SHA `6e2a26a3` confirmado local=remoto vía API de GitHub; 16 commits reales de "Arturo Cruz" (el conteo de 10 del diagnóstico original quedó corto); `ESTADO.md` y `BLOQUES.md` existen; `docs/HISTORIAL.md` (411 líneas) reconstruye el 4-22 de julio.
- **Residuo pendiente (verificar en ESTADO.md, cerrar si falta):** veredicto documentado de la anomalía git del 19-20 jul y el candado `UPGRADE_LOCK` + freeze de pip.

### Fase 0.5 — EMERGENCIA DE CREDENCIALES (nueva en v1.2 — máxima prioridad, antes que cualquier otro trabajo)
- **Objetivo:** cerrar la exposición de llaves que lleva abierta desde el 4 de julio.
- **Por qué es lo primero:** el historial real documenta (a) 4-jul: una API key de Google pegada en texto plano y 2 llaves de Gemini + 2 de Groq repetidas por Hermes en sus propias respuestas, semanas sin detectarse; (b) 20-jul: segundo hallazgo de credenciales expuestas; (c) **rotación jamás confirmada en ningún reporte**; (d) el tar de respaldo del repo git accidental de `~/.hermes` (Bloque G) todavía contiene `.env`/`auth.json` en texto plano; (e) un cron roto corre `vigilar_hermes.sh` cada 15 min en silencio. Todo el blindaje de git del proyecto protege el código; nada de eso sirve si las llaves siguen siendo las expuestas.
- **Entregables:** las ~11 llaves rotadas (prioridad: las 5 con exposición confirmada — Google, 2 Gemini, 2 Groq — y después el resto por higiene, dado que estuvieron en un repo git en stage); `.env` regenerado; tar de respaldo saneado (extraer lo valioso, purgar los blobs con secretos, recomprimir cifrado con `age` o VeraCrypt) y el tar original destruido; cron silencioso eliminado o reparado con log; línea en `CHANGELOG_SISTEMA.md` por cada llave rotada con fecha.
- **Verificación E2E:** cada servicio responde 200 con su llave nueva; las llaves viejas devuelven 401/403 (probado, no supuesto); `grep -r` de fragmentos de las llaves viejas sobre `~/.hermes`, el fork y los backups accesibles = 0 resultados en texto plano; `crontab -l` limpio.
- **Esfuerzo:** 1 S. **Nota:** la rotación en cada consola (Google AI Studio, Groq, etc.) la hace Arturo con guía paso a paso de la sesión; Claude Code hace todo lo demás.

### Fase 1 — Fugas urgentes — 🔄 PARCIAL (sincronizado 22-jul)
- **Ya hecho con evidencia:** USER.md/MEMORY.md consolidados el 21-jul (102→81 entradas — verificar contra ESTADO.md si las contradicciones de "Tony"/presupuesto que HISTORIAL marca como abiertas quedaron de verdad resueltas o resurgieron); escáner de secretos con el hueco "sin comillas" corregido el 22-jul.
- **Pendiente:** cleanup_audio_cache, prueba E2E DeepSeek, Whisper→gateway, allowed_fails (confirmar cada uno contra ESTADO.md antes de re-trabajar — regla K.0: verificar antes de rehacer).
- **Objetivo:** cerrar la deuda técnica que causa daño hoy.
- **Dependencias:** Fase 0 ✅ y Fase 0.5 (credenciales) cerrada.
- **Entregables:** (1) `USER.md` consolidado vía `memory_tool.py` (las 8 contradicciones de la sección 6 del maestro, con las resoluciones ya confirmadas: Arturo/jefe/señor nunca Tony; $100 MXN/mes; rutas reales; Groq activo como fallback; LiteLLM central); (2) `cleanup_audio_cache()` escrita y en el ciclo de limpieza; (3) prueba E2E real de la notificación DeepSeek (despacho controlado de $0.01); (4) escáner de secretos insertado en `fase2_extract_candidates.py`; (5) **Whisper conectado al gateway**: nota de voz de Telegram → transcripción → tratada como texto normal; (6) `allowed_fails` distinguiendo rate-limit de error duro.
- **Verificación E2E:** mandas una nota de voz real y Hermes responde a su contenido; mandas un audio y a las 48h+1 tick ya no existe en cache; el despacho DeepSeek de prueba produce las 2 notificaciones Telegram; un candidato-trampa con una API key falsa es bloqueado por el escáner.
- **Esfuerzo:** 2 S.

### Fase 2 — Blindaje y actualización
- **Objetivo:** actualizar a 0.19.x sin perder nada, y que la próxima actualización sea un procedimiento, no una cirugía.
- **Dependencias:** Fase 0 (ramas), Fase 1 (producción estable para comparar).
- **Entregables:** migración por archivo según la tabla B2; venv paralelo con 0.19.x + rebase de `arturo/base`; suite de smoke tests (10 escenarios: arranque gateway, mensaje Telegram, slash commands propios, detector de complejidad, guardias de permisos, cola, curator tick, memoria, media, fallback); skill `hermes-upgrade` documentando el procedimiento; producción cambiada al venv nuevo con rollback listo.
- **Verificación E2E:** los 10 smoke tests pasan en el venv nuevo; se simula una "actualización siguiente" (rebase sobre un commit upstream posterior) y el procedimiento la resuelve sin intervención creativa.
- **Esfuerzo:** 3–4 S (la más delicada; no comprimir).

### Fase 3 — Ciclo de vida de skills
- **Objetivo:** 136 skills → inventario sano con metadata y contador de uso correcto.
- **Dependencias:** Fase 2 (para no arreglar dos veces).
- **Entregables:** borrado de las 2 basura-404 (con respaldo, por el fundacional); resolución de los 3 duplicados (regla: se conserva la de `superpowers/` si el diff muestra que es superset; si son divergentes de verdad, fusión manual en sesión y la otra se archiva); reinstalación de `torch`/`websocket`/`validators`/`marker` **solo si la skill se va a usar** (comfyui: evaluar si cabe en el i3 — probablemente se archiva; powerpoint y ocr: reparar, el tutor las necesita); fix del bug de `.usage.json` reindexando por ruta relativa (documentando que los 3 pares colisionados pierden historial); esquema de metadata (sección E3) aplicado a las 136; triage de las 32 sin uso (archivar las irrelevantes, **conservar y marcar `pinned` todas las de desarrollo/DB/redes/ciberseguridad** por decisión explícita de Arturo).
- **Verificación E2E:** dos skills homónimas registran contadores independientes tras usarse una vez cada una; `hermes skills audit` (comando nuevo) reporta 0 archivos-404, 0 nombres duplicados, 0 scripts con imports rotos entre las activas.
- **Esfuerzo:** 2 S.

### Fase 4 — Memoria que encuentra
- **Objetivo:** capa 2 viva + índice semántico funcionando.
- **Dependencias:** Fase 1 (escáner de secretos), Fase 2 (base estable).
- **Entregables:** proceso de aprobación de candidatos (`hermes memoria revisar` interactivo por Telegram: candidato + fuente + botones aprobar/rechazar/editar); los 20 candidatos procesados; corrida semanal de Fase 2 agendada; `memoria_semantica.db` con sqlite-vec + e5-small; reindexado incremental nocturno (timer systemd); retrieval híbrido FTS5+vector con ranking recencia·relevancia·importancia inyectado al contexto de Hermes; "diario de reflexión" semanal.
- **Verificación E2E:** la prueba del fallo real — preguntar a Hermes por el procedimiento de SSH a la MacBook en sesión limpia y que lo recupere de las 565 notas; ≥15 hechos en `memoria_estructurada` con fuente verificada; el reindexado nocturno corre 3 noches seguidas sin intervención.
- **Esfuerzo:** 3 S.

### Fase 5 — Tablero central y cola garantizada
- **Objetivo:** un solo lugar donde ver todo; ninguna tarea encolada se pierde jamás.
- **Dependencias:** Fase 4 (datos que mostrar). **Requiere de Arturo:** crear la integración de Notion y pegar `NOTION_API_KEY` en `.env` (5 minutos, instrucciones en OT-5).
- **Entregables:** consolidar a UNA skill de Notion (la `notion-api` personal, archivando la bundled); tablero con 6 vistas (Hoy, Kanban, Finanzas del mes, Avance HAS %, Cola de tareas, Escuela); sync unidireccional Hermes→Notion cada 15 min; **cola de tareas v2** con máquina de estados `encolada→en_proceso→resuelta→notificada` en `state.db`, reintento con escalera de proveedores (Groq→Gemini→OpenRouter), watchdog de tareas huérfanas (>2h en_proceso → re-encolar y avisar), y notificación garantizada al canal activo; checklist diario generado cada mañana (B11).
- **Verificación E2E:** se encolan 15 tareas sintéticas con el proveedor primario deshabilitado a propósito; las 15 terminan en `notificada` con su mensaje de Telegram, cero perdidas; el tablero refleja el estado en <15 min.
- **Esfuerzo:** 3 S.

### Fase 6 — Tutor académico
- **Objetivo:** el flujo completo de la sección 4.6.3 del maestro, listo antes del nuevo cuatrimestre.
- **Dependencias:** Fase 4 (memoria), Fase 5 (tablero, cola), Fase 3 (skills pptx/ocr reparadas).
- **Entregables:** ingesta de horario por foto (Gemini Vision → tabla `horario` en state.db → vista Escuela en Notion); flujo pizarrón (foto+descripción → carpeta `biblioteca/escuela/<materia>/` permanente → identificación de tema → investigación con Brave+Gemini → explicación pedagógica → registro de tema visto → detección de tareas → kanban); recomendador de repaso (cruza horario+gym+kanban, propone hueco concreto); tareas dictadas (crear archivo + recordatorio + aviso previo); integración Classroom (monitoreo → análisis de dificultad → propuesta "¿la hago?" → generación del entregable → **entrega solo con aprobación explícita, regla dura**).
- **Verificación E2E:** con una foto real de horario y una foto real de pizarrón, el ciclo completo termina con la explicación recibida, la foto en la carpeta de la materia, el tema registrado y la tarea en el kanban; una tarea de Classroom de prueba genera un PPTX que llega por Telegram y NO se entrega sin el "sí".
- **Esfuerzo:** 3–4 S.

### Fase 7 — Archivo permanente y finanzas
- **Objetivo:** Hermes archivista: caché efímero ≠ biblioteca permanente.
- **Dependencias:** Fase 5 (tablero), esquema `media_files` (Fase 1 lo crea, esta lo extiende).
- **Entregables:** árbol `biblioteca/` (E2) + `retention_class=permanent` en `media_files`; clasificador de entrada (foto llega → Gemini Vision decide: ticket/familiar/escuela/contenido/otro → pregunta si duda); flujo tickets (extraer monto+categoría → tabla `gastos` → imagen a `biblioteca/finanzas/AAAA-MM/`); reporte mensual con evidencia fotográfica (PDF); fotos familiares → `biblioteca/familia/AAAA/` con confirmación de guardado (para que puedas borrar del iPhone); limpieza mensual **siempre con autorización** (lista de candidatos a basura → apruebas → borra).
- **Verificación E2E:** foto de ticket real → aparece en el reporte del mes con la imagen adjunta y la categoría correcta; 10 fotos familiares → organizadas y confirmadas; la limpieza mensual NO borra nada sin el "sí".
- **Esfuerzo:** 2 S.

### Fase 8 — Producción de video
- **Objetivo:** del "alista el setup" al borrador en la línea de tiempo.
- **Dependencias:** Fase 5 (cola — la edición corre encolada de noche).
- **Entregables:** (A) Setup: script `alista_setup` en la M1 (vía SSH desde Hermes) que abre QuickTime con la ventana de grabación de iPhone, carga el guion del día al teleprompter Elgato (su app acepta archivos/URL — verificar método exacto en la OT), fija el Yeti Nano como entrada, y responde "setup listo, jefe" — disparado por "voy en 20 minutos". Enchufe inteligente WiFi (~$250–350 MXN, ej. Sonoff S26/TP-Link Tapo) para encender teleprompter/luces por comando; acomodar la cámara físicamente NO es automatizable sin comprar motorización (no vale la pena). (B) Corte de silencios v2 con los parámetros de E6 y **verificación automática anti-destrucción de habla** antes de entregarte nada. (C) Edición en línea de tiempo vía API de scripting de DaVinci Resolve Studio (Python) en la M1: importar material, ordenar clips, aplicar cortes de silencio aprobados, marcar capítulos — **sin renderizar, sin efectos**; proyecto queda abierto para tu revisión. (D) Cadena de contenido: tendencias YouTube (API gratuita) × nodos de Obsidian → propuestas de guion; programación de grabación en calendario; analítica del canal semanal. Las skills `davinci-resolve`, `youtube-analytics` y `social-media-content-repurposer` se auditan y reescriben sobre estos flujos reales en vez de descartarse.
- **Verificación E2E:** un video de prueba con silencios pasa el pipeline y la re-transcripción confirma 0 palabras perdidas (E6); "alista el setup" deja QuickTime+guion+mic listos medido con cronómetro (<2 min sin tocar nada); un proyecto DaVinci queda armado en la línea de tiempo tras una corrida nocturna encolada.
- **Esfuerzo:** 4 S.

### Fase 9 — Proactividad
- **Objetivo:** reglas explícitas + detección espontánea, sin volverse spam.
- **Dependencias:** Fases 4, 5, 6 (memoria, cola, horario).
- **Entregables:** motor de reglas ("recuérdame X los domingos 8pm") sobre el scheduler existente; detección espontánea en conversación (compromisos con fecha mencionados de pasada → periodo de entrenamiento 2 semanas con "¿la anoto?" → luego automático con resumen diario de lo capturado); selección de canal por contexto (última actividad: Telegram vs voz vía Piper en la HP); seguimiento de metas de vida (peso, ahorro Mac Mini, ritmo YouTube/TikTok, cuatrimestre) con check-in semanal, alimentado por lo que digas en conversación normal.
- **Verificación E2E:** el guion textual del maestro ("mencionaste una reunión hoy a las 3…") reproducido con datos reales de una semana de uso; una regla explícita dispara 4 domingos seguidos.
- **Esfuerzo:** 2–3 S.

### Fase 10 — Trading en papel
- **Objetivo:** el laboratorio de 2 meses, midiendo desde el día uno.
- **Dependencias:** Fase 5 (cola, tablero), Fase 9 (notificaciones).
- **Entregables (v1.1):** feed gratuito desde la API pública de Binance + CoinGecko (RSS/Brave para noticias); motor de estrategia determinista versionada; **laboratorio permanente en el testnet de spot de Binance** (API real, corridas diarias que no se apagan al graduar); registro completo por operación; tablero de desempeño con comparativa laboratorio-vs-real; apagados automáticos y OCO probados en testnet; ruta de pesos documentada (Bitso como puerta SPEI regulada). La fase real **no se activa** hasta cumplir los criterios de B4, y las decisiones reales serán semanales con aprobación por operación.
- **Verificación E2E:** 2 semanas de simulación continua sin caídas; el reporte de calibración se genera y los números cuadran contra el registro crudo a mano en 5 operaciones muestreadas.
- **Esfuerzo:** 3 S (+2 S cuando gradúe a real).

### Fase 11 — Voz completa y USB-llave (horizonte Mac Mini)
- **Objetivo:** lo diferido de B5 y B8.
- **Dependencias:** Mac Mini comprada (voz); Fase 2+4 estables (USB).
- **Entregables:** USB-llave completo (bóveda VeraCrypt, lanzadores 3 OS, toolkit, registro de autorización) — **esto NO requiere la Mac Mini y puede adelantarse si lo necesitas para la escuela**; pipeline de voz conversacional en Mac Mini (Whisper streaming + Kokoro/Piper es_MX fine-tuneada, full-duplex con VAD); skills de ciberseguridad doméstica (E7); hardware de recámara evaluado con datos de uso real.
- **Esfuerzo:** USB 2 S; voz 4–6 S (post-Mac Mini).

**Ruta crítica (v1.2):** 0 ✅ → **0.5 (emergencia, hoy)** → 1 (resto) → 2 → 4 → 5 → 6. Todo lo demás puede reordenarse por ganas sin romper dependencias; estas seis no.

---

# D. ÓRDENES DE TRABAJO PARA CLAUDE CODE

**Cabecera común** — pégala al inicio de CADA sesión, antes de la orden de la fase:

```
REGLAS DE ESTA SESIÓN (no negociables):
1. Modelo: Sonnet 4.6, esfuerzo medio. No escales de modelo por tu cuenta.
2. Deny-list activa: rm -rf, git push --force, DROP/DELETE SQL directo,
   instalar/ejecutar código de terceros no revisado, tocar credenciales o
   producción sin mostrar diff primero. sudo lo ejecuta Arturo, no tú
   (única excepción: systemctl restart hermes-gateway.service).
3. NUNCA confíes en lo que Hermes dice de sí mismo: verifica en disco,
   logs o API real.
4. Toda corrección de memoria vía memory_tool.py, nunca editando
   MEMORY.md/USER.md a mano.
5. Nada se da por cerrado sin la verificación E2E indicada en la orden.
   "El código se ve bien" no es verificación.
6. No dejes pendientes indefinidos: ante duda de diseño, decide con un
   supuesto razonable, márcalo como SUPUESTO en el reporte, y sigue.
7. Si necesitas subagentes: solo para lectura/investigación, y su
   resultado se acepta únicamente si el artefacto verificable existe y
   pasa el comando de verificación definido ANTES de lanzarlo.
8. Reporte final obligatorio con el formato: HECHO / VERIFICADO (comando
   y salida) / SUPUESTOS / PENDIENTE PARA ARTURO / NADA MÁS.
9. Presupuesto: cero servicios de paga nuevos. Portabilidad Linux↔macOS
   en todo código nuevo (pathlib, sin rutas hardcodeadas, sin GNU-only).
```

## OT-0 — Caja fuerte (git + fork)

```
CONTEXTO: repo Hermes en producción con 10 commits locales (2,016 líneas,
15 archivos) sin push. Fork vacío existe: arturocruz9602-sudo/hermes-agent.
Anomalía: el 19-jul se reportaron 13,222 commits solo-locales con tip de
origin/main = a7d7c02cb; el 20-jul un fetch dio 0 solo-locales, 2,327
commits nuevos, y a7d7c02cb ya no es ancestro de HEAD.

BLOQUE 1 — Respaldo del estado exacto:
1.1 cd al repo de producción. git status; git stash list; confirmar árbol
    limpio (si hay cambios sin commitear, commitéalos a una rama wip/).
1.2 git bundle create /mnt/seagate/backups/hermes_repo_$(date +%F).bundle --all
1.3 Verifica el bundle: git bundle verify <ruta>. Reporta salida.

BLOQUE 2 — Push al fork:
2.1 git remote add fork git@github.com:arturocruz9602-sudo/hermes-agent.git
    (si no hay llave SSH para GitHub, usa HTTPS y pide a Arturo el token;
    NO guardes el token en ningún archivo del repo).
2.2 git push fork HEAD:refs/heads/arturo/prod
2.3 git fetch origin; git branch upstream-main origin/main;
    git push fork upstream-main
2.4 Verificación: gh api o curl a la API de GitHub listando las ramas del
    fork; deben aparecer arturo/prod y upstream-main con los SHAs locales.

BLOQUE 3 — Diagnóstico de la anomalía (acotado, máx 30 min):
3.1 git reflog show origin/main | head -30 — ¿cuándo cambió la ref remota
    localmente?
3.2 Via API de GitHub: fecha de autor y committer de a7d7c02cb
    (GET /repos/NousResearch/hermes-agent/commits/a7d7c02cb). Si la API
    devuelve 404/422, el commit fue eliminado de upstream ⇒ evidencia de
    reescritura de main. Si existe, compara: git merge-base a7d7c02cb
    origin/main — si no hay base común, también es reescritura.
3.3 Veredicto en el reporte: (a) upstream reescribió main, o (b) el fetch
    del 19-jul estaba corrupto/desactualizado. Con la evidencia citada.
    No investigues más allá de estos comandos.

BLOQUE 4 — Congelar producción:
4.1 Crea ~/.hermes/UPGRADE_LOCK.md explicando que producción no se
    actualiza hasta cerrar Fase 2, con referencia a este documento.
4.2 En el venv de producción: pip freeze > ~/.hermes/prod_freeze_$(date +%F).txt
4.3 Agrega al shell de Arturo un alias defensivo:
    alias pip='echo "⚠ UPGRADE_LOCK activo — ver ~/.hermes/UPGRADE_LOCK.md"; false'
    SOLO en la sesión interactiva por default; documenta cómo saltarlo
    (command pip) para uso consciente.

REPORTAR: formato de la regla 8.
```

## OT-0.5 — Emergencia de credenciales (EJECUTAR ANTES QUE TODO)

```
CONTEXTO (docs/HISTORIAL.md): llaves expuestas el 4-jul (1 Google, 2
Gemini, 2 Groq, repetidas por Hermes en chat) y segundo hallazgo el
20-jul; rotación NUNCA confirmada; el tar de backup del repo git
accidental de ~/.hermes aún contiene .env/auth.json en texto plano;
cron roto ejecuta vigilar_hermes.sh cada 15 min en silencio.

1. INVENTARIO: lista las ~11 credenciales de .env con su servicio.
   Marca las 5 de exposición confirmada. NO imprimas valores completos
   en el chat ni en logs — solo últimos 4 caracteres para identificar.
2. ROTACIÓN GUIADA: para cada llave, dale a Arturo el paso a paso de
   su consola (Google AI Studio / Groq / etc.), espera la llave nueva
   (que Arturo pega DIRECTO en .env editándolo él, o vía un paste que
   se escribe a disco sin quedar en historial de shell), actualiza
   litellm/config.yaml si aplica, prueba 200 OK con la nueva, y
   CONFIRMA que la vieja devuelve 401/403 con una llamada real.
3. TAR DE BACKUP: extrae el contenido valioso a un directorio de
   trabajo, purga .env/auth.json y todo blob git con secretos
   (git filter-repo o eliminación del .git interno), recomprime
   cifrado (age con passphrase de Arturo), verifica el cifrado
   abriéndolo, y destruye el tar original (shred o rm + confirmación).
4. CRON: crontab -l completo; el vigilar_hermes.sh roto se elimina o
   se repara con logging a journald — decide por evidencia de si su
   función sigue teniendo sentido (probable: lo reemplazó el watchdog
   real). Nada corre en silencio: regla permanente.
5. BARRIDO FINAL: grep -r de fragmentos (últimos 8 chars) de CADA
   llave vieja sobre ~/.hermes, el árbol del fork, /mnt/seagate/backups
   accesibles y el historial git local. Resultado esperado: 0 hits en
   texto plano. Si aparece un hit en historial git del fork: evaluar
   filter-repo + force push COORDINADO con Arturo (única excepción
   permitida al no-force-push, documentada aquí).
6. CHANGELOG_SISTEMA.md: una línea por llave rotada, con fecha.
   ESTADO.md actualizado: "emergencia de credenciales CERRADA" solo si
   los 6 pasos tienen evidencia.
REPORTAR: tabla llave→rotada sí/no→vieja invalidada sí/no→hits de grep.
```

## OT-1 — Fugas urgentes

```
BLOQUE 1 — Consolidación de USER.md (vía memory_tool.py, jamás a mano):
1.1 Lee USER.md completo. Construye la lista de operaciones de
    supersede/corrección para las 8 contradicciones documentadas:
    - Trato: gana "Arturo/jefe/señor, NUNCA Tony". Elimina/supersede las
      entradas de las líneas ~52 y ~193.
    - Presupuesto: $100 MXN/mes. Supersede toda cifra distinta.
    - Watchdog real: ~/.hermes/scripts/watchdog.sh. Corrige línea ~222.
    - auto_fix_watcher.sh, fix_provider.sh, resurrection.sh,
      context_saver.sh: marcar como "archivados en backup 18-jul, no
      activos".
    - Groq: activo como fallback (litellm/config.yaml manda). Supersede
      "GROQ DESCARTADO".
    - LiteLLM: infraestructura central activa. Supersede "deprecated".
    - Pendientes de líneas ~214, ~224, ~228: marcar resueltos.
    - Redundancias (Iguala, español, presupuesto, no-inventar, Arial,
      Gemini/DeepSeek): consolidar cada hecho a UNA entrada canónica.
1.2 Antes de aplicar: muestra el plan completo de operaciones como diff
    conceptual y aplícalo en bloque. Después: relee USER.md y verifica
    con grep que "Tony" solo aparece en la prohibición, que solo hay una
    cifra de presupuesto, y que las rutas muertas ya no están.

BLOQUE 2 — cleanup_audio_cache():
2.1 Localiza dónde viven cleanup de images/documents. Escribe
    cleanup_audio_cache() con retención 48h, mismo patrón, y regístrala
    en el mismo ciclo. Test: crea un archivo con mtime falso de 3 días en
    cache/audio/, corre el ciclo, confirma que se borró y que uno de 1h
    sobrevive. Borra también el backlog real de 3 semanas (lista primero
    cuántos archivos y MB, luego borra).

BLOQUE 3 — Prueba E2E de notificación DeepSeek:
3.1 Con autorización explícita de Arturo EN ESTA SESIÓN (pídesela),
    dispara un despacho real mínimo a DeepSeek (~$0.01). Confirma en
    Telegram: notificación previa y posterior. Si alguna no llega,
    depura hasta que llegue. Registra el gasto en el contador mensual.

BLOQUE 4 — Escáner de secretos en Fase 2:
4.1 Importa/invoca el escáner de memory_tool.py dentro de
    fase2_extract_candidates.py, antes de escribir candidatos. Test: mete
    en un JSONL de prueba un mensaje con "API_KEY=sk-falsa123..." y
    confirma que el candidato sale bloqueado/redactado.

BLOQUE 5 — Whisper → gateway:
5.1 Localiza en el adapter de Telegram dónde se reciben voice notes (hoy
    solo se guardan). Conecta: descarga → whisper local (modelo small o
    el instalado) → texto → inyectar al flujo normal como mensaje del
    usuario, con prefijo interno [transcrito de voz].
5.2 Cuida el caso de audios largos (>2 min): transcribe en chunks.
5.3 E2E: Arturo manda una nota de voz real diciendo "Hermes, anota:
    comprar filamento"; Hermes debe responder al contenido.

BLOQUE 6 — allowed_fails rate-limit vs error duro:
6.1 En la config de LiteLLM/fallback, distingue HTTP 429 (cuota: reintento
    con backoff en el mismo proveedor + cola) de 4xx/5xx duros (salto
    inmediato al siguiente proveedor, para que chat-fallback3/OpenRouter
    entre cuando Groq falla por parámetros). Test con mocks de ambos.

REPORTAR: formato regla 8, incluyendo conteo de entradas de USER.md
antes/después.
```

## OT-2 — Blindaje y actualización a 0.19.x

```
PROHIBIDO tocar el venv de producción hasta el bloque 6.

BLOQUE 1 — Rebase en paralelo:
1.1 git worktree add ~/hermes-019 arturo/base (crea arturo/base desde
    arturo/prod si no existe).
1.2 git fetch origin; actualiza upstream-main; en la worktree:
    git rebase upstream-main. Resuelve conflictos archivo por archivo
    siguiendo la tabla de destinos del HAS §B2. En cada conflicto,
    registra en MIGRATION_LOG.md: archivo, qué cambió upstream, cómo se
    resolvió.

BLOQUE 2 — Extracción a plugins:
2.1 complexity_detector.py → plugin. Investiga primero la API real de
    plugin lifecycle hooks en 0.19 (lee el código, no la docs). Si el
    hook de pre-turno existe: migra y borra el parche del core. Si NO
    existe un hook viable: déjalo como parche y documenta por qué
    (SUPUESTO invalidado, no lo fuerces).
2.2 Igual para slash_commands propios y el adapter de Telegram.
2.3 Los archivos de seguridad (approval.py, file_tools.py,
    context_switch_guard.py, toolset_validation.py) se quedan como
    parches SIEMPRE, aunque exista hook. Razón en HAS §B2.

BLOQUE 3 — venv nuevo:
3.1 python -m venv ~/venvs/hermes-019; pip install -e ~/hermes-019
3.2 Instala deps con las versiones del freeze de OT-0 donde no choquen.

BLOQUE 4 — Suite de smoke tests (créala en tests/smoke/):
    S1 arranque de CLI, S2 arranque de gateway apuntando a un bot de
    prueba o modo dry-run, S3 slash commands propios, S4 detector de
    complejidad con 5 mensajes de la lista validada, S5 guardias de
    permisos (intento de rm -rf simulado → denegado), S6 cola de
    mensajes, S7 tick de curator (dry), S8 lectura de MEMORY/USER,
    S9 pipeline de media (imagen de prueba → media_files), S10 fallback
    de proveedores con mock. Cada uno con assert real, no con "corrió".

BLOQUE 5 — Ensayo de actualización futura:
5.1 Simula: git rebase sobre un commit upstream 50 commits más nuevo.
    Documenta el procedimiento completo en la skill hermes-upgrade
    (SKILL.md nueva, con el checklist exacto).

BLOQUE 6 — Cambio de producción (con Arturo presente):
6.1 systemctl stop hermes-gateway; respaldo incremental de ~/.hermes;
    cambiar el venv del service file al nuevo; systemctl start.
6.2 Corre los 10 smoke contra producción real. Si ≥1 falla: rollback
    inmediato al venv viejo (documenta el comando exacto de rollback
    ANTES de cambiar).
6.3 24h de observación: revisar logs al día siguiente antes de declarar
    cerrada la fase.

REPORTAR: tabla archivo→destino final real vs planeado, y resultado de
los 10 smoke.
```

## OT-3 — Skills

```
BLOQUE 1 — Limpieza:
1.1 Respaldo: tar de ~/.hermes/skills a /mnt/seagate/backups/.
1.2 Borra los 2 archivos-404 (verifica primero byte-size 10,220 e
    identidad con sha256 entre ambos; registra en el historial de
    cambios).
1.3 Duplicados: para cada par (test-driven-development,
    systematic-debugging, requesting-code-review): diff completo. Si
    superpowers/ ⊇ software-development/: archiva la segunda. Si
    divergen: fusiona en superpowers/ tomando lo mejor de ambas, archiva
    la otra. Registra decisión por par.

BLOQUE 2 — Scripts rotos:
2.1 powerpoint (validators) y ocr-and-documents (marker): instala deps
    en el venv (pip install validators marker-pdf), corre el script de
    cada skill con un archivo real de prueba hasta que funcione.
2.2 comfyui (torch, websocket): NO instalar torch en el i3 (2GB+ de
    disco, inutilizable sin GPU). Archivar ambas skills de comfyui con
    nota "reactivar en Mac Mini". SUPUESTO: Arturo no usa ComfyUI hoy —
    si lo usa, que lo diga y se reevalúa.

BLOQUE 3 — Bug de .usage.json:
3.1 En tools/skill_usage.py: cambia la llave de indexado de name: a la
    ruta relativa del SKILL.md. Migra el .usage.json existente: entradas
    sin colisión se reasignan a su ruta; los 3 pares colisionados se
    resetean a 0 con nota en historial (dato irrecuperable, documentado).
3.2 Test E2E: usa dos skills homónimas y verifica contadores separados.

BLOQUE 4 — Metadata (esquema en HAS §E3):
4.1 Script idempotente que agrega los campos faltantes al frontmatter de
    las 136 skills (valores iniciales derivables: origin, status,
    pinned, last_verified, deps). Corre y commitea.
4.2 Marca pinned:true en TODAS las de desarrollo de software, bases de
    datos, redes y ciberseguridad (decisión de Arturo, no de curator).
4.3 Ajusta la config del curator: prune_builtins sigue true, pero
    verifica que pinned/protected cubra las hand-written + las del 4.2.

BLOQUE 5 — Comando de auditoría:
5.1 hermes skills audit (o script ~/.hermes/scripts/skills_audit.py):
    reporta 404s, duplicados por name Y por ruta, imports rotos
    (importlib de cada script en dry), skills sin uso >90 días no
    pinned, frontmatter incompleto. Salida JSON + resumen humano. Este
    script lo correrá Hermes semanalmente (Fase 5 lo agenda).

REPORTAR: inventario final (activas/archivadas/pinned) y salida del
audit en limpio.
```

## OT-4 — Memoria

```
BLOQUE 1 — Aprobación de candidatos:
1.1 Construye el flujo interactivo por Telegram: /memoria revisar →
    Hermes presenta candidato + fuente textual de la capa cruda +
    botones [Aprobar][Rechazar][Editar]. Aprobado → INSERT en
    memoria_estructurada con fuente. Todo pasa por el escáner de
    secretos (ya integrado en OT-1).
1.2 Corre el proceso con los 20 candidatos verificados existentes,
    CON Arturo en la sesión.
1.3 Agenda la corrida semanal de fase2_extract_candidates.py (domingo
    9pm) que deja los candidatos nuevos en cola de revisión y avisa.

BLOQUE 2 — Índice semántico:
2.1 pip install sqlite-vec sentence-transformers; descarga
    intfloat/multilingual-e5-small. Mide RAM del proceso de embedding
    con 100 chunks reales; si >1.5GB o el i3 se ahoga, degrada a
    paraphrase-multilingual-MiniLM-L12-v2 y repórtalo.
2.2 Crea memoria_semantica.db con el esquema de HAS §E4.
2.3 Indexador incremental: lee hermes_raw (chunks de ~10 mensajes),
    memoria_estructurada, frontmatter+primeras 40 líneas de cada
    SKILL.md activa, y los .md del vault de Obsidian. Guarda cursor de
    avance; corre por systemd timer a las 3am; primer backfill de los
    ~15,800 mensajes puede tardar horas — lánzalo en nohup y verifica al
    final el conteo de filas vs chunks esperados.
2.4 Retrieval híbrido: función buscar(q) = unión de FTS5 top-20 y
    vector top-20, re-rank con score = 0.5·similitud + 0.3·recencia_exp
    + 0.2·importancia. Exponla como tool de Hermes (memory_search) y
    conéctala al prompt builder para inyección de contexto (top-5, con
    presupuesto máximo de 1,200 tokens).
2.5 Diario de reflexión: job semanal (Gemini) que escribe 5
    observaciones de la semana y las indexa con importancia=alta.

BLOQUE 3 — Verificación E2E:
3.1 Sesión limpia de Hermes: "¿cómo me conecto por SSH a la MacBook?"
    → debe recuperar el procedimiento real de las notas. 
3.2 3 preguntas más sobre hechos viejos conocidos de la capa cruda.
3.3 Confirmar 3 noches de reindexado automático en logs.

REPORTAR: filas indexadas por fuente, RAM/tiempo del backfill, y las 4
pruebas de retrieval con resultado.
```

## OT-5 — Tablero y cola

```
PRERREQUISITO (Arturo, 5 min): crear integración interna en
notion.so/my-integrations, compartir la página raíz "Hermes" con la
integración, y pegar NOTION_API_KEY=... en ~/.hermes/.env.

BLOQUE 1 — Una sola skill de Notion:
1.1 Diff entre notion-api (personal) y notion (bundled). Consolida en
    notion-api, archiva la bundled, verifica con una escritura real.

BLOQUE 2 — Tablero (databases de Notion, creadas por API):
    Vistas: Hoy (checklist generado + horario del día), Kanban (espejo
    de kanban.db, unidireccional Hermes→Notion; el kanban real se sigue
    operando por Telegram), Finanzas (suma del mes por categoría +
    gasto de APIs), Avance HAS (E8), Cola de tareas (estado vivo),
    Escuela (se llena en Fase 6). Sync cada 15 min por timer; el sync
    calcula diff y solo escribe cambios (respeta rate limits de Notion).

BLOQUE 3 — Cola v2 (esquema HAS §E5):
3.1 Migra el mecanismo de Tarea C a la tabla task_queue con la máquina
    de estados encolada→en_proceso→resuelta→notificada.
3.2 Reintentos: escalera Groq→Gemini→OpenRouter con backoff; máx 5
    intentos por proveedor; si los 3 fallan, estado=atorada y
    notificación "necesito ayuda con esta".
3.3 Watchdog: tarea >2h en en_proceso → re-encolar (idempotencia:
    result_hash evita duplicar efectos).
3.4 GARANTÍA: la transición a resuelta SIEMPRE dispara la notificación
    "ya está, puedes revisarla ahora o más tarde" y solo entonces marca
    notificada. Si Telegram falla, reintenta la notificación — la tarea
    no puede quedar resuelta-sin-avisar.

BLOQUE 4 — Checklist diario:
4.1 Job 6:30am: genera la lista (kanban del día + horario + metas con
    check-in pendiente) → publica en Notion vista Hoy + mensaje
    Telegram. El palomeo es manual; el job de las 11pm lee lo palomeado
    y lo registra en state.db para la métrica de avance.

VERIFICACIÓN E2E: la prueba de las 15 tareas sintéticas con el proveedor
primario deshabilitado (ver Fase 5 del plan). Reporta la traza de cada
una.
```

## OT-6 — Tutor académico

```
BLOQUE 1 — Horario por foto: Gemini Vision → parser a tabla horario
(materia, día, hora_inicio, hora_fin, aula, profesor) → confirmación con
Arturo de la tabla extraída (mostrarla, corregir en chat) → alta en
Notion/Escuela. Manejar el caso de re-envío (nuevo cuatrimestre =
reemplaza con archivado del anterior; toda tabla académica lleva campo
cuatrimestre según la regla F7 — el historial de cuatrimestres es
permanente, nunca se pisa).

BLOQUE 2 — Pizarrón: foto+texto → (a) guardar original en
biblioteca/escuela/<materia>/<AAAA-MM-DD>_<n>.jpg (la materia se infiere
del horario por día/hora de recepción; si ambiguo, pregunta); (b) Vision
extrae contenido; (c) identificar tema y registrarlo en tabla
temas_vistos; (d) investigación (Brave + Gemini) → explicación
pedagógica con analogías (recuerda: Arturo es maestro de formación,
quiere claridad pedagógica) → enviada por Telegram y guardada como nota
en Obsidian/escuela/<materia>/; (e) detección de tareas mencionadas →
kanban con fecha.

BLOQUE 3 — Repaso proactivo: job diario 7pm que cruza temas_vistos sin
repaso + horario de mañana + kanban + rutina de gym (pedir a Arturo sus
horarios de gym una vez, guardarlos como hecho aprobado) → propone hueco
concreto estilo "mañana a las 5 cuando llegues del gym, ~1 hora".

BLOQUE 4 — Tareas dictadas: intent "me dejaron X, hazlo y recuérdame
mandarlo el viernes a las 10, avísame 2h antes" → crear el archivo
(usando skills pptx/docx/pdf reparadas) → encolar → recordatorio viernes
8am y 10am. E2E con un ejemplo real.

BLOQUE 5 — Classroom: OAuth de Google Classroom (scope solo-lectura de
cursos y tareas + lectura de anuncios; Arturo autoriza el flujo OAuth él
mismo); polling cada 30 min; nueva tarea → análisis de dificultad
(rúbrica simple: entregable, tema conocido, esfuerzo estimado) →
propuesta "¿la hago y te la envío para verificar?" → si sí, generar y
mandar por Telegram. REGLA DURA CODIFICADA: no existe ninguna ruta de
código que entregue/suba nada a Classroom sin aprobación explícita por
mensaje; de hecho v1 NO implementa entrega automática — Arturo entrega
a mano lo que apruebe.

VERIFICACIÓN E2E: la descrita en Fase 6 del plan, con fotos reales.
```

## OT-7 — Archivo y finanzas (compacta)

```
1. Crear árbol biblioteca/ (HAS §E2) + retention_class=permanent en
   media_files + clasificador de entrada con Vision (ticket / familiar /
   escuela / contenido / otro; ante duda pregunta por Telegram).
2. Tickets: Vision extrae fecha, comercio, monto, categoría (gasolina,
   saldo/internet, DeepSeek, gimnasio, trabajo/escuela/Hermes) → tabla
   gastos → imagen a biblioteca/finanzas/AAAA-MM/. Corrección por chat
   ("era gasolina, no trabajo").
3. Reporte mensual: PDF (skill pdf) con totales por categoría, delta vs
   mes anterior, y miniaturas de evidencia. Se genera el día 1, llega
   por Telegram, se archiva en biblioteca/finanzas/reportes/.
4. Fotos familiares: →biblioteca/familia/AAAA/ + confirmación explícita
   "guardadas N fotos, ya puedes borrarlas del iPhone".
5. Limpieza mensual: lista de candidatos (caché vencida + duplicados por
   hash) → aprobación → borrado. Cero borrado sin "sí".
E2E: ticket real de gasolina de punta a punta; verificar que el monto
del reporte cuadra con la suma manual.
```

## OT-8 — Video (compacta)

```
1. Corte de silencios v2 con parámetros HAS §E6 y verificación
   anti-destrucción obligatoria; se prueba primero contra el material
   del fallo original si aún existe.
2. Script alista_setup en la M1 (AppleScript/Shortcuts + shell vía SSH):
   abrir QuickTime → New Movie Recording, seleccionar iPhone y Yeti
   Nano (cliclick o AppleScript UI scripting; pedir permisos de
   Accesibilidad una vez), cargar guion del día en la app del
   teleprompter Elgato (investigar en la M1 el método: archivo
   observado / URL / paste). Trigger: frase "voy en N minutos".
   Enchufe inteligente para teleprompter/luces: proponer modelo y precio
   a Arturo antes de comprar.
3. Edición en línea de tiempo: API Python de DaVinci Resolve Studio en
   la M1 (Resolve corriendo headless no es posible — la app debe estar
   abierta; el script la abre). Pipeline: crear proyecto desde template
   → importar carpeta indicada → clips al timeline en orden → aplicar
   lista de cortes aprobada del paso 1 → guardar. SIN render, SIN
   efectos. Corre encolado de noche vía cola v2.
4. Cadena de contenido: YouTube Data API (gratuita) para tendencias +
   analítica; cruce con nodos de Obsidian para propuestas de guion;
   programación en calendario. Reescribir las 3 skills existentes
   (davinci-resolve, youtube-analytics, social-media-content-repurposer)
   sobre estos flujos verificados.
E2E: los tres criterios de la Fase 8 del plan.
```

## OT-9 — Proactividad (compacta)

```
1. Motor de reglas explícitas sobre el scheduler (tabla reglas_recordatorio;
   parser de lenguaje natural con Gemini → regla estructurada →
   confirmación).
2. Detección espontánea: post-proceso de cada conversación (Gemini,
   gratis) que extrae compromisos con fecha/hora → modo entrenamiento 2
   semanas ("¿la anoto?") → automático + resumen diario 9pm de lo
   capturado. Umbral anti-spam: máx 3 preguntas "¿anoto?" por día.
3. Canal por contexto: si hubo actividad Telegram <30 min → Telegram;
   si no y es horario despierto → Piper TTS en bocina de la HP + Telegram.
4. Metas de vida: tabla metas con check-in semanal (peso, ahorro,
   videos/semana, clips/semana); los datos se capturan de conversación
   normal ("hoy pesé 112") vía la misma detección espontánea.
E2E: guion de la reunión cancelada reproducido con datos reales.
```

## OT-P — Permisos y fin de la fricción de terminal (30 min, alta prioridad)

```
OBJETIVO: que Arturo no vuelva a teclear en terminal para tareas de
rutina, sin darle a Claude Code un cheque en blanco.
1. Crea/edita .claude/settings.json del repo con allowlist de Bash:
   git (status/log/diff/add/commit/push al fork), pytest y el arnés de
   pruebas, grep/rg/ls/cat, python y pip DENTRO del venv, sqlite3 en
   lectura, systemctl status/restart de hermes-gateway y litellm,
   journalctl de esas units. DENY permanente: sudo genérico, rm -rf,
   push --force, DROP/DELETE SQL, edición de .env, ejecución de código
   de terceros sin revisar.
2. Propón el contenido EXACTO de /etc/sudoers.d/hermes-claude con
   NOPASSWD SOLO para: systemctl restart/stop/start de
   hermes-gateway.service y litellm.service, systemctl daemon-reload,
   y journalctl de esas units. Muéstraselo a Arturo; él lo instala UNA
   vez con visudo (última vez que se le pide terminal para rutina).
3. Registra en PROTOCOLO como C15: la allowlist crece con evidencia
   (comando pedido ≥3 veces sin incidente → candidato, registrado),
   nunca por comodidad del momento.
VERIFICACIÓN: correr una sesión completa de trabajo real sin que Arturo
teclee un solo comando; contar cuántas veces se le pidió permiso (meta:
solo por gasto, seguridad o irreversibles).
```

## OT-QA — Cuenta QA de Telegram (condicionada a cerrar L13)

```
PRERREQUISITO DURO: L13 cerrado (la bóveda debe dejar de fabricar
confirmaciones de guardado antes de recibir el session string, que es
acceso total a esa cuenta). Chip ya comprado (Bait).
1. Crear cuenta de Telegram "Hermes QA" con el chip nuevo. Madurarla
   ≥5 días con uso manual normal antes de automatizar (evita ban).
2. Userbot (Telethon/Pyrogram) controlado por Claude Code; session
   string SOLO en la bóveda cifrada verificada. Volumen bajo (decenas
   de mensajes/día).
3. Extender el arnés (Bloque V) con: enviar_texto, enviar_voz,
   enviar_foto, leer_respuesta, cerrar_conversacion.
4. Marcado origen=qa en todo lo que siembre + limpiar_memoria_qa.py
   que borra solo eso. Verificar conteo de hechos reales antes/después.
5. Conectar con docs/GUION_PRUEBAS.md: el arnés corre la rutina diaria;
   la cuenta QA produce la evidencia [E2E real] de cierre de bloques.
VERIFICACIÓN: correr el Bloque 10 del guion (día completo) de punta a
punta sin que Arturo mande un solo mensaje, con reporte por caso.
```

## OT-9.5 — Modo llamada interino (Gemini Live API)

```
PROPÓSITO: llamadas cortas manos-libres con Hermes (dar tareas,
preguntar avances, rebotar ideas) desde el iPhone con audífonos.
Es PUENTE, no destino: la voz local llega con la Mac Mini, y "Hermes
en la oreja todo el día" queda formalmente diferido a esa fase.

PRERREQUISITO (Arturo, 5 min): crear un proyecto de Google NUEVO y
DEDICADO para esto (correo independiente, como el resto de sus llaves)
y pegar GEMINI_LIVE_KEY en .env. Confirmado: sus llaves Gemini viven en
correos/proyectos independientes, así que las cuotas NO compiten entre
sí — mantener esa disciplina aquí.

1. Página web mínima servida desde la HP (puerto local, accesible SOLO
   por Tailscale desde el iPhone): un botón grande "Llamar a Hermes",
   WebRTC/WebSocket de audio contra la Live API (audio nativo,
   interrupciones reales). Guardar como acceso directo en la pantalla
   de inicio de Safari.
2. Puente de contexto: al abrir sesión, inyectar system prompt con
   USER.md consolidado + top-5 del índice semántico sobre "hoy" +
   tareas activas del kanban. Al cerrar (o al corte), la transcripción
   pasa por el flujo normal de Hermes (detección de tareas, memoria,
   kanban) y llega resumen por Telegram.
3. Manejo de límites duros de la Live API: conexión ~10 min / sesión de
   solo-audio máx 15 min / contexto de sesión 128k; escuchar la señal
   "going away" y reconectar automático re-inyectando el contexto
   resumido. Si llega un 429: avisar con Piper local ("se acabó la
   cuota de voz por ahora, jefe, sigo por Telegram") y degradar.
4. Registro de consumo: contar minutos de llamada por día en state.db
   y mostrarlos en la vista de Avance (para saber cuándo la capa
   gratuita queda chica y con qué evidencia).
E2E: llamada real de 3 min desde la calle (datos móviles + Tailscale):
dictar una tarea, colgar, y verificar que quedó en el kanban y llegó
el resumen por Telegram. Probar también una sesión que cruce los 10
min y verificar la reconexión sin perder el hilo.
```

## OT-10 — Trading: laboratorio Binance + puerta Bitso

```
ARQUITECTURA (HAS §B4 v1.1): Binance = operación/entrenamiento;
Bitso = entrada/salida de pesos; lista blanca BTC, ETH, USDT (+SOL
satélite condicionado); laboratorio diario permanente + decisiones
reales semanales.

1. Feed de mercado: API pública de Binance (velas diarias y 4h de
   BTC/MXN o BTC/USDT, ETH, SOL) + CoinGecko de respaldo; velas en
   trading.db. Noticias: RSS CoinDesk/Cointelegraph/Google News +
   Brave Search, resumidas 1 vez al día por el alias trading-analista
   (LiteLLM: Gemini→Groq→OpenRouter→DeepSeek solo autorizado — el
   módulo es agnóstico al modelo por diseño).
2. Estrategia v1 versionada en estrategia.yaml (reglas deterministas,
   sin ML al inicio): tendencia + gestión de riesgo (posición máx 10%
   del capital, stop-loss obligatorio, OCO, correlación máx 2
   posiciones >0.7, y veto por noticias: si el resumen del día marca
   evento de alto riesgo, no se abre posición).
3. LABORATORIO PERMANENTE: cuenta en el testnet de spot de Binance
   (API real, dinero falso). Corre DIARIO por systemd timer, para
   siempre — no se apaga al graduar. Registra cada operación:
   timestamp, señal, razonamiento, confianza (0-100), órdenes,
   resultado. Prohibido operar sin registro.
4. Ciclo semanal real (cuando gradúe): domingo por la noche Hermes
   compara la semana del laboratorio vs las propuestas reales y genera
   el reporte de calibración. Propuestas reales: 1-3 por semana, por
   Telegram, con razonamiento y exposición acumulada; ejecución SOLO
   con "sí" explícito (HAS §B4, permanente).
5. Panel en Notion: expectativa, win rate, drawdown, curva de capital,
   calibración confianza-vs-acierto, y comparativa laboratorio-vs-real.
6. Apagados automáticos: -3% día / -6% semana (probados en testnet).
7. Graduación a dinero real SOLO con los criterios de §B4 cumplidos.
   La OT de dinero real incluirá: llaves API de Binance solo-trade SIN
   retiro + whitelist de IP de la HP, llaves fuera del repo, cuenta
   Bitso verificada como puerta SPEI, y la regla "ganancia realizada
   aprobada → transferencia a Bitso/banco, nada vive en Binance".
   Recordatorio fiscal: las ganancias causan ISR; Hermes registra todo
   para la evidencia, la obligación es de Arturo.
E2E: 2 semanas continuas de laboratorio en testnet sin caídas +
auditoría manual de 5 operaciones contra el registro + un ciclo
completo simulado de retiro (testnet→cálculo de ruta Bitso documentada).
```

## OT-11 — USB-llave (adelantable) y voz Mac Mini

```
USB (no requiere Mac Mini):
1. Particionar USB: partición A VeraCrypt (llave SSH hermes-portable
   dedicada + tailscale authkey re-generable + doc de emergencia),
   partición B intercambio exFAT con lanzadores start-{linux,macos,
   windows} y toolkit portable (binarios estáticos: tailscale, clamav
   portable, scripts de inventario/red).
2. Lanzador: montar bóveda (pide passphrase) → levantar tailscale →
   ssh arturo@hp -i llave → hermes cli. Probar en los 3 OS de verdad
   (Windows: usar una VM o la compu de la escuela).
3. Flujo de autorización de terceros: texto de consentimiento en el
   lanzador → Hermes registra en state.db (nombre, fecha, alcance) →
   toda acción del toolkit valida alcance. Revocación: borrar la llave
   hermes-portable de authorized_keys de la HP (documentar el comando).
4. Modo sin internet: toolkit corre local, reportes a partición B,
   ingesta al volver a casa (script ingest_usb.sh).

Voz (post-Mac Mini): pipeline Whisper streaming + VAD (silero) + LLM +
Kokoro-82M/Piper es_MX; full-duplex con cancelación de eco; despertar
por botón del audífono. Se especifica en detalle cuando exista el
hardware — no antes, para no diseñar en el aire.
```

---

# E. CÓDIGO Y ESPECIFICACIONES CONCRETAS

## E1. Convención de archivos — VALIDADA con extensiones

La propuesta existente (bucket por fecha, nombres con timestamp+hash, tabla `media_files`, retenciones) **se aprueba tal cual para el caché**, con dos extensiones:

1. **`retention_class`** gana un valor nuevo: `permanent`. Un archivo `permanent` no tiene `expires_at` y su `filepath` apunta a `biblioteca/`, no a `cache/`.
2. **La decisión caché-vs-biblioteca la toma el clasificador de entrada** (OT-7), nunca el tiempo: nada se "promueve" automáticamente por viejo, y nada permanente se borra por cron.

## E2. Árbol de la biblioteca permanente

```
/mnt/seagate/biblioteca/
├── escuela/<materia>/            # fotos de pizarrón, PDFs, entregables
├── finanzas/
│   ├── AAAA-MM/                  # tickets del mes
│   └── reportes/                 # PDF mensual con evidencia
├── familia/AAAA/
├── contenido/
│   ├── guiones/                  # fuente en Obsidian; aquí exports
│   ├── material/<slug-video>/    # crudo por video
│   └── publicados/
├── proyectos/<nombre>/
└── inbox/                        # clasificados "otro", revisar mensual
```
Reglas: la Seagate es el hogar (la HP solo cachea); todo `permanent` entra a `media_files` con su categoría; respaldo de `biblioteca/` entra al mismo ciclo de backups que `~/.hermes`.

## E3. Esquema de metadata de skills (frontmatter)

```yaml
name: systematic-debugging          # único POR RUTA tras el fix
version: 2.1.0                      # semver; bump obligatorio al editar
origin: bundled | agent | arturo | claude
status: active | archived
pinned: true                        # el curator no la toca
category: desarrollo | escuela | contenido | finanzas | sistema | ...
deps: [python: [validators], system: []]   # para el audit de imports
last_verified: 2026-07-21           # última vez que su script corrió OK
verified_by: claude-code | manual
changelog: CHANGELOG.md             # relativo a la carpeta de la skill
telemetry_note: "contadores en .usage.json por ruta relativa"
```
El campo `last_verified` es el que permite "detectar información obsoleta": el barrido semanal marca `stale` toda skill activa con `last_verified` > 180 días y la mete a la cola de mantenimiento.

## E4. Esquema del índice semántico

```sql
-- memoria_semantica.db
CREATE TABLE chunks (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,          -- 'raw' | 'hechos' | 'skill' | 'obsidian'
  source_ref TEXT NOT NULL,      -- ruta/fecha+offset del chunk (auditable)
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,      -- del contenido, no del indexado
  importancia REAL DEFAULT 0.3,  -- 0-1; hechos aprobados=0.8, reflexión=0.9
  indexed_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE chunks_fts USING fts5(content, content=chunks);
CREATE VIRTUAL TABLE chunks_vec USING vec0(embedding float[384]);
CREATE TABLE index_cursor (source TEXT PRIMARY KEY, last_ref TEXT);
```
Ranking de retrieval: `score = 0.5·cos_sim + 0.3·exp(-días/90) + 0.2·importancia`, top-5, presupuesto 1,200 tokens de inyección.

## E5. Cola de tareas v2

```sql
CREATE TABLE task_queue (
  id INTEGER PRIMARY KEY,
  descripcion TEXT NOT NULL,
  payload TEXT NOT NULL,            -- JSON de la tarea
  estado TEXT NOT NULL DEFAULT 'encolada',
    -- encolada | en_proceso | resuelta | notificada | atorada
  proveedor_actual TEXT,
  intentos INTEGER DEFAULT 0,
  result_hash TEXT,                 -- idempotencia en re-encolado
  resultado TEXT,
  chat_id TEXT NOT NULL,            -- a quién notificar y por dónde
  created_at TEXT, started_at TEXT, resolved_at TEXT, notified_at TEXT
);
```
Invariantes (se verifican con un test): (1) toda fila llega tarde o temprano a `notificada` o `atorada`+aviso; (2) `resolved_at NOT NULL ⇒ notified_at NOT NULL` dentro de los siguientes 5 min o hay reintento activo; (3) el watchdog corre cada 30 min.

## E6. Corte de silencios — parámetros y verificación

Calibración inicial para el Blue Yeti Nano (se ajusta con una grabación de calibración de 60 s: 30 s de silencio de cuarto + 30 s de habla):
- **Umbral:** ruido de piso medido + 12 dB (arranque típico ≈ −38 a −42 dBFS; NO usar un número fijo sin calibrar).
- **Duración mínima de silencio para considerar corte:** 500 ms.
- **Padding:** conservar 200 ms antes y 250 ms después de cada segmento de habla (las colas de las consonantes finales viven ahí — este fue el fallo original).
- **Nunca cortar** silencios dentro de una misma oración detectada (<300 ms entre palabras).

**Verificación automática obligatoria antes de entregar:** transcribir con Whisper el original y el resultado; comparar conteo de palabras y WER entre ambas transcripciones. **Criterio: pérdida de palabras = 0 y WER del resultado vs original ≤ 2%.** Si falla, el pipeline relaja el umbral 3 dB y aumenta padding 50 ms, reintenta (máx 3 iteraciones), y si aun así falla, entrega el original con el reporte "no pude cortar sin riesgo".

## E7. Skills de ciberseguridad doméstica (alcance: infraestructura propia o autorización registrada)

Conjunto v1 (cada una con su script verificado):
1. `red-inventario` — nmap del segmento local, tabla de dispositivos conocidos (MAC/hostname), alerta por dispositivo nuevo.
2. `router-checkup` — checklist de configuración del módem (admin password no-default, WPS off, firmware, UPnP, DNS), guiado porque el acceso al panel lo hace Arturo.
3. `higiene-credenciales` — auditoría de `.env`, `authorized_keys`, permisos de archivos sensibles, edad de llaves; recordatorio de rotación.
4. `anomalias-equipo` — en HP/MacBook: procesos con conexiones salientes inusuales, crontabs/LaunchAgents nuevos, logins recientes.
5. `wifi-intrusos` — corte transversal periódico de `red-inventario` con notificación.
Regla codificada: cualquier objetivo fuera de la lista de equipos propios exige un registro de autorización vigente (B8.4) o la skill se niega.

## E8. Modelo de avance honesto y auditable

**Principio: el porcentaje es una suma ponderada de criterios binarios verificables en disco.** Nada de estimaciones a ojo.

- Cada fase aporta un peso (suman 100): F0=4, F1=8, F2=14, F3=8, F4=14, F5=12, F6=12, F7=6, F8=10, F9=5, F10=5, F11=2 (solo USB; la voz Mac Mini queda fuera del 100 del proyecto actual).
- Cada fase se descompone en sus entregables con checks automáticos: *archivo existe*, *test pasa*, *fila en DB ≥ N*, *service activo*, *timer corrió en las últimas 48h*. Ejemplo F4: `[peso 3] memoria_semantica.db existe y >10k chunks`, `[peso 3] retrieval pasa las 4 pruebas guardadas`, `[peso 4] timer nocturno OK 3 días`, `[peso 4] ≥15 hechos aprobados con fuente`.
- **Recolección:** `~/.hermes/scripts/has_progress.py` corre los checks (definidos en `has_checks.yaml`, versionado en el fork) diario a las 11pm → JSON con desglose → Notion (vista Avance) + resumen semanal por Telegram los domingos: "esta semana pasamos de 41% a 47%; se cerró X".
- **Anclaje inicial:** en la OT-0 se corre por primera vez para fijar la línea base real (adiós al "~50% a ojo").
- **La fecha faltante de inicio de vacaciones:** recuperable con evidencia — `git log --reverse` del primer commit del proyecto, mtime más antiguo en `/mnt/seagate/backups/`, y la primera fecha en `hermes_raw/`. La OT-0 incluye correr esos tres comandos, tomar la más antigua como fecha de inicio, y registrarla como hecho aprobado. Con eso, la vista de avance también grafica avance-vs-tiempo.
- **El checklist diario manual** alimenta una métrica separada (cumplimiento personal), que NO se mezcla con el % del proyecto: una mide al sistema, la otra te mide a ti.

## E9. Gestión de tokens y plan de Claude

**Reglas de sesión de Claude Code (Sonnet 4.6 por default):**
1. **Una fase = una o más sesiones cortas; nunca dos fases en una sesión.** `/clear` al cambiar de bloque grande dentro de una OT si el contexto pasó de ~60% — el historial completo de la conversación activa es lo que encarece, así que sesión corta = sesión barata.
2. **Contexto mínimo viable:** cada sesión carga solo la cabecera común + su OT + los archivos que va a tocar. Este documento completo NO se pega en Claude Code; vive en el repo (`docs/HAS.md`) y la OT referencia secciones puntuales.
3. **`CLAUDE.md` del repo** contiene: reglas duras, rutas clave, comandos de verificación frecuentes, y el veredicto por archivo de B2 — para que ninguna sesión re-descubra el proyecto.
4. **Subagentes en background:** solo lectura/investigación (B10). El costo de un subagente fallido no es solo tokens: es re-verificación.
5. **Trabajo que hace Hermes gratis (Gemini/Groq), nunca Claude:** barridos semanales (skills audit, duplicados, obsoletos), extracción de candidatos de memoria, clasificación de fotos, detección espontánea de tareas, reportes de avance, diario de reflexión, resúmenes de analítica. Regla: *si la tarea tiene molde definido y su fallo es barato y visible, es de Hermes; si requiere criterio o toca código, es de Claude.*
6. **Escalamiento de modelo (con nombres reales):** Sonnet 4.6 por default → **Opus 4.8** solo con evidencia concreta de atasco (2 intentos fallidos verificados en el mismo problema, no "se siente difícil") → **Fable 5** solo si Opus también se atascó, y en chat de claude.ai (no en Code) para decisiones de arquitectura, una consulta puntual con el contexto destilado a mano.
7. **Modelo de suscripción (v1.1 — el plan real de Arturo):** Claude Pro se paga **un mes cada ~4 meses**, como ventana de mantenimiento; entre ventanas, Hermes debe ser autosuficiente con sus modelos gratuitos. Implicaciones de diseño obligatorias: (a) **la ruta crítica (Fases 0-6) se cierra en la ventana actual**, mientras hay Claude — no se raciona; (b) Hermes acumula entre ventanas una **cola de mantenimiento con evidencia** (bugs con logs, skills stale, propuestas del barrido semanal) para que la sesión de mantenimiento llegue con el diagnóstico hecho y gaste tokens en arreglar, no en investigar; (c) al abrir cada ventana, la primera sesión corre `has_progress.py` + `skills audit` + los smoke tests para saber el estado real antes de tocar nada; (d) Max solo se considera dentro de una ventana si en ella pierdes ≥3 días de trabajo planificado por límites — fuera de ventanas la pregunta no existe. (Límites exactos de cada plan: verifica en https://support.claude.com al decidir.)
8. **Contexto de Proyectos de claude.ai:** como usa RAG, es el lugar correcto para este documento en tus chats de diseño — no lo pegues completo en conversaciones; deja que el proyecto lo recupere por fragmentos.

## E10. Plan financiero personal — los rieles (v1.1)

Estos números son **hechos aprobados** que Hermes debe conocer (se cargan en `memoria_estructurada` en la Fase 4) y la base del reporte mensual de rieles.

**Punto de partida (jul-2026):**
- Ingreso: $200/día, lunes a domingo con martes de descanso → ~26 días → **~$5,200/mes** (trabajo informal; sin comprobantes de nómina — irrelevante para CETES, ver abajo).
- Gastos fijos declarados: gym $500 + servicio de moto ~$100 ($300/trimestre) + recargas $200 + gasolina $200 + presupuesto IA/DeepSeek $100 = **~$1,100/mes**.
- Margen teórico ~$4,100/mes. **SUPUESTO marcado:** comida y vivienda cubiertas fuera de este flujo; si no, Arturo lo corrige y Hermes recalcula todo.

**Los tres rieles de ingreso (vista mensual obligatoria en Notion):**
1. **Trabajo + ahorro directo** — el riel que garantiza. Meta de depósito mensual configurable (inicial: $3,500).
2. **Trading (experimento Binance)** — el riel que puede adelantar. Solo cuentan **ganancias realizadas y transferidas** a Bitso/banco; el papel no suma al riel.
3. **Monetización YouTube/TikTok** — el riel futuro. Se activa en la vista cuando exista el primer pago real; mientras, se grafican los requisitos de monetización (subs/horas) como sub-meta.

Cuarto riel a futuro (post-graduación): proyecto propio / empresa de servicios tecnológicos / empleo formal — se agrega por migración F7 cuando exista.

**Metas ancladas con números:**
- **Mac Mini (~$27,000):** para el 31-dic se requieren ~$5,100/mes de ahorro — **no alcanza solo con el riel 1**; para mediados de febrero, ~$3,860/mes — posible pero al límite del margen. Fecha base realista: **febrero-marzo por ahorro**, y los rieles 2 y 3 existen para adelantarla. Hermes reporta cada mes: "fondo Mac Mini: $X (riel 1) + $Y (riel 2) + $Z (riel 3); fecha estimada al ritmo actual: ___".
- **Mac Studio 64GB (~$55,000–65,000, meta de segundo horizonte):** con $3,500/mes en CETES al ~5.5% neto → **~16-17 meses** después de arrancar ese fondo (los intereses aportan ~$2,000; el motor es el depósito). Se arranca DESPUÉS de liquidar la Mac Mini, no en paralelo.

**CETES (el colchón del riel 1):**
- Requisitos de cetesdirecto: **CURP, RFC, INE, correo y CLABE bancaria — nada más; NO pide comprobar ingresos** (es inversión, no crédito; el trabajo informal no es barrera). Desde $100.
- Tasas de referencia al 21-jul-2026: 28d 6.20%, 91d 6.63%, 175d 6.75%, 693d 7.94% anual bruto; retención provisional ISR 2026: 0.90% anual sobre capital → neto ~5.3–6.2%. Hermes verifica la tasa vigente cada semana (Banxico subasta los martes).
- Estrategia: escalera simple — el ahorro del mes entra a 28 días mientras el fondo es chico (liquidez para la compra), migrando parte a 91/182 días si la fecha de compra se aleja.
- **Principio que Hermes debe repetir en el reporte: CETES no genera la meta, la protege de la inflación; el motor es el depósito mensual.**

**Regla de privacidad del módulo financiero:** los montos y tickets se procesan con Gemini free, cuyos términos permiten usar entradas para mejorar sus modelos. Aceptado por ser datos de sensibilidad baja (gastos personales sin números de cuenta), pero **prohibido que por ese canal pase cualquier dato bancario: CLABE, números de tarjeta, saldos de cuentas, llaves de exchange.** Esos viven solo en la HP.

## E11. Higiene de tamaño de conversación en el gateway (v1.2)

Hallazgo Q.0 del historial: una conversación de Telegram creció a **262,593 tokens**; cuando Gemini agotó cuota diaria, **ningún proveedor de la escalera podía recibirla** (no estaban caídos — no cabía), y el fallback entero quedó inútil justo cuando se necesitaba. Especificación:

1. **Presupuesto duro de contexto conversacional: 40,000 tokens** hacia el modelo por turno (holgado para el proveedor más chico de la escalera, con margen para system prompt + inyección de memoria).
2. **Compactación automática:** al superar ~30,000 tokens, el gateway resume la parte vieja de la conversación (Gemini, gratis) a un bloque `[resumen de la conversación hasta aquí]` + conserva íntegros los últimos ~20 mensajes. El crudo completo sigue en la capa 1 de memoria — no se pierde nada, se compacta solo lo que viaja al modelo (mismo principio de siempre: el crudo es sagrado, se comprime el índice/contexto).
3. **Invariante de fallback:** cualquier payload que el gateway arme debe caber en TODOS los proveedores de la escalera, no solo en el primario. Test permanente en la suite smoke: conversación sintética de 300k tokens → el turno se compacta y Groq (el de contexto más chico) lo acepta.
4. **Aviso al usuario una sola vez por conversación:** "esta charla ya está larga, jefe; compacté lo viejo para seguir ágil — todo quedó guardado en memoria."
5. Relación con el índice semántico (E4): la compactación dispara indexado inmediato de los mensajes compactados, para que lo "resumido fuera del contexto" sea recuperable por búsqueda en el mismo minuto.

## E12. Presupuesto de pruebas y verificación de memoria (v1.4)

**Presupuesto autónomo de pruebas: $100 MXN/mes** de DeepSeek, sin pedir permiso por llamada. Cortacircuitos: $10 MXN/día máximo; alto y reporte si una corrida individual pasa de $3 MXN; aviso al 80% del mes. Etiqueta `test` en el ledger, reportado aparte del uso real (referencia histórica: un mes de uso real fueron ~$3 MXN). Fuera de pruebas, DeepSeek sigue requiriendo aprobación explícita.

**Verificación de memoria en 3 capas** (responde a "si prueba con otra cuenta, ¿cómo sé que la memoria funciona?"): la memoria de Hermes es **una sola** y vive en la HP; Telegram es solo la puerta de entrada. Por eso una cuenta QA distinta prueba la misma memoria sin ensuciar la de Arturo.
- **Capa A — mecanismo (cuenta QA, automática):** sembrar dato → verificar en disco → cerrar conversación → preguntar con otras palabras en sesión nueva → verificar recuperación. Cubre persistencia, cruce de sesión, supervivencia a compactación, supersede de contradicciones, bloqueo de secretos y **aislamiento de identidad** (nada de QA aparece en el cajón de Arturo).
- **Capa B — inspección de la memoria real de Arturo (SOLO LECTURA):** conteos, recuperación de 5 preguntas de su vida real, hechos huérfanos o contradictorios, barrido de credenciales. Nunca escribe.
- **Capa C — el juicio de Arturo (bitácora):** sus preguntas reales en su cuenta. Vale más que A y B juntas.
**Criterio de distinción permanente:** que una conversación nueva no arrastre el hilo de la anterior es diseño correcto; que un dato guardado y verificado en disco no se recupere después es bug.

---

# F. GOBERNANZA PERMANENTE (Documento Fundacional v2)

Reemplaza al original **conservando su espíritu íntegro** — sus cuatro principios (modelos locales, mejora continua, seguridad, misión permanente) siguen siendo la autoridad máxima; esto los vuelve operables.

## F1. Principios (heredados, ahora medibles)
1. **Independencia de modelo:** todo estándar de este documento aplica igual con APIs de nube hoy y con modelos locales mañana (Mac Mini). Ninguna regla puede depender de un proveedor específico.
2. **Misión permanente, con métrica:** "necesitar cada vez menos ayuda externa" se mide con dos números mensuales: (a) % de tareas resueltas por Hermes sin escalar a modelos de pago, (b) tokens de Claude gastados por entregable equivalente. Ambos en la vista de Avance.
3. **El crudo es sagrado.** Nunca comprimir destruyendo; solo se comprime el índice. Nunca eliminar conocimiento sin respaldo.

## F2. Protocolo de Mejora de Skill (las "preguntas antes de mejorar")
Antes de que CUALQUIER agente (curator, Hermes, Claude) modifique una skill, debe contestar por escrito en el changelog:
1. ¿Qué evidencia concreta motiva el cambio? (uso real, fallo registrado, información nueva verificada — cita la fuente)
2. ¿Existe respaldo? (ruta del respaldo previo)
3. ¿Qué se prueba para validar y cuál fue el resultado? (comando + salida)
4. ¿Sube versión? (semver obligatorio)
5. ¿Contradice algo del HAS o del historial real? (verificado contra el índice semántico)
Sin las 5 respuestas, el cambio no se aplica. El curator, por diseño, nunca puede contestar la 1 y la 3 — por eso solo poda y nunca edita.

## F3. Consolidación permanente de memoria (el fin del append-only ciego)
- `MEMORY.md`/`USER.md` siguen siendo append-only en escritura diaria, PERO cada trimestre corre una **sesión de consolidación** (Claude, con el diff mostrado a Arturo) que aplica semántica de *supersede*: un hecho nuevo que contradice a uno viejo lo marca reemplazado con fecha, nunca lo borra.
- El barrido semanal de Hermes (Gemini) detecta y REPORTA: contradicciones nuevas en USER.md, hechos repetidos ≥3 veces, rutas/archivos mencionados que ya no existen, pendientes con >30 días. El reporte llega los domingos junto al de avance.
- Toda corrección pasa por `memory_tool.py` (guardia anti-drift). Editar los .md a mano queda prohibido para humanos y agentes por igual.

## F4. Registro de cambios universal
Todo cambio de skill, de configuración, de esquema o de reglas se registra en `~/.hermes/CHANGELOG_SISTEMA.md` (append-only, una línea: fecha, qué, por qué, quién — humano/claude/hermes, ruta del respaldo). El barrido semanal verifica que los archivos con mtime reciente en zonas gobernadas tengan su línea correspondiente; los huérfanos se reportan como "cambio sin registrar".

## F5. Detección de obsolescencia
Tres relojes automáticos: skills con `last_verified` >180 días → stale; hechos de memoria que referencian rutas/servicios inexistentes (verificable en disco) → cola de revisión; credenciales sin uso en 90 días (por logs de LiteLLM) → candidata a revocar (como ELEVENLABS hoy).

## F6. Jerarquía de autoridad ante conflicto
1. Restricciones duras de la sección 8 del maestro (presupuesto, sudo, deny-list, verificación E2E).
2. Este HAS.
3. Hechos aprobados en `memoria_estructurada`.
4. `USER.md` consolidado.
5. Cualquier salida de un modelo.
`docs/HISTORIAL.md` es memoria histórica de solo-lectura: no manda sobre nadie, pero cualquier afirmación sobre "lo que ya se hizo" debe ser consistente con él o corregirlo con evidencia (nunca ignorarlo).
Un agente que detecte conflicto entre niveles se detiene y pregunta; nunca resuelve hacia abajo.

## F7. Evolución de esquema y versionado por ciclos de vida (v1.1)
La vida de Arturo cambia por ciclos (cuatrimestres hoy; carrera, proyectos y empresa mañana) y la base de datos debe crecer con ella **sin que nadie la altere a mano ni de sesión en sesión**:
1. **Versionado por cuatrimestre:** las tablas académicas (`horario`, `temas_vistos`, materias) llevan campo `cuatrimestre` (ej. `2026-C3`). Un horario nuevo **archiva** al anterior (`status=archivado`), nunca lo pisa ni lo borra — el historial académico completo es parte de la memoria de años.
2. **Migraciones propuestas, nunca ejecutadas solas:** cuando Hermes detecte que necesita una "casilla" nueva (columna, tabla, categoría — ej. si Arturo empieza a estudiar arquitectura de software, un proyecto nuevo, o funda su empresa), **propone** una migración: archivo SQL numerado en `~/.hermes/migrations/`, con descripción de qué agrega y por qué, registrado en `CHANGELOG_SISTEMA.md`. Se aplica solo con aprobación de Arturo (o de Claude en ventana de mantenimiento). Prohibido el `ALTER TABLE` improvisado en medio de una conversación.
3. **Solo aditivo:** las migraciones agregan; nunca eliminan columnas ni tablas con datos. Lo obsoleto se archiva (mismo principio que las skills y la memoria: el crudo es sagrado).
4. **Las categorías también evolucionan así:** categorías nuevas de gastos, de biblioteca o de skills se agregan por el mismo canal, para que Notion, los reportes y el clasificador se enteren juntos y nada quede desincronizado.

## F8. "Cerrado" solo con evidencia pegada (v1.2)
El HISTORIAL documenta el patrón transversal del proyecto: reportes que declaran "verificado en producción real" sobre evidencia parcial (caso máximo: el commit del Bloque O decía "Verificado E2E" y la rendición de cuentas real mostró 1 de 6 casos limpio). Reglas permanentes:
1. **La palabra "verificado" sin transcript no verifica nada.** Un bloque solo se marca `cerrado ✅` en BLOQUES.md si el reporte incluye, por cada caso E2E, el comando/mensaje real y su salida real pegada. Sin eso, el estado máximo es `en curso`.
2. **Rendición de cuentas al cierre, siempre:** el orquestador termina cada bloque pidiendo la contabilidad caso por caso ("de los N casos: ¿cuántos pasaron limpios, cuántos no se probaron, cuántos fallaron?") — no "¿terminaste?". El HISTORIAL demuestra que esta pregunta, cuando se hizo, atrapó el problema todas las veces; ahora es obligatoria, no heroica.
3. **Corregir un reporte previo es mérito, no falla.** El estado de un bloque puede regresar de ✅ a `en curso` con evidencia nueva; eso se registra, jamás se penaliza. Lo que se penaliza (se documenta como incidente) es declarar sin evidencia.
4. Esta regla obliga a los tres: Claude Code al reportar, el orquestador al aceptar cierres, y Arturo al no aceptar un "ya quedó" sin su tabla.


## F9. Lecciones permanentes (v1.3 — jurisprudencia del proyecto)

Registro citable de fallas reales y la regla que nació de cada una. F8 es el principio; esto es su historial de casos. Toda sesión puede (y debe) citar "F9-L*n*" al detectar una reincidencia. Fuente: sesión de ejecución 22-23 jul (17 fallas documentadas en ESTADO/BLOQUES).

**Familia A — Verificación inflada o fabricada** (extiende F8; casos L1, L3, L5, L10, L12-L13):
- **L1** (Bloque O reportado "Verificado E2E", realidad 1/6 limpio): la rendición de cuentas caso-por-caso de F8.2 es OBLIGATORIA en cada cierre — nunca fue opcional, pero desde hoy el orquestador que acepte un cierre sin la tabla comete la falla, no solo quien reportó.
- **L3** (evidencia de prueba aislada mezclada con E2E real de forma ambigua): todo reporte etiqueta cada evidencia como `[arnés]` o `[E2E real]` — mezclarlas sin etiqueta invalida el reporte completo.
- **L5** (timestamp de log inventado en una verificación de incidente): toda cita de log incluye la línea textual copiada, no parafraseada. Un timestamp sin su línea textual no existe. (Refuerza la skill `verificar-incidente` del Bloque O.6.)
- **L10** (subagente devolvió resumen incoherente con su tarea): reafirma B10 con dureza nueva — el resumen del subagente NO SE LEE hasta después de verificar el artefacto en disco; el orden importa, porque leer primero el resumen ancla el juicio.
- **L12-L13** (dos hallazgos de seguridad en la bóveda nueva; uno — fabricación de confirmación de guardado — SIGUE ABIERTO): ninguna función de seguridad se declara operativa sin un test adversarial que intente engañarla; el pendiente L13 requiere sesión de diagnóstico dedicada ANTES de que la bóveda guarde nada real por voz.

**Familia B — Higiene de estado** (extiende PROTOCOLO §2; casos L2, L11):
- **L2** (cierre de protocolo saltado en silencio, varias veces): el cierre (ESTADO+BLOQUES+push) deja de ser el "último paso" que se olvida — es la definición de sesión terminada (C10); una sesión sin cierre se registra como incidente en el propio ESTADO al detectarse.
- **L11** (ESTADO/BLOQUES vivían fuera del repo versionado): al abrir sesión, `git ls-files docs/ESTADO.md docs/BLOQUES.md` debe devolverlos; si no, detener todo y corregir la desviación primero.

**Familia C — Higiene de pruebas** (extiende PROTOCOLO §6; casos L4, L8):
- **L4** (regresión por diagnóstico temporal dejado en producción): reafirma C11; además, todo diagnóstico temporal se agrega con un marcador `# TEMP-DIAG` greppeable, y el cierre de sesión corre `grep -r "TEMP-DIAG"` = 0 resultados.
- **L8** (ventana de pruebas contaminada con reinicios en paralelo): reafirma P1; la ventana se declara con timestamp en ESTADO.md y cualquier reinicio dentro de ella invalida TODOS los resultados de la ventana, sin excepción ni rescate parcial.

**Familia D — Fallos silenciosos** (casos L6, L14, L17):
- **L6** (enforcement de idioma falló sin rastro) y **L14** (config perdió entradas críticas sin causa raíz): **el silencio nunca es un estado válido de fallo.** Todo mecanismo de enforcement o de escritura de config debe loggear tanto su éxito como su fallo; un mecanismo que puede fallar sin dejar rastro está mal construido por definición y se repara antes de confiar en él de nuevo.
- **L17** (la escalera de fallback dejaba la oferta de DeepSeek en silencio al caer todo lo gratis) — **RESUELTO con supuesto marcado (Arturo puede revertir con una línea):** en caída total de la escalera gratuita, Hermes envía UN aviso de modo degradado: "toda la escalera gratuita está caída, jefe; puedo intentar con DeepSeek (~$X MXN estimado) — ¿sí/no? Si no, reintento lo gratis cada 15 min y te aviso cuando vuelva". Nunca despacha solo (la regla dura de B4/Tarea E no se toca) y nunca calla.

**Familia E — Contexto no leído** (casos L9, L15 → regla D7 del PROTOCOLO v1.1):
- **L9** (prompt orquestador generado con estado desactualizado) y **L15** (sesión con el ESTADO pegado preguntó algo que estaba textual ahí): leer no es tener el documento en contexto — es citarlo. Ver D7.

**Familia F — Comunicación con Arturo** (caso L16 → regla D8 del PROTOCOLO v1.1):
- **L16** (bitácora construida sin mostrarle el formato antes): todo artefacto cuyo consumidor final es Arturo (bitácoras, tableros, reportes, formatos de mensaje) se muestra en borrador de UNA muestra antes de construirse completo.

**Operación de rutina (petición explícita de Arturo, permanente):** las pruebas de rutina corren por el arnés interno del Bloque V — Claude Code/Hermes las disparan y leen sin que Arturo mande mensajes a mano. Telegram real se reserva para (a) la evidencia final de cierre de un bloque y (b) los ejemplos de `docs/BITACORA_ARTURO.md`, que es donde Arturo verifica y experimenta cada mejora en su día a día. La bitácora es entregable obligatorio del cierre de sesión cuando hubo cambios visibles al usuario (C13 del PROTOCOLO).

---

# G. QUÉ NO SE VA A HACER Y POR QUÉ

Sin endulzar:

1. **Modelos LLM locales en la HP: no.** Un i3-7020U con 8GB corre, con suerte, un 3B cuantizado a 3-5 tokens/seg comiéndose la RAM del gateway. Sería un juguete que degrada al sistema que sí funciona. Se hace en la Mac Mini.
2. **Hermes completo y offline en el USB: no.** Sin internet no hay cerebro (sus modelos son APIs). Lo que sí: el USB-llave (B8), que cumple el 90% del caso de uso real con el 10% del riesgo.
3. **Voz conversacional full-duplex "como Her" en el hardware actual: no.** La HP no puede con STT streaming + TTS de calidad simultáneos, y la M1 de 8GB queda justa si además está editando video. Interino: Gemini Zephyr (ya lo tienes) + Piper para avisos locales. La versión real llega con la Mac Mini.
4. **Clonar una voz de actriz o entrenar "la voz de Her": no, nunca.** Riesgo legal real (caso Sky/OpenAI 2024). Voz sintética con licencia, ajustada al tono cálido que quieres.
5. **Trading autónomo con dinero real: no, permanente.** Propone-y-apruebas (B4). La autonomía total vive solo en simulación.
6. **Apple Watch: no por ahora.** El dinero compite con la Mac Mini y el iPhone cubre el caso (B6). Reevaluable con datos.
7. **Micrófono de Alexa: imposible.** Amazon no lo expone; tu propia prueba lo confirmó. Solo bocina BT, si acaso.
8. **Renderizado de video por Hermes: no** (además lo prohibiste): la HP no puede y en la M1 el render es tu decisión creativa. Hermes deja la línea de tiempo lista.
9. **Automatizar el acomodo físico de la cámara: no** sin comprar motorización que no vale lo que cuesta. Todo lo demás del setup sí.
10. **Entrega automática de tareas a Classroom: no en v1.** Genera el entregable; tú lo subes. Elimina de raíz el riesgo de que "se entregue solo" algo incorrecto.
11. **ComfyUI en la HP: no** (torch en un i3 sin GPU). Archivado hasta Mac Mini.
12. **RAPTOR/resúmenes jerárquicos hoy: no.** El costo LLM de construir el árbol no cabe en $100/mes; el índice plano híbrido resuelve el problema real de recuperación. Se agrega en Mac Mini con modelos locales gratis.

---

# H. PREGUNTAS ABIERTAS (solo las que nadie puede decidir aún)

Todas las demás decisiones quedaron tomadas arriba con supuesto marcado. Quedan cuatro cosas que **solo Arturo** puede aportar, y una externa:

1. **`NOTION_API_KEY`** — requiere que crees la integración (5 min, instrucciones en OT-5). Bloquea Fase 5.
2. **Cuentas de exchange** — RESUELTO en v1.1 (Binance operación + Bitso puerta de pesos). Lo único pendiente de Arturo: abrir/verificar ambas cuentas y la de cetesdirecto cuando toque la Fase 10.
3. **Acceso al panel del módem** (usuario/contraseña del router) — necesario para `router-checkup`. Solo tú lo tienes.
4. **Horarios de gimnasio** — un mensaje tuyo a Hermes cuando la Fase 4 esté viva; se guarda como hecho aprobado y alimenta el recomendador de repaso.
5. **Externa: la API de plugins de hermes-agent 0.19** — si los lifecycle hooks reales no soportan el hook de pre-turno que el plan asume para `complexity_detector`, la OT-2 ya trae la salida (queda como parche); no bloquea nada, solo cambia el veredicto de un archivo.

La fecha de inicio de tus vacaciones NO queda abierta: se recupera con evidencia en la OT-0 (E8).

---

*Fin de la entrega. Este documento se guarda como `docs/HAS.md` en el fork y es la referencia de todas las sesiones posteriores. — Claude*
