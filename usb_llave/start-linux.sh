#!/usr/bin/env bash
# start-linux.sh -- lanzador Linux del USB-llave (HAS §B8, §OT-11 punto 2).
#
# "La llave, no el cerebro": este script NUNCA copia a Hermes a la máquina
# prestada. Solo monta la bóveda cifrada (partición A, VeraCrypt), levanta
# Tailscale, y abre una sesión SSH contra la HP donde Hermes ya vive --
# Hermes nunca sale de casa (HAS §B8).
#
# Flujo (2-3 clics reales, ya sin contar el passphrase):
#   1. Verifica que veracrypt/tailscale/ssh existan en la máquina prestada.
#   2. Monta la bóveda (`$VAULT_FILE`) -- VeraCrypt PIDE el passphrase de
#      forma interactiva; este script JAMAS lo acepta como argumento ni lo
#      lee de una variable de entorno (mismo principio que
#      scripts/bovedar_secretos.py: el único secreto no automatizable).
#   3. Lee `config.env` DE DENTRO de la bóveda ya montada (nunca vive fuera,
#      sin cifrar, en la partición de intercambio) -- ahí está a qué
#      hostname/IP de Tailscale conectar y dónde está la llave SSH dedicada
#      `hermes-portable` (revocable independiente de las 11 API keys, que
#      NUNCA viajan en este USB).
#   4. Levanta Tailscale si hace falta (con el authkey re-generable de la
#      bóveda) y abre la sesión SSH -> `hermes` (CLI) en la HP.
#   5. Al cerrar la sesión SSH, desmonta la bóveda y, si este script fue
#      quien levantó Tailscale, lo vuelve a bajar. Siempre limpia, incluso
#      si algo falló a medio camino (trap EXIT).
#
# Variables de entorno (todas con default sensato; los tests las pisan para
# inyectar binarios falsos sin tocar hardware real -- mismo principio de
# "puerto inyectable" que scripts/reglas_recordatorio.py):
#   USB_ROOT        raíz del USB (default: carpeta que contiene este script)
#   VAULT_FILE       ruta al contenedor VeraCrypt (default: $USB_ROOT/partition-a/hermes-vault.hc)
#   VAULT_MOUNT      punto de montaje (default: ${TMPDIR:-/tmp}/hermes-portable-mount)
#   VERACRYPT_BIN    binario de veracrypt (default: veracrypt)
#   TAILSCALE_BIN    binario de tailscale (default: tailscale)
#   SSH_BIN          binario de ssh (default: ssh)
#
# `config.env` dentro de la bóveda (NO vive en este repo -- se genera cuando
# Arturo arme la bóveda real, punto 1 de OT-11, aún pendiente):
#   HERMES_TS_TARGET       hostname o IP de Tailscale de la HP (ej. la que
#                           reporta hoy `tailscale status`: nunca se hardcodea
#                           aquí porque puede rotar).
#   HERMES_SSH_KEY          ruta relativa DENTRO del mount a la llave privada
#                           `hermes-portable` (ej. "ssh/hermes-portable").
#   HERMES_TS_AUTHKEY_FILE  ruta relativa DENTRO del mount al authkey de
#                           Tailscale re-generable (opcional: si la máquina
#                           prestada ya está en el tailnet, se omite).
#
# Qué es fantasía y se dice de frente (HAS §B8): sin bóveda real armada
# (OT-11 punto 1, pendiente) este script falla claro en el paso 2 -- a
# propósito, mejor un error honesto que un lanzador a medio construir que
# parece funcionar.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USB_ROOT="${USB_ROOT:-$SCRIPT_DIR}"
VAULT_FILE="${VAULT_FILE:-$USB_ROOT/partition-a/hermes-vault.hc}"
VAULT_MOUNT="${VAULT_MOUNT:-${TMPDIR:-/tmp}/hermes-portable-mount}"
VERACRYPT_BIN="${VERACRYPT_BIN:-veracrypt}"
TAILSCALE_BIN="${TAILSCALE_BIN:-tailscale}"
SSH_BIN="${SSH_BIN:-ssh}"

