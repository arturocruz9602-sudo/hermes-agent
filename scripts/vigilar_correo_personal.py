#!/usr/bin/env python3
"""
vigilar_correo_personal.py — Vigila el Gmail PERSONAL de Arturo
(arturocruz9602@gmail.com) y avisa por Telegram solo lo prioritario, con
una sugerencia de que hacer. Mismo patron que vigilar_correo_escuela.py
(bloque AS), adaptado a personal: r.107-108 del CUESTIONARIO_MAESTRO.

Prioritario (r.108): banco, compras, invitaciones a eventos.
Ruido (r.108): "alguien comento", "alguien compartio" y notificaciones
sociales equivalentes.

De donde lee: IMAP directo (imap.gmail.com), con las credenciales que ya
viven en .env (EMAIL_ADDRESS/EMAIL_PASSWORD/EMAIL_IMAP_HOST/_PORT) --
mismas que usa el adaptador de chat por correo (plugins/platforms/email),
pero este script NUNCA escribe: SELECT en modo readonly + FETCH con
BODY.PEEK, asi que jamas marca un correo como leido ni lo toca. Solo
lectura real, no de nombre (F6-1, r.107: "puede ser" borradores algun dia,
hoy nada de eso).

Blindaje "jamas la bandeja historica de 4,223" (bloque F6-1): la primera
corrida NUNCA descarga ni clasifica el historico. Solo pide UIDNEXT
(un numero, sin tocar mensajes) y lo guarda como frontera. De ahi en
adelante solo se leen UIDs nuevos (mayores a la frontera) -- el tamano
del barrido no crece nunca con el tamano del buzon.

USO:
  python3 vigilar_correo_personal.py            -> corrida normal
  python3 vigilar_correo_personal.py --probar N -> clasifica los ultimos
                                                     N correos (default 40)
                                                     y los imprime, sin
                                                     avisar ni tocar estado
"""

import datetime
import imaplib
import json
import os
import re
import ssl
import subprocess
import sys
from email.header import decode_header
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv

HOME = os.path.expanduser("~")
ENV_PATH = os.path.join(HOME, ".hermes/.env")
ESTADO = os.path.join(HOME, ".hermes/state/correo_personal_estado.json")
LOG = os.path.join(HOME, ".hermes/logs/correo_personal.log")
ENVIAR = os.path.join(HOME, ".hermes/scripts/enviar.py")
PYTHON = os.path.join(HOME, ".hermes/hermes-agent/venv/bin/python")

load_dotenv(ENV_PATH)

IMAP_HOST = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("EMAIL_IMAP_PORT", "993"))
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

# Remitentes/dominios que son puro ruido social. Se callan siempre
# (r.108: "alguien comento"/"alguien compartio" y equivalentes).
RUIDO_DOMINIOS = (
    "facebookmail.com", "linkedin.com", "pinterest", "quora.com",
    "twitter.com", "x.com", "instagram.com", "tiktok.com", "threads.net",
    "medium.com", "notification@", "notifications@", "noreply@",
    "no-reply@",
)
RUIDO_FRASES = (
    "comento", "comentaron", "compartio", "compartieron", "le gusto",
    "reacciono", "reaccionaron", "menciono", "mencionaron", "etiqueto",
    "te etiqueto", "nuevo seguidor", "te siguio", "empezo a seguirte",
    "recomendacion para ti", "tal vez conozcas",
)

# Bancos y finanzas -> PRIORITARIO
CLAVES_BANCO = (
    "banco", "bbva", "santander", "banorte", "hsbc", "banamex",
    "citibanamex", "spei", "estado de cuenta", "tarjeta de credito",
    "tarjeta de debito", "movimiento", "cargo realizado", "deposito",
    "transferencia", "saldo", "pago realizado", "nu mexico", "nubank",
)

# Compras/envios -> PRIORITARIO. Frases completas, nunca "envio" a secas:
# "te envio un mensaje" (chat de red social) normaliza a una cadena que
# contiene "envio" como substring de "envió" y disparaba falsos positivos
# (hallado en la prueba real del 03 ago contra la bandeja de Arturo).
CLAVES_COMPRAS = (
    "amazon", "mercadolibre", "mercado libre", "mercado pago",
    "tu pedido", "pedido #", "compra realizada", "confirmacion de compra",
    "confirmacion de tu compra", "factura", "tu factura", "paquete",
    "rastreo", "numero de guia", "tu envio", "estado de tu envio",
    "envio en camino", "pedido enviado", "shein", "temu", "aliexpress",
)

