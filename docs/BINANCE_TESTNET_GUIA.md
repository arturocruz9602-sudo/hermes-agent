# Guía: sacar las llaves de Binance Spot Testnet (para el bloque AT)

**03 ago 2026 · investigado con fuentes oficiales vigentes (testnet.binance.vision, developers.binance.com,
GitHub binance/binance-spot-api-docs) por orden de Arturo. 5 minutos, lo hace Arturo.**

## Qué es (y qué NO es)

El Spot Testnet es un entorno de prueba **completamente separado** de tu cuenta real de Binance. Fondos
virtuales, imposibles de retirar o transferir a una cuenta real. **Las llaves del testnet NO sirven para
la cuenta real, y las llaves de la cuenta real NO sirven aquí** — son sistemas de credenciales distintos.

## Procedimiento paso a paso

1. Entra a **https://testnet.binance.vision/**
2. Inicia sesión con **"Log In with GitHub"** — el testnet usa OAuth de GitHub, NO tu usuario/contraseña
   de Binance. Necesitas una cuenta de GitHub (si Arturo no tiene una, crearla es gratis y toma 2 minutos).
3. Una vez dentro, la plataforma **genera la API Key automáticamente** al autenticarte — no hay que llenar
   un formulario largo, es prácticamamente automático tras el login.
4. Al registrarte, la cuenta de testnet **recibe saldo virtual automático** en varios activos (BTC, ETH,
   USDT, etc. — exactamente los que la lista blanca de AT ya usa).
5. Copia **API Key y Secret Key** y guárdalos — Binance advierte que ambas son sensibles: **nunca las
   compartas**. Van a `~/.hermes/.env` como `BINANCE_TESTNET_API_KEY` y `BINANCE_TESTNET_API_SECRET`
   (nombres que ya espera `scripts/trading_entrenador.py`, cliente `MercadoBinanceTestnet`).
6. Opcional pero recomendado: al crear la key puedes restringir sus permisos (`TRADE` vs `USER_DATA` por
   separado) — para el laboratorio de AT basta con lectura de mercado + trade, no hace falta retiro (los
   retiros no existen en testnet de todas formas).

## Endpoints que usa el código (ya apuntan aquí, no hay que tocarlos)
| Tipo | URL testnet |
|---|---|
| REST API | `https://testnet.binance.vision/api` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/stream` |

## Detalles que importan para el bloque AT
- **El testnet se resetea ~1 vez al mes** (vuelve a blanco) — pero **las API keys sobreviven el reset**
  (así es desde ago 2020, según la doc oficial), no hay que regenerarlas cada mes.
- Solo endpoints `/api` (no `/sapi`) — el trading spot normal que usa AT no los necesita.
- Rate limits y filtros son "generalmente los mismos" que en producción — el entrenamiento en testnet es
  representativo de cómo se comportaría en real.
- Si algo raro pasa con la cuenta (actividad no reconocida): revocar las llaves de inmediato y contactar
  soporte de Binance — esto es sobre la llave del testnet, sin riesgo de dinero real de por medio.

## Fuentes (verificadas 03 ago 2026)
- https://testnet.binance.vision/
- https://developers.binance.com/docs/binance-spot-api-docs/testnet/general-info
- https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/testnet/rest-api.md
