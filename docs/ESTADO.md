# ESTADO — actualizado: 04 ago 2026 (F11-2 REALINEADO: agente Go al repo, corrige desviación VeraCrypt/SSH)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅, F6-3 ✅) | F7 🔄 bloques 1+2+3 | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | **F11-2 🔄 REALINEADO** | E14 🔄 falta disparo automático | **P3/P5/P6/P7/P8/F6-2/F6-3 ✅** | F12-F14 ⬜ | E10 → v1.7.

## ✅ F11-2 REALINEADO ESTA SESIÓN — agente Go al repo (corrige desviación VeraCrypt/Tailscale/SSH)
Hermes señaló que la implementación anterior (VeraCrypt+Tailscale+SSH a
equipos ajenos) se DESVIÓ del diseño aprobado del skill `hermes-portable-
usb`: la USB es vehículo de un AGENTE Go que habla por Telegram+ntfy.sh,
NUNCA SSH/Tailscale a equipos que no son de Arturo. Verificado antes de
aceptar: el skill existe con esas reglas exactas, y el agente/gateway YA
estaban escritos y compilados desde julio — pero vivían sin control de
versiones en `~/Desktop/hermes_portable/`. Traído a
`usb_llave/agente-go/` (paquetes `agente/` + `gateway/`, Go módulo propio,
sin dependencias externas). **Corrección al propio reporte de Hermes:**
la lista negra de comandos peligrosos y el router multi-dispositivo por
alias YA estaban implementados (no eran pendientes). Compilación cruzada
verificada real: Linux+Windows+**macOS** (amd64 y arm64, antes faltaba).
12/12 pruebas Go nuevas (lista negra, alias, device_id estable).
`usb_llave/start-linux.sh` (VeraCrypt) marcado SUPERADO, no borrado.
**Sigue pendiente:** `device_id` de la HP hardcodeado en el gateway,
token cifrado local, mensaje `bye`/limpieza, prueba real en ALMENDRA sin
Tailscale, fases 5-7 del skill.

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
