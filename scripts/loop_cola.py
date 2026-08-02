#!/usr/bin/env python3
"""loop_cola.py -- La cola COMPLETA del proyecto que el loop autónomo va a trabajar.

NO inventa alcance. Cada bloque sale de los documentos que Arturo ya dejó
(01 ago 2026) y se resuelve, ante cualquier duda, con el CUESTIONARIO_MAESTRO:
  - docs/ESTADO.md          -> OBJETIVO ACTUAL y COLA DE AGOSTO (lo en vuelo)
  - docs/BLOQUES.md         -> bloques abiertos (AS, AT, AU...)
  - docs/HAS.md             -> Plan por Fases 0-11 y Órdenes de Trabajo (OT-N)
  - docs/DECISIONES.md      -> lo ya cerrado que acota cada bloque
  - docs/CUESTIONARIO_MAESTRO.md -> la voz de Arturo (r.NN), árbitro de dudas
  - docs/LIBRETA_SEED.md    -> datos de vida que alimentan finanzas/rieles

Estado del proyecto (HAS): F0-F4 cerradas; de la Fase 5 en adelante es lo que
falta. El loop recorre esta cola de arriba hacia abajo, respetando `depende_de`,
clasifica cada bloque con Haiku y lo corre con el modelo que le toca.

Orden: r.97 (dinero -> YouTube/redes -> Hermes completo), pero primero se cierra
lo que ya está a medias (AS) y la base que muchos bloques necesitan (Fase 5).

Campos:
  id           -- letra/código de bloque
  titulo       -- una línea (lo que se ve en la terminal)
  descripcion  -- suficiente para clasificar y para arrancar el bloque
  has          -- ancla en el HAS (Fase / OT / sección)
  cuestionario -- respuestas r.NN que lo gobiernan (o [] si es puro HAS)
  entorno      -- "docker_qa" (toca datos/tráfico, r.119) | "repo" (solo código)
  depende_de   -- ids que deben cerrarse antes (dependencias duras)
  estado       -- "pendiente" | "en_curso" | "hecho" (lo actualiza el loop)
"""

