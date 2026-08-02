# ESTADO — actualizado: 02 ago 2026 (AV en curso: capa de confiabilidad para loop autónomo; AS pausado por redirección)
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
Meta de Arturo: SSH desde MacBook → tmux (sesión `claude`) → loop PAUSADO que avanza la cola solo, visible en terminal, con **modelo por dificultad** (Sonnet simple / Opus 4.8 complejo) y tokens medidos por bloque. **Paso 1 HECHO y verificado a mano:** hook `.claude/hooks/hermes-arranque.sh` (SessionStart, `exit 0` siempre, salud en `--user`) + skill `/cierre` (6 pasos) + lista de tareas viva. Ambos entran en vigor al próximo `/clear`/arranque. **SIGUIENTE:** orquestador con ruteo de modelo por dificultad (respeta B10: skills, no subagentes-que-escriben).
⚠️ Hallazgo: CLAUDE.md pt.5 usa `systemctl is-active` SIN `--user` → falso 'inactive' con prod ENCENDIDA (gateway/litellm `active`). El hook usa `--user`; falta corregir esa línea de CLAUDE.md (propuesto, pendiente del ok de Arturo — es su archivo-contrato).

## EN COLA — Bloque AS (pausado por redirección de Arturo, retomar tras AV)
✅ **Brief 6:30 LISTO y desplegado:** `scripts/brief_matutino.py` (agenda horario+citas · clima Open-Meteo sin llave, cruzado con gym/trabajo · pagos realmente próximos · tareas · meta capital · trading Brave best-effort). Timer `hermes-brief-matutino.timer` armado (próx. dom 06:30). Verificado en SIMULACIÓN (lunes con reloj adelantado) + corre desde ruta de prod. Todo determinista/APIs gratis.
Falta para cerrar AS:
- **Cierre nocturno en AUDIO (r.90):** hoy `cierre_del_dia.py` (22:45) empuja la pregunta en TEXTO; falta el resumen del día en audio a la hora de dormir.
- **Verificar voz→libreta punta a punta:** STT transcribe y el Hermes vivo extrae a la libreta — probarlo con una nota de voz real (cuenta QA o Arturo).
⚠️ Hueco anotado (AT/simulación): la clase `Libreta` no conoce el entorno `laboratorio` (solo real/simulación); en el contenedor se sortea con `real`.

## COLA DE AGOSTO (tras AS; orden r.97: dinero → YouTube/redes → Hermes completo)
1. **AT — Trading testnet (OT-10)**: `trading_entrenador.py` a testnet Binance; simular capital hasta **5,000 MXN, ciclos SEMANALES**; estrategia news-driven (caída + noticias que apuntan a alza = arriesgar); **investigar mejores estrategias en la web**. Meta 2,000/sem = objetivo de ENTRENAMIENTO, no promesa (r.36-43). Primero entrenar el modelo.
2. **AU — Motor de guiones desde Obsidian + pipeline de clips** (r.45-48): guion gancho/cierre/retención; TODOS los clips ≤2 min programados en mejores horarios; OAuth YouTube (r.59).
3. Transversal: **presupuesto de contexto** — prueba permanente del arnés (techo 19.1k/vuelta, ≥3 muestras).

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
02 ago: Arturo redirige a montar el **loop autónomo que mira por SSH+tmux** con modelo por dificultad. AV paso 1 (capa de confiabilidad: hook de arranque + skill `/cierre`) HECHO y verificado. Prod CONFIRMADA arriba (gateway/litellm `active` en `--user`; mi "prod caída" del inicio fue error de scope). Siguiente: orquestador multi-modelo, luego encender loop y retomar AS.
