#!/usr/bin/env bash
# restaurar_hermes.sh -- recuperación total de Hermes (HAS §E13).
#
# Orquesta los 3 respaldos ya construidos (memoria vía Backup API de
# sqlite3, skills + timers/servicios systemd, y la bóveda cifrada de
# credenciales) en UNA sola corrida con UN solo timestamp compartido --
# antes de este script, cada pieza generaba su propio timestamp por
# separado.
#
# Estado real (30 jul 2026, plan nocturno, Bloque 2 paso 4/5):
#   - `respaldar`  -- IMPLEMENTADO Y PROBADO contra datos de producción.
#   - `restaurar`  -- NO IMPLEMENTADO TODAVIA. Reconstruir Hermes desde
#     cero (venv, config, systemd enable, descifrar credenciales) es el
#     siguiente paso, deliberadamente separado -- ver docs/ESTADO.md.
#     Correr `restaurar_hermes.sh restaurar` hoy solo imprime un aviso
#     y sale sin tocar nada, a propósito: mejor un comando honesto que
#     falla claro, que uno a medio construir que parece funcionar.
#
# Uso:
#   scripts/restaurar_hermes.sh respaldar [--dest-dir RUTA] [--con-credenciales]
#   scripts/restaurar_hermes.sh restaurar   # placeholder, ver arriba
#
# --con-credenciales cifra el .env real de HERMES_HOME con age -p de
# forma INTERACTIVA (pide la passphrase en la terminal real -- age no
# acepta passphrase por pipe, verificado en vivo) y lo guarda como la
# copia "más reciente" en BOVEDA_RECUPERACION_DIR, además de meterla en
# esta corrida. Sin esa bandera, el respaldo de credenciales se omite
# por completo si nunca se ha corrido con ella (nightly automático NO
# puede pedir la passphrase de nadie); si ya existe una copia reciente,
# esta corrida SÍ la incluye copiándola tal cual, sin re-cifrar --  el
# .env no cambia seguido, no hace falta pedir la passphrase cada noche.
#
# NUNCA usa `.env` real automáticamente sin `--con-credenciales`
# explícito -- CLAUDE.md: tocar credenciales reales siempre se pregunta.
#
# BOVEDA_RECUPERACION_DIR es DISTINTO de ~/.hermes/boveda/ (ese es
# tools/vault_tool.py, Bloque T -- credenciales que Arturo pide a Hermes
# recordar en conversación, un mecanismo ya existente y separado). No
# se tocan entre sí.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME_DIR="${HERMES_HOME:-$HOME/.hermes}"
PYTHON="${HERMES_PYTHON:-$SCRIPT_DIR/../venv/bin/python3}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

DEST_BASE_DEFAULT="/mnt/seagate/hermes_backups"
BOVEDA_RECUPERACION_DIR="$HERMES_HOME_DIR/boveda_recuperacion"

print_help() {
  cat <<'EOF'
Uso:
  restaurar_hermes.sh respaldar [--dest-dir RUTA] [--con-credenciales]
  restaurar_hermes.sh restaurar

Ver el encabezado de este archivo para el detalle completo.
EOF
}

cmd_respaldar() {
  local dest_base="$DEST_BASE_DEFAULT"
  local con_credenciales=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dest-dir)
        dest_base="$2"
        shift 2
        ;;
      --con-credenciales)
        con_credenciales=1
        shift
        ;;
      -h|--help)
        print_help
        exit 0
        ;;
      *)
        echo "opción desconocida: $1" >&2
        print_help >&2
        exit 2
        ;;
    esac
  done

  local stamp
  stamp="$(date +%Y%m%d_%H%M%S)"
  local dest="$dest_base/$stamp"
  mkdir -p "$dest"

  echo "=== restaurar_hermes.sh respaldar -- $dest ==="
  local resultado=0

  echo "--- 1/3 memoria ---"
  if ! "$PYTHON" "$SCRIPT_DIR/respaldar_memoria.py" --dest-dir "$dest" --no-timestamp; then
    resultado=1
  fi

  echo "--- 2/3 skills + systemd ---"
  if ! "$PYTHON" "$SCRIPT_DIR/respaldar_skills_y_sistema.py" --dest-dir "$dest" --no-timestamp; then
    resultado=1
  fi

  echo "--- 3/3 credenciales ---"
  local env_real="$HERMES_HOME_DIR/.env"
  local env_cifrado_destino="$dest/env.age"
  if [[ "$con_credenciales" -eq 1 ]]; then
    if [[ ! -f "$env_real" ]]; then
      echo "[FAIL] $env_real no existe, no hay nada que cifrar"
      resultado=1
    else
      mkdir -p "$BOVEDA_RECUPERACION_DIR"
      echo "Vas a cifrar $env_real -- age te va a pedir la passphrase dos veces (escribir + confirmar)."
      if "$PYTHON" "$SCRIPT_DIR/bovedar_secretos.py" cifrar "$env_real" --dest "$BOVEDA_RECUPERACION_DIR/env.age"; then
        cp "$BOVEDA_RECUPERACION_DIR/env.age" "$env_cifrado_destino"
        echo "[OK] credenciales: $env_real -> $env_cifrado_destino (y guardado como la copia más reciente en $BOVEDA_RECUPERACION_DIR)"
      else
        echo "[FAIL] cifrado de credenciales falló"
        resultado=1
      fi
    fi
  elif [[ -f "$BOVEDA_RECUPERACION_DIR/env.age" ]]; then
    cp "$BOVEDA_RECUPERACION_DIR/env.age" "$env_cifrado_destino"
    echo "[OK] credenciales: copiada la más reciente ya cifrada ($BOVEDA_RECUPERACION_DIR/env.age) -- sin re-pedir passphrase"
  else
    echo "[SKIP] credenciales: no hay ninguna copia cifrada todavía -- corre con --con-credenciales una vez, con Arturo presente, para crear la primera"
  fi

  echo ""
  if [[ "$resultado" -eq 0 ]]; then
    echo "=== RESPALDO COMPLETO: $dest ==="
  else
    echo "=== RESPALDO CON PROBLEMAS: $dest ==="
  fi
  return "$resultado"
}

cmd_restaurar() {
  cat <<'EOF'
[SIN IMPLEMENTAR] restaurar_hermes.sh restaurar todavía no existe.

Lo que SÍ está listo y probado hoy (Bloque 2, HAS §E13):
  - respaldo real de memoria (state.db + memoria_semantica.db)
  - respaldo real de skills + unidades systemd
  - mecanismo de bóveda cifrada para .env (age -p)

Lo que falta antes de que "restaurar" sea seguro de correr:
  - reconstrucción de venv + dependencias desde el fork de GitHub
  - restaurar las 3 piezas de arriba a sus rutas reales
  - descifrar la bóveda de credenciales (pide la passphrase de Arturo)
  - systemctl --user daemon-reload + enable --now de cada unidad
  - la primera prueba real, obligatoria, en una máquina/usuario limpio
    -- NUNCA sobre este mismo equipo en producción (HAS §E13-b)

Ver docs/ESTADO.md (Bloque 2) para el plan completo, paso por paso.
EOF
  return 1
}

if [[ $# -eq 0 ]]; then
  print_help
  exit 2
fi

case "$1" in
  respaldar)
    shift
    cmd_respaldar "$@"
    ;;
  restaurar)
    shift
    cmd_restaurar "$@"
    ;;
  -h|--help)
    print_help
    ;;
  *)
    echo "subcomando desconocido: $1" >&2
    print_help >&2
    exit 2
    ;;
esac
