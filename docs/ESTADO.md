# ESTADO — actualizado: 05 ago 2026 (F8-2: motor de sugerencias v2)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅, F6-3 ✅) | F7 🔄 bloques 1+2+3 | **F8 🔄 F8-1 ✅ F8-2 ✅** | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | F11-2 🔄 REALINEADO | E14 🔄 falta disparo automático | P3/P5/P6/P7/P8/F6-2/F6-3 ✅ | F12-F14 ⬜ | E10 → v1.7.

## ✅ F8-2: motor de sugerencias v2 — pagos_recurrentes + negocio (r.24-27)
`scripts/motor_sugerencias_gasto.py` (F8-1) ampliado: `gastos` hoy casi
vacía (1 registro), así que el consolidado dominical ahora también cruza
(1) `pagos_recurrentes` — `detectar_pagos_recurrentes_sin_registrar()`
señala un fijo (gym/deepseek/colegiatura/...) sin gasto en su ciclo
actual, PERO solo si ya hubo un registro previo de ese fijo (nunca
confirmado ≠ desviación, mismo criterio que `brief_matutino.py` con
`ultimo_pago` NULL — evita ruido desde el día uno); (2) negocio de
refrescos (`negocio_compras`/`negocio_ventas`) — `detectar_reja_mas_cara()`
(última compra vs. la anterior), `detectar_ritmo_ventas_bajo()` (piezas/día
de la semana vs. promedio de 4 semanas, mismo patrón que
`detectar_categorias_disparadas` pero hacia abajo), y
`detectar_negocio_no_recupera_reja()` (usa `margen_negocio()` de Libreta,
plazo de gracia de 10 días desde la última compra). Todo entra a
`construir_consolidado_dominical()`; `--evaluar` y el cron (ya agendado
aparte, jobs 13bea6149ae0/7132f383cb07) no cambiaron — este bloque solo
amplió lectura de datos. Verificado con `--dominical --probar --entorno
real` contra libreta.db real: sin ruido falso hoy (esperado, dado el
historial casi vacío). 18 pruebas nuevas, 38/38
`test_motor_sugerencias_gasto.py`, 457/457 `tests/scripts/` verde.
Registrado permanente en `scripts/loop_cola.py` (F8-2, "hecho").
BITACORA_ARTURO.md actualizada (visible el próximo domingo 8am). Commit
8726a8440.

## Decisiones pendientes ARTURO
1. **F8-1/F8-2 sin timer propio decidido:** el cron YA quedó agendado por
   Hermes aparte (jobs 13bea6149ae0 `--evaluar`/7132f383cb07 `--dominical`
   domingo 8am) — esta línea queda solo como registro, no bloquea nada.
2. Horario escuela sept-dic (r.61): espera a que la escuela lo publique.
3. Correr `systemctl --user daemon-reload` para que el cierre nocturno a
   las 23:00 quede activo (Claude Code no puede, candado de servicios).
4. F11-2: prueba real en ALMENDRA (Windows, sin Tailscale) — falta que
   Arturo tenga el equipo a mano para probar agente+gateway de verdad.

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 3.
**F11-2:** falta device_id HP dinámico, token cifrado, bye/limpieza, prueba ALMENDRA.

## ⚠️ Hallazgos sin arreglar (arrastrados, no son de esta sesión)
1. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.

## Bloques recientes CERRADOS
F8-2: motor de sugerencias v2 (fijos+negocio), 18/18. · F8-1: motor de
sugerencias de gasto, 20/20. · F11-2 realineado: agente Go al repo,
12/12. · F6-3 seguimiento ajustado, 23/23. · F6-2: horario por foto
vision real, 7/7. · P8: corroboración 6 pendientes. · resto: ver archivo.

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
ALMENDRA. Cerrar E14. F7-1 bloques 2/3. F6-2 resto de OT-6. F5 resto
vistas. F9 puntos 3/4.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal
(49°C esta sesión). Esta sesión: F8-2 completo (motor ampliado+pruebas),
457/457 `tests/scripts/` verde, registrado en `loop_cola.py`, BITACORA
actualizada.
