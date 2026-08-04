# ESTADO — actualizado: 03 ago 2026 (loop: F7-2 — fix real, ingresos de refrescos)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | **F7 🔄 BLOQUES 1+2 hecho (F7-2 CERRADO real esta vuelta)** | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ F7-2 CERRADO ESTA VUELTA (loop) — Ingresos de refrescos (r.16, HAS §E10)
El bloque ya estaba marcado "hecho" (632ff215c, `analizador_refrescos.py`
detecta el patrón), pero DECISIONES.md (01 ago) pedía además "tabla
`ingresos` la registra por separado" — y eso NUNCA se cumplió:
`registrar_compra_negocio()`/`registrar_venta_negocio()` (de antes de F7-2)
solo escribían en `negocio_compras`/`negocio_ventas`, nunca en
`gastos`/`ingresos`. Verificado en disco: `cierre_del_dia_audio.py` usa
`lib.balance()`, que suma `ingresos` — un día con venta real de refrescos
reportaba "no registré ingresos hoy". Fix (`scripts/libreta.py`): ambas
funciones ahora también insertan en gastos (categoría `negocio_<producto>`)
/ ingresos (fuente `negocio_<producto>`), monto consistente con
`ganancia_total()` del analizador (venta bruta − costo de cajas). +1 prueba
en `test_libreta.py` (balance real tras compra+venta: ingresos=200,
gastos=328, saldo=-128). **356/356 `tests/scripts/` verde.** Commit
436b1d5e5. Bitácora actualizada con ejemplo verificado en vivo.

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

## 🔄 E14 EN CURSO (arrastrado, sin cambios esta sesión) — Ventana de mantenimiento nocturna
Motor + gate horario/térmico + 1a fuente (`detectar_skills_stale`) listos,
17/17 pruebas (ver `docs/archivo/` para detalle). **Falta:** timer systemd
real (nada invoca `correr()` solo), fuente "bugs con logs" (no existe el
subsistema), fuente "barrido semanal" (tampoco existe), decisión 8 de arriba.

## 🔄 F11-2 EN CURSO (arrastrado, sin cambios esta sesión) — USB-llave
Candado de autorización (18/18) + lanzador Linux (7/7) ya listos (ver
`docs/archivo/` para detalle completo). Falta: OT-11 pt.1 (particionar
USB físico, necesita hardware real), `start-macos.command`/
`start-windows.bat`, `ingest_usb.sh`, y decisiones 1-2 de arriba.

## Bloques recientes CERRADOS
F7-2: analizador_refrescos.py + fix real de ingresos, 8/8 + 1 nueva = verde. · AT: trading testnet 17/17. · AU: 75/75 pruebas motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29 (vision pendiente). · F9 pts 1+2: reglas+detección, 33/33. · F11-1: notif_voz + integracion cola 26/26 tests. · F10-rec: recetario buscar/validar/nueva, 17/17 pruebas.

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
vistas.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta corrida: `tests/scripts/test_libreta.py` 44/44 ✅ (1 nueva),
`tests/scripts/` completo 356/356 ✅ (sin regresión), TEMP-DIAG=0,
temp HP 55°C (normal).
