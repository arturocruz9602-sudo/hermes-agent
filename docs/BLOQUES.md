# BLOQUES — índice (una línea por bloque, PROTOCOLO §3)
**Narrativa completa de cada bloque: `docs/archivo/BLOQUES_2026-07.md`. Letras consecutivas, únicas, no se reusan.**
**⚠️ Deuda detectada 01 ago: las letras AG y AH se usaron DOS veces (24 jul y 30 jul) — violación de §3 ya ocurrida.
Se conservan con sufijo de fecha para no romper referencias. El siguiente bloque libre es AQ.**

O  | 22 jul | Tarea E v2: autoevaluación real vía Gemini | cerrado ✅ (O.6 el 27 jul)
P  | 22 jul | Diagnóstico punto ciego de inyección de contexto | cerrado ✅
OT-0.5 | 22-23 jul | Emergencia de credenciales: rotación y purga | cerrado ✅
Q  | 23 jul | Cierre real de O: fix + verificación E2E | cerrado ✅
Q-Z | 23 jul | Sesión nocturna autónoma (arnés, QA, fixes varios) | cerrados ✅ (detalle en archivo)
AA-AD | 23 jul | Sesión de mañana | cerrados ✅
AE | 23 jul | Diagnóstico fabricación "guardé tu contraseña" | cerrado ✅ en AF
AF | 24 jul | Fix L13/AE + prep OT-QA | cerrado ✅
AG(24jul) | 24 jul | Memoria SQL separada para cuenta QA | cerrado ✅
AH(24jul) | 24 jul | Bug duplicación por compactación en state.db | cerrado ✅
AI | 24-25 jul | Incidente: Bash roto por cuota de disco /tmp | cerrado ✅
OT-QA | 27 jul | Login real cuenta QA Telegram | cerrado ✅ (userbot api_id/api_hash: abandonable, decidir)
S.5 | 27 jul | Cascada de compactación infinita + ventana O.6 | cerrado ✅
F2 | 27-28 jul | HAS Fase 2 completa + corte a producción (Bloque 6) | cerrado ✅
F3 | 28 jul | HAS Fase 3 completa (OT-3 Bloques 1-5, skills) | cerrado ✅
F4 | 28-29 jul | HAS Fase 4: índice semántico + aprobación candidatos | Bloques 2-3 ✅ · OT-4 B1 en curso (¿derogar?)
— | 29 jul | Obsidian local + tool + espejo Notion | cerrado ✅
— | 29 jul | Cola v2 (E5) · SSH solo Tailscale · fix /memoria | cerrados ✅
O.1.2 | 29 jul | Hueco O.1 vs web_search + arranque Fase 5 | cerrado parcial ❌ (hueco SIGUE abierto)
AG(30jul) | 30 jul | Tarea E muerta en silencio: credenciales LiteLLM | cerrado ✅
AH(30jul) | 30 jul | Watchdog revertía config por "401" en session_id | cerrado ✅ (causa raíz de AG)
AI-AM | 30 jul | Jornada de rendimiento: peaje 65k→19.1k tokens/vuelta | cerrados ✅
AN | 30 jul | DeepSeek llave principal + frenos (max_turns 25) | cerrado ✅
AO | 31 jul | Sesión arquitectura: 3 hallazgos (libreta, privacidad, Ollama) | cerrado ✅
AP | 31 jul | Separación de entornos: HAS §F11 + lab Docker | en curso 🔄 (docs ✅, lab nunca corrido; se cierra con AQ)
— | 01 ago | Reestructura documental + cuestionario 123 respuestas integrado (ESTADO/DECISIONES/SEED) | cerrado ✅
AQ | 01 ago | Primera corrida real del lab: imagen + restaurar respaldo 20260731 (integrity ok) + smoke + arnés 57/57 + gate térmico (pico 59°C) | cerrado ✅
AR | 01 ago | La libreta RECONCILIADA: la libreta ya existia (libreta.db); migracion v4 (gastos/meta $100k/peso/habitos) validada en lab F11-e + aplicada a prod con respaldo; +libreta.db al respaldo; HAS §E10 v1.7 | cerrado ✅
AS | 01 ago | Brief 6:30 DESPLEGADO (brief_matutino.py + timer, verificado en simulacion con reloj virtual); falta cierre nocturno en audio + verificar voz→libreta | en curso 🔄
AS-2 | 02 ago | Cierre nocturno en AUDIO (r.90): cierre_del_dia_audio.py genera+verifica .ogg (ffprobe=opus) reusando tts_tool; enviar.py ahora detecta .ogg→sendVoice (verificado sin trafico real, mock de requests.post) | en curso 🔄 (falta: canal QA o aprobacion de Arturo para envio en vivo, timer nocturno, hora r.90 confirmada) ← SIGUIENTE
AT | — | Trading testnet: conectar trading_entrenador.py, corridas diarias autónomas | pendiente (necesita AQ)
AU | — | Motor de guiones desde Obsidian + pipeline de clips + OAuth YouTube | pendiente
AV | 02 ago | Capa de confiabilidad para loop autónomo: hook arranque SessionStart + skill /cierre + lista de tareas viva | en curso 🔄 (paso 1 hecho; sigue orquestador multi-modelo)
F5-1 | 02 ago | Tablero único Notion: vista "Finanzas" (notion_finanzas.py) + timer 15min, verificado en vivo contra API real, 7/7 pruebas | en curso 🔄 (2/6 vistas de OT-5; faltan Hoy/Kanban/Cola/Escuela + Bloques 1/3/4)
