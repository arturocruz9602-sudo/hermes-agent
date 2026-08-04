# ESTADO — actualizado: 03 ago 2026 (F11-2 loop: candado de autorización + lanzador Linux del USB-llave)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7 🔄 BLOQUES 1+2 hecho | F9 🔄 puntos 1+2 hechos | F8,F10 ⬜ | F11-1 ✅ | **F11-2 🔄 en curso (loop)** | F12-F14 ⬜ | **E10 → v1.7** (meta capital $100k/31-dic-2027).

## REGLA QUE CAMBIA TODO (r.20, permanente — ya en CLAUDE.md, regla 6)
Todo dato de fechas/pagos/citas mencionado en pruebas = **SIMULADO** salvo que Arturo marque "dato real". Inventar escenarios y adelantar el reloj: SOLO en el laboratorio Docker. Producción jamás.

## 🔄 F11-2 EN CURSO (03 ago, loop) — USB-llave: la llave, no el cerebro (§B8/§OT-11)
`scripts/registro_autorizacion_terceros.py` (B8.4/OT-11 pt.3, candado que exige §E7):
registrar/revocar/vigentes/autoriza/exigir_autorizacion — consentimiento con
expiración dura (nunca indefinido sobre equipo ajeno), log de todo intento
concedido o negado. `EQUIPOS_PROPIOS` deliberadamente VACÍO por default
(HERMES_EQUIPOS_PROPIOS sin definir) — **no se inventó la lista de hostnames
propios de Arturo (HP/MacBook), queda como decisión pendiente abajo.** 18/18 pruebas.

`usb_llave/start-linux.sh` (OT-11 pt.2, lanzador Linux): monta bóveda VeraCrypt
(passphrase SIEMPRE interactivo vía el propio `veracrypt`, nunca por
argumento/env — mismo principio que `bovedar_secretos.py`), lee `config.env`
de DENTRO de la bóveda ya montada (nunca en la partición sin cifrar), levanta
tailscale solo si hace falta, abre `ssh -> hermes` en la HP; limpieza (desmontar
+ bajar tailscale si lo levantó él) SIEMPRE corre al salir vía trap EXIT, incluso
si ssh falla. Probado con veracrypt/tailscale/ssh FALSOS inyectados por PATH
(sin bóveda real ni hardware prestado no se puede probar contra binarios de
verdad). 7/7 pruebas.

**PENDIENTE de F11-2:** OT-11 punto 1 (particionar el USB físico — requiere el
USB real de Arturo, no se puede desde esta sesión); `start-macos.command` y
`start-windows.bat` (mismo diseño que el de Linux, sin escribir aún);
`ingest_usb.sh` (modo sin internet, OT-11 pt.4); generar la llave SSH dedicada
`hermes-portable` real y el authkey de Tailscale re-generable — **NO generados
en automático a propósito: tocar `authorized_keys`/credenciales reales de
producción exige el "sí" de Arturo (CLAUDE.md regla de acciones irreversibles)**.

## Decisiones pendientes ARTURO (actualizado 03 ago, F11-2)
1. **Nueva:** lista de "equipos propios" (hostnames/IPs de la HP/MacBook que
   NUNCA piden registro de autorización) — hoy `HERMES_EQUIPOS_PROPIOS` vacío.
2. **Nueva:** autorizar generar la llave SSH `hermes-portable` + authkey de
   Tailscale reales y meterlos a la bóveda (acción irreversible sobre `authorized_keys`).
3. Vision: tier pago/local/gratis? Bloquea 2 extractores (r.91).
4. YouTube: SE OCUPAN LAS DOS llaves (confirmado) — guía en `docs/YOUTUBE_LLAVES_GUIA.md`.
5. Telegram QA: `chat_id=8727618189` verificado; falta `TELEGRAM_QA_CHANNEL` en `.env`.
6. Binance testnet: llaves en guía `docs/BINANCE_TESTNET_GUIA.md`.
7. Horario escuela (r.61): espera a sept-dic; `horario_por_foto.py` listo si se resuelve decisión 3.

## Bloques recientes CERRADOS
AQ/AR: Docker validado + libreta v4 prod. · AS: brief+cierre audio+STT. · F5-1: Notion Finanzas 2/6. · F5-2: cola v2 11/11 pruebas. · AT: trading testnet 17/17. · AU: 75/75 pruebas motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29 (vision pendiente). · F9 pts 1+2: reglas+detección, 33/33. · **F11-1: notif_voz + integracion cola 26/26 tests.**

## No tocar / reglas de equipo
- M1 PRESTADA (r.102): reversa antes 6:00.
- Correo solo-lectura (ambos vigilados 15min).
- Pruebas masivas SOLO Docker QA.
- Nombres/correos/contraseñas/salud NUNCA a API gratis (r.91).
- has_progress.py NO se usa (bug abierto).
- **Nueva (F11-2):** ninguna credencial real (llave SSH `hermes-portable`,
  authkey Tailscale) se genera/instala en automático — siempre pregunta primero.

## Próximos candidatos
Terminar F11-2 (macOS/Windows launchers + ingest_usb.sh, una vez resueltas
decisiones 1-2 de arriba), F7-1 bloques 2/3 (reporte PDF), F6-2 bloques 2/3,
F5 resto de vistas, AV (loop confiabilidad).

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta corrida: `tests/scripts/` completo 321/321 ✅ (sin regresiones), TEMP-DIAG=0,
temp HP pico 52°C (normal).