MONTADO=0
TAILSCALE_LEVANTADO_POR_NOSOTROS=0

log() { printf '[usb-llave] %s\n' "$1" >&2; }
err() { printf '[usb-llave] ERROR: %s\n' "$1" >&2; }

cleanup() {
    local rc=$?
    if [ "$TAILSCALE_LEVANTADO_POR_NOSOTROS" = "1" ]; then
        log "bajando tailscale (lo levantamos nosotros)..."
        "$TAILSCALE_BIN" down >/dev/null 2>&1 || err "no se pudo bajar tailscale (revisar a mano)"
    fi
    if [ "$MONTADO" = "1" ]; then
        log "desmontando la bóveda..."
        "$VERACRYPT_BIN" --text --non-interactive --dismount "$VAULT_MOUNT" >/dev/null 2>&1 \
            || err "no se pudo desmontar $VAULT_MOUNT (desmontar a mano antes de sacar el USB)"
    fi
    rmdir "$VAULT_MOUNT" 2>/dev/null || true
    exit "$rc"
}
trap cleanup EXIT

require_bin() {
    if ! command -v "$1" >/dev/null 2>&1; then
        err "'$1' no está instalado en esta máquina -- instálalo antes de seguir."
        exit 1
    fi
}

require_bin "$VERACRYPT_BIN"
require_bin "$TAILSCALE_BIN"
require_bin "$SSH_BIN"

if [ ! -f "$VAULT_FILE" ]; then
    err "no existe la bóveda '$VAULT_FILE'."
    err "OT-11 punto 1 (particionar el USB) todavía no está hecho -- ver docs/ESTADO.md."
    exit 1
fi

mkdir -p "$VAULT_MOUNT"

log "montando la bóveda -- VeraCrypt va a pedir el passphrase ahora:"
if ! "$VERACRYPT_BIN" --text --mount "$VAULT_FILE" "$VAULT_MOUNT" \
        --pim 0 --keyfiles "" --protect-hidden no; then
    err "no se pudo montar la bóveda (¿passphrase incorrecto?)."
    exit 1
fi
MONTADO=1

CONFIG_FILE="$VAULT_MOUNT/config.env"
if [ ! -f "$CONFIG_FILE" ]; then
    err "la bóveda montó pero no tiene '$CONFIG_FILE' -- bóveda incompleta."
    exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

for var in HERMES_TS_TARGET HERMES_SSH_KEY; do
    if [ -z "${!var:-}" ]; then
        err "config.env de la bóveda no define '$var'."
        exit 1
    fi
done

SSH_KEY_PATH="$VAULT_MOUNT/$HERMES_SSH_KEY"
if [ ! -f "$SSH_KEY_PATH" ]; then
    err "config.env apunta a '$HERMES_SSH_KEY' pero ese archivo no existe en la bóveda."
    exit 1
fi
chmod 600 "$SSH_KEY_PATH" 2>/dev/null || true

ESTADO_TS="$("$TAILSCALE_BIN" status --json 2>/dev/null | grep -o '"BackendState":"[A-Za-z]*"' || true)"
if [ "$ESTADO_TS" != '"BackendState":"Running"' ]; then
    if [ -n "${HERMES_TS_AUTHKEY_FILE:-}" ] && [ -f "$VAULT_MOUNT/$HERMES_TS_AUTHKEY_FILE" ]; then
        log "levantando tailscale con el authkey de la bóveda..."
        "$TAILSCALE_BIN" up --authkey="file:$VAULT_MOUNT/$HERMES_TS_AUTHKEY_FILE" \
            --hostname="hermes-portable-$(date +%s)"
        TAILSCALE_LEVANTADO_POR_NOSOTROS=1
    else
        err "tailscale no está corriendo en esta máquina y la bóveda no trae authkey."
        exit 1
    fi
fi

log "abriendo sesión con Hermes en ${HERMES_TS_TARGET}..."
"$SSH_BIN" -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=accept-new \
    "arturo@${HERMES_TS_TARGET}" -- hermes