# Invitaciones a eventos -> PRIORITARIO
CLAVES_EVENTOS = (
    "te invito a", "invitacion", "evento", "boletos", "entradas",
    "confirmar asistencia", "rsvp", "cumpleanos",
)

# Redes sociales que le importan a Arturo (r.45/54/55: YouTube/TikTok/
# Instagram/Facebook) -> PRIORITARIO. Agregado 04 ago a peticion de Arturo,
# tras encontrar que "unidad IV_complemento.docx" de un compañero cayo en
# "neutral" -- pidio ademas esta categoria para: comunicacion de marca,
# infracciones/strikes, logros de monetizacion, y cambios de politica.
# OJO: estas mismas plataformas viven en RUIDO_DOMINIOS (facebookmail.com,
# instagram.com, tiktok.com...) porque la mayoria de sus correos SI son
# ruido ("alguien te siguio"). clasificar() revisa CLAVES_REDES ANTES del
# filtro de ruido, para que un aviso real (ej. "tu cuenta fue suspendida")
# no se calle solo por venir del mismo dominio que el ruido.
CLAVES_REDES = (
    # infracciones / strikes / suspensiones
    "infraccion", "violacion de", "viola nuestras", "viola nuestros",
    "normas de la comunidad", "community guidelines", "derechos de autor",
    "copyright strike", "copyright claim", "reclamo de copyright",
    "cuenta suspendida", "cuenta restringida", "contenido eliminado",
    "advertencia de la comunidad", "penalizacion", "shadowban",
    "account suspended", "account restricted", "content removed",
    "strike en tu cuenta", "strike received",
    # monetizacion
    "monetizacion", "monetizar tu", "elegible para monetizacion",
    "programa de socios", "partner program", "ingresos por publicidad",
    "ad revenue", "pago disponible", "umbral de pago", "payout disponible",
    "creator fund", "fondo de creadores", "ya eres monetizable",
    "monetization enabled", "youtube partner",
    # cambios de politica
    "actualizacion de terminos", "terminos de servicio actualizados",
    "nueva politica", "nuevas politicas", "cambios en la politica",
    "cambios en las politicas", "politica de privacidad actualizada",
    "policy update", "updated terms", "terms of service update",
    # comunicacion de marca / colaboracion
    "colaboracion", "propuesta de colaboracion", "patrocinio",
    "auspicio", "brand deal", "sponsored content", "partnership opportunity",
    "oportunidad de colaboracion", "queremos trabajar contigo",
)

# Contenido escolar que llega por el correo PERSONAL, no el institucional
# (compañeros mandando tareas/documentos por Gmail) -> PRIORITARIO.
# Agregado 04 ago: "unidad IV_complemento.docx" de un compañero cayo en
# "neutral" porque r.108 nunca definio "escolar" como categoria del correo
# personal (solo del institucional). Mismas claves que vigilar_correo_
# escuela.py, mas patrones de nombre de archivo escolar.
CLAVES_ESCOLAR = (
    "tarea", "entrega", "examen", "proyecto", "practica", "unidad",
    "complemento", "apuntes", "resumen", "exposicion", "equipo de trabajo",
    "trabajo en equipo", "materia", "profesor", "profesora", "maestro",
    "maestra", "clase de", ".docx", ".pptx", ".xlsx",
)

DOMINIO_PROPIO = "gmail.com"


def log(msg):
    """Deja rastro de exito Y de fallo. Nunca falla en silencio (HAS L6/L14)."""
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ts}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")
    print(linea)


def dec(raw):
    if not raw:
        return ""
    partes = []
    for p, enc in decode_header(raw):
        if isinstance(p, bytes):
            partes.append(p.decode(enc or "utf-8", errors="replace"))
        else:
            partes.append(p)
    return "".join(partes)


def normalizar(texto):
    """Minusculas y sin acentos, para comparar sin sorpresas."""
    t = texto.lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        t = t.replace(a, b)
    return t


