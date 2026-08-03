# ESTADO — actualizado: 02 ago 2026 (AU-1 cerrado: motor de guiones desde Obsidian; AV en curso: capa de confiabilidad loop autónomo)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6-F14 ⬜ | **F11 laboratorio VALIDADO (AQ)**. **E10 → v1.7** (meta capital $100k/31-dic-2027, Mac Mini descartada; corregido en AR).

## REGLA QUE CAMBIA TODO (r.20, permanente — ya en CLAUDE.md, regla 6)
Todo dato de fechas/pagos/citas mencionado en pruebas = **SIMULADO** salvo que Arturo marque "dato real". La colegiatura del 31 jul queda ANULADA. Inventar escenarios y adelantar el reloj: SOLO en el laboratorio Docker. Producción jamás.

## ✅ AQ CERRADO (01 ago) — primera corrida real del laboratorio, con evidencia
Imagen `hermes-agent:latest` construida (966 MB) + respaldo `20260731_040925` restaurado en volumen aislado `hermes-lab-data` (nunca `~/.hermes`) → `integrity_check` de state.db y memoria_semantica.db = **ok** (27 tablas, 2919 msgs, 273 sesiones) + smoke del código real de Hermes leyendo la DB + arnés host 57/57. Pico térmico **59°C** (umbral 85, nunca disparó). `down -v` hecho. **Primera prueba real de que los respaldos de Arturo SÍ restauran.** Detalle: BLOQUES/DECISIONES.

## ✅ AR CERRADO (01 ago) — la libreta reconciliada, aplicada a PRODUCCIÓN con respaldo y aprobación (F7.2)
HALLAZGO: la libreta YA existía (`libreta.db`, 17 tablas, clase `Libreta` real/simulación — NO state.db, SEED corregido). AR = **migración v4**: gym→500, moto→550 bimestral, internet→recarga_telefono 230, +deepseek 100/+gasolina 200, **meta capital $100k/31-dic-2027 (Mac Mini descartada)**, colegiatura $1,200 (colchón, Arturo), peso 111.5, 6 hábitos. Validada en copia aislada + **contenedor F11-e** (integrity ok, v4, clase Libreta lee/escribe) → aplicada a producción con respaldo previo `20260801_165400`. ✅ **libreta.db ya en `respaldar_memoria.py`** (bug data-safety cerrado). HAS §E10→v1.7.

## ✅ BUG RESUELTO (AR, hallado y corregido 01 ago) — sin tocar la migración aplicada
La v4 siembra datos base en toda BD migrada, lo que rompía 2 tests que contaban toda la tabla (`test_libreta.py`). Fix elegido (respeta la regla "no editar migración ya aplicada"): las 2 pruebas ahora verifican SOLO la fila que crean (`WHERE nombre=...`), que es lo que de verdad prueban. **49/49 en verde.** Producción intacta.

## OBJETIVO ACTUAL — Bloque AV: capa de confiabilidad para LOOP autónomo (EN CURSO, redirección de Arturo 02 ago)
Meta de Arturo: SSH desde MacBook → tmux (sesión `claude`) → loop PAUSADO que avanza la cola solo, visible en terminal, con **modelo por dificultad** (Sonnet simple / Opus 4.8 complejo) y tokens medidos por bloque. **Paso 1 HECHO y verificado a mano:** hook `.claude/hooks/hermes-arranque.sh` (SessionStart, `exit 0` siempre, salud en `--user`) + skill `/cierre` (6 pasos) + lista de tareas viva. Ambos entran en vigor al próximo `/clear`/arranque. **SIGUIENTE:** orquestador con ruteo de modelo por dificultad (respeta B10: skills, no subagentes-que-escriben). **Decisión de Arturo al reanudar — modo del loop:** (A) sesiones VISIBLES en tmux por bloque, ve todo en vivo incl. pruebas (se inclina por A) / (B) headless con bitácora de tokens. Confirmará "A" tras ver el hook despertar con un `/clear`. Pruebas: Docker + cuenta QA (r.119), nunca prod; charla de Hermes visible desde Telegram QA.
⚠️ Hallazgo: CLAUDE.md pt.5 usa `systemctl is-active` SIN `--user` → falso 'inactive' con prod ENCENDIDA (gateway/litellm `active`). El hook usa `--user`; falta corregir esa línea de CLAUDE.md (propuesto, pendiente del ok de Arturo — es su archivo-contrato).

