# Hermes Portable — agente Go (F11-2, USB-llave)

**Corrección de diseño 04 ago 2026 (ver `docs/DECISIONES.md`):** la USB NO es una bóveda cifrada que
levanta Tailscale/SSH — eso era una desviación del diseño aprobado. La función real: conectar Hermes a
**cualquier PC/laptop con cualquier sistema operativo**, con unos cuantos clics, dando órdenes desde
Telegram. Diseño fuente: skill `hermes-portable-usb` (`~/.hermes/skills/hermes-tools/hermes-portable-usb/`).

## Arquitectura

```
agente (USB, en la PC ajena) → ntfy.sh (solo hello/bye, máquina-a-máquina) → gateway (HP, el cerebro)
gateway (HP) → bot de Telegram de dispositivos → Arturo (notificaciones + botones ✅/❌)
Arturo → bot de Telegram → gateway (respuestas, aprobaciones)
```

- **`agente/`** — binario único, sin dependencias externas (solo stdlib + `net/http`), compilado cruzado
  para Linux/Windows/macOS. Manda `hello` al conectar (device_id estable por hardware), escucha comandos
  aprobados por ntfy.sh, los ejecuta, reporta el resultado.
- **`gateway/`** — corre SOLO en la HP (el cerebro; memoria/contexto siempre aquí, nunca en la USB).
  Escucha `hello`/`exec_result` por ntfy.sh, te notifica y pide confirmación por Telegram (botones
  inline ✅/❌ — nunca comandos manuales), aplica la lista negra de comandos peligrosos ANTES de proponer
  nada, resuelve alias de dispositivo (`test: almendra: <comando>`).
- **Regla de seguridad dura:** Tailscale queda limitado a HP + Mac + iPhone. Equipos ajenos (la USB en
  cualquier PC de fuera) hablan SOLO por Telegram/ntfy — sin SSH, sin Tailscale.

## Compilar

```
./build.sh
```

Genera en `dist/`: `hermes-agente-linux`, `hermes-agente.exe`, `hermes-agente-macos`,
`hermes-agente-macos-arm` (M1/M2), y `hermes-gateway-linux` (solo para la HP).

## Correr en desarrollo (sin compilar)

```
cp .env.example .env   # llenar HERMES_DISPOSITIVOS_TOKEN, HERMES_CHAT_ID, HERMES_NTFY_TOPIC
./run.sh gateway        # en la HP
./run.sh agente          # en la máquina que se está conectando
```

## Pruebas

```
go test ./...
```

12/12 — cubren la lista negra de comandos (el candado real antes de proponer algo por Telegram), la
resolución de alias multi-dispositivo, y la generación estable de `device_id`.

## Estado (04 ago 2026)

Hecho: agente+gateway compilados para Linux/Windows/macOS, protocolo `HERMES_MSG::` sobre ntfy.sh,
lista negra de comandos peligrosos, confirmación por botón inline, router multi-dispositivo por alias,
`device_id` estable (hash de hardware, sobrevive reinicios).

Falta: `device_id` de la HP hardcodeado en el gateway (`deviceIDDefaultHP`) en vez de detectarlo
dinámicamente, token cifrado en local (hoy `.env` plano), mensaje `bye`/limpieza al desconectar el
agente, prueba real en ALMENDRA (Windows, sin Tailscale), fases 5-7 del skill.
