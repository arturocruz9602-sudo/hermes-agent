#!/usr/bin/env python3
"""
vigilar_correo_escuela.py — Vigila el buzon institucional de Arturo y le avisa
por Telegram SOLO cuando llega algo que importa (opcion B, elegida por el
31 jul 2026).

De donde lee: el buzon que Thunderbird mantiene sincronizado en disco
(cuenta 5725111428@utrng.edu.mx). NO se conecta a ninguna API: la
clasificacion es 100% local, por reglas. Esto es deliberado -- regla de
Arturo del 30 jul: ningun dato personal suyo sale a una API gratuita.

Solo lectura: nunca responde, borra ni mueve un correo.

USO:
  python3 vigilar_correo_escuela.py            → corrida normal
  python3 vigilar_correo_escuela.py --probar   → clasifica todo el historico
                                                 y lo imprime, sin avisar ni
                                                 tocar el estado
"""

import datetime
import email.utils
import json
import mailbox
import os
import re
import subprocess
import sys
from email.header import decode_header

HOME = os.path.expanduser("~")
MBOX = os.path.join(
    HOME,
    "snap/thunderbird/common/.thunderbird/afaz2mse.default",
    "ImapMail/imap.gmail.com/INBOX",
)
ESTADO = os.path.join(HOME, ".hermes/state/correo_escuela_vistos.json")
LOG = os.path.join(HOME, ".hermes/logs/correo_escuela.log")
ENVIAR = os.path.join(HOME, ".hermes/scripts/enviar.py")
PYTHON = os.path.join(HOME, ".hermes/hermes-agent/venv/bin/python")

# Salud del sincronizado (hallazgo 04 ago: Thunderbird murio 3 dias en
# silencio -- "sin novedades" mentia por omision, nunca vio nada nuevo de
# verdad). Nunca reportar "todo bien" sin poder confirmarlo (HAS regla 3).
SALUD = os.path.join(HOME, ".hermes/state/correo_escuela_salud.json")
UMBRAL_STALE_HORAS = 4
REALERTA_HORAS = 4

# Arturo (04 ago, tras la primera alerta real): no quiere avisos de salud del
# vigilante por Telegram -- solo quiere que le avisen de CORREOS reales. El
# hallazgo que motivó esto (Thunderbird 3 días caído en silencio) sigue
# detectándose y quedando en el log para diagnóstico; solo se apagó el canal
# de Telegram. Criterio para volver a prenderlo: si alguna vez el vigilante
# se queda ciego de verdad varios días de nuevo sin que Arturo lo note antes
# que Hermes, vale la pena reabrir esta decisión con esa evidencia.
AVISAR_FRESCURA_POR_TELEGRAM = False

# Remitentes que son publicidad pura. Se callan siempre.
RUIDO = (
    "canva.com",
    "medium.com",
    "pinterest",
    "linkedin",
    "indeed.com",
    "notification@service",
    "noreply@redditmail",
    "quora.com",
    "facebookmail",
    "twitter.com",
    "info@educaplay.com",
)

# Palabras que marcan un correo como importante. Sin acentos: el texto se
# normaliza antes de comparar.
CLAVES = (
    "tarea", "entrega", "examen", "calificacion", "calificaciones",
    "inscripcion", "reinscripcion", "beca", "tramite", "titulacion",
    "servicio social", "estadia", "estadias", "kardex", "colegiatura",
    "constancia", "comunicado", "convocatoria", "aviso", "urgente",
    "clase", "clases", "horario", "evaluacion", "proyecto", "practica",
    "acta", "credencial", "pago", "adeudo", "documentacion", "titulo",
    "certificado", "grupo", "materia", "profesor", "docente", "director",
    "coordinacion", "escolares", "vencimiento", "fecha limite", "recordatorio",
)

DOMINIO_ESCUELA = "utrng.edu.mx"

# ── análisis + sugerencia (r.62-64): no basta avisar, hay que decir qué es
# y preguntar qué hacer -- nunca asumir ni actuar solo (r.64, r.89).
CATEGORIAS_ORDEN = (
    ("examen", ("examen", "evaluacion", "quiz")),
    ("entrega", ("entrega", "entregar", "fecha limite", "vencimiento")),
    ("tarea", ("tarea", "actividad", "proyecto", "practica")),
    ("aviso", ("aviso", "comunicado", "convocatoria", "urgente", "recordatorio",
               "inscripcion", "reinscripcion", "beca", "colegiatura", "kardex",
               "constancia", "certificado", "credencial", "pago", "adeudo",
               "documentacion", "titulo", "titulacion", "servicio social",
               "estadia", "tramite")),
)

