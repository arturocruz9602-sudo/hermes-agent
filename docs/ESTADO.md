# ESTADO — actualizado: 04 ago 2026 (F11-2 realineado + regla vieja de DeepSeek corregida en 3 documentos)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅, F6-3 ✅) | F7 🔄 bloques 1+2+3 | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | **F11-2 🔄 REALINEADO** | E14 🔄 falta disparo automático | **P3/P5/P6/P7/P8/F6-2/F6-3 ✅** | F12-F14 ⬜ | E10 → v1.7.

## ✅ F11-2 REALINEADO — agente Go al repo (detalle completo en BLOQUES)
Corrige desviación VeraCrypt/Tailscale/SSH del diseño aprobado
(`hermes-portable-usb`). Traído a `usb_llave/agente-go/` desde
`~/Desktop/hermes_portable/` (sin control de versiones ahí). Probado en
vivo con infraestructura real hoy: agente→ntfy.sh→gateway→Telegram
round-trip exitoso, `device_id` estable confirmado. 12/12 pruebas Go.
Falta: `device_id` HP dinámico, token cifrado, `bye`/limpieza, prueba
real en ALMENDRA, fases 5-7.

## ✅ CORREGIDA regla vieja de DeepSeek en 3 documentos (obsoleta desde 30 jul)
Hermes reportó un incidente (429 Gemini/Groq, fallback a DeepSeek
~$0.011 USD) como posible violación de "DeepSeek nunca automático" —
esa regla quedó obsoleta el 30 jul cuando DeepSeek pasó a `chat-primary`
(Bloque AN), mismo bug de raíz que P3 (hoy) pero viviendo en documentos,
no en código. Verificado: `litellm/config.yaml` confirma chat-primary=
DeepSeek real. Corregidos `~/.hermes/CLAUDE.md` (+ respaldo del original,
no tiene git), `docs/MANDATO_ARTURO.md`, `docs/HAS.md` (regla L17) — los
3 ya dicen que DeepSeek automático es el diseño vigente, protegido por
`max_turns`+`hard_stop`+presupuesto, no por un aviso sí/no.

## ✅ F6-3: segundo aviso de seguimiento DESACTIVADO (confirmado por Arturo)
"Si un correo llega aunque yo no te diga nada, que no se vuelva a mandar
el segundo aviso" — el aviso DESPUÉS ("¿ya subiste?") ya no se manda por
Telegram, solo queda en el log (mismo patrón que P5-b). 23/23 pruebas.

## ⚠️ Hallazgos sin arreglar (arrastrados, no son de esta sesión)
1. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.

## Decisiones pendientes ARTURO
1. ~~Llave SSH `hermes-portable` + authkey Tailscale~~ — RESUELTO: Arturo
   confirmó que NO se necesitan en el diseño correcto (agente Go, no SSH).
2. Horario escuela sept-dic (r.61): espera a que la escuela lo publique.
3. Correr `systemctl --user daemon-reload` para que el cierre nocturno a
   las 23:00 quede activo (Claude Code no puede, candado de servicios).
4. F11-2: prueba real en ALMENDRA (Windows, sin Tailscale) — falta que
   Arturo tenga el equipo a mano para probar agente+gateway de verdad.

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 3.
**F11-2:** ver arriba — falta device_id HP dinámico, token cifrado, bye/limpieza, prueba ALMENDRA.

## Bloques recientes CERRADOS
F11-2 realineado: agente Go al repo, 12/12. · F6-3 seguimiento ajustado,
23/23. · F6-2: horario por foto vision real, 7/7. · P8: corroboración 6
pendientes. · P7: bug IMAP, 2/2. · P6: correo personal categorías, 7/7. ·
P5: alarma de frescura, 7/7. · P3: watchdog cuota, 11/11. · resto: ver archivo.

## No tocar / reglas de equipo
- M1 PRESTADA: reversa antes 6:00. · Correo solo-lectura. · Pruebas masivas
  SOLO Docker QA. · Nada personal a API gratis (r.91), EXCEPTO fotos de
  horario escolar → Gemini Vision (excepción acotada, ver DECISIONES).
- `.env` línea 503 (app password Gmail): NUNCA se toca, no está corrupta.
- **F11-2/USB: SOLO Telegram+ntfy.sh — sin SSH, sin Tailscale a equipos
  ajenos (regla dura del skill hermes-portable-usb).** Tailscale limitado
  a HP+Mac+iPhone; eso es un tema DISTINTO (HERMES_EQUIPOS_PROPIOS), no
  es parte de la USB.
- Watchdog vive FUERA del repo; sus pruebas sí van al repo.

## Próximos candidatos
F11-2: device_id HP dinámico, token cifrado, bye/limpieza, prueba
ALMENDRA. Cerrar E14. F7-1 bloques 2/3. F6-2 resto de OT-6. F5 resto vistas.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta sesión: agente/gateway Go compilan y pasan pruebas desde el repo
(verificado desde cero, como clon limpio) + F6-3 ajustado.
