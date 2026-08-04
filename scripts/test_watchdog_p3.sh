#!/bin/bash
# test_watchdog_p3.sh — Bloque P3: pruebas de la alarma de cuota del watchdog.
#
# El watchdog vive fuera del repo (~/.hermes/scripts/watchdog.sh). Este arnes
# lo corre en una casa (HOME) de mentiras, con journalctl/curl/systemctl/ping
# reemplazados por stubs, para probar la logica de alerta SIN tocar produccion,
# sin mandar Telegram y sin gastar un peso de cuota.
#
# Caso central (bug del 04 ago 06:54): 429 en los logs de LiteLLM mientras
# DeepSeek —el principal desde el Bloque AN— responde. Eso NO es una caida:
# es la escalera gratuita (respaldo) haciendo su trabajo. No debe alertar.

WATCHDOG="$HOME/.hermes/scripts/watchdog.sh"
PASS=0
FAIL=0

LOG_429='Aug 04 06:54:01 hp litellm[123]: INFO: 127.0.0.1:5000 - "POST /v1/chat/completions HTTP/1.1" 429 Too Many Requests'
LOG_OK='Aug 04 06:54:01 hp litellm[123]: INFO: 127.0.0.1:5000 - "POST /v1/chat/completions HTTP/1.1" 200 OK'

# corre_watchdog <logs_litellm> <http_code_deepseek> <ts_ultima_respuesta_ledger|"">
# Imprime el log que genero la corrida. El sandbox lo crea el LLAMADOR en
# $SANDBOX y sobrevive a la corrida: se inspecciona despues (la salida se
# captura con $(...), que es subshell — una asignacion aqui no saldria viva).
corre_watchdog() {
    local litellm_logs="$1" ds_code="$2" ledger_ts="$3"
    mkdir -p "$SANDBOX/.hermes/logs" "$SANDBOX/.hermes/litellm/cost_ledger" "$SANDBOX/.hermes/context_backups"
    printf '  provider: deepseek\n  base_url: https://api.deepseek.com\n  api_key: ${DEEPSEEK_API_KEY}\n  default: deepseek-v4-flash\n' \
        > "$SANDBOX/.hermes/config.yaml"
    if [ -n "$ledger_ts" ]; then
        printf '{"ts": %s, "model": "chat-fallback3"}\n' "$ledger_ts" \
            > "$SANDBOX/.hermes/litellm/cost_ledger/$(date +%Y-%m).jsonl"
    fi
    [ -n "$ESTADO_PREVIO_PAUSA" ] && touch "$SANDBOX/.hermes/logs/.quota_alert_state"

    (
        export HOME="$SANDBOX"
        export TELEGRAM_BOT_TOKEN="" TELEGRAM_HOME_CHANNEL=""   # alert_telegram queda mudo
        export _LITELLM_LOGS="$litellm_logs" _DS_CODE="$ds_code"

        journalctl() {
            case "$*" in
                *litellm.service*) echo "$_LITELLM_LOGS" ;;
                *)                 echo "" ;;   # gateway y kernel: limpios
            esac
        }
        curl() {
            case "$*" in
                *api.deepseek.com*) echo "$_DS_CODE" ;;
                *)                  return 0 ;;  # Telegram y demas: no-op
            esac
        }
        systemctl() { [[ "$*" == *is-active* ]] && return 0; return 0; }
        ping()      { return 0; }
        ssh()       { return 1; }

        source "$WATCHDOG"
    ) >/dev/null 2>&1
    cat "$SANDBOX/.hermes/logs/watchdog.log"
}

check() {
    local nombre="$1" cond="$2"
    if [ "$cond" = "ok" ]; then
        echo "  ✅ $nombre"; PASS=$((PASS + 1))
    else
        echo "  ❌ $nombre"; FAIL=$((FAIL + 1))
    fi
}

echo "── Caso 1: 429 en LiteLLM + DeepSeek vivo (el bug del 04 ago 06:54) ──"
SANDBOX=$(mktemp -d)
SALIDA=$(corre_watchdog "$LOG_429" "200" "")
check "no alerta: reconoce que el principal responde" \
    "$(echo "$SALIDA" | grep -q 'DeepSeek — el principal — responde' && echo ok)"
check "no marca pausa (.quota_alert_state ausente)" \
    "$([ ! -f "$SANDBOX/.hermes/logs/.quota_alert_state" ] && echo ok)"
check "no declara escalera caida" \
    "$(echo "$SALIDA" | grep -q 'Escalera COMPLETA caida' || echo ok)"
rm -rf "$SANDBOX"

echo "── Caso 2: 429 + DeepSeek caido + sin respuestas recientes → SI alerta ──"
SANDBOX=$(mktemp -d)
SALIDA=$(corre_watchdog "$LOG_429" "000" "")
check "declara escalera COMPLETA caida" \
    "$(echo "$SALIDA" | grep -q 'Escalera COMPLETA caida' && echo ok)"
check "marca pausa (.quota_alert_state creado)" \
    "$([ -f "$SANDBOX/.hermes/logs/.quota_alert_state" ] && echo ok)"
rm -rf "$SANDBOX"

echo "── Caso 3: regresion del fix del 30 jul (ledger con respuesta <240s) ──"
SANDBOX=$(mktemp -d)
SALIDA=$(corre_watchdog "$LOG_429" "000" "$(date +%s)")
check "no alerta: la escalera sigue respondiendo" \
    "$(echo "$SALIDA" | grep -q 'resolviendo en silencio' && echo ok)"
check "no marca pausa" \
    "$([ ! -f "$SANDBOX/.hermes/logs/.quota_alert_state" ] && echo ok)"
rm -rf "$SANDBOX"

echo "── Caso 4: sin 429 y con pausa previa → sale de pausa ──"
ESTADO_PREVIO_PAUSA=1
SANDBOX=$(mktemp -d)
SALIDA=$(corre_watchdog "$LOG_OK" "200" "")
check "limpia el estado de pausa" \
    "$([ ! -f "$SANDBOX/.hermes/logs/.quota_alert_state" ] && echo ok)"
check "dispara reprocesamiento de pendientes" \
    "$([ -f "$SANDBOX/.hermes/logs/.reprocess_pending_trigger" ] && echo ok)"
rm -rf "$SANDBOX"
ESTADO_PREVIO_PAUSA=""

echo "── Caso 5: el texto viejo y falso ya no existe ──"
check "no dice 'NO se usara DeepSeek automaticamente'" \
    "$(grep -q 'NO se usara DeepSeek' "$WATCHDOG" || echo ok)"
check "el aviso nuevo nombra a DeepSeek como el principal" \
    "$(grep -q 'ni DeepSeek (el principal)' "$WATCHDOG" && echo ok)"

echo
echo "Resultado: $PASS pasaron, $FAIL fallaron"
[ "$FAIL" -eq 0 ]
