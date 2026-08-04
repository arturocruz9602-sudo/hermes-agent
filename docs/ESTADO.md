# ESTADO — actualizado: 04 ago 2026 (correo escolar: Thunderbird caído 3 días en silencio, arreglado + alarma de frescura)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7 🔄 bloques 1+2+3 hecho | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | **P3/P5 ✅ CERRADOS** | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ P5 CERRADO ESTA SESIÓN — Correo escolar: 3 días ciego en silencio + alarma de frescura
Arturo reportó que ayer llegó correo y Hermes no avisó. Causa raíz real:
`vigilar_correo_escuela.py` NO usa IMAP en vivo — lee el mbox LOCAL que
Thunderbird sincroniza. `app-thunderbird\x2dhermes@autostart.service`
llevaba MUERTO desde el 01 ago 02:55 (3 días); el vigilante leía la misma
foto congelada y honestamente reportaba "sin novedades" cada 15 min — sin
poder confirmar que de verdad no había nada nuevo. Una tarea real ("Plan
de pruebas") se quedó sin avisar los 3 días.
**Arreglo (1):** Arturo reinició Thunderbird por SSH (nombre de unidad
escapado `\x2d`, requiere comillas simples) — reconectó solo, sin pedir
OAuth. Confirmado: mbox creció de inmediato; corrida manual avisó la tarea.
**Arreglo (2, permanente):** `scripts/vigilar_correo_escuela.py` +
`verificar_frescura()` — si el mbox lleva >4h sin tocarse (o no existe),
avisa por Telegram en vez de reportar "todo bien" a ciegas; no satura
(reavisa cada 4h mientras siga caído); avisa también cuando se recupera.
7/7 pruebas nuevas, 387/387 `tests/scripts/` verde.
**Pendiente real, más grande:** el vigilante hoy solo reenvía
remitente/asunto — NO analiza ni sugiere qué hacer (r.62-64 lo pide).
Construido el 31 jul, antes de que el cuestionario pidiera esa capa.

## ⚠️ Hallazgos sin arreglar (arrastrados, no son de esta sesión)
1. `~/.hermes/.env` línea 503 corrupta: cada corrida del watchdog escupe
   `zxei: orden no encontrada` al hacer `source`. Requiere el sí de Arturo.
2. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.

## Decisiones pendientes ARTURO
1. Lista "equipos propios" (`HERMES_EQUIPOS_PROPIOS` vacío hoy).
2. Autorizar llave SSH `hermes-portable` + authkey Tailscale reales.
3. Vision: ¿tier pago/local/gratis? Bloquea 2 extractores (r.91).
4. YouTube: sacar las 2 llaves — guía en `docs/YOUTUBE_LLAVES_GUIA.md`.
5. Telegram QA: falta `TELEGRAM_QA_CHANNEL=8727618189` en `.env`.
6. Binance testnet: llaves en guía `docs/BINANCE_TESTNET_GUIA.md`.
7. Horario escuela (r.61): espera a sept-dic.
8. E14: ¿evidencia nocturna al brief matutino, o prefiere otro canal?
9. F7-3: ¿reporte semanal se dispara solo domingo AM, o sigue a demanda?
10. `.env` línea 503 corrupta: ¿la limpio?
11. Correo escolar: ¿agrego la capa de análisis+sugerencia (r.62-64)?

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 8.
**F11-2:** candado+lanzador Linux 25/25. Falta USB físico, launchers mac/win, decisiones 1-2.

## Bloques recientes CERRADOS
P5: correo escolar, alarma de frescura, 7/7 (detalle arriba). · P3: watchdog cuota, 11/11. · F7-3: rieles semanales, 24/24 (380→387 total). · F7-2: refrescos, 8/8+1. · AT: trading testnet 17/17. · AU: 75/75. · F6-1: correo personal vigilado+deployed. · F6-2: horario_por_foto 29/29. · F9 pts 1+2: 33/33. · F11-1: voz+cola 26/26. · F10-rec: recetario 17/17.

## No tocar / reglas de equipo
- M1 PRESTADA: reversa antes 6:00. · Correo solo-lectura. · Pruebas masivas
  SOLO Docker QA. · Nada personal a API gratis (r.91). · `has_progress.py`
  NO se usa. · Ninguna credencial real se genera/instala en automático.
- Watchdog vive FUERA del repo; sus pruebas sí van al repo.
- `vigilar_correo_escuela.py` depende de que Thunderbird esté VIVO — si
  falla, ya avisa solo (P5), pero arreglarlo de raíz es cosa de Arturo.

## Próximos candidatos
Capa de análisis+sugerencia en correo escolar (r.62-64, decisión 11).
Cerrar E14 (timer + fuentes + decisión 8). Terminar F11-2. F7-1 bloques
2/3. F6-2 bloques 2/3. F5 resto de vistas.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta sesión: 387/387 `tests/scripts/` ✅ + Thunderbird revivido y verificado
con evidencia real (tarea "Plan de pruebas" avisada 07:46).
