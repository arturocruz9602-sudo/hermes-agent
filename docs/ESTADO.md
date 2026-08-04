# ESTADO — actualizado: 04 ago 2026 (loop: F7-3 — reporte semanal rieles)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | **F7 🔄 BLOQUES 1+2+3 hecho (F7-3 CERRADO esta vuelta)** | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ F7-3 CERRADO ESTA VUELTA (loop) — Reporte semanal de rieles financieros (r.18)
`scripts/reporte_rieles_semanales.py` (commit 354afa0b3, ya en main al
abrir esta vuelta): balance semanal, ingresos por fuente, gastos por
categoría, negocio de refrescos (rejas/invertido/ROI), meta $100k por
31-dic-2027 (r.28, piso $90k), depósito objetivo $3,500/mes prorrateado
(r.29), pagos recurrentes. Esta vuelta: +24 pruebas nuevas
(`test_reporte_rieles_semanales.py`, todas verdes en aislado). Al correr
la suite COMPLETA salieron 21 fallas que no estaban en el archivo nuevo
mismo — causa raíz real: 4 fixtures (`test_libreta.py`,
`test_motor_guiones.py`, `test_pipeline_clips.py`,
`test_archivo_biblioteca.py`) hacían `importlib.reload(libreta)` en el
teardown ANTES de que `monkeypatch` revirtiera `HERMES_DISCO_PRUEBAS`,
dejando el módulo `libreta` envenenado (apuntando a un tmp_path ya
borrado) para el resto de la sesión de pytest — cualquier prueba después
de esas 4, en cualquier archivo, que abriera entorno "simulacion" fallaba.
Fix: `monkeypatch.undo()` antes del reload final en las 4. Además se
verificaron a mano (real, no simulado) los números de negocio de
refrescos de esta semana contra `libreta.db`: coinciden exacto con lo que
ya traía `BITACORA_ARTURO.md` sin commitear (ingresos $300, gastos
$10.80, saldo $289.20, ROI -8.5%). Hallazgo sin arreglar (no es bug, es
esperado): la compra de $328 del 03-ago (23:10) quedó fuera de `gastos`
porque el fix de F7-2 (436b1d5e5, 23:36 ese mismo día) no es retroactivo
— compras/ventas ANTERIORES al fix no se reescriben. **380/380
`tests/scripts/` verde** (356 previos + 24 nuevas). Commit 9417f0184.

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
9. F7-3: ¿reporte semanal se dispara solo domingo AM (r.18 lo pide), o
   sigue a demanda? Hoy solo corre si se invoca.

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
F7-2: analizador_refrescos.py + fix real de ingresos, 8/8 + 1 nueva = verde. · AT: trading testnet 17/17. · AU: 75/75 pruebas motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29 (vision pendiente). · F9 pts 1+2: reglas+detección, 33/33. · F11-1: notif_voz + integracion cola 26/26 tests. · F10-rec: recetario buscar/validar/nueva, 17/17 pruebas. · F7-3: reporte semanal de rieles, 24/24 nuevas + fix de aislamiento entre pruebas.

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
Esta corrida: `test_reporte_rieles_semanales.py` 24/24 ✅ (nuevo),
`tests/scripts/` completo 380/380 ✅ (sin regresión, incluye fix de
contaminación entre pruebas), TEMP-DIAG=0, temp HP 48°C (normal).
