# ESTADO — actualizado: 06 ago 2026 (auditoría de todo lo desplegado, a pedido de Arturo)
**Versiones vigentes: HAS v1.6 · PROTOCOLO v1.4**
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 (F6-2 ✅, F6-3 ✅) | F7 🔄 bloques 1+2+3 | F8 🔄 F8-1 ✅ F8-2 ✅ | F9 🔄 pts 1+2 | F10 🔄 recetario listo | F11-1 ✅ | F11-2 🔄 REALINEADO | E14 🔄 falta disparo automático | P3/P5/P6/P7/P8/F6-2/F6-3 ✅ | F12-F14 ⬜ | E10 → v1.7.

## 🔴 Hallazgo de hoy: incidente nocturno por `git reset` a `origin/main` — YA CORREGIDO
Reflog (05 ago 23:59→06 ago 10:01): un merge manual de upstream dejó el
working tree de `main` en el estado puro de `origin/main` (sin código de
Hermes) ~10h de madrugada, mismo directorio de donde corren los timers,
sin ventana de mantenimiento que lo proteja. 4 timers fallaron:
`hermes-memoria-reflexion-nocturna` (02:20, `ModuleNotFoundError
agent.memory_semantic`), `hermes-memoria-index` (03:02, ídem),
`hermes-respaldo-total` (04:14, `restaurar_hermes.sh` no existía),
`hermes-brief-matutino` (06:30 — Arturo se quedó SIN brief hoy). El
merge de las 10:01 (`aa6633941`) restauró el árbol, verificado con
import manual. `fork/arturo/prod` estaba 2 commits atrás (push de
cierre pendiente de la sesión pasada) — **ya sincronizado**
(`git push fork HEAD:arturo/prod` → `da81beb3f..aa6633941`).
Pendiente: los 4 `.service` siguen `failed` (no bloquea el próximo
disparo, corren solos mañana) — intenté catch-up manual y el hook de
seguridad lo bloqueó correctamente (hard-deny reinicio producción, no
es la excepción de `hermes-gateway`). Decidir con Arturo: ¿catch-up con
confirmación explícita, o se deja correr solo? Causa raíz de fondo sin
resolver: merges manuales de upstream sobre el mismo directorio donde
corre cron, sin ventana de mantenimiento que bloquee eso.

## 🔴 Hallazgo de hoy: alerta de presupuesto DeepSeek, 2 noches seguidas
`hermes-deepseek-balance-check` (03:00 hoy y ayer): caída real de saldo
$0.83 USD/noche vs. lo que registró el ledger de litellm (~$0.73 USD) —
diferencia ~$0.09-0.10 USD sobre el umbral ($0.01), posible gasto que no
pasa por el proxy. Saldo real hoy: **$2.77 USD**. El script sí tiene
`alert_telegram()` (`scripts/deepseek_balance_crosscheck.py:82`) — no
confirmé que el mensaje llegó de verdad al chat (L5: sin evidencia
pegada no está verificado). Falta investigar qué llamada no pasa por el
proxy antes de que el circuito de $10 MXN/día se dispare.

## Decisiones pendientes ARTURO
1. Catch-up manual de `hermes-memoria-index`/`hermes-respaldo-total` de
   hoy: ¿lo autorizas explícito ahora, o se deja correr solo mañana?
2. F8-1/F8-2 sin timer propio decidido: cron ya agendado aparte (jobs
   13bea6149ae0/7132f383cb07), esta línea es solo registro.
3. Horario escuela sept-dic (r.61): espera a que la escuela lo publique.
4. F11-2: prueba real en ALMENDRA (Windows, sin Tailscale) — falta equipo a mano.
5. `reboot-required` pendiente en el sistema — no forzado, decide Arturo cuándo.

## 🔄 EN CURSO (arrastrados)
**E14:** motor+gate+1ra fuente 17/17. Falta timer systemd, 2 fuentes, decisión 3.
**F11-2:** falta device_id HP dinámico, token cifrado, bye/limpieza, prueba ALMENDRA.

## ⚠️ Hallazgos sin arreglar (arrastrados)
1. Ruido cosmético en `watchdog.log`: "Tubería rota" al cortar con grep -q.
2. Sin ventana de mantenimiento que proteja los timers de un merge/reset en curso (ver hallazgo de hoy arriba).

## Bloques recientes CERRADOS (detalle completo en `docs/BLOQUES.md`)
F8-2: motor de sugerencias v2 (fijos+negocio), 18/18 · F8-1: motor de
sugerencias de gasto, 20/20 · F11-2 realineado: agente Go al repo,
12/12 · resto: ver archivo.

## No tocar / reglas de equipo
- M1 PRESTADA: reversa antes 6:00. · Correo solo-lectura. · Pruebas masivas
  SOLO Docker QA. · Nada personal a API gratis (r.91), EXCEPTO fotos de
  horario escolar → Gemini Vision (excepción acotada, ver DECISIONES).
- `.env` línea 503 (app password Gmail): NUNCA se toca, no está corrupta.
- **F11-2/USB: SOLO Telegram+ntfy.sh — sin SSH, sin Tailscale a equipos
  ajenos.** Tailscale limitado a HP+Mac+iPhone, tema DISTINTO.
- Watchdog vive FUERA del repo; sus pruebas sí van al repo.
- Flujo normal: local `main` + `git push fork HEAD:arturo/prod` (no hay
  branch local `arturo/prod`) — el riesgo real es dejar `main` reseteado
  a `origin/main` sin remergear rápido (ver hallazgo de hoy).

## Próximos candidatos
Gap $0.09 USD/noche en DeepSeek. Ventana de mantenimiento que bloquee
timers durante merge/reset de git. F11-2 resto. Cerrar E14. F5/F9 resto.

## Al cierre
Esta sesión: auditoría completa a pedido de Arturo — causa raíz de 4
timers rotos anoche encontrada y corregida + `arturo/prod` sincronizado
(2 commits atrás). Sin commit de código; falta decidir catch-up manual.
