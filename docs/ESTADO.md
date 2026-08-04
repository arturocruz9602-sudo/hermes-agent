# ESTADO — actualizado: 04 ago 2026 (F6-3 cerrado: correo escolar ya analiza+sugiere)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso (F6-3 ✅) | F7 🔄 bloques 1+2+3 hecho | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | **P3/P5/F6-3 ✅ CERRADOS** | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ F6-3 CERRADO ESTA SESIÓN — Correo escolar: analiza + sugiere (r.62-64)
`vigilar_correo_escuela.py` solo reenviaba remitente/asunto. Ahora clasifica
en tarea/entrega/examen/aviso (`categorizar()`), extrae fecha límite local
por regex (`extraer_fecha_limite()` — prioriza el campo propio de Classroom
"Fecha de entrega: D mes"; nunca manda contenido de correo a ninguna API,
r.91) y arma el aviso con el formato EXACTO de Arturo: "Arturo, te llegó un
correo de la escuela, es una tarea para hoy a las 11, ¿qué quieres que
realice?" (`construir_mensaje()`) — cierra preguntando, nunca asume/actúa
solo. **Hallazgo real al probar contra el buzón real:** la primera versión
leía cualquier "HH:MM" suelto del cuerpo como hora límite y confundía
"Publicado el 5:01 p.m." (pie de Classroom) con la entrega — se quitó ese
fallback, la hora solo cuenta pegada a "a las/antes de las/hasta las".
**Seguimiento r.64:** `registrar_seguimiento()`+`verificar_seguimientos()`
guardan tarea/entrega/examen con fecha resuelta en JSON de pendientes;
1er aviso (1h antes: "solo faltan estos detalles...") y 2do aviso (después
del límite: "¿ya subiste...?") ambos implementados y probados — no quedó
como WIP, alcanzó el tiempo de la sesión. Decisión de diseño: seguimiento
usa JSON propio (mismo patrón que SALUD/vistos ya en este archivo), NO
`cola_v2.py` — su máquina de estados no tiene noción de "no antes de esta
hora", encaja para tareas con solver/escalera de proveedores, no para
recordatorios de reloj de pared (ver DECISIONES). 23 pruebas nuevas + 8 de
`verificar_frescura` = 403/403 `tests/scripts/` verde.

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
F6-3: correo escolar analiza+sugiere, 23/23 (detalle arriba). · P5: correo
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
