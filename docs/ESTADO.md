# ESTADO — actualizado: 03 ago 2026 (F10-rec loop: recetario de soluciones)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7 🔄 BLOQUES 1+2 hecho | F9 🔄 puntos 1+2 hechos | **F10 🔄 recetario listo, falta índice semántico (Fase 4) y métrica E8** | F11-1 ✅ | F11-2 🔄 en curso | F12-F14 ⬜ | **E10 → v1.7** (meta capital $100k/31-dic-2027).

## REGLA QUE CAMBIA TODO (r.20, permanente — ya en CLAUDE.md, regla 6)
Todo dato de fechas/pagos/citas mencionado en pruebas = **SIMULADO** salvo que Arturo marque "dato real". Inventar escenarios y adelantar el reloj: SOLO en el laboratorio Docker. Producción jamás.

## ✅ F10-rec CERRADO (03 ago, loop) — Recetario de soluciones (§F10)
`scripts/recetario.py`: `buscar(consulta)` — lo que Hermes consulta ANTES
de razonar un problema desde cero (F10-b), grep por palabra clave sobre
sintoma_corto/componente/cuerpo, ranking por score. `validar_receta()`/
`validar_todas()` — candado de formato (front-matter fecha/autor/
sintoma_corto/componente + 5 secciones en orden + nombre descriptivo,
no `receta-N.md`). `nueva_receta()` — obligación de cierre de Claude
(F10-a) y de Hermes cuando resuelve algo nuevo (F10-c): nunca escribe un
archivo que no pase `validar_receta` primero. CLI + API Python. README
de `docs/recetario/` documenta el uso. 17/17 pruebas, incluidas las 2
recetas reales existentes (`compactacion-en-cascada...`,
`telethon-signin-cliente-distinto...`) validando limpio sin tocarlas.

**PENDIENTE de F10 (no bloquea el resto):** conectar `buscar()` al
índice semántico de la Fase 4 (hoy es grep, HAS F10-b pide indexado
semántico — mejora futura, no defecto); métrica mensual de E8 (%
resuelto por receta/Hermes sin tocar a Claude, depende de que loop_cola
u otro caller reporte cuándo una receta evitó escalar).

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

## 🔄 F11-2 EN CURSO (arrastrado, sin cambios esta sesión) — USB-llave
Candado de autorización (18/18) + lanzador Linux (7/7) ya listos (ver
`docs/archivo/` para detalle completo). Falta: OT-11 pt.1 (particionar
USB físico, necesita hardware real), `start-macos.command`/
`start-windows.bat`, `ingest_usb.sh`, y decisiones 1-2 de arriba.

## Bloques recientes CERRADOS
AQ/AR: Docker validado + libreta v4 prod. · AS: brief+cierre audio+STT. · F5-1: Notion Finanzas 2/6. · F5-2: cola v2 11/11 pruebas. · AT: trading testnet 17/17. · AU: 75/75 pruebas motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29 (vision pendiente). · F9 pts 1+2: reglas+detección, 33/33. · F11-1: notif_voz + integracion cola 26/26 tests. · P2: presupuesto de contexto — guarda de punta a punta, 4/4 pruebas, 3/3 corridas estables. · **F10-rec: recetario buscar/validar/nueva, 17/17 pruebas.**

## No tocar / reglas de equipo
- M1 PRESTADA (r.102): reversa antes 6:00.
- Correo solo-lectura (ambos vigilados 15min).
- Pruebas masivas SOLO Docker QA.
- Nombres/correos/contraseñas/salud NUNCA a API gratis (r.91).
- has_progress.py NO se usa (bug abierto).
- Ninguna credencial real (llave SSH `hermes-portable`, authkey
  Tailscale) se genera/instala en automático — siempre pregunta primero.

## Próximos candidatos
Terminar F11-2 (macOS/Windows launchers + ingest_usb.sh, una vez resueltas
decisiones 1-2 de arriba), F7-1 bloques 2/3 (reporte PDF), F6-2 bloques 2/3,
F5 resto de vistas, AV (loop confiabilidad), conectar `recetario.buscar()`
al índice semántico cuando la Fase 4 exista.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta corrida: `tests/scripts/test_recetario.py` 17/17 ✅ (nuevo), TEMP-DIAG=0,
temp HP 50°C (normal).
