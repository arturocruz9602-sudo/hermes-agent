# ESTADO — actualizado: 05 ago 2026 (F8-1: motor de sugerencias de gasto)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅, F6-3 ✅) | F7 🔄 bloques 1+2+3 | **F8 🔄 F8-1 ✅** | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | F11-2 🔄 REALINEADO | E14 🔄 falta disparo automático | P3/P5/P6/P7/P8/F6-2/F6-3 ✅ | F12-F14 ⬜ | E10 → v1.7.

## ✅ F8-1: motor de sugerencias de gasto (evaluación proactiva, r.24-27/r.91)
`scripts/motor_sugerencias_gasto.py` — evalúa `libreta.db` con reglas
locales (r.91) y SUGIERE, nunca decide (r.25/r.26). Dos hallazgos: (1)
gasto individual atípico (≥2.5x el promedio histórico de su categoría,
piso $150, mínimo 3 gastos previos) avisado apenas se detecta; (2)
categoría disparada en la semana (≥50% sobre el promedio de las 4
semanas previas, piso $100) para el consolidado dominical. Ninguna
categoría excluida (r.24/r.26 verificado con `inversion_ia`), método de
pago irrelevante (r.27 — libreta.db no lo distingue). No duplica F7-3
(números): este solo dice cuándo algo se sale de lo normal y pregunta
qué hacer. Reusa el patrón de `vigilar_correo_escuela.py` (avisar() vía
`enviar.py`, estado JSON de "vistos" por id, estado ilegible = no
reavisar el histórico). Fix real encontrado al probar: `avisar_fn=avisar`
como default de firma congelaba la función original al importar el
módulo — un monkeypatch de pruebas no llegaba; corregido a
`avisar_fn=None` + resolución dinámica en el cuerpo. 20/20 pruebas
nuevas, 439/439 `tests/scripts/` verde. Registrado permanente en
`scripts/loop_cola.py` (F8-1, estado "hecho"). Commits 52948caa7,
02be93957.

## Decisiones pendientes ARTURO
1. **F8-1 sin disparo automático:** `--evaluar` y `--dominical` corren
   por CLI; falta decidir si `--evaluar` va a un timer frecuente (mismo
   patrón que correo, cada 15 min) y `--dominical` a un timer domingo AM
   (mismo horario que F7-3, r.18) — o si conviven en un solo timer.
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
F8-1: motor de sugerencias de gasto, 20/20. · F11-2 realineado: agente Go
al repo, 12/12. · F6-3 seguimiento ajustado, 23/23. · F6-2: horario por
foto vision real, 7/7. · P8: corroboración 6 pendientes. · P7: bug IMAP,
2/2. · P6: correo personal categorías, 7/7. · resto: ver archivo.

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
F8-1: decidir timers (ver Decisiones pendientes #1). F11-2: device_id HP
dinámico, token cifrado, bye/limpieza, prueba ALMENDRA. Cerrar E14. F7-1
bloques 2/3. F6-2 resto de OT-6. F5 resto vistas.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal
(53°C esta sesión). Esta sesión: F8-1 completo (motor+pruebas), 439/439
`tests/scripts/` verde, registrado en `loop_cola.py`.
