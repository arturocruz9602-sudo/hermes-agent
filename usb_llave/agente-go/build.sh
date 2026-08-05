#!/bin/bash
# build.sh -- compila el agente Hermes Portable para Linux/Windows/macOS
# (GOOS cross-compile, sin dependencias externas -- solo stdlib + net/http,
# HAS §Arquitectura Hermes Portable). El gateway solo corre en la HP
# (el "cerebro"), así que solo se compila para Linux.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

DIST="dist"
mkdir -p "$DIST"

echo "== agente (Linux + Windows + macOS) =="
GOOS=linux   GOARCH=amd64 go build -o "$DIST/hermes-agente-linux"     ./agente
GOOS=windows GOARCH=amd64 go build -o "$DIST/hermes-agente.exe"       ./agente
GOOS=darwin  GOARCH=amd64 go build -o "$DIST/hermes-agente-macos"     ./agente
GOOS=darwin  GOARCH=arm64 go build -o "$DIST/hermes-agente-macos-arm" ./agente

echo "== gateway (solo Linux, corre en la HP) =="
GOOS=linux GOARCH=amd64 go build -o "$DIST/hermes-gateway-linux" ./gateway

echo ""
echo "listo en $DIST/:"
ls -la "$DIST"
