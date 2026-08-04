# ESTADO — actualizado: 04 ago 2026 (F6-3, P6 categorías redes/escolar, P7 bug real de IMAP corregido)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso (F6-3 ✅) | F7 🔄 bloques 1+2+3 hecho | F9 🔄 puntos 1+2 hechos | F10 🔄 recetario listo, falta índice semántico | F11-1 ✅ | F11-2 🔄 en curso | E14 🔄 motor+1a fuente lista, falta disparo automático | **P3/P5/P6/P7/F6-3 ✅ CERRADOS** | F12-F14 ⬜ | E10 → v1.7 (meta capital $100k/31-dic-2027).

## ✅ F6-3/P6/P7 CERRADOS ESTA SESIÓN (detalle completo en BLOQUES.md)
**F6-3** — correo escolar: `categorizar()`+`extraer_fecha_limite()` arman
el aviso con el formato EXACTO de Arturo ("te llegó un correo, es tarea
para hoy a las 11, ¿qué quieres que realice?"); seguimiento r.64 (aviso 1h
antes + después preguntando si se subió, JSON propio no `cola_v2`, ver
DECISIONES). 23 pruebas, 403/403.
**P6** — correo personal: categorías "redes" (marca/infracciones/
monetización/cambios de política YouTube/TikTok/Instagram/Facebook) y
"escolar". `clasificar()` reordenado: `CLAVES_REDES` se revisa ANTES del
filtro de ruido (mismas plataformas mandan ambas cosas). 7 pruebas, 410/410.
**P7** — bug real: correo personal reavisaba el mismo email para siempre
(Arturo reportó 3 avisos duplicados). Causa: gotcha de IMAP (RFC 3501) —
con la frontera ya al día, "UID N:*" NO regresa vacío, el servidor regresa
el último correo de todos modos. Fix: `_fetch_uids_desde` filtra
`> desde_uid` del lado de acá. Verificado en vivo (antes: reavisaba;
después: "Sin correos nuevos"). 2 pruebas, 412/412 `tests/scripts/` verde.

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
P7: bug real IMAP (reaviso infinito) corregido, 2/2. · P6: correo personal, categorías redes+escolar, 7/7. · F6-3: correo escolar analiza+sugiere, 23/23. · P5: correo
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
