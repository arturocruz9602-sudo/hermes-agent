# Guía: sacar las 2 llaves de YouTube (para AU-1/AU-2 y youtube-analytics)

**03 ago 2026 · confirmado por Arturo: se necesitan LAS DOS (ver `docs/DECISIONES.md`). ~10 min totales.**

## Antes que nada
Ambas se sacan del **mismo proyecto** de Google Cloud — no hace falta crear dos proyectos.
Necesitas iniciar sesión con la cuenta de Google **dueña del canal** de YouTube (`@ArturoRMN1`).

---

## Paso 0 — Crear/elegir el proyecto y activar la API (una sola vez)

1. Entra a **https://console.cloud.google.com/**
2. Arriba a la izquierda, crea un proyecto nuevo (ej. "Hermes") o usa uno existente.
3. Ve a **https://console.cloud.google.com/apis/library/youtube.googleapis.com**
4. Dale **"Habilitar"** (Enable) — activa la YouTube Data API v3 en ese proyecto. Gratis, sin tarjeta.

## Llave 1 — API key pública (datos públicos: métricas de canal, búsquedas)

1. Ve a **https://console.cloud.google.com/apis/credentials**
2. **"+ Crear credenciales" → "Clave de API"**.
3. Se genera al instante — cópiala. (Opcional pero recomendado: click en la llave recién creada →
   "Restringir clave" → limita a "YouTube Data API v3" para que no sirva para otras APIs de Google
   por accidente.)
4. Mándamela y la guardo en `.env` como `YOUTUBE_API_KEY` (mismo candado que `.env` en general: yo no
   puedo escribir ahí directo, tú confirmas o la pegas tú mismo).

## Llave 2 — OAuth (login tuyo → HERMES; datos privados + publicar)

1. En la misma página de credenciales: **"+ Crear credenciales" → "ID de cliente de OAuth"**.
2. Si es la primera vez, te pedirá configurar la **"Pantalla de consentimiento OAuth"** primero:
   tipo **"Externo"**, nombre de la app ("Hermes"), tu correo en soporte/contacto. Como sigue en modo
   "Prueba" (Testing), agrega tu propio correo (`arturocruz9602@gmail.com`) en **"Usuarios de prueba"**
   — así el consentimiento no expira/no pide revisión de Google mientras solo lo uses tú.
3. Tipo de aplicación: **"Aplicación de escritorio"** (Desktop app) — es el tipo correcto para un
   script que corre en tu HP, no un servidor web público. Usa `http://localhost` como retorno, no
   necesitas configurar dominio ni HTTPS.
4. Al crear, descarga el JSON de credenciales (`client_secret_....json`).
5. Este archivo lo recibe **HERMES** (no Claude Code, decisión ya tomada 31 jul) para hacer el
   flujo de login una sola vez — te va a abrir una pantalla de Google pidiéndote iniciar sesión y
   aceptar permisos; ahí generas el token real que usa `TokenYouTube` (`scripts/pipeline_clips.py`).
   Ese token SÍ vence cada cierto tiempo — el código ya avisa solo cuando toca reconectar (nunca falla
   en silencio).

## Scopes que va a pedir el consentimiento (para que no te sorprenda el permiso)
- `youtube.readonly` — leer datos del canal (analytics).
- `youtube.upload` — subir videos (lo necesita `PublicadorYouTube`, y aun así NUNCA sube sin tu
  aprobación explícita — eso ya está en el código, r.59).

## Resumen de dónde queda cada cosa
| Llave | Variable | Quién la usa |
|---|---|---|
| API key pública | `YOUTUBE_API_KEY` | skill `youtube-analytics` (métricas) |
| OAuth (client_secret.json + token) | ruta gestionada por Hermes | `TokenYouTube`/`PublicadorYouTube` (AU-2) |

## Fuentes
- https://console.cloud.google.com/apis/library/youtube.googleapis.com
- https://console.cloud.google.com/apis/credentials
- Costos/cuota verificados 03 ago 2026 (ver conversación con Arturo, sin doc separado): gratis, 10,000
  unidades/día, sin plan de pago existente.
