# ESTADO — actualizado: 07 ago 2026 (F11-2c: cierre de pendientes USB)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅, F6-3 ✅) | F7 🔄 bloques 1+2+3 | F8 🔄 F8-1 ✅ F8-2 ✅ | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | **F11-2 🔄 solo falta Fase 4 (prueba real en ALMENDRA)** | E14 🔄 falta disparo automático | P3/P5/P6/P7/P8/F6-2/F6-3 ✅ | F12-F14 ⬜ | E10 → v1.7.

## ✅ F11-2c: los 3 pendientes técnicos de la USB portátil, cerrados (detalle en BLOQUES.md)
A pedido de Arturo: `deviceIDLocalHP` del gateway ya no es un string
hardcodeado (calculado igual que el del agente, hostname+hash de
machine-id) · token de ntfy.sh cifrado local con `secret.enc`
(AES-256-GCM + KDF propia, sin dependencias externas — límite conocido:
passphrase visible al teclear, sin lib de terminal cross-platform en
stdlib) · mensaje `bye` real al recibir Ctrl+C/SIGTERM, el gateway lo
recibe y marca `connected:false` en dispositivos.json. Verificado real:
24/24 pruebas Go, cross-build de los 5 binarios limpio, y prueba
end-to-end con el binario compilado (passphrase mala falla limpio,
buena descifra y publica hello real en ntfy.sh, SIGTERM publica bye
real). De paso corregido `hermes-portable-usb/SKILL.md` (checklist
desactualizado desde 04 ago, decía lista negra de 4 y sin router
multi-dispositivo cuando el código ya tenía ambos completos) → v0.3.0.
**Único pendiente real de F11-2: Fase 4, prueba en ALMENDRA físico —
necesita a Arturo con el equipo a mano, no se resuelve desde la HP.**

## Hallazgos de la sesión de ayer (06 ago), resueltos o seguidos
- **Incidente nocturno resuelto:** `git reset` a `origin/main` dejó el
  árbol sin código de Hermes ~10h (madrugada 06 ago), tumbó 4 timers.
  Causa raíz ya corregida (merge `aa6633941`) y `arturo/prod`
  sincronizado. Detalle completo: `docs/archivo/` o commit `18d36bd77`.
- **Sigue abierto:** alerta DeepSeek 2 noches seguidas (05-06 ago),
  gap ~$0.09 USD/noche entre saldo real y ledger de litellm, saldo
  $2.77 USD. No investigado aún — falta decidir con Arturo si se
  prioriza antes de que el circuito de $10 MXN/día se dispare.

## Decisiones pendientes ARTURO
1. Gap $0.09 USD/noche en DeepSeek: ¿investigar ahora o después?
2. F11-2 Fase 4: prueba real en ALMENDRA — falta que Arturo tenga el equipo a mano.
3. Horario escuela sept-dic (r.61): espera a que la escuela lo publique.
4. `reboot-required` pendiente en el sistema — no forzado, decide Arturo cuándo.

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 3.
**F11-2:** solo falta Fase 4 (prueba ALMENDRA) — resto ya cerrado hoy.

## ⚠️ Hallazgos sin arreglar (arrastrados)
1. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.
2. Sin ventana de mantenimiento que proteja timers de un merge/reset git en curso.
3. Passphrase de `secret.enc` (USB) se teclea visible — falta input sin eco cross-platform.

## Bloques recientes CERRADOS (detalle completo en `docs/BLOQUES.md`)
F11-2c: device_id dinámico + token cifrado + bye (USB), 24/24 · F8-2:
motor de sugerencias v2, 18/18 · F8-1: motor de sugerencias, 20/20.

## No tocar / reglas de equipo
- M1 PRESTADA: reversa antes 6:00. · Correo solo-lectura. · Pruebas masivas
  SOLO Docker QA. · Nada personal a API gratis (r.91), EXCEPTO fotos de
  horario escolar → Gemini Vision (excepción acotada, ver DECISIONES).
- `.env` línea 503 (app password Gmail): NUNCA se toca, no está corrupta.
- **F11-2/USB: SOLO Telegram+ntfy.sh — sin SSH, sin Tailscale a equipos
  ajenos.** Tailscale limitado a HP+Mac+iPhone, tema DISTINTO.
- Watchdog vive FUERA del repo; sus pruebas sí van al repo.
- Flujo normal: local `main` + `git push fork HEAD:arturo/prod` (no hay
  branch local `arturo/prod`) — el riesgo real es dejar `main` reseteado
  a `origin/main` sin remergear rápido.
- Modo `-encrypt` del agente USB corre SIEMPRE en la HP (equipo de
  confianza), NUNCA en la USB ya insertada en un equipo ajeno.

## Próximos candidatos
Gap $0.09 USD/noche en DeepSeek. Ventana de mantenimiento que bloquee
timers durante merge/reset de git. F11-2 Fase 4 (ALMENDRA). Cerrar E14.
F5/F9 resto.

## Al cierre
Esta sesión: cerrados los 3 pendientes técnicos de F11-2 (device_id
dinámico, token cifrado, bye) a pedido de Arturo, verificado con
pruebas reales + binario compilado. Falta commit+push de código (Go +
SKILL.md) y decidir con Arturo el gap de DeepSeek.
