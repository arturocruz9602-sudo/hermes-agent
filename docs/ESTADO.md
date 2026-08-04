# ESTADO — actualizado: 03 ago 2026 (loop: E14 ventana de mantenimiento nocturna)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7 🔄 BLOQUES 1+2 hecho | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | **E14 🔄 motor+1a fuente lista, falta disparo automático** | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## 🔄 E14 EN CURSO (03 ago, loop) — Ventana de mantenimiento nocturna (§E14, r.103)
`scripts/ventana_mantenimiento.py`: gate horario (`en_ventana()`, solo 2:00-5:00,
se niega salvo `--forzar`) + gate térmico (r.103, pausa si HP>=85°C, lector/
dormir inyectables) + persistencia SOBRE `cola_v2` (F5-2, decisión en
DECISIONES.md 03 ago — no se inventó cola nueva, la garantía dura de F5-2 ya
cubre "evidencia": toda tarea termina notificada/atorada, nunca en silencio).
Primera fuente conectada: `detectar_skills_stale()` (§F5/§E3, last_verified
>180d sobre skills `status:active`); `acumular()` encola sin duplicar;
`solver_mantenimiento()` re-verifica al ejecutar (no repara — eso es F2v2,
mecanismo aparte) y deja evidencia real en `task_queue`/`task_queue_log`.
17/17 pruebas (ventana, gate térmico, detección, dedup, skill corregida/
borrada entre acumular y correr, tipo desconocido→atorada, conteo no mezcla
otros usos reales de la cola). CLI verificado en vivo contra `~/.hermes/skills`
real (16 skills con `last_verified`, ninguna stale hoy → 0 encolados, `estado`
correcto en `{}`).

**PENDIENTE de E14 (no cerrar el bloque sin esto):**
1. Fuente "bugs con logs" — el subsistema real de reporte de errores no
   existe todavía; no se inventó aquí.
2. Fuente "propuestas del barrido semanal" — el barrido semanal en sí
   (F3/F4) tampoco corre todavía; cuando exista, alimenta esta misma cola.
3. **Disparo automático real**: hoy NADA invoca `correr()` solo dentro de
   2:00-5:00 — falta timer systemd (mismo patrón que `hermes-correo-
   personal.timer` de F6-1). Sin esto, el mecanismo existe pero no actúa.
4. Decidir con Arturo si/cómo la evidencia llega a él (hoy `notificador_
   mantenimiento` es no-op a propósito — no se quiso inventar un canal de
   aviso a las 3am sin que él lo pida; candidato: engancharlo al brief
   matutino de AS cuando ese resumen exista).

## Decisiones pendientes ARTURO (sin cambios esta sesión, ver F11-2)
1. Lista de "equipos propios" (hostnames/IPs HP/MacBook que NUNCA piden
   registro de autorización) — hoy `HERMES_EQUIPOS_PROPIOS` vacío.
2. Autorizar generar la llave SSH `hermes-portable` + authkey de
   Tailscale reales (acción irreversible sobre `authorized_keys`).
3. Vision: tier pago/local/gratis? Bloquea 2 extractores (r.91).
4. YouTube: SE OCUPAN LAS DOS llaves (confirmado) — guía en `docs/YOUTUBE_LLAVES_GUIA.md`.
5. Telegram QA: `chat_id=8727618189` verificado; falta `TELEGRAM_QA_CHANNEL` en `.env`.
6. Binance testnet: llaves en guía `docs/BINANCE_TESTNET_GUIA.md`.
7. Horario escuela (r.61): espera a sept-dic; `horario_por_foto.py` listo si se resuelve decisión 3.
8. E14 punto 4 de arriba: ¿engancho la evidencia nocturna al brief matutino, o prefiere otro canal?

## 🔄 F11-2 EN CURSO (arrastrado, sin cambios esta sesión) — USB-llave
Candado de autorización (18/18) + lanzador Linux (7/7) ya listos (ver
`docs/archivo/` para detalle completo). Falta: OT-11 pt.1 (particionar
USB físico, necesita hardware real), `start-macos.command`/
`start-windows.bat`, `ingest_usb.sh`, y decisiones 1-2 de arriba.

## Bloques recientes CERRADOS
AT: trading testnet 17/17. · AU: 75/75 pruebas motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29 (vision pendiente). · F9 pts 1+2: reglas+detección, 33/33. · F11-1: notif_voz + integracion cola 26/26 tests. · P2: presupuesto de contexto — guarda de punta a punta, 4/4 pruebas. · F10-rec: recetario buscar/validar/nueva, 17/17 pruebas.

## No tocar / reglas de equipo
- M1 PRESTADA (r.102): reversa antes 6:00.
- Correo solo-lectura (ambos vigilados 15min).
- Pruebas masivas SOLO Docker QA.
- Nombres/correos/contraseñas/salud NUNCA a API gratis (r.91).
- has_progress.py NO se usa (bug abierto).
- Ninguna credencial real (llave SSH `hermes-portable`, authkey
  Tailscale) se genera/instala en automático — siempre pregunta primero.

## Próximos candidatos
Cerrar E14 (timer systemd + fuentes 2/3 + decisión 8 de Arturo), terminar
F11-2 (macOS/Windows launchers + ingest_usb.sh, una vez resueltas decisiones
1-2 de arriba), F7-1 bloques 2/3 (reporte PDF), F6-2 bloques 2/3, F5 resto de
vistas, AV (loop confiabilidad).

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta corrida: `tests/scripts/test_ventana_mantenimiento.py` 17/17 ✅ (nuevo),
`tests/scripts/test_cola_v2.py` 11/11 ✅ (sin regresión), TEMP-DIAG=0,
temp HP 45°C (normal).