def clasificar(remitente, asunto):
    """Devuelve (categoria, motivo). categoria in
    {"banco", "compras", "eventos", "redes", "escolar", "ruido", "neutral"}.
    Reglas locales por r.108, sin modelo -- ningun dato personal sale a una
    API (regla del 30 jul, misma que vigilar_correo_escuela.py).

    CLAVES_REDES se revisa ANTES del filtro de ruido a proposito: TikTok/
    Instagram/Facebook mandan tanto ruido (alguien te siguio) como avisos
    reales (infraccion, monetizacion) desde el MISMO dominio -- si el ruido
    se checara primero, los avisos reales se callarian por error."""
    r = normalizar(remitente)
    a = normalizar(asunto)
    junto = f"{r} {a}"

    for clave in CLAVES_REDES:
        if clave in junto:
            return "redes", f"dice '{clave}'"

    if any(d in r for d in RUIDO_DOMINIOS) or any(f in a for f in RUIDO_FRASES):
        return "ruido", "notificacion social / automatizada"

    for clave in CLAVES_BANCO:
        if clave in junto:
            return "banco", f"dice '{clave}'"
    for clave in CLAVES_COMPRAS:
        if clave in junto:
            return "compras", f"dice '{clave}'"
    for clave in CLAVES_EVENTOS:
        if clave in junto:
            return "eventos", f"dice '{clave}'"
    for clave in CLAVES_ESCOLAR:
        if clave in junto:
            return "escolar", f"dice '{clave}'"

    return "neutral", "sin señales de que sea prioritario"


def sugerir(categoria):
    """La sugerencia de que hacer que pide r.107/108 -- avisar no basta,
    hay que decir que sigue."""
    return {
        "banco": "revisa el movimiento; si no lo reconoces, entra al banco directo (no des clic en el correo)",
        "compras": "confirma que el pedido/envio sea tuyo y sigue el rastreo si aplica",
        "eventos": "decide si asistes -- si quieres que lo agende, dimelo y pregunto antes de tocar el calendario (r.89)",
        "redes": "revisalo -- si es infraccion o cambio de politica, evalua que ajustar; si es una marca, decide si te interesa (yo no respondo por ti)",
        "escolar": "puede ser tarea/material de un compañero -- si trae fecha de entrega, dimelo y lo agrego a seguimiento",
    }.get(categoria, "revisalo cuando tengas tiempo")


def cargar_estado():
    if not os.path.exists(ESTADO):
        return None  # None = primera corrida
    try:
        with open(ESTADO, encoding="utf-8") as f:
            data = json.load(f)
            return int(data["uid_frontera"])
    except Exception as e:
        log(f"⚠️  No pude leer el estado ({e}) — no avanzo la frontera para no "
            f"arriesgar un salto sobre correos nuevos sin avisar")
        return None


def guardar_estado(uid_frontera):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"uid_frontera": uid_frontera,
                   "actualizado": datetime.datetime.now().isoformat()}, f)
    os.replace(tmp, ESTADO)


def avisar(mensaje):
    try:
        r = subprocess.run([PYTHON, ENVIAR, "--mensaje", mensaje],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            log(f"🔴 FALLO al avisar por Telegram (rc={r.returncode}): "
                f"{r.stderr.strip()[:200]}")
            return False
        return True
    except Exception as e:
        log(f"🔴 FALLO al avisar por Telegram: {e}")
        return False


def _parse_headers(raw_bytes):
    """RFC822 header block crudo -> (remitente, asunto, fecha)."""
    msg_text = raw_bytes.decode("utf-8", errors="replace")
    remitente = asunto = fecha_raw = ""
    for linea in msg_text.splitlines():
        low = linea.lower()
        if low.startswith("from:"):
            remitente = dec(linea[5:].strip())
        elif low.startswith("subject:"):
            asunto = dec(linea[8:].strip())
        elif low.startswith("date:"):
            fecha_raw = linea[5:].strip()
    try:
        dt = parsedate_to_datetime(fecha_raw)
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        dt = None
    return remitente, asunto, dt


def _conectar():
    if not (EMAIL_ADDRESS and EMAIL_PASSWORD and IMAP_HOST):
        log("🔴 Faltan credenciales EMAIL_* en .env — no puedo conectar")
        return None
    try:
        ctx = ssl.create_default_context()
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ctx)
        imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        # readonly=True: IMAP nunca marca \Seen aunque se haga FETCH BODY
        # normal; el modo readonly es una segunda cerradura -- si algun
        # FETCH llegara a pedir el cuerpo completo (no lo hacemos hoy),
        # tampoco podria escribir la bandera.
        imap.select("INBOX", readonly=True)
        return imap
    except Exception as e:
        log(f"🔴 FALLO al conectar/logear a {IMAP_HOST}: {e}")
        return None