COLA = [
    # ---- En vuelo: cerrar AS (brief ya desplegado; faltan estas 2) ----------
    {
        "id": "AS-2",
        "titulo": "Cierre nocturno del día en AUDIO",
        "descripcion": (
            "cierre_del_dia.py (22:45) hoy empuja la pregunta de cierre en TEXTO. "
            "Falta el resumen del día en AUDIO a la hora de dormir (r.90). Reusar la "
            "síntesis de voz que Hermes ya tiene; no crear un TTS nuevo. Probar en el "
            "laboratorio con la cuenta QA, nunca en el Telegram real."
        ),
        "guia": (
            "MAPA DE REUSO (verificado 02 ago por Hermes; NO re-explores, todo esto ya existe):\n"
            "1. TTS: tools/tts_tool.py, funcion text_to_speech_tool(text, output_path=None). "
            "Lee el provider de ~/.hermes/config.yaml (seccion tts:). En Telegram genera .ogg "
            "(Opus, nota de voz) solo. Usala como modulo (from tools.tts_tool import "
            "text_to_speech_tool); NO crees un TTS nuevo.\n"
            "2. Envio: ~/.hermes/scripts/enviar.py tiene enviar_mensaje(texto) y "
            "enviar_archivo(path, caption). OJO: detectar_tipo() NO reconoce .ogg ni .mp3 -> "
            "caen en sendDocument (archivo generico, NO nota de voz). Para nota de voz nativa "
            "hace falta sendVoice (solo .ogg/Opus). Decision tuya: extender detectar_tipo para "
            ".ogg->sendVoice, o enviar directo con requests a "
            "https://api.telegram.org/bot<TOKEN>/sendVoice. Token y chat viven en ~/.hermes/.env "
            "(TELEGRAM_BOT_TOKEN, TELEGRAM_HOME_CHANNEL).\n"
            "3. Referencia: tests/gateway/test_telegram_audio_vs_voice.py confirma .ogg = nota "
            "de voz (entra a STT), .mp3 = archivo de audio (no STT). Para el cierre del dia "
            "queremos NOTA DE VOZ -> .ogg.\n"
            "4. Punto de integracion natural: scripts/cierre_del_dia.py ya maneja la hora "
            "(22:45 por defecto), el dedupe diario (~/.hermes/state/cierre_del_dia.json) y el "
            "envio via ~/.hermes/scripts/enviar.py. Extiendelo (o crea un hermano) para que "
            "genere el audio y lo mande.\n"
            "5. r.90 (hora del cierre) sigue PENDIENTE en el cuestionario: respeta 22:45 como "
            "default configurable y deja anotado en ESTADO.md que la hora final la confirma "
            "Arturo.\n"
            "6. Prueba en entorno docker_qa con la cuenta QA de Telegram, NUNCA el chat real. "
            "Evidencia minima: .ogg generado + respuesta 200 de sendVoice.\n"
            "7. Entregable: flujo cierre-en-audio funcionando en QA + commit WIP aun si es "
            "parcial."
        ),
        "has": "Fase 9 (TTS interino Piper/Gemini)", "cuestionario": ["r.90"],
        "entorno": "docker_qa", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "AS-3",
        "titulo": "Verificar voz→libreta punta a punta",
        "descripcion": (
            "Comprobar que una nota de voz real entra por STT, se transcribe, y el "
            "Hermes vivo EXTRAE los datos a la libreta (libreta.db, clase Libreta). "
            "Verificación de un flujo existente con una nota de voz de prueba (QA). "
            "Reportar cada eslabón con evidencia."
        ),
        "has": "Fase 1 (Whisper→gateway)", "cuestionario": ["r.90"],
        "entorno": "docker_qa", "depende_de": [], "estado": "pendiente",
    },

    # ---- Fase 5: tablero + cola garantizada (base de casi todo lo demás) -----
    {
        "id": "F5-1",
        "titulo": "Tablero único en Notion",
        "descripcion": (
            "Notion como el ÚNICO lugar donde Arturo ve todo (agenda, dinero, "
            "escuela, tareas). Sync por timer; Notion es espejo, Obsidian es la "
            "fuente de verdad (B7). La llave de Notion ya está autorizada para uso "
            "libre; su Notion está vacío, Hermes crea la estructura."
        ),
        "has": "Fase 5 / OT-5", "cuestionario": [],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "F5-2",
        "titulo": "Cola de tareas v2 con garantía encolada→resuelta→notificada",
        "descripcion": (
            "Cola con garantía dura: toda tarea encolada se resuelve y se notifica, "
            "sin excepción (E5). Todo mecanismo loggea éxito Y fallo (el silencio no "
            "es estado válido de fallo). Es la espina dorsal de la proactividad."
        ),
        "has": "Fase 5 / OT-5 / E5", "cuestionario": [],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },

    # ---- Dinero primero (r.97 #1): Trading testnet ---------------------------
    {
        "id": "AT",
        "titulo": "Trading testnet news-driven (entrenamiento)",
        "descripcion": (
            "Conectar trading_entrenador.py a testnet de Binance (verificada sin "
            "fondos). Capital simulado hasta 5,000 MXN, ciclos SEMANALES. Estrategia: "
            "cruzar caída de precio con señales de noticias/web (buy-the-dip informado "
            "por sentimiento); INVESTIGAR en la web las mejores estrategias primero. "
            "Freno duro -3% diario (confirmado). Meta 2,000/sem = objetivo de "
            "ENTRENAMIENTO, no promesa: reportar números reales, nunca prometer. "
            "Dinero real atado a B4 (2 meses de papel) y a propone-y-apruebas."
        ),
        "has": "Fase 10 / OT-10 / B4", "cuestionario": ["r.36-43", "r.91"],
        "entorno": "docker_qa", "depende_de": ["F5-2"], "estado": "pendiente",
    },

    # ---- YouTube/redes (r.97 #2): motor de guiones + clips + video -----------
    {
        "id": "AU-1",
        "titulo": "Motor de guiones desde Obsidian",
        "descripcion": (
            "Desde las notas de Obsidian, armar guion con gancho / cierre / "
            "retención según el estilo que Arturo ya describió (r.49-50 capturado). "
            "La edición creativa autónoma NO se promete; aprende del proceso real."
        ),
        "has": "Fase 8 / OT-8", "cuestionario": ["r.45", "r.46", "r.47"],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "AU-2",
        "titulo": "Pipeline de clips ≤2 min + horarios + OAuth YouTube",
        "descripcion": (
            "Programar TODOS los clips de ≤2 min en los mejores horarios. OAuth de "
            "YouTube conectado a HERMES (no a Claude Code); avisar si el token vence, "
            "nunca fallar en silencio. Publicar NUNCA es automático: Hermes prepara, "
            "Arturo da el 'sí, súbelo'. Requiere de Arturo el OAuth (5 min)."
        ),
        "has": "Fase 8 / OT-8 / OT-11", "cuestionario": ["r.48", "r.59"],
        "entorno": "repo", "depende_de": ["AU-1"], "estado": "pendiente",
    },
    {
        "id": "AU-3",
        "titulo": "Corte de silencios + edición en DaVinci por SSH a la M1",
        "descripcion": (
            "Corte de silencios que no destruye habla, con verificación automática "
            "(E6). Edición en la línea de tiempo de DaVinci vía SSH a la M1. La M1 es "
            "PRESTADA (r.102): toda config nocturna se aplica, se usa y se REVIERTE "
            "antes de las 6:00, verificada revertida. Render automático sí."
        ),
        "has": "Fase 8 / OT-8 / E6", "cuestionario": ["r.102"],
        "entorno": "repo", "depende_de": ["AU-2"], "estado": "pendiente",
    },

    # ---- Hermes completo (r.97 #3): escuela, correo, archivo, finanzas -------
    {
        "id": "F6-1",
        "titulo": "Correo: analizar → avisar prioritarios → sugerir → (futuro) borrador",
        "descripcion": (
            "Adaptador de correo solo-lectura (blindado: EMAIL_ALLOWED_USERS, jamás la "
            "bandeja histórica de 4,223). Analizar → avisar prioritarios (banco, "
            "compras, eventos, TODO lo escolar con entrega) → sugerir qué hacer → "
            "(futuro F6) BORRADOR con ejemplo + autorización explícita por correo, "
            "jamás envío automático. Ruido: 'alguien comentó/compartió'."
        ),
        "has": "Fase 6 / OT-6", "cuestionario": ["r.62-64", "r.67", "r.107-108"],
        "entorno": "repo", "depende_de": ["F5-1"], "estado": "pendiente",
    },
    {
        "id": "F6-2",
        "titulo": "Tutor académico: horario por foto, pizarrón por materia, repaso proactivo",
        "descripcion": (
            "Horario por foto, un 'pizarrón' por materia, repaso proactivo antes del "
            "nuevo cuatrimestre. Google Classroom CANCELADO (los avisos llegan por "
            "correo, DECISIONES 31 jul) → el frente escuela se cubre analizando correo."
        ),
        "has": "Fase 6 / OT-6", "cuestionario": [],
        "entorno": "repo", "depende_de": ["F5-1", "F6-1"], "estado": "pendiente",
    },
    {
        "id": "F7-1",
        "titulo": "Archivo permanente: caché efímero vs biblioteca + tickets con evidencia",
        "descripcion": (
            "Clasificador de entrada decide caché-vs-biblioteca (nunca el tiempo; "
            "E1). Árbol de biblioteca permanente (E2). Tickets/gastos con evidencia. "
            "Fotos familiares a la HP. Nada permanente se borra por cron."
        ),
        "has": "Fase 7 / OT-7 / E1 / E2", "cuestionario": [],
        "entorno": "repo", "depende_de": ["F5-1"], "estado": "pendiente",
    },
    {
        "id": "F7-2",
        "titulo": "Ingresos: venta de refrescos + detectar patrón real",
        "descripcion": (
            "Fuente de ingreso nueva (r.16): caja 328 MXN/24 pzas, venta 20 MXN/pza "
            "(Coca-Cola y Yoli), patrón desconocido. Tabla `ingresos` la registra "
            "por separado; Hermes detecta el patrón y reporta cuánto deja realmente."
        ),
        "has": "Fase 7 / E10", "cuestionario": ["r.16"],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "F7-3",
        "titulo": "Reporte SEMANAL de rieles financieros",
        "descripcion": (
            "Reporte semanal (domingo AM, r.18) de los rieles de E10 desde libreta.db "
            "(fuente viva, v4): meta capital $100k/31-dic-2027 (piso $90k), depósito "
            "objetivo 3,500/mes provisional, ingresos (refrescos), gastos. Números "
            "reales, sin promesas."
        ),
        "has": "Fase 7 / E10", "cuestionario": ["r.18", "r.28-31", "r.35"],
        "entorno": "repo", "depende_de": ["F7-2"], "estado": "pendiente",
    },

    # ---- Proactividad (necesita memoria+cola+horario) -----------------------
    {
        "id": "F9",
        "titulo": "Proactividad: reglas explícitas + detección espontánea '¿la anoto?'",
        "descripcion": (
            "Reglas explícitas + detección de patrones repetidos 3+ veces que Hermes "
            "PROPONE, nunca adopta solo (B9). Captura espontánea en producción: "
            "siempre preguntar '¿lo agendo?' antes de crear nada (r.89). Periodo de "
            "entrenamiento con '¿la anoto?'."
        ),
        "has": "Fase 9 / OT-9 / B9", "cuestionario": ["r.89"],
        "entorno": "repo", "depende_de": ["F5-2", "F6-2"], "estado": "pendiente",
    },

    # ---- Voz y portabilidad (horizonte Mac Mini; interinos gratis ahora) -----
    {
        "id": "F11-1",
        "titulo": "Voz local interina (Piper es_MX)",
        "descripcion": (
            "Voz local funcional gratis mientras llega la Mac Mini: Piper voz es_MX "
            "en la HP con CPU (B5), para alarmas y avisos hablados. La voz cálida de "
            "calidad sigue siendo Gemini Zephyr mientras sea gratis. Gemini Live "
            "DESCARTADO (r.99): alertas por Telegram que vibran como llamada."
        ),
        "has": "Fase 11 / OT-11 / B5", "cuestionario": ["r.99"],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "F11-2",
        "titulo": "USB-llave portable (la llave, no el cerebro)",
        "descripcion": (
            "USB portable como llave de acceso/identidad, no como cerebro de Hermes "
            "(B8). Adelantable. Depende de Fase 2+4 estables (ya lo están)."
        ),
        "has": "Fase 11 / OT-11 / B8", "cuestionario": [],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },

    # ---- Transversales permanentes ------------------------------------------
    {
        "id": "P2",
        "titulo": "Presupuesto de contexto como regresión del arnés",
        "descripcion": (
            "Techo de tokens de prompt por tipo de llamada (base 30 jul: 19.1k/vuelta), "
            "medido con ≥3 muestras en cada corrida del laboratorio; exceder = suite en "
            "rojo, mismo trato que un bug funcional. La eficiencia deja de ser opcional."
        ),
        "has": "E8 / arnés", "cuestionario": [],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "F10-rec",
        "titulo": "Recetario de soluciones (docs/recetario/)",
        "descripcion": (
            "Biblioteca de soluciones que Claude alimenta al cerrar (obligación de "
            "cierre) y Hermes cuando resuelve algo nuevo, consultada por Hermes ANTES "
            "de razonar un problema desde cero (F10)."
        ),
        "has": "F10 / Recetario", "cuestionario": [],
        "entorno": "repo", "depende_de": [], "estado": "pendiente",
    },
    {
        "id": "E14",
        "titulo": "Ventana de mantenimiento nocturna (2:00–5:00)",
        "descripcion": (
            "Ventana nocturna donde Hermes acumula y ejecuta mantenimiento con "
            "evidencia: bugs con logs, skills stale, propuestas del barrido semanal "
            "(E14). Con gate térmico de la HP (r.103): pausa si sube de 85°C."
        ),
        "has": "E14", "cuestionario": ["r.103"],
        "entorno": "repo", "depende_de": ["F5-2"], "estado": "pendiente",
    },
]
