"""Pruebas de vigilar_correo_personal.py (F6-1, r.107-108).

El bloque promete: analizar -> avisar prioritarios (banco, compras,
invitaciones a eventos) -> sugerir que hacer; ruido = notificaciones
sociales ("alguien comento/compartio"). Estas pruebas clavan:

  1. CLASIFICACION: cada categoria de r.108 dispara con ejemplos reales de
     asunto/remitente, y el ruido social se calla.
  2. REGRESION real (03 ago, prueba en vivo contra la bandeja de Arturo):
     "te envio un mensaje" de una notificacion social NO debe clasificar
     como "compras" solo porque "envio" es substring de "envió" -- el bug
     que se encontro y se corrigio en esta misma sesion.
  3. SUGERENCIA: cada categoria prioritaria trae una sugerencia concreta,
     nunca vacia.
  4. ESTADO / "jamas la bandeja historica": la primera corrida guarda la
     frontera de UID sin marcar nada mas, y las corridas siguientes solo
     avanzan la frontera -- nunca retrocede.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import vigilar_correo_personal as vcp  # noqa: E402


# ── clasificar() ─────────────────────────────────────────────────────────
def test_banco_es_prioritario():
    cat, motivo = vcp.clasificar("BBVA México <alertas@bbva.com>", "Movimiento en tu tarjeta de crédito")
    assert cat == "banco"
    assert motivo


def test_compras_es_prioritario():
    cat, _ = vcp.clasificar("Amazon.com <auto-confirm@amazon.com>", "Tu pedido ha sido enviado")
    assert cat == "compras"


def test_evento_es_prioritario():
    cat, _ = vcp.clasificar("Ana <ana@example.com>", "Te invito a mi cumpleaños")
    assert cat == "eventos"


def test_ruido_social_se_calla():
    cat, motivo = vcp.clasificar(
        "TikTok <notification@service.tiktok.com>", "El May dio me gusta a tu publicación"
    )
    assert cat == "ruido"
    assert "social" in motivo


def test_correo_sin_señales_es_neutral():
    cat, _ = vcp.clasificar("The New York Times <nytimes@e.nytimes.com>", "Two ways to try The Times")
    assert cat == "neutral"


def test_regresion_envio_no_es_compras_por_accidente():
    """Bug real hallado el 03 ago en la prueba en vivo: 'Karenn en TikTok'
    con asunto 'te envió un mensaje' clasificaba como compras porque
    'envio' (normalizado) es substring de 'envió'. Corregido: CLAVES_COMPRAS
    ya no usa 'envio' a secas, solo frases completas de compra real."""
    cat, _ = vcp.clasificar("Karenn en TikTok <mensajes@tiktok.com>", "Karenn te envió un mensaje")
    assert cat != "compras"


def test_mensaje_de_messenger_no_es_compras():
    cat, _ = vcp.clasificar("Manuel a través de Messenger <notification@facebookmail.com>", "Manuel te envió un mensaje")
    assert cat == "ruido"


# ── redes (04 ago, petición de Arturo): marca, infracciones, monetización, política ──
def test_infraccion_de_tiktok_es_redes_no_ruido():
    """El punto central: el MISMO dominio (tiktok.com) manda ruido social Y
    avisos reales -- un aviso real no debe perderse en 'ruido' solo por
    venir de un dominio que normalmente calla."""
    cat, motivo = vcp.clasificar("TikTok <no-reply@tiktok.com>",
                                  "Tu cuenta ha sido suspendida por infraccion de nuestras normas")
    assert cat == "redes"
    assert "infraccion" in motivo


def test_monetizacion_de_youtube_es_redes():
    cat, _ = vcp.clasificar("YouTube <no-reply@youtube.com>",
                             "Felicidades, tu canal ya es elegible para monetizacion")
    assert cat == "redes"


def test_cambio_de_politica_es_redes():
    cat, _ = vcp.clasificar("Instagram <security@mail.instagram.com>",
                             "Actualizacion de terminos de servicio")
    assert cat == "redes"


def test_propuesta_de_marca_es_redes():
    cat, _ = vcp.clasificar("Contacto Marca X <marketing@marcax.com>",
                             "Propuesta de colaboracion para tu contenido")
    assert cat == "redes"


def test_ruido_social_normal_de_tiktok_sigue_siendo_ruido():
    """Regresión: agregar 'redes' NO debe convertir todo lo de TikTok en
    prioritario -- el 'te siguio'/'te comento' normal se sigue callando."""
    cat, _ = vcp.clasificar("alguien en TikTok <notification@service.tiktok.com>",
                             "alguien te empezo a seguir")
    assert cat == "ruido"


# ── escolar por correo personal (04 ago): compañeros mandando tareas ────
def test_documento_de_companero_es_escolar():
    """Caso real hallado el 04 ago: este correo cayó en 'neutral' antes de
    agregar la categoría -- r.108 nunca definió 'escolar' para el personal."""
    cat, motivo = vcp.clasificar("Cruz Roman <cruzrr1996@gmail.com>", "unidad IV_complemento.docx")
    assert cat == "escolar"
    assert motivo


def test_tarea_de_companero_es_escolar():
    cat, _ = vcp.clasificar("Ana <ana@gmail.com>", "Tarea de la practica 3, equipo de trabajo")
    assert cat == "escolar"


# ── sugerir() ─────────────────────────────────────────────────────────────
def test_sugerencias_no_vacias_para_prioritarios():
    for cat in ("banco", "compras", "eventos", "redes", "escolar"):
        s = vcp.sugerir(cat)
        assert s and isinstance(s, str)


def test_sugerencia_eventos_no_agenda_sola():
    """r.89: captura espontánea = preguntar antes de agendar. La sugerencia
    de un evento nunca debe prometer que Hermes ya lo metió al calendario."""
    s = vcp.sugerir("eventos")
    assert "agend" in s.lower()
    assert "pregunt" in s.lower() or "dime" in s.lower()


# ── _parse_headers() ────────────────────────────────────────────────────
def test_parse_headers_extrae_de_asunto_fecha():
    raw = (
        b"From: Banco X <alertas@bancox.com>\r\n"
        b"Subject: Aviso de cargo\r\n"
        b"Date: Mon, 03 Aug 2026 10:00:00 -0600\r\n"
    )
    de, asunto, fecha = vcp._parse_headers(raw)
    assert de == "Banco X <alertas@bancox.com>"
    assert asunto == "Aviso de cargo"
    assert fecha is not None
    assert fecha.year == 2026


# ── estado / frontera de UID ────────────────────────────────────────────
def test_primera_corrida_no_hay_estado_previo(tmp_path, monkeypatch):
    monkeypatch.setattr(vcp, "ESTADO", str(tmp_path / "estado.json"))
    assert vcp.cargar_estado() is None


def test_guardar_y_cargar_estado_redondea(tmp_path, monkeypatch):
    monkeypatch.setattr(vcp, "ESTADO", str(tmp_path / "estado.json"))
    vcp.guardar_estado(4244)
    assert vcp.cargar_estado() == 4244


def test_frontera_solo_avanza_nunca_retrocede_en_uso_normal(tmp_path, monkeypatch):
    """No es una garantía que el código imponga sola (el llamador decide qué
    guardar), pero el flujo normal de main() siempre usa max(...); esta
    prueba documenta el contrato: guardar un UID mayor lo reemplaza."""
    monkeypatch.setattr(vcp, "ESTADO", str(tmp_path / "estado.json"))
    vcp.guardar_estado(100)
    vcp.guardar_estado(150)
    assert vcp.cargar_estado() == 150


# ── _fetch_uids_desde: gotcha real de IMAP (04 ago) ─────────────────────
# Reporte real de Arturo: el mismo correo ("unidad IV_complemento.docx")
# se avisó 3 veces seguidas, 15 min aparte, con la frontera YA al día.
# Causa raíz reproducida contra Gmail real: cuando desde_uid es el UID más
# alto del buzón, el rango "N:*" NO regresa vacío -- RFC 3501 dice que "*"
# siempre es el UID más grande que exista, así que el servidor regresa ese
# último correo de todos modos, sin importar N. El fix filtra del lado de
# acá: nunca confiar en que el servidor respetó el rango pedido.

class _FakeIMAP:
    """Simula el SEARCH/FETCH de imaplib, incluido el gotcha real de Gmail
    (N:* regresando el último UID aunque N lo rebase)."""

    def __init__(self, search_result: bytes, fetch_map: dict):
        self._search_result = search_result
        self._fetch_map = fetch_map

    def uid(self, command, *args):
        if command == "SEARCH":
            return "OK", [self._search_result]
        if command == "FETCH":
            uid = int(args[0])
            raw = self._fetch_map.get(uid)
            if raw is None:
                return "NO", [None]
            return "OK", [(b"1 (BODY[...])", raw)]
        raise NotImplementedError(command)


def _raw_headers(de, asunto, fecha="Tue, 04 Aug 2026 12:00:00 -0600"):
    return (f"From: {de}\r\nSubject: {asunto}\r\nDate: {fecha}\r\n").encode()


def test_gotcha_imap_frontera_al_dia_no_reavisa():
    """El caso exacto del bug: desde_uid=4255 (ya es el UID más alto real),
    pero el servidor (simulado igual que Gmail) regresa '4255' de todos
    modos -- _fetch_uids_desde debe filtrarlo y devolver vacío."""
    imap = _FakeIMAP(
        search_result=b"4255",  # el gotcha: servidor regresa el ultimo UID
        fetch_map={4255: _raw_headers("Cruz Roman <cruzrr1996@gmail.com>",
                                       "unidad IV_complemento.docx")},
    )
    correos = vcp._fetch_uids_desde(imap, desde_uid=4255)
    assert correos == []


def test_gotcha_imap_correo_genuinamente_nuevo_si_avisa():
    """Regresión inversa: el filtro no debe volverse tan agresivo que
    calle un correo REAL nuevo."""
    imap = _FakeIMAP(
        search_result=b"4256",
        fetch_map={4256: _raw_headers("Alguien <alguien@example.com>", "Hola")},
    )
    correos = vcp._fetch_uids_desde(imap, desde_uid=4255)
    assert len(correos) == 1
    assert correos[0]["uid"] == 4256
