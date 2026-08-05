#!/bin/bash
# run.sh -- corre el agente o el gateway en modo desarrollo (go run, sin
# compilar). Para producción usa build.sh y copia el binario correspondiente.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ No encontré $ENV_FILE"
    echo "   Crea el archivo .env con:"
    echo "     HERMES_DISPOSITIVOS_TOKEN=<token del bot de Telegram de dispositivos>"
    echo "     HERMES_CHAT_ID=<tu chat_id>"
    echo "     HERMES_NTFY_TOPIC=<tema privado de ntfy.sh, dificil de adivinar>"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [ -z "$HERMES_NTFY_TOPIC" ]; then
    echo "❌ HERMES_NTFY_TOPIC está vacío. Revisa tu .env"
    exit 1
fi

case "$1" in
    gateway)
        if [ -z "$HERMES_DISPOSITIVOS_TOKEN" ] || [ -z "$HERMES_CHAT_ID" ]; then
            echo "❌ El gateway necesita HERMES_DISPOSITIVOS_TOKEN y HERMES_CHAT_ID en .env"
            exit 1
        fi
        echo "🚀 Corriendo gateway (cerebro, solo en la HP)..."
        cd "$DIR/gateway" && go run .
        ;;
    agente)
        echo "🚀 Corriendo agente (vehículo portátil)..."
        cd "$DIR/agente" && go run .
        ;;
    *)
        echo "Uso: ./run.sh [gateway|agente]"
        exit 1
        ;;
esac
