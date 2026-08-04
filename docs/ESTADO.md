# ESTADO — actualizado: 04 ago 2026 (F6-2 cerrado: horario por foto YA con vision real, excepción r.91)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅ vision real, F6-3 ✅) | F7 🔄 bloques 1+2+3 | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | F11-2 🔄 | E14 🔄 falta disparo automático | **P3/P5/P6/P7/P8/F6-2/F6-3 ✅ CERRADOS** | F12-F14 ⬜ | E10 → v1.7.

## ✅ F6-2 CERRADO ESTA SESIÓN — horario por foto YA lee de verdad (excepción r.91 confirmada)
Arturo confirmó la foto real (`img_8cb21472cfba.jpg`, Grupo 301 DSM UTRNG,
mayo-agosto 2026) y, tras marcarle la contradicción con r.91 ("nunca
nombres a API gratis" vs. el horario trae 7 nombres de profesores), eligió
**abrir excepción puntual acotada** (ver DECISIONES) en vez de esperar un
tier de pago. `extractor_gemini_vision()` cableado al alias `vision` de
LiteLLM (Gemini 2.5 Flash, `GEMINI_VISION_KEY_NEW`). **Hallazgo de
eficiencia real:** sin `thinking_config.thinking_budget=0`, el modelo
gastaba ~95% del límite de tokens "pensando" una tarea de puro OCR y el
JSON se cortaba a medias — con el parámetro apagado, 0 tokens de
razonamiento, ~7s de respuesta. Verificado en vivo contra la foto real:
**18/18 clases extraídas correctamente**, nombres incluidos, sin tocar la
libreta (solo `--foto`, sin `--aplicar`). 7 pruebas nuevas (mockean red),
36/36 del módulo, 419/419 `tests/scripts/` verde.

## ⚠️ Hallazgos sin arreglar (arrastrados, no son de esta sesión)
1. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.

## Decisiones pendientes ARTURO
1. Autorizar llave SSH `hermes-portable` + authkey Tailscale reales.
2. Horario escuela sept-dic (r.61): espera a que la escuela lo publique.
   La foto de mayo-agosto ya usada es de PRUEBA (r.20), no el definitivo.
3. F6-3: ¿el segundo aviso de seguimiento (después del límite) también
   dispara si Arturo nunca contestó el primero, o se calla si ya intervino?
4. Correr `systemctl --user daemon-reload` para que el cierre nocturno a
   las 23:00 quede activo (Claude Code no puede, candado de servicios).
5. ¿Aplicar de verdad el horario mayo-agosto a la libreta (`--aplicar`),
   o esperar directo al de sept-dic ya que este cuatrimestre casi termina?

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 3 (ver arriba, era 5).
**F11-2:** candado+lanzador Linux 25/25. Falta USB físico, launchers mac/win, decisión 1.

## Bloques recientes CERRADOS
F6-2: horario por foto con vision real, excepción r.91, 7/7. · P8:
corroboración 6 pendientes (.env no corrupto, 3 ya resueltos, 2 nuevos
registrados). · P7: bug IMAP (reaviso infinito), 2/2. · P6: correo
personal categorías redes+escolar, 7/7. · F6-3: correo escolar
analiza+sugiere, 23/23. · P5: alarma de frescura, 7/7. · P3: watchdog
cuota, 11/11. · F7-3: rieles semanales, 24/24. · AT/AU/F6-1/F9/F11-1: ver archivo.

## No tocar / reglas de equipo
- M1 PRESTADA: reversa antes 6:00. · Correo solo-lectura. · Pruebas masivas
  SOLO Docker QA. · **Nada personal a API gratis (r.91), EXCEPTO fotos de
  horario escolar → Gemini Vision (excepción acotada 04 ago, ver
  DECISIONES) — no es puerta abierta a nombres en general.**
- `.env` línea 503 (app password Gmail): NUNCA se toca, no está corrupta.
- Watchdog vive FUERA del repo; sus pruebas sí van al repo.
- `vigilar_correo_escuela.py` depende de que Thunderbird esté VIVO — si
  falla, ya avisa solo (P5).

## Próximos candidatos
Cerrar E14 (timer + fuentes + decisión). Terminar F11-2. F7-1 bloques 2/3.
F6-2 resto de OT-6 (foto de pizarrón, seguimiento de entregas escalonado).
F5 resto de vistas.

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta sesión: 419/419 `tests/scripts/` ✅, extractor de visión real probado
contra la foto real de Arturo con evidencia pegada (18/18 clases).
