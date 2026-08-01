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