ARTICULO_CATEGORIA = {
    "examen": "un examen",
    "entrega": "una entrega",
    "tarea": "una tarea",
    "aviso": "un aviso",
    "correo": "un correo importante",
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}

# Classroom manda la fecha de entrega abreviada ("Fecha de entrega: 13 dic").
MESES_ABR = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}

# Seguimiento r.64: aviso ANTES de la hora límite y aviso DESPUÉS
# preguntando si ya se subió -- nunca asumir que se hizo.
SEGUIMIENTOS = os.path.join(HOME, ".hermes/state/correo_escuela_seguimientos.json")
MARGEN_ANTES_MIN = 60


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
    """Devuelve (es_importante, motivo). Reglas locales, sin modelo."""
    r = normalizar(remitente)
    a = normalizar(asunto)

    # Una persona real de la escuela siempre importa, diga lo que diga.
    if DOMINIO_ESCUELA in r:
        return True, "viene de la escuela"

    if any(x in r for x in RUIDO):
        return False, "publicidad"

    for clave in CLAVES:
        if clave in a:
            return True, f"dice '{clave}'"

    return False, "sin señales de que importe"


def categorizar(asunto, cuerpo=""):
    """Qué ES el correo (r.62): tarea/entrega/examen/aviso/correo. Solo
    reglas locales sobre texto ya en disco -- nada sale a ninguna API
    (r.91: correos jamás a API gratis)."""
    t = normalizar(f"{asunto} {cuerpo[:500]}")
    for categoria, claves in CATEGORIAS_ORDEN:
        if any(c in t for c in claves):
            return categoria
    return "correo"


def _texto_fecha(dia, ahora, hora_min):
    if dia == ahora.date():
        base = "hoy"
    elif dia == ahora.date() + datetime.timedelta(days=1):
        base = "mañana"
    else:
        base = dia.strftime("%d/%m")
    if hora_min:
        return f"{base} a las {hora_min[0]:02d}:{hora_min[1]:02d}"
    return base