## ✅ AS CERRADO (02 ago) — flujo voz→STT→libreta verificado punta a punta
Brief 6:30 + cierre nocturno en audio + verificación punta a punta completados.
- ✅ **AS-1 Brief matutino (06:30):** `scripts/brief_matutino.py` desplegado y timer armado. Verificado en simulación.
- ✅ **AS-2 Cierre nocturno en audio:** `scripts/cierre_del_dia_audio.py` generado, TTS → .ogg Opus verificado. Envío a Telegram PENDIENTE (candado r.119: canal QA inexistente).
- ✅ **AS-3 Voz→STT→Libreta verificado:** `scripts/verify_voice_to_libreta_real.py` ejecutado, 5 pasos OK. Audio Opus → STT → VoiceDataExtractor (regex) → `lib.registrar_gasto()` → BD. Log: gastos guardados id=13, $50 comida.
Pendiente para después: (a) envío en vivo a Telegram QA/producción; (b) timer nocturno de cierre; (c) `~/.hermes/scripts/enviar.py` vive solo fuera de repo.

## ✅ F5-1 EN CURSO (02 ago, bloque del loop) — vista "Finanzas" en Notion, tablero único (OT-5 Bloque 2)
`tools/notion_finanzas.py` (mismo patrón que `notion_avance_has.py`, B7: libreta.db fuente de verdad, Notion espejo solo-lectura): balance del mes, gastos por categoría, metas de ahorro, pagos recurrentes próximos. 7/7 pruebas en verde + **verificado en vivo contra la API real** (page_id `3b1c1df3-4107-8194-8baa-cab2ac2d44f0`, contenido leído de vuelta y confirmado). Timer `hermes-notion-finanzas.timer` activo cada 15 min (mismo patrón que el de Avance HAS, no versionado en repo). **De las 6 vistas de OT-5 van 2/6** (Avance HAS, Finanzas). Faltan: Hoy, Kanban espejo, Cola de tareas, Escuela (bloqueada a Fase 6) + BLOQUE 1 (consolidar skill notion-api) + BLOQUE 3 (cola v2) + BLOQUE 4 (checklist diario).
⚠️ Hallazgo sin arreglar: `notion_avance_has.py` sigue llamando a `has_progress.py` directo aunque ESTADO dice "NO se usa, reporta 90% engañoso" — la vista Avance HAS en Notion hoy muestra ese dato erróneo. No corregido este bloque (fuera de alcance de F5-1); anotado para revisión.

## ✅ F5-2 CERRADO (02 ago, bloque del loop) — cola de tareas v2 con garantía dura (OT-5 Bloque 3 / HAS §E5)
`scripts/cola_v2.py` (patrón libreta.py: real=state.db / simulacion aparte): máquina de estados `encolada→en_proceso→resuelta→notificada|atorada` en `state.db`, escalera de reintentos Groq→Gemini→OpenRouter (5/prov, **sin DeepSeek automático**), watchdog de huérfanas >2h con **idempotencia por result_hash** (no re-ejecuta el efecto), notificación **GARANTIZADA** (resuelta⇒notificada; si Telegram falla, queda resuelta y el siguiente barrido renotifica — nunca resuelta-sin-avisar), y `task_queue_log` que escribe éxito Y fallo de cada intento. **solver/notificador son INYECTABLES**: la cola es la espina dorsal de la proactividad sin poder gastar sola. **11/11 pruebas** (`tests/scripts/test_cola_v2.py`) clavan los 3 invariantes E5, incl. lote mixto de 15 tareas donde NADA queda en estado no-terminal. **Pendiente de despliegue:** cablear solver real (skill/proveedor por tarea) + notificador real (`~/.hermes/scripts/enviar.py`) + timer systemd del watchdog cada 30 min. **OT-5 Bloque 3 hecho; van 2/6 vistas + cola v2.**

## ✅ AT CERRADO (02 ago, bloque del loop) — entrenador de trading testnet news-driven (OT-10/B4)
`scripts/trading_entrenador.py`: buy-the-dip informado por sentimiento. Investigación web (02 ago): dip a secas rinde mal → la entrada exige el CRUCE de 3 (caída ≥umbral + RSI<30 sobreventa + score de sentimiento alcista; r.91 solo números). Capital SIMULADO tope **5,000 MXN**, ciclos semanales, freno duro **-3% diario** (r.40, circuit-breaker independiente), fees 0.1%+slippage por fill. Mercado y sentimiento son puertos **INYECTABLES** → el módulo no toca red solo (r.119: host con creds de prod, sin QA). Cliente `MercadoBinanceTestnet` (python-binance `testnet=True`) cableado pero **PENDIENTE**. **17/17 pruebas** con dobles locales: freno dispara+bloquea+reinicia por día, cruce de señal, capital nunca negativo/tope duro, fee+slippage, RSI Wilder, TP/SL.
**Pendiente de despliegue (r.119, requiere QA):** (a) keys `BINANCE_TESTNET_API_KEY/_SECRET` en `.env`; (b) correr en Docker/QA, nunca host-prod; (c) fuente de sentimiento real (Fear&Greed alternative.me, solo números, apta r.91); (d) reporte Notion (r.42); (e) datos reales para calibrar umbrales.

