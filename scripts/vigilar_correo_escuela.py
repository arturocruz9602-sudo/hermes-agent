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
                        "de": remitente, "asunto": asunto, "fecha": dt})
    return correos


def main():
    probar = "--probar" in sys.argv

    if not probar:
        verificar_frescura()

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
        f = c["fecha"].strftime("%d %b %H:%M") if c["fecha"] else "sin fecha"
        remitente = re.sub(r"\s*<.*?>", "", c["de"]).strip() or c["de"]
        msg = (f"📧 Correo de la escuela\n\n"
               f"De: {remitente}\n"
               f"Asunto: {c['asunto']}\n"
               f"Recibido: {f}\n\n"
               f"(te aviso porque {motivo})")
        if avisar(msg):
            log(f"✅ Avisado: {c['asunto'][:60]} — {motivo}")
        else:
            log(f"🔴 NO se pudo avisar de: {c['asunto'][:60]}")

    guardar_vistos(todos_ids)


if __name__ == "__main__":
    main()