def extraer_fecha_limite(texto, ahora=None):
    """Busca fecha/hora límite en el texto (asunto+cuerpo) con reglas
    locales -- 'hoy a las 11', 'antes de las 12', '5 de agosto', 'dd/mm',
    y el campo estructurado que ya manda Classroom ('Fecha de entrega: 13
    dic'). Devuelve (texto_legible, datetime) o (None, None) si no
    encuentra nada. Sin día explícito pero con hora -> se asume HOY
    (correo recién llegado, mismo criterio del ejemplo de Arturo: r.64).

    Deliberadamente NO busca una hora "suelta" (\\d:\\d\\d sin más contexto):
    probado contra el buzón real (04 ago), esa regla capturaba basura del
    pie de los correos de Classroom ("Publicado el 5:01 p.m." se leía como
    hora límite). La hora solo cuenta si viene pegada a una frase que
    realmente la anuncia ('a las'/'antes de las'/'hasta las')."""
    ahora = ahora or datetime.datetime.now()
    t = normalizar(texto)

    hora = minuto = None
    m = re.search(r"(?:antes de las|hasta las|a las)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
    if m:
        hora = int(m.group(1))
        minuto = int(m.group(2)) if m.group(2) else 0
        ampm = m.group(3)
        if ampm == "pm" and hora < 12:
            hora += 12
        elif ampm == "am" and hora == 12:
            hora = 0
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            hora = minuto = None

    dia = None
    # Fuente más confiable primero: el campo propio de Classroom.
    fc = re.search(r"fecha de entrega:\s*(\d{1,2})\s*(" + "|".join(MESES_ABR) + r")\b", t)
    if fc:
        d, mo = int(fc.group(1)), MESES_ABR[fc.group(2)]
        try:
            dia = datetime.date(ahora.year, mo, d)
            if dia < ahora.date() - datetime.timedelta(days=30):
                dia = datetime.date(ahora.year + 1, mo, d)
        except ValueError:
            dia = None

    if dia is None:
        if "hoy" in t:
            dia = ahora.date()
        elif "manana" in t:
            dia = (ahora + datetime.timedelta(days=1)).date()
        else:
            fm = re.search(r"\b(\d{1,2})\s*de\s*(" + "|".join(MESES) + r")\b", t)
            if fm:
                d, mo = int(fm.group(1)), MESES[fm.group(2)]
                try:
                    dia = datetime.date(ahora.year, mo, d)
                    if dia < ahora.date():
                        dia = datetime.date(ahora.year + 1, mo, d)
                except ValueError:
                    dia = None
            else:
                fm2 = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
                if fm2:
                    d, mo = int(fm2.group(1)), int(fm2.group(2))
                    anio = int(fm2.group(3)) if fm2.group(3) else ahora.year
                    if anio < 100:
                        anio += 2000
                    try:
                        dia = datetime.date(anio, mo, d)
                    except ValueError:
                        dia = None

    if hora is None and dia is None:
        return None, None
    if dia is None:
        dia = ahora.date()

    if hora is None:
        dt = datetime.datetime.combine(dia, datetime.time(23, 59))
        texto_legible = _texto_fecha(dia, ahora, None)
    else:
        dt = datetime.datetime.combine(dia, datetime.time(hora, minuto))
        texto_legible = _texto_fecha(dia, ahora, (hora, minuto))

    return texto_legible, dt


def construir_mensaje(remitente, asunto, categoria, fecha_texto, motivo):
    """Formato EXACTO pedido por Arturo (04 ago): avisa qué es y CIERRA
    preguntando qué hacer -- nunca asume ni actúa solo (r.62-64, r.89)."""
    frase_cat = ARTICULO_CATEGORIA.get(categoria, "un correo importante")
    frase_fecha = f" para {fecha_texto}" if fecha_texto else ""
    pregunta = (f"Arturo, te llegó un correo de la escuela, es {frase_cat}"
                f"{frase_fecha}, ¿qué quieres que realice?")
    remitente_limpio = re.sub(r"\s*<.*?>", "", remitente).strip() or remitente
    return (f"📧 {pregunta}\n\n"
            f"De: {remitente_limpio}\n"
            f"Asunto: {asunto}\n"
            f"(te aviso porque {motivo})")


def cargar_seguimientos():
    if not os.path.exists(SEGUIMIENTOS):
        return []
    try:
        with open(SEGUIMIENTOS, encoding="utf-8") as f:
            return json.load(f).get("pendientes", [])
    except Exception as e:
        log(f"⚠️  No pude leer seguimientos ({e}) — empiezo vacío")
        return []


def guardar_seguimientos(pendientes):
    os.makedirs(os.path.dirname(SEGUIMIENTOS), exist_ok=True)
    tmp = SEGUIMIENTOS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"pendientes": pendientes,
                   "actualizado": datetime.datetime.now().isoformat()},
                  f, ensure_ascii=False)
    os.replace(tmp, SEGUIMIENTOS)


def registrar_seguimiento(correo_id, asunto, categoria, deadline_dt):
    """r.64: solo tareas/entregas/exámenes con hora límite resuelta entran
    al seguimiento de dos avisos (antes/después)."""
    if categoria not in ("tarea", "entrega", "examen") or deadline_dt is None:
        return
    pendientes = cargar_seguimientos()
    if any(p["id"] == correo_id for p in pendientes):
        return
    pendientes.append({
        "id": correo_id,
        "asunto": asunto,
        "categoria": categoria,
        "deadline": deadline_dt.isoformat(),
        "aviso_antes_enviado": False,
        "aviso_despues_enviado": False,
    })
    guardar_seguimientos(pendientes)
    log(f"🗓️  Seguimiento registrado: {asunto[:60]} — vence {deadline_dt.isoformat()}")


