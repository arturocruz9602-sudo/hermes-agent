# ESTADO — actualizado: 04 ago 2026 (loop: P3 — watchdog, alarma falsa de cuota)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7 🔄 bloques 1+2+3 hecho | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | **P3 ✅ CERRADO esta vuelta** | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ P3 CERRADO ESTA VUELTA (loop) — Watchdog: alarma falsa de cuota
Hoy 06:54 el watchdog le avisó a Arturo "Gemini y Groq agotaron su cuota,
Hermes entra en pausa" mientras **DeepSeek respondía todo el tiempo**. No
fue caída: desde el Bloque AN (30 jul) `chat-primary` es
`deepseek-v4-flash` y la escalera gratuita (Gemini→Groq→OpenRouter) es
RESPALDO; falló una llamada interna a `chat-gratis` con Groq en cooldown
de 16h por un 429 de ayer — el diseño funcionando. El watchdog veía un 429
en los logs de LiteLLM y concluía "ambos agotados" sin mirar si el
PRINCIPAL seguía vivo, y prometía "NO se usará DeepSeek automáticamente",
falso desde el 30 jul.
**Arreglo** en `~/.hermes/scripts/watchdog.sh` (FUERA del repo; respaldo en
`watchdog.sh.bak-P3-20260804-070528`): (1) si `is_deepseek_ok` —el curl que
ya existía, sin gasto extra— da 200, `both_quota_exhausted=false`; (2)
alerta solo si cae TODA la escalera, DeepSeek incluido; (3) texto nuevo sin
la promesa falsa + aviso de vuelta genérico. Intactos el fix del 30 jul
(ledger <240s → no alerta) y las demás secciones (auth, contexto, gateway,
flapping NIC). NO se tocó `hermes-gateway` ni `litellm/config.yaml`.
**Pruebas:** `scripts/test_watchdog_p3.sh` corre el watchdog REAL en un HOME
sandbox con `journalctl`/`curl`/`systemctl`/`ping` stubeados (sin Telegram,
sin producción, sin gastar cuota): **11/11 verde**. Evidencia REAL en
producción 07:08:38, con 429 verdadero en la ventana: `🟢 Cuota agotada en
la escalera gratuita (Gemini/Groq), pero DeepSeek — el principal — responde
(HTTP 200) — resolviendo en silencio, sin alertar a Arturo`. P3 registrado
permanente en `scripts/loop_cola.py`.

## ⚠️ Hallazgos sin arreglar (esta vuelta, NO son de P3)
1. `~/.hermes/.env` línea 503 corrupta: cada corrida del watchdog escupe
   `zxei: orden no encontrada` al hacer `source`. No rompe nada hoy, pero
   tocar `.env` requiere el sí de Arturo → pendiente de autorización.
2. Ruido cosmético en `watchdog.log`: `echo: error de escritura: Tubería
   rota` cuando `grep -q` corta la tubería. Inofensivo, fuera de P3.

## Decisiones pendientes ARTURO (sin cambios esta sesión)
1. Lista de "equipos propios" (hostnames/IPs HP/MacBook que NUNCA piden
   registro de autorización) — hoy `HERMES_EQUIPOS_PROPIOS` vacío.
2. Autorizar generar la llave SSH `hermes-portable` + authkey de
   Tailscale reales (acción irreversible sobre `authorized_keys`).
3. Vision: tier pago/local/gratis? Bloquea 2 extractores (r.91).
4. YouTube: SE OCUPAN LAS DOS llaves (confirmado) — guía en `docs/YOUTUBE_LLAVES_GUIA.md`.
5. Telegram QA: `chat_id=8727618189` verificado; falta `TELEGRAM_QA_CHANNEL` en `.env`.
6. Binance testnet: llaves en guía `docs/BINANCE_TESTNET_GUIA.md`.
7. Horario escuela (r.61): espera a sept-dic; `horario_por_foto.py` listo si se resuelve decisión 3.
8. E14: ¿engancho la evidencia nocturna al brief matutino, o prefiere otro canal?
9. F7-3: ¿reporte semanal se dispara solo domingo AM (r.18 lo pide), o sigue a demanda?
10. `.env` línea 503 corrupta (hallazgo 1 de arriba): ¿la limpio?

## 🔄 EN CURSO (arrastrados, sin cambios esta sesión)
**E14 (ventana nocturna):** motor + gate horario/térmico + `detectar_skills_stale`,
17/17 (detalle en `docs/archivo/`). Falta: timer systemd real (nada invoca
`correr()` solo), fuentes "bugs con logs" y "barrido semanal" (no existen), decisión 8.
**F11-2 (USB-llave):** candado (18/18) + lanzador Linux (7/7). Falta: OT-11 pt.1
(USB físico), `start-macos.command`/`start-windows.bat`, `ingest_usb.sh`, decisiones 1-2.

## Bloques recientes CERRADOS
P3: watchdog deja de alertar cuando cae solo el respaldo, 11/11. · F7-3: reporte semanal de rieles, 24/24 nuevas + fix de aislamiento entre pruebas (380/380 `tests/scripts/`). · F7-2: analizador_refrescos.py + fix real de ingresos, 8/8+1. · AT: trading testnet 17/17. · AU: 75/75 motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29. · F9 pts 1+2: 33/33. · F11-1: notif_voz + cola, 26/26. · F10-rec: recetario, 17/17.

## No tocar / reglas de equipo
- M1 PRESTADA (r.102): reversa antes 6:00. · Correo solo-lectura. ·
  Pruebas masivas SOLO Docker QA. · Nada personal a API gratis (r.91). ·
  `has_progress.py` NO se usa (bug abierto). · Ninguna credencial real se
  genera/instala en automático — siempre pregunta primero.
- El watchdog vive FUERA del repo (`~/.hermes/scripts/watchdog.sh`): sus
  cambios se documentan aquí y en BITÁCORA, y sus pruebas sí van al repo.

## Próximos candidatos
Cerrar E14 (timer systemd + fuentes 2/3 + decisión 8), terminar F11-2
(launchers macOS/Windows + `ingest_usb.sh`), F7-1 bloques 2/3 (reporte PDF),
F6-2 bloques 2/3, F5 resto de vistas.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta corrida: `test_watchdog_p3.sh` 11/11 ✅ + corrida real del watchdog en
producción con evidencia pegada arriba (07:08:38). TEMP-DIAG=0.
