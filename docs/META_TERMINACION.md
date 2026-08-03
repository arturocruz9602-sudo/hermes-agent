# META DE TERMINACIÓN — cuándo Hermes está listo, en trabajo realizado
**03 ago 2026 · fuente: `CUESTIONARIO_MAESTRO.md` (123 respuestas) · verificado contra código/timers/logs reales, no de memoria.**

## 1. Definición de "Hermes terminado"

**Hermes está terminado cuando cubre, sin que Arturo tenga que pedírselo, sus 5 ejes de vida
(horario/escuela, dinero, contenido/YouTube, cuerpo, agenda) con capacidades DESPLEGADAS — no
solo construidas — y el sistema se sostiene solo (respaldos, watchdog, presupuesto, sin que
"olvidar y autosabotear" — r.115, lo peor que Arturo describió — le pase a Hermes.**

Criterios de aceptación (verificables, no de opinión):
1. Cada necesidad del cuestionario tiene una capacidad en estado 🚀 (desplegada), no solo código con pruebas en verde.
2. Nada que dependa de Arturo (OAuth, llaves, decisiones) sigue bloqueado más de lo que él mismo autorizó.
3. Los mecanismos de soporte (cola con garantía, respaldos, watchdog, memoria semanal) corren solos, medidos.
4. El presupuesto real (Riel B) se sostiene bajo $100 MXN/mes con margen (ver Tarea B).

## 2. Tabla necesidad → capacidad → estado
⬜ no existe · 🏗 construida (código+pruebas) · ✅ probada (verificada en lab/sim) · 🚀 desplegada en producción

| # | Necesidad (cuestionario) | Capacidad | Estado | Evidencia |
|---|---|---|---|---|
|1|Horario: cuadrar bloques/Notion al vuelo (r.1)|Vista "Hoy" Notion + reprogramación|⬜|F5-1 solo hizo Avance HAS + Finanzas (2/6 vistas)|
|2|% de avance de vida por objetivos (r.1)|BD medible de objetivos|⬜|no existe|
|3|Alarmas de despertar amistosas (r.2)|Gestión de alarmas|⬜|no existe|
|4|Sugerir cursos en huecos libres (r.1)|Detección de tiempo próspero|⬜|no existe|
|5|Ingreso refresco + patrón (r.16)|Tabla `ingresos` + detección|⬜|F7-2 en cola, no corrido|
|6|Reporte de ingreso multi-modal (r.17)|voz/texto/foto/PDF→libreta|🏗|voz probada (AS-3) NO conectada al chat; foto/PDF no existen|
|7|Reporte semanal de rieles (r.18)|Resumen semanal|⬜|F7-3 en cola, no corrido|
|8|Registro de todo gasto (r.19-27)|libreta.db v4|🚀|AR, producción, respaldo+aprobación, 49/49 tests|
|9|Extracción de gasto por voz en vivo|Chat real→libreta|🏗|`voice_data_extractor.py` probado aislado, verifiqué HOY que ningún tool del gateway lo importa|
|10|Motor de sugerencias de gasto (r.25)|Evaluación proactiva|⬜|no existe|
|11|Meta capital $100k + vista (r.28-31)|libreta v4 + Notion Finanzas|🚀|verificado contra API real (page_id confirmado), 7/7 tests|
|12|Guía apertura CETES (r.32)|Acompañamiento|⬜|no existe|
|13|Rastreo precio/promos Mac Studio (r.35)|Vigilancia de precio|⬜|no existe|
|14|Laboratorio trading + freno -3% (r.36-40)|`trading_entrenador.py`|🏗|17/17 tests; faltan llaves testnet + Docker/QA|
|15|Reporte de trading en Notion (r.42)|Vista Notion trading|⬜|no existe|
|16|Guion gancho/cierre/retención (r.47)|`motor_guiones.py`|🏗|15/15 tests + nota real leída; sin tool de runtime|
|17|Clips ≤2min + horarios (r.46/48)|`pipeline_clips.py`|🏗|25/25 tests; sin tool de runtime|
|18|Publicar en YouTube (r.59)|OAuth+API key+`PublicadorYouTube`|🏗|**CONFIRMADO 03 ago: se necesitan LAS DOS llaves** (API key pública Google Cloud Console + OAuth login Arturo→HERMES) — resuelve contradicción de sesión 31 jul, ver DECISIONES.md; cableado, bloqueado por que Arturo las saque (~10 min)|
|19|Corte silencios + DaVinci M1 (r.49/102)|`corte_silencios.py`+`edicion_m1.py`|🏗|17+18 tests; falta SSH real M1 + Whisper real|
|20|TikTok/Instagram (r.45/54/55)|Distribución multi-red|⬜|no existe|
|21|Sonido/imágenes de contexto auto (r.49)|Automatización de edición|⬜|explícitamente no prometido (decisión AU-1)|
|22|Vigilar correo escolar, avisar (r.62-64)|`vigilar_correo_escuela.py`|🚀|**verificado con logs reales HOY**: corre c/15min, "203 correos, sin novedades"|
|23|Foto pizarrón + seguimiento escalonado (r.64)|Análisis+recordatorio 8am/12pm|⬜|no existe|
|24|Libreta hábitos/peso (r.68-77)|libreta v4, 6 hábitos seed|🏗|protocolo de pesaje (r.69) PENDIENTE de Arturo|
|25|Cierre nocturno en audio (r.90)|`cierre_del_dia_audio.py`|🏗|.ogg generado+verificado (ffprobe); envío bloqueado (candado r.119, sin canal QA)|
|26|Autoevaluación dominical (r.76)|Preguntas semanales|⬜|no existe|
|27|Cola de tareas con garantía (agenda)|`cola_v2.py`|🏗|11/11 tests; solver/notificador reales sin cablear, sin timer watchdog|
|28|Notificaciones proactivas reales (r.80-81)|Avisos 2h antes / pagos 1 día antes|⬜|depende de #27 sin cablear|
|29|Vigilar correo personal banco/compras (r.108)|Adaptador personal|🏗|**CORREGIDO 03 ago**: acceso YA otorgado (credenciales reales en `.env`, adapter `plugins/platforms/email/adapter.py` existe); vigilancia sigue apagada (sin timer, sin `EMAIL_ALLOWED_USERS`) — pendiente es cablear, no acceso|
|30|Enrutamiento de privacidad por API (r.91)|DeepSeek comanda / gratis repetitivo|🚀|**medido HOY en ledger real: 55.6% DeepSeek, 44.4% Gemini/Groq** — la regla se cumple|
|31|Auditoría semanal de memoria (r.95)|Timer reflexión semanal|🚀|**verificado HOY: próxima corrida domingo 09 ago 08:00, última corrida domingo 02 ago**|
|32|Distinguir entorno QA de producción (r.119)|Canal QA de Telegram|🏗|**RESUELTO 03 ago**: "Hermes QA De La Cruz" `chat_id=8727618189`, verificado en `state.db::gateway_routing` (desde 24 jul) — YA existía, no era cuenta nueva. Falta `TELEGRAM_QA_CHANNEL` en `.env`, pendiente de confirmación de Arturo (regla dura .env)|
|33|Brief 6:30 + trato "jefe" (r.84/86/98)|`brief_matutino.py`+tono|🚀|timer activo, verificado en simulación, tono ya en CLAUDE.md|

**% de avance real (🚀/33 necesidades): 6/33 = 18%.**
**% construido-o-más (🏗+🚀)/33: 16/33 = 48%** — coincide con la nota de ESTADO "F5 ~50%": mucho
código probado, mucho menos desplegado. El cuello de botella es despliegue, tal como advirtió Hermes en el brief.

## 3. Qué falta para 100% — realista en 2 semanas vs. post-16-ago

**En 2 semanas (prioriza reducir dependencia de Arturo, MANDATO §2 — cerrar despliegue, no construir más):**
- Cablear `voice_data_extractor` como tool de runtime del chat real (#9) — chico, alto impacto (r.115).
- Cablear cola_v2: solver+notificador reales + timer watchdog (#27) → desbloquea #28 (proactividad real).
- Correr F6-1 (correo personal, si Arturo da las 2 direcciones) y F7-2/F7-3 (refrescos+reporte semanal) — ya diseñados en la cola, listos para correr.
- Vista Notion "Hoy" (#1) — alto valor percibido, esfuerzo medio.
- **Resolver el canal QA (#32)** — es el bloqueo más repetido (AS-2, AT, docker_qa en general).
- En cuanto Arturo dé OAuth YouTube (5 min) y llaves Binance testnet (5 min): #14 y #16-19 pasan a 🚀 solos.

**Post-16-ago (se documenta, no bloquea el cierre de ventana):**
- SSH real + Whisper real en la M1 (depende de tener la M1 físicamente con Arturo).
- CETES (#12), TikTok/Instagram (#20), sonido/imágenes automáticas en edición (#21).
- Autoevaluación dominical (#26), alarmas de despertar (#3), sugerencia de cursos (#4).
- Botón de pánico y Home Assistant — explícitamente diferidos por el propio Arturo (r.96/101).
- F11 (voz Piper local, USB-llave) — no bloquean nada crítico.

## 4. Calibración real de tokens/mes del RUNTIME de Hermes (Tarea B, MANDATO §5-6)

**Dos rieles, NUNCA mezclados:**
- **Riel A (cuota Claude Pro del loop, `scripts/loop_tokens.jsonl`):** 8 bloques construidos hoy
  consumieron ~$23 equivalentes de cuota (12 llamadas, 9.6k in / 308.7k out / 28.3M cache_read).
  Es costo de CONSTRUCCIÓN puntual, no recurrente — no es gasto del runtime de Hermes.
- **Riel B (runtime real, `~/.hermes/litellm/cost_ledger/*.jsonl`, DINERO REAL):** medido con
  **1,054 registros reales en 11 días con actividad** (22 jul → 03 ago), no una sola muestra
  (MANDATO §5).
  - **Gasto real total del periodo: $1.275 USD.**
  - **Tokens reales del periodo: 46,067,284** (44.97M prompt + 1.09M completion; 33.7M de eso es
    cache_hit — ~75% cache, por eso el costo se mantiene bajo pese al volumen).
  - Por proveedor: **DeepSeek 55.6%** ($0.709) · **Gemini 30.5%** ($0.388) · **Groq 13.9%** ($0.177)
    — confirma con datos reales que la regla de enrutamiento (r.91, DeepSeek comanda / gratis
    absorbe repetitivo) se está cumpliendo.
  - **Ojo con la tendencia:** 2 de los 11 días (30 jul, y sobre todo 02 ago con 21M tokens — el día
    del loop autónomo) concentran la mayoría del volumen. Días "normales" (22-29 jul, sin
    construcción activa) promedian ~1.68M tokens/día.

**Proyección mensual (dos escenarios, ambos con evidencia real, ninguno inventado):**
| Escenario | Tokens/mes | Gasto/mes |
|---|---|---|
| Promedio de TODOS los 11 días (incluye días de construcción pesada) | ~125.6M | **~$3.48 USD ≈ $64 MXN** |
| Solo días "normales" sin construcción activa (7 de los 11) | ~50.5M | **~$1.40 USD ≈ $26 MXN** |

**Conclusión explícita: SÍ cabe en el presupuesto de $100 MXN/mes, con margen 36-74% incluso en el
escenario más caro medido.** El margen da colchón para cuando entren en producción los flujos que
hoy están 🏗 sin desplegar (correo personal, proactividad real, trading) — pero conviene volver a
medir 30 días después de que Fase 6/9 estén 🚀, no antes, porque hoy el runtime real aún no incluye
esas tareas en producción.

## 5. Pendientes de decisión de Arturo (no inventados, anotados también en ESTADO.md)
- **YouTube: sacar/conectar LAS DOS llaves** (API key Google Cloud Console + OAuth) — confirmado 03 ago, ~10 min.
- **`TELEGRAM_QA_CHANNEL=8727618189` en `.env`** — canal QA ya identificado (03 ago); falta solo escribir la variable, pendiente de confirmación explícita para tocar `.env` (regla dura CLAUDE.md).
- Llaves `BINANCE_TESTNET_API_KEY/_SECRET` (5 min) — guía lista en `docs/BINANCE_TESTNET_GUIA.md`.
- ~~Direcciones de los 2 correos~~ — RESUELTO 03 ago, ya las tenía Hermes; pendiente real es cablear vigilancia del personal (#29).
- Protocolo de pesaje (r.69) y hora exacta del cierre nocturno (r.90) — ya pendientes, sin cambio.