## ✅ AU-1 CERRADO (02 ago, bloque del loop) — motor de guiones desde Obsidian (Fase 8/OT-8, r.45-47)
`scripts/motor_guiones.py`: nota Obsidian (frontmatter+cuerpo) → ANDAMIAJE de guion con las 3 partes que Arturo pidió "siempre en mente" (r.47): gancho (≤15s) / promesa-payoff / segmentos con open-loops + transiciones-microgancho / cierre / CTA + **analizador de retención medible** (r.91: nº open-loops, duración, payoff-cierra-gancho, transiciones). Reglas ancladas en **investigación web 02 ago** (open-loops +32% watch time; tras 15s sin gancho retención <45%; transición=micro-gancho; podcast narrativo: primeros minutos deciden). **NO promete edición creativa** (decisión del bloque): pone el molde y mide, la prosa final la escribe el LLM/Arturo. Registro en tabla `guiones` **inyectable** (no abre DB solo). **15/15 pruebas** + verificado en vivo contra nota real del vault (solo lectura). **PENDIENTE de AU:** (a) tool de runtime en el registry/toolsets para que Hermes lo llame en chat; (b) pipeline de clips ≤2 min + programación (r.46/48); (c) OAuth YouTube (r.59).
Transversal aún pendiente: **presupuesto de contexto** — prueba permanente del arnés (techo 19.1k/vuelta, ≥3 muestras).

## EFICIENCIA — 3 preocupaciones de Arturo (01 ago)
- **P1 variantes:** matriz = GUION_PRUEBAS × 5 roles (F11-d) × escenarios simulados (r.20); cada corrida nocturna agrega escenarios.
- **P2 exceso de contexto:** techo de tokens por tipo de llamada, medido en cada corrida del lab (≥3 muestras); exceder = suite en rojo. Base 30 jul: 19.1k/vuelta.
- **P3 DeepSeek:** repetitivo → Gemini-extra/Groq/OpenRouter (r.91), DeepSeek solo comanda; ledger $/función semanal; recorte del prompt ~40k entra con AR.

## Decisiones pendientes de ARTURO
1. OAuth de YouTube (5 min) cuando arranque AU. (Único pendiente vivo.)
(Resuelto 01 ago: **Trading -3% diario CONFIRMADO** (Arturo: "que quede así"). **PRIVACIDAD** — montos/tickets SÍ a gratis; correos/contraseñas/nombres/salud/datos que vulneren su seguridad NO. **Horario** oficial lo manda él a Hermes; may-ago = simulación. **Correos** = trabajo F6. Estándar de docs lo define Claude Code, MANDATO §8.)

## No tocar / reglas de equipo
- **M1 PRESTADA (r.102):** config nocturna (caffeinate) se REVIERTE antes de 6:00 y se verifica revertida.
- Correo: solo-lectura; borradores con aprobación por correo se diseñan en F6, nada encendido.
- Gemini Live DESCARTADO (r.99) → alertas iPhone vía Telegram que vibran como llamada.
- Pruebas masivas SOLO en Docker con cuenta QA (r.119). Producción sin tráfico de prueba.
- **has_progress.py NO se usa** (reporta 90% engañoso, bug abierto). Avance real = este archivo.

## Al cierre de cada sesión
ESTADO ≤80 sobreescrito · BLOQUES 1 línea · DECISIONES si hubo · commit+push · TEMP-DIAG=0 · temperatura HP normal.

## Último contexto
02 ago: el loop despachó AU-1 (motor de guiones desde Obsidian, primer bloque de YouTube — r.97 #2), además de F5-1/F5-2/AT esta sesión. AV paso 1 (hook de arranque + skill `/cierre`) HECHO y verificado; prod CONFIRMADA arriba (`--user`). Siguiente: orquestador multi-modelo, seguir AU (tool de runtime + clips + OAuth YouTube), retomar AS, OT-5 (Hoy/Kanban/Escuela + Bloques 1/4); F5-2 y AT pendientes solo de despliegue.
