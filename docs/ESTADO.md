# ESTADO — actualizado: 01 ago 2026 (post-cuestionario: 123 respuestas de Arturo integradas)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` (respondido) = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6-F14 ⬜ | E10 INVALIDADO por respuesta 28 (meta nueva: capital $100,000, Mac Mini descartada) — corregir con AR.

## REGLA NUEVA QUE CAMBIA TODO (respuesta 20, permanente)
**Todo dato de fechas/pagos/citas mencionado en pruebas = SIMULADO salvo que Arturo marque "dato real".**
La colegiatura del 31 jul queda ANULADA como dato real. Claude Code tiene autorización para inventar
escenarios completos y adelantar el reloj — SOLO dentro del laboratorio Docker. Producción jamás.

## OBJETIVO ACTUAL (bloqueado hasta cerrarse)
**Bloque AQ: primera corrida real del laboratorio Docker.** Imagen + compose.lab + restaurar respaldo
20260731 + 1 suite del arnés en verde con evidencia. Arturo autorizó gasto de pruebas (r.78: "si se van
a gastar 200 pesos en tokens, que se gasten, pero que Hermes salga súper eficiente") — cortacircuitos vigentes.
**Gate térmico nuevo (r.103): medir temperatura de la HP antes/durante corridas; pausar si sube de umbral (definir con sensors).**

## COLA DE AGOSTO (orden por los dolores de r.97: dinero → YouTube/redes → Hermes completo)
1. **AR — La libreta + datos semilla reales** (`libreta_seed.md` ya existe con las 123 respuestas estructuradas).
   Probada en lab (AQ la desbloquea) → producción con respaldo. Incluye: fuente de ingreso NUEVA
   (venta de refrescos, r.16 — Hermes mide el patrón), meta capital $100,000, gastos corregidos.
2. **AS — Brief 6:30 + cierre nocturno por VOZ** (r.73, r.86, r.90): brief con clima cruzado vs agenda +
   noticias de trading + plan del día; cierre nocturno donde Arturo manda nota de voz y Hermes extrae
   gastos/hábitos/peso. Necesita AR.
3. **AT — Trading testnet (OT-10)**: conectar `trading_entrenador.py` a testnet Binance, corridas diarias
   autónomas, registro completo. Lo pidió "lo más pronto posible" (r.36). VER NOTA DE EXPECTATIVAS abajo.
4. **AU — Motor de guiones desde Obsidian + pipeline de clips** (r.45-48): guion con gancho/cierre/retención
   de podcast; TODOS los clips valiosos ≤2 min se programan en mejores horarios; OAuth YouTube (r.59: se adapta).
5. Transversal SIEMPRE: **presupuesto de contexto** (ver abajo) — es parte del arnés, no una tarea aparte.

## EFICIENCIA — respuesta directa a las 3 preocupaciones de Arturo (01 ago)
- **P1 "variantes en Docker":** la matriz de pruebas = GUION_PRUEBAS (13 bloques) × 5 roles (F11-d) ×
  escenarios inventados bajo la regla de simulación (r.20). Claude Code EXTIENDE el guion con eventos
  inesperados (r.78: "todas las variables posibles") — cada corrida nocturna agrega escenarios nuevos al guion.
- **P2 "que nunca haya llamadas con exceso de contexto":** el arnés gana una prueba PERMANENTE de
  regresión de tokens: techo de tokens de prompt por tipo de llamada (chat simple / con memoria / con tools),
  medido en CADA corrida del lab con ≥3 muestras. Si una llamada excede su techo → la suite FALLA como
  si fuera un bug funcional. Base medida el 30 jul: 19.1k/vuelta tras el recorte de 65k. Ese es el techo inicial.
- **P3 "eficientizar DeepSeek":** (a) todo lo repetitivo va a Gemini-extra/Groq/OpenRouter (r.91), DeepSeek
  solo comanda; (b) ledger por llamada con costo, ya existe — se agrega reporte semanal de $/función;
  (c) el recorte de prompt de sistema (~40k) sube de prioridad: entra como parte de AQ-AR, no después.

## Decisiones pendientes de ARTURO (lo que él debe mandar/decidir)
1. **Horario del cuatrimestre sept-dic** — lo manda cuando lo tenga (r.61); este ciclo ya no se carga (termina ~15 ago).
2. **Correos exactos de las 2 cuentas** (escuela y redes) para configurar a HERMES (Claude Code ya tiene acceso; Hermes no — r.63).
3. **Privacidad (r.91 quedó sin resolver — no entendió la pregunta):** propuesta default para que confirme:
   montos y tickets SÍ pueden ir a APIs gratis; correos completos, nombres y salud NO. Un "ok jefe" y queda.
4. Confirmar el apagado de emergencia de trading a -3% diario (r.40: no entendió — ya explicado en chat).
5. OAuth de YouTube (5 min) cuando arranque AU.

## No tocar / reglas nuevas de equipo
- **M1 es PRESTADA (r.102):** toda config nocturna (caffeinate para render) se REVIERTE antes de las 6:00.
  Script de préstamo: aplicar → trabajar → restaurar → verificar restaurado. Jamás dejar la Mac alterada.
- Correo: sigue solo-lectura. NUEVO destino aprobado (r.67, r.107): borradores de respuesta con aprobación
  explícita por correo — se diseña en F6, no se enciende nada todavía.
- Gemini Live/llamadas: DESCARTADO (r.99). En su lugar: investigar alertas críticas en iPhone vía Telegram
  (notificaciones que vibran como llamada) para emergencias y olvidos.
- Pruebas masivas SOLO en Docker con cuenta QA (r.119). Producción no recibe tráfico de prueba.

## Al cierre de cada sesión
ESTADO ≤80 líneas sobreescrito · BLOQUES 1 línea · DECISIONES si hubo · commit+push · TEMP-DIAG=0 · temperatura HP ok.

## Último contexto
01 ago: cuestionario de 123 respuestas integrado. E10 invalidado (meta nueva). Regla de simulación adoptada.
Cola de agosto fijada por los dolores reales de Arturo. Eficiencia de contexto convertida en prueba permanente del arnés.
