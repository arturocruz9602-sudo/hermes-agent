#!/usr/bin/env bash
# ============================================================================
# hermes-arranque.sh  ·  Hook SessionStart de Claude Code para el proyecto Hermes
# ----------------------------------------------------------------------------
# Corre los chequeos DETERMINISTAS del arranque (CLAUDE.md "LO PRIMERO, SIEMPRE"
# puntos 3-8) para que dejen de depender de que Claude se acuerde de teclearlos.
# Su stdout se inyecta como contexto al abrir/reanudar/clear/compactar sesion.
#
# Extiende la reestructura documental del 1 ago 2026 (arranque ligero): NO lee
# archivos ni razona -- solo junta datos verificables y los presenta compactos.
# El juicio (leer MANDATO/ESTADO, elegir tarea, saludar) sigue siendo de Claude.
#
# CONTRATO: pase lo que pase, termina con exit 0. Nunca debe trancar el arranque.
# Tolera ausencia de gsettings/D-Bus, de tailscale, o de cualquier comando.
# ============================================================================

# Nada de set -e: un chequeo que falle no puede tumbar el arranque.
set +e

# Drena el JSON que el harness manda por stdin (source, session_id, cwd...).
# No lo necesitamos, pero hay que consumirlo para no bloquear.
input="$(cat 2>/dev/null)"
source="$(printf '%s' "$input" | grep -o '"source"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"$/\1/')"
[ -z "$source" ] && source="startup"

# Directorio del repo: preferimos la variable del harness; si no, derivamos de
# la ubicacion del script (.claude/hooks/ -> raiz); ultimo recurso, ruta conocida.
if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR/.git" ]; then
  REPO="$CLAUDE_PROJECT_DIR"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
  REPO="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)"
fi
[ -d "$REPO/.git" ] || REPO="/home/arturo/.hermes/hermes-agent"

G() { git -C "$REPO" "$@" 2>/dev/null; }

# --- 3) git: rama, arbol sucio, ultimo commit -------------------------------
rama="$(G rev-parse --abbrev-ref HEAD)"; [ -z "$rama" ] && rama="?"
sucio_n="$(G status --short | grep -c .)"
if [ "${sucio_n:-0}" -eq 0 ]; then arbol="limpio"; else arbol="${sucio_n} sin commitear"; fi
ultimo="$(G log -1 --oneline)"; [ -z "$ultimo" ] && ultimo="(sin commits)"

# --- 2/L11) archivos del sistema nuevo siguen versionados -------------------
l11=""
for f in docs/ESTADO.md docs/BLOQUES.md docs/DECISIONES.md docs/CUESTIONARIO_MAESTRO.md; do
  base="$(basename "$f" .md)"
  if [ -n "$(G ls-files "$f")" ]; then l11="${l11}${base}=si "; else l11="${l11}${base}=NO! "; fi
done

# --- 4) diagnosticos temporales vivos en codigo -----------------------------
td="$(grep -rn --include='*.py' 'TEMP-DIAG' "$REPO" 2>/dev/null | grep -v '/.venv/' | grep -c .)"

# --- 5) salud real: units --user (NO scope de sistema; ahi salen inactive) ---
sg="$(systemctl --user is-active hermes-gateway 2>/dev/null)"; [ -z "$sg" ] && sg="?"
sl="$(systemctl --user is-active litellm 2>/dev/null)"; [ -z "$sl" ] && sl="?"
salud_alerta=""
[ "$sg" = "active" ] && [ "$sl" = "active" ] || salud_alerta="  <-- REVISAR"

# --- 6) reinicio inesperado -------------------------------------------------
up="$(uptime -p 2>/dev/null)"; [ -z "$up" ] && up="$(uptime 2>/dev/null)"
if [ -f /var/run/reboot-required ]; then reboot="SI (pendiente)"; else reboot="no"; fi

# --- 7) tmux: el trabajo real no debe correr fuera de tmux ------------------
if [ -n "${TMUX:-}" ]; then tmux_st="si"; else tmux_st="NO (trabajo real fuera de tmux = riesgo)"; fi

# --- 8) la tapa, por partida doble (logind + GNOME pueden contradecirse) ----
logind="$(grep -E '^\s*HandleLidSwitch=' /etc/systemd/logind.conf 2>/dev/null | tail -1 | cut -d= -f2)"
[ -z "$logind" ] && logind="(default)"
g_ac="$(gsettings get org.gnome.settings-daemon.plugins.power lid-close-ac-action 2>/dev/null | tr -d \"\')"
g_bat="$(gsettings get org.gnome.settings-daemon.plugins.power lid-close-battery-action 2>/dev/null | tr -d \"\')"
[ -z "$g_ac" ] && g_ac="?"; [ -z "$g_bat" ] && g_bat="?"
tapa_alerta=""
if [ "$logind" != "ignore" ] || { [ "$g_ac" != "nothing" ] && [ "$g_ac" != "?" ]; } || { [ "$g_bat" != "nothing" ] && [ "$g_bat" != "?" ]; }; then
  tapa_alerta="  <-- REVISAR (suspende al cerrar)"
fi

# --- gate: ESTADO.md <= 80 lineas -------------------------------------------
estado_n="$(wc -l < "$REPO/docs/ESTADO.md" 2>/dev/null | tr -d ' ')"; [ -z "$estado_n" ] && estado_n="?"
estado_alerta=""; [ "${estado_n:-0}" -gt 80 ] 2>/dev/null && estado_alerta="  <-- PASA DE 80"

# --- temperatura HP (r.103): sin sudo, leyendo /sys/class/thermal -----------
tmax=0
for z in /sys/class/thermal/thermal_zone*/temp; do
  [ -r "$z" ] || continue
  v="$(cat "$z" 2>/dev/null)"; [ -z "$v" ] && continue
  [ "$v" -gt "$tmax" ] 2>/dev/null && tmax="$v"
done
if [ "$tmax" -gt 0 ] 2>/dev/null; then
  tc=$(( tmax / 1000 )); temp_st="${tc}C"
  [ "$tc" -ge 85 ] 2>/dev/null && temp_st="${tc}C  <-- ALTA (umbral 85)"
else
  temp_st="(no legible)"
fi

# ---------------------------------------------------------------------------
cat <<BLOQUE
===== ARRANQUE HERMES · chequeos deterministas (hook, source=${source}) =====
git      : rama ${rama} · ${arbol} · ultimo: ${ultimo}
L11      : ${l11}
TEMP-DIAG: ${td} en *.py
salud    : gateway=${sg} litellm=${sl}${salud_alerta}
sistema  : ${up} · reboot-required: ${reboot}
tmux     : ${tmux_st}
tapa     : logind=${logind} · gnome ac=${g_ac}/bat=${g_bat}${tapa_alerta}
ESTADO   : ${estado_n}/80 lineas${estado_alerta} · temp HP: ${temp_st}
=========================================================================
Recordatorio: esto son datos, no juicio. Falta leer MANDATO+ESTADO, elegir
la tarea (una sola, C17) y saludar proponiendo. Salud en --user (no sistema).
BLOQUE

exit 0
