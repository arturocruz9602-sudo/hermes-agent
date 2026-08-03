# ESTADO — actualizado: 03 ago 2026 (F6-2 BLOQUE 1 hecho: horario por foto, OT-6)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7-F14 ⬜ | **F11 laboratorio VALIDADO (AQ)**. **E10 → v1.7** (meta capital $100k/31-dic-2027, Mac Mini descartada; corregido en AR).

## REGLA QUE CAMBIA TODO (r.20, permanente — ya en CLAUDE.md, regla 6)
Todo dato de fechas/pagos/citas mencionado en pruebas = **SIMULADO** salvo que Arturo marque "dato real". Inventar escenarios y adelantar el reloj: SOLO en el laboratorio Docker. Producción jamás.

## ✅ F6-2 BLOQUE 1 HECHO (03 ago, bloque del loop) — horario por foto (Fase 6/OT-6, r.61-64)
`scripts/horario_por_foto.py`: filas crudas de una foto → `EntradaHorario` (día/hora/materia/aula/profesor) → propuesta legible en Telegram → `aplicar_horario()` **se niega sin `confirmado=True`** explícito (HAS 653-659, nunca auto-alta). Versionado por cuatrimestre (HAS 1157): horario nuevo archiva al anterior (`activo=0`), **nunca lo borra ni lo pisa**; reaplicar el mismo cuatrimestre es idempotente. Filas ilegibles no truenan el parseo, se separan para que Arturo las corrija. Migración `libreta_migrar.py` v5 (columnas `materia`/`profesor`/`cuatrimestre` en `horario`) aplicada en simulación y real — aditiva, sin riesgo, no afecta filas de gym/taquería que ya usan esa tabla. **29/29 pruebas** + CLI `--simular/--aplicar` verificado punta a punta contra `libreta_sim.db` (inserta, idempotente, archivado no pisa otras filas). Bug real corregido en el camino: `normalizar_dia()` matcheaba prefijo invertido ("marciano" colaba como "martes").
**Extractor de vision (foto→filas) es INYECTABLE, PENDIENTE de cablear real** — hallazgo de este bloque: el horario trae nombres de profesores, r.91 (DECISIONES 01 ago) prohíbe mandar **nombres** a API gratuita, y no hay verificación de que `GEMINI_VISION_KEY_NEW` (litellm, modelo `vision`) sea tier de pago. **Decisión pendiente de Arturo:** ¿confirmar que esa llave es de paga, o procesar la foto con modelo local (Ollama HP / M1)? Sin eso, no se manda ninguna foto real de horario a la API.
**Bloques 2 (pizarrón por materia) y 3 (repaso proactivo) de F6-2 NO empezados** — dependían de que el horario existiera primero. Arturo aún no manda la foto real (r.61: este cuatrimestre termina mediados de agosto, no vale la pena; el que importa arranca inicios de septiembre).

## ⏸ Bloque AV — capa de confiabilidad para LOOP autónomo (PAUSADO, redirigido a F6-2 este bloque)
Meta: SSH→tmux→loop que avanza la cola solo, modelo por dificultad, tokens medidos. Paso 1 (hook `hermes-arranque.sh` + skill `/cierre`) HECHO. Siguiente: orquestador con ruteo de modelo por dificultad. Decisión de Arturo pendiente: modo visible en tmux (A) vs headless con bitácora (B) — se inclina por A.
⚠️ Hallazgo sin corregir: CLAUDE.md pt.5 usa `systemctl is-active` SIN `--user` → falso 'inactive' con prod encendida. El hook ya usa `--user`; falta el ok de Arturo para tocar su archivo-contrato.

