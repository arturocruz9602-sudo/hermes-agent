# ESTADO — actualizado: 04 ago 2026 (F6-3 cerrado + P6: correo personal con categorías redes/escolar)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso (F6-3 ✅) | F7 🔄 bloques 1+2+3 hecho | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | **P3/P5/F6-3 ✅ CERRADOS** | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ F6-3 CERRADO ESTA SESIÓN — Correo escolar: analiza + sugiere (r.62-64)
`categorizar()`+`extraer_fecha_limite()` (reglas locales, r.91) arman el
aviso con el formato EXACTO de Arturo: "te llegó un correo, es tarea para
hoy a las 11, ¿qué quieres que realice?" — nunca asume/actúa solo.
Seguimiento r.64: aviso 1h antes + aviso después preguntando si se subió
(JSON propio, no `cola_v2` — ver DECISIONES). Detalle completo en BLOQUES.
23 pruebas + 8 de frescura = 403/403 verde.

## ✅ P6 CERRADO ESTA SESIÓN — Correo personal: categorías "redes" y "escolar"
Arturo encontró en vivo un correo real ("unidad IV_complemento.docx" de un
compañero) que cayó en "neutral" — r.108 nunca definió "escolar" para el
personal. Pidió además "redes" (marca/infracciones/monetización/cambios de
política de YouTube/TikTok/Instagram/Facebook). Hallazgo de diseño: esas
plataformas viven en `RUIDO_DOMINIOS` — `clasificar()` reordenado para
revisar `CLAVES_REDES` ANTES del filtro de ruido, si no un aviso real
("cuenta suspendida") se callaría por venir del mismo dominio que el
ruido social normal. Verificado contra el correo real + regresión (ruido
social sigue callándose). 7 pruebas nuevas, 410/410 `tests/scripts/` verde.

## ⚠️ Hallazgos sin arreglar (arrastrados, no son de esta sesión)
1. `~/.hermes/.env` línea 503 corrupta: cada corrida del watchdog escupe
   `zxei: orden no encontrada` al hacer `source`. Requiere el sí de Arturo.
2. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.

## Decisiones pendientes ARTURO
1. Lista "equipos propios" (`HERMES_EQUIPOS_PROPIOS` vacío hoy).
2. Autorizar llave SSH `hermes-portable` + authkey Tailscale reales.
3. Vision: ¿tier pago/local/gratis? Bloquea 2 extractores (r.91).
4. Horario escuela (r.61): espera a sept-dic.
5. E14: ¿evidencia nocturna al brief matutino, o prefiere otro canal?
6. F7-3: ¿reporte semanal se dispara solo domingo AM, o sigue a demanda?
7. `.env` línea 503 corrupta: ¿la limpio?
8. F6-3: ¿el segundo aviso de seguimiento (después del límite) también
   dispara si Arturo nunca contestó el primero, o se calla si ya intervino
   por su cuenta? Hoy dispara siempre a su hora, sin leer si hubo respuesta.

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 5.
**F11-2:** candado+lanzador Linux 25/25. Falta USB físico, launchers mac/win, decisiones 1-2.

## Bloques recientes CERRADOS
P6: correo personal, categorías redes+escolar, 7/7. · F6-3: correo escolar analiza+sugiere, 23/23. · P5: correo
escolar, alarma de frescura, 7/7. · P3: watchdog cuota, 11/11. · F7-3:
rieles semanales, 24/24. · F7-2: refrescos, 8/8+1. · AT: trading testnet
17/17. · AU: 75/75. · F6-1: correo personal vigilado+deployed. · F6-2:
horario_por_foto 29/29. · F9 pts 1+2: 33/33. · F11-1: voz+cola 26/26.

## No tocar / reglas de equipo
- M1 PRESTADA: reversa antes 6:00. · Correo solo-lectura. · Pruebas masivas
  SOLO Docker QA. · Nada personal a API gratis (r.91). · `has_progress.py`
  NO se usa. · Ninguna credencial real se genera/instala en automático.
- Watchdog vive FUERA del repo; sus pruebas sí van al repo.
- `vigilar_correo_escuela.py` depende de que Thunderbird esté VIVO — si
  falla, ya avisa solo (P5), pero arreglarlo de raíz es cosa de Arturo.

## Próximos candidatos
Cerrar E14 (timer + fuentes + decisión 5). Terminar F11-2. F7-1 bloques
2/3. F6-2 bloques 2/3. F5 resto de vistas. Classroom (r.63): pedir acceso
real a los 2 correos institucionales que Arturo mencionó (hoy solo hay
acceso vía Claude Code, no vía Hermes).

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
Esta sesión: 403/403 `tests/scripts/` ✅, correo escolar con capa de
análisis+sugerencia completa (r.62-64) probada contra el buzón real.