def _uidnext(imap):
    typ, data = imap.status("INBOX", "(UIDNEXT)")
    if typ != "OK":
        raise RuntimeError(f"STATUS UIDNEXT fallo: {data}")
    m = re.search(rb"UIDNEXT (\d+)", data[0])
    return int(m.group(1))


def _fetch_uids_desde(imap, desde_uid, hasta_uid=None):
    """Trae remitente/asunto/fecha de los UIDs > desde_uid. BODY.PEEK
    para no tocar la bandera \\Seen (solo-lectura real)."""
    rango_hasta = "*" if hasta_uid is None else str(hasta_uid)
    typ, data = imap.uid("SEARCH", None, f"UID {desde_uid + 1}:{rango_hasta}")
    if typ != "OK" or not data or not data[0]:
        return []
    uids = data[0].split()
    correos = []
    for uid in uids:
        typ, msg_data = imap.uid(
            "FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
        )
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        remitente, asunto, fecha = _parse_headers(raw)
        correos.append({"uid": int(uid), "de": remitente, "asunto": asunto, "fecha": fecha})
    return correos


def main():
    argv = sys.argv[1:]
    probar = "--probar" in argv
    n_probar = 40
    if probar:
        idx = argv.index("--probar")
        if idx + 1 < len(argv) and argv[idx + 1].isdigit():
            n_probar = int(argv[idx + 1])

    imap = _conectar()
    if imap is None:
        sys.exit(1)

    try:
        if probar:
            uidnext = _uidnext(imap)
            desde = max(0, uidnext - 1 - n_probar)
            correos = _fetch_uids_desde(imap, desde)
            imp = ruido = neutral = 0
            for c in sorted(correos, key=lambda x: x["fecha"] or datetime.datetime.min):
                cat, motivo = clasificar(c["de"], c["asunto"])
                if cat == "ruido":
                    ruido += 1
                    marca = "   calla "
                elif cat == "neutral":
                    neutral += 1
                    marca = "   calla "
                else:
                    imp += 1
                    marca = f"✅ AVISA[{cat}] "
                f = c["fecha"].strftime("%Y-%m-%d") if c["fecha"] else "??"
                print(f"{marca} {f} | {c['de'][:32]:<32} | {c['asunto'][:44]:<44} | {motivo}")
            print(f"\nTotal revisado: {len(correos)} · avisaria de {imp} · "
                  f"ruido {ruido} · neutral {neutral}")
            return

        uid_frontera = cargar_estado()
        primera = uid_frontera is None

        if primera:
            uidnext = _uidnext(imap)
            guardar_estado(uidnext - 1)
            log(f"✅ Primera corrida: frontera fijada en UID {uidnext - 1} SIN "
                f"leer historico (bandeja actual ~miles de correos, nunca se toca). "
                f"De aqui en adelante solo se clasifica lo nuevo.")
            return

        correos = _fetch_uids_desde(imap, uid_frontera)
        if not correos:
            log("✅ Sin correos nuevos")
            return

        prioritarios = []
        max_uid = uid_frontera
        for c in correos:
            max_uid = max(max_uid, c["uid"])
            cat, motivo = clasificar(c["de"], c["asunto"])
            if cat not in ("ruido", "neutral"):
                prioritarios.append((c, cat, motivo))

        if not prioritarios:
            log(f"✅ {len(correos)} correo(s) nuevo(s), ninguno prioritario")
            guardar_estado(max_uid)
            return

        prioritarios.sort(key=lambda x: x[0]["fecha"] or datetime.datetime.min)
        for c, cat, motivo in prioritarios:
            f = c["fecha"].strftime("%d %b %H:%M") if c["fecha"] else "sin fecha"
            remitente = re.sub(r"\s*<.*?>", "", c["de"]).strip() or c["de"]
            msg = (f"📧 Correo personal — {cat}\n\n"
                   f"De: {remitente}\n"
                   f"Asunto: {c['asunto']}\n"
                   f"Recibido: {f}\n\n"
                   f"Sugerencia: {sugerir(cat)}\n"
                   f"(te aviso porque {motivo})")
            if avisar(msg):
                log(f"✅ Avisado [{cat}]: {c['asunto'][:60]} — {motivo}")
            else:
                log(f"🔴 NO se pudo avisar de: {c['asunto'][:60]}")

        guardar_estado(max_uid)
    finally:
        try:
            imap.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