## Bloques recientes CERRADOS (narrativa completa en `docs/BLOQUES.md`; larga en `docs/archivo/ESTADO_2026-07.md`)
AQ/AR (01 ago): laboratorio Docker validado + libreta reconciliada v4 en producción, 49/49 verde, HAS §E10→v1.7. · AS (02 ago): brief matutino + cierre nocturno en audio + voz→STT→libreta verificado punta a punta. · F5-1 (02 ago, en curso): vista Finanzas en Notion, 2/6 vistas de OT-5. · F5-2 (02 ago): cola de tareas v2 con garantía dura, 11/11 pruebas, pendiente cablear solver/notificador reales. · AT (02 ago): entrenador de trading testnet, 17/17 pruebas, pendiente keys+QA. · AU-1/2/3 (02 ago): motor de guiones + pipeline de clips + corte de silencios/edición M1, 75/75 pruebas combinadas, pendiente OAuth YouTube + SSH M1 real. · F6-1 (03 ago): correo personal vigilado y DESPLEGADO, timer cada 15 min.

## EFICIENCIA — 3 preocupaciones de Arturo (01 ago)
- **P1 variantes:** matriz = GUION_PRUEBAS × 5 roles (F11-d) × escenarios simulados (r.20).
- **P2 exceso de contexto:** techo de tokens por tipo de llamada (base 30 jul: 19.1k/vuelta).
- **P3 DeepSeek:** repetitivo → Gemini-extra/Groq/OpenRouter (r.91), DeepSeek solo comanda; ledger $/función semanal.

## Decisiones pendientes de ARTURO (actualizado 03 ago)
1. **NUEVA (03 ago):** ¿`GEMINI_VISION_KEY_NEW` es tier de pago, o proceso la foto del horario con modelo local? Bloquea cablear el extractor real de `horario_por_foto.py` (r.91: nombres nunca a API gratis).
2. **YouTube: SE OCUPAN LAS DOS llaves (CONFIRMADO 03 ago)** — guía en `docs/YOUTUBE_LLAVES_GUIA.md`. AU-1/AU-2 listos; falta que Arturo las saque (~10 min).
3. **Canal QA de Telegram — RESUELTO 03 ago:** `chat_id=8727618189` verificado. Falta `TELEGRAM_QA_CHANNEL=8727618189` en `.env` — pendiente confirmación para tocar ese archivo.
4. **Llaves `BINANCE_TESTNET_API_KEY/_SECRET`** — AT construido y probado (17/17); guía en `docs/BINANCE_TESTNET_GUIA.md`.
5. **Horario real de la escuela (r.61)** — Arturo lo manda "después", para el cuatrimestre sept-dic. `horario_por_foto.py` ya está listo para recibirlo, en cuanto se resuelva la decisión 1.
(Resuelto: Trading -3% diario CONFIRMADO · PRIVACIDAD montos/tickets SÍ a gratis, correos/contraseñas/nombres/salud NO · Direcciones de los 2 correos, ambos vigilados.)

## No tocar / reglas de equipo
- **M1 PRESTADA (r.102):** config nocturna (caffeinate) se REVIERTE antes de 6:00 y se verifica revertida.
- Correo: solo-lectura SIEMPRE (escuela + personal, ambos vigilados c/15min); borradores/respuestas F6 futuro.
- Gemini Live DESCARTADO (r.99) → alertas iPhone vía Telegram que vibran como llamada.
- Pruebas masivas SOLO en Docker con cuenta QA (r.119). Producción sin tráfico de prueba.
- **has_progress.py NO se usa** (reporta 90% engañoso, bug abierto). Avance real = este archivo.
- **Nombres/correos/contraseñas/salud NUNCA a API gratis** (r.91) — aplica también a fotos de horario/pizarrón (Fase 6).

## Al cierre de cada sesión
ESTADO ≤80 sobreescrito · BLOQUES 1 línea · DECISIONES si hubo · commit+push · TEMP-DIAG=0 · temperatura HP normal.

## Último contexto
03 ago: **F6-2 BLOQUE 1 hecho este bloque** (horario por foto, ver arriba) — F6-2 sigue ABIERTO (bloques 2/3 pendientes). Siguiente candidato natural: cuando Arturo resuelva la decisión de vision (gratis/local/pago), cablear el extractor real; si no, seguir con AV (loop autónomo) o F7 (archivo/finanzas).