def verificar_seguimientos(ahora=None):
    """r.64: ANTES de la hora límite avisa qué falta y hay que subirlo;
    DESPUÉS pregunta si ya se subió -- nunca asume que se hizo. No dispara
    dos veces el mismo aviso (se marca por separado antes/después)."""
    ahora = ahora or datetime.datetime.now()
    pendientes = cargar_seguimientos()
    if not pendientes:
        return
    quedan = []
    for p in pendientes:
        deadline = datetime.datetime.fromisoformat(p["deadline"])
        margen = deadline - datetime.timedelta(minutes=MARGEN_ANTES_MIN)

        if not p["aviso_antes_enviado"] and ahora >= margen:
            msg = (f"⏰ Solo faltan estos detalles: revisa y sube "
                   f"\"{p['asunto']}\" antes de las {deadline.strftime('%H:%M')}.")
            if avisar(msg):
                p["aviso_antes_enviado"] = True
                log(f"✅ Aviso ANTES enviado: {p['asunto'][:60]}")
            else:
                log(f"🔴 NO se pudo avisar (antes) de: {p['asunto'][:60]}")

        if not p["aviso_despues_enviado"] and ahora >= deadline:
            msg = (f"❓ ¿Ya subiste/resolviste \"{p['asunto']}\"? La hora "
                   f"límite ({deadline.strftime('%H:%M')}) ya pasó -- "
                   f"confírmame para cerrar el pendiente.")
            if avisar(msg):
                p["aviso_despues_enviado"] = True
                log(f"✅ Aviso DESPUÉS enviado: {p['asunto'][:60]}")
            else:
                log(f"🔴 NO se pudo avisar (después) de: {p['asunto'][:60]}")

        if not (p["aviso_antes_enviado"] and p["aviso_despues_enviado"]):
            quedan.append(p)
    guardar_seguimientos(quedan)


def cuerpo_texto(m, limite=4000):
    """Cuerpo en texto plano del mensaje, local -- nunca sale a ninguna
    API (r.91). Solo se usa para extraer fecha límite con regex."""
    try:
        if m.is_multipart():
            for parte in m.walk():
                if parte.get_content_type() == "text/plain":
                    payload = parte.get_payload(decode=True)
                    if payload:
                        charset = parte.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")[:limite]
            return ""
        payload = m.get_payload(decode=True)
        if payload:
            charset = m.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")[:limite]
        return ""
    except Exception:
        return ""


def cargar_vistos():
    if not os.path.exists(ESTADO):
        return None  # None = primera corrida
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return set(json.load(f).get("vistos", []))
    except Exception as e:
        log(f"⚠️  No pude leer el estado ({e}) — trato esta corrida como primera "
            f"para no inundarte de avisos viejos")
        return None


def guardar_vistos(vistos):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"vistos": sorted(vistos),
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


def _cargar_salud():
    if not os.path.exists(SALUD):
        return {"alertando": False, "ultima_alerta": None}
    try:
        with open(SALUD, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"⚠️  No pude leer el estado de salud ({e}) — trato como sano para "
            f"no reavisar de más")
        return {"alertando": False, "ultima_alerta": None}


def _guardar_salud(estado):
    os.makedirs(os.path.dirname(SALUD), exist_ok=True)
    tmp = SALUD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f)
    os.replace(tmp, SALUD)


def verificar_frescura(ahora=None):
    """Antes de confiar en 'sin novedades', confirma que el buzon SIGUE
    sincronizando de verdad. Si no puede confirmarlo, avisa por Telegram --
    nunca reporta 'todo bien' a ciegas (hallazgo 04 ago: Thunderbird murio 3
    dias en silencio, nadie se entero hasta que Arturo pregunto).

    No reavisa cada corrida (cada 15 min saturaria): solo al entrar en el
    estado caido, y despues cada REALERTA_HORAS mientras siga caido. Cuando
    se recupera, avisa que ya volvio -- cierra el ciclo, no deja a Arturo
    adivinando si se arreglo solo.

    Devuelve True si el buzon esta fresco (seguro seguir), False si no.
    """
    ahora = ahora or datetime.datetime.now()
    salud = _cargar_salud()

    if not os.path.exists(MBOX):
        fresco = False
        razon = "el archivo del buzón no existe — ¿Thunderbird está corriendo?"
    else:
        edad_horas = (ahora.timestamp() - os.path.getmtime(MBOX)) / 3600
        if edad_horas > UMBRAL_STALE_HORAS:
            fresco = False
            razon = f"el buzón lleva {edad_horas:.1f}h sin sincronizar"
        else:
            fresco, razon = True, None

    if fresco:
        if salud.get("alertando"):
            msg = ("🟢 El correo escolar volvió a sincronizar normal — "
                    "ya puedo confiar de nuevo en lo que vigilo.")
            if AVISAR_FRESCURA_POR_TELEGRAM and avisar(msg):
                log("✅ Frescura recuperada, aviso de vuelta enviado")
            else:
                log("✅ Frescura recuperada (solo log, Arturo pidió no avisar por Telegram)")
        _guardar_salud({"alertando": False, "ultima_alerta": None})
        return True

    ultima = salud.get("ultima_alerta")
    debe_avisar = (
        not salud.get("alertando")
        or ultima is None
        or (ahora - datetime.datetime.fromisoformat(ultima)
            >= datetime.timedelta(hours=REALERTA_HORAS))
    )
    if debe_avisar:
        msg = (f"⚠️ No puedo confirmar que el correo escolar esté sincronizando: "
               f"{razon}. Puede que me esté perdiendo correos reales sin avisarte "
               f"— revisa Thunderbird.")
        if AVISAR_FRESCURA_POR_TELEGRAM:
            if avisar(msg):
                log(f"⚠️  Alerta de frescura enviada: {razon}")
            else:
                log(f"🔴 No pude avisar de la falta de frescura ({razon}) — Telegram también falló")
        else:
            log(f"⚠️  {razon} (solo log, Arturo pidió no avisar por Telegram — "
                f"04 ago, ver AVISAR_FRESCURA_POR_TELEGRAM)")
        _guardar_salud({"alertando": True, "ultima_alerta": ahora.isoformat()})
    else:
        log(f"⚠️  Buzón sigue sin fresco ({razon}) — ya avisado, no reavisar aún")
    return False


