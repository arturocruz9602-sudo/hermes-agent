# ESTADO — actualizado: 01 ago 2026 (AQ cerrado: laboratorio Docker validado; siguiente AR)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6-F14 ⬜ | **F11 laboratorio VALIDADO (AQ)**. E10 INVALIDADO por r.28 (meta: capital $100,000, Mac Mini descartada) — se corrige en AR.

## REGLA QUE CAMBIA TODO (r.20, permanente — ya en CLAUDE.md, regla 6)
Todo dato de fechas/pagos/citas mencionado en pruebas = **SIMULADO** salvo que Arturo marque "dato real". La colegiatura del 31 jul queda ANULADA. Inventar escenarios y adelantar el reloj: SOLO en el laboratorio Docker. Producción jamás.

## ✅ AQ CERRADO (01 ago) — primera corrida real del laboratorio, con evidencia
Imagen `hermes-agent:latest` construida (966 MB) + respaldo `20260731_040925` restaurado en volumen aislado `hermes-lab-data` (nunca `~/.hermes`) → `integrity_check` de state.db y memoria_semantica.db = **ok** (27 tablas, 2919 msgs, 273 sesiones) + smoke del código real de Hermes leyendo la DB + arnés host 57/57. Pico térmico **59°C** (umbral 85, nunca disparó). `down -v` hecho. **Primera prueba real de que los respaldos de Arturo SÍ restauran.** Detalle: BLOQUES/DECISIONES.

## OBJETIVO ACTUAL (bloqueado hasta cerrarse)
**Bloque AR: la libreta.** Migración aditiva de tablas de vida a state.db (ingresos por fuente / gastos / ahorro_metas / peso / entrenamientos / habitos / horario / citas / guiones) + carga de `LIBRETA_SEED.md` (123 datos reales) + reescritura HAS §E10 (v1.7: meta capital $100,000; refrescos r.16 como fuente nueva; gastos corregidos). Secuencia F11-e: migración numerada → probar en lab sobre state.db restaurado + meses simulados encima → integrity_check + skills finanzas/salud leyendo y escribiendo → SOLO entonces producción con respaldo y tu aprobación (F7.2). Gate térmico r.103 vigente.

## COLA DE AGOSTO (tras AR; orden r.97: dinero → YouTube/redes → Hermes completo)
1. **AS — Brief 6:30 + cierre nocturno por VOZ** (r.73/86/90): brief clima×agenda + noticias trading + plan; cierre por nota de voz, Hermes extrae gastos/hábitos/peso. Necesita AR.
2. **AT — Trading testnet (OT-10)**: `trading_entrenador.py` a testnet Binance; simular capital hasta **5,000 MXN, ciclos SEMANALES**; estrategia news-driven (caída + noticias que apuntan a alza = arriesgar); **investigar mejores estrategias en la web**. Meta 2,000/sem = objetivo de ENTRENAMIENTO, no promesa (r.36-43). Primero entrenar el modelo.
3. **AU — Motor de guiones desde Obsidian + pipeline de clips** (r.45-48): guion gancho/cierre/retención; TODOS los clips ≤2 min programados en mejores horarios; OAuth YouTube (r.59).
4. Transversal: **presupuesto de contexto** — prueba permanente del arnés (techo 19.1k/vuelta, ≥3 muestras).

## EFICIENCIA — 3 preocupaciones de Arturo (01 ago)
- **P1 variantes:** matriz = GUION_PRUEBAS × 5 roles (F11-d) × escenarios simulados (r.20); cada corrida nocturna agrega escenarios.
- **P2 exceso de contexto:** techo de tokens por tipo de llamada, medido en cada corrida del lab (≥3 muestras); exceder = suite en rojo. Base 30 jul: 19.1k/vuelta.
- **P3 DeepSeek:** repetitivo → Gemini-extra/Groq/OpenRouter (r.91), DeepSeek solo comanda; ledger $/función semanal; recorte del prompt ~40k entra con AR.

## Decisiones pendientes de ARTURO (sigue leyendo el cuestionario — 01 ago)
1. Freno de emergencia de trading a **-3% diario, sí/no** (r.40) — coexiste con la estrategia agresiva, solo protege el capital.
2. OAuth de YouTube (5 min) cuando arranque AU.
(Resuelto 01 ago: **PRIVACIDAD confirmada** — montos/tickets SÍ a gratis; correos/contraseñas/nombres/salud/datos que vulneren su seguridad NO. **Horario** oficial lo manda él a Hermes; may-ago = simulación (`docs/HORARIO_SIMULACION.md`). **Correos** = trabajo F6, no decisión. Estándar de docs lo define Claude Code, MANDATO §8.)

## No tocar / reglas de equipo
- **M1 PRESTADA (r.102):** config nocturna (caffeinate) se REVIERTE antes de 6:00 y se verifica revertida.
- Correo: solo-lectura; borradores con aprobación por correo se diseñan en F6, nada encendido.
- Gemini Live DESCARTADO (r.99) → alertas iPhone vía Telegram que vibran como llamada.
- Pruebas masivas SOLO en Docker con cuenta QA (r.119). Producción sin tráfico de prueba.
- **has_progress.py NO se usa** (reporta 90% engañoso, bug abierto). Avance real = este archivo.

## Al cierre de cada sesión
ESTADO ≤80 sobreescrito · BLOQUES 1 línea · DECISIONES si hubo · commit+push · TEMP-DIAG=0 · temperatura HP normal.

## Último contexto
01 ago: reestructura documental + cuestionario 123 integrado + CLAUDE.md v1.3 (4 parches) + **AQ cerrado (laboratorio Docker validado, respaldos que restauran probados por primera vez)**. Siguiente: AR (la libreta).