def leer_correos():
    if not os.path.exists(MBOX):
        log(f"🔴 No existe el buzon en {MBOX} — ¿Thunderbird esta corriendo?")
        return None
    correos = []
    for m in mailbox.mbox(MBOX):
        mid = m.get("Message-ID") or ""
        remitente = dec(m.get("From"))
        asunto = dec(m.get("Subject"))
        fecha = m.get("Date")
        try:
            dt = email.utils.parsedate_to_datetime(fecha)
            if dt.tzinfo:
                dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        except Exception:
            dt = None
        correos.append({"id": mid or f"{remitente}|{asunto}|{fecha}",
                        "de": remitente, "asunto": asunto, "fecha": dt,
                        "cuerpo": cuerpo_texto(m)})
    return correos


def main():
    probar = "--probar" in sys.argv

    if not probar:
        verificar_frescura()
        verificar_seguimientos()

    correos = leer_correos()
    if correos is None:
        sys.exit(1)

    if probar:
        imp = ruido = 0
        for c in sorted(correos, key=lambda x: x["fecha"] or datetime.datetime.min):
            ok, motivo = clasificar(c["de"], c["asunto"])
            imp += ok
            ruido += not ok
            marca = "✅ AVISA " if ok else "   calla "
            f = c["fecha"].strftime("%Y-%m-%d") if c["fecha"] else "??"
            print(f"{marca} {f} | {c['de'][:32]:<32} | {c['asunto'][:44]:<44} | {motivo}")
        print(f"\nTotal: {len(correos)} · avisaria de {imp} · callaria {ruido}")
        return

    vistos = cargar_vistos()
    primera = vistos is None
    if primera:
        vistos = set()

    nuevos_importantes = []
    todos_ids = set()
    for c in correos:
        todos_ids.add(c["id"])
        if c["id"] in vistos:
            continue
        ok, motivo = clasificar(c["de"], c["asunto"])
        if ok:
            nuevos_importantes.append((c, motivo))

    if primera:
        # No inundar con el historico: se marca todo como visto y se avisa
        # desde el proximo correo.
        guardar_vistos(todos_ids)
        log(f"✅ Primera corrida: {len(correos)} correos marcados como ya vistos. "
            f"De aqui en adelante aviso solo lo nuevo e importante.")
        return

    if not nuevos_importantes:
        log(f"✅ Sin novedades importantes ({len(correos)} correos en el buzon)")
        guardar_vistos(todos_ids)
        return

    nuevos_importantes.sort(key=lambda x: x[0]["fecha"] or datetime.datetime.min)
    for c, motivo in nuevos_importantes:
        categoria = categorizar(c["asunto"], c.get("cuerpo", ""))
        fecha_texto, deadline_dt = extraer_fecha_limite(
            f"{c['asunto']} {c.get('cuerpo', '')}")
        msg = construir_mensaje(c["de"], c["asunto"], categoria, fecha_texto, motivo)
        if avisar(msg):
            log(f"✅ Avisado [{categoria}]: {c['asunto'][:60]} — {motivo}")
            registrar_seguimiento(c["id"], c["asunto"], categoria, deadline_dt)
        else:
            log(f"🔴 NO se pudo avisar de: {c['asunto'][:60]}")

    guardar_vistos(todos_ids)


if __name__ == "__main__":
    main()
