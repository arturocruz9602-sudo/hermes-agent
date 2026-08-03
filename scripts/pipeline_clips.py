#!/usr/bin/env python3
"""pipeline_clips — Bloque AU-2 (HAS Fase 8 / OT-8 / OT-11, r.46/r.48/r.59).

Del VIDEO LARGO de la semana saca los clips valiosos que NO pasen de 2 min,
los distribuye en los mejores horarios de la semana, y prepara la publicación
en YouTube — que NUNCA es automática: Hermes deja todo listo y Arturo da el
"sí, súbelo" (DECISIONES 31 jul; r.59).

Tres piezas, todas deterministas y probables sin red ni modelos de pago:

  1. EXTRACCIÓN (r.46/r.48): de un transcripto con tiempos, encuentra ventanas
     ≤120s autocontenidas y las puntúa por "valor de clip" (gancho, curiosidad,
     emoción, idea completa). Devuelve solo las valiosas, sin traslape, rankeadas.
     Si salen 10 clips buenos, son 10; si salen 20, son 20 (r.48). El tope de
     2 min es DURO: el extractor jamás emite una ventana más larga.

  2. PROGRAMACIÓN (r.46): reparte los clips valiosos en los mejores horarios de
     la semana (anclados en investigación, ver MEJORES_FRANJAS), el mejor clip
     al mejor hueco, espaciados para "siempre estar subiendo" y sin amontonar en
     un día. Todo queda en estado 'propuesta': es un PLAN para que Arturo apruebe.

  3. OAUTH + PUBLICACIÓN (r.59, DECISIONES 31 jul): el OAuth vive en HERMES, no
     en Claude Code. `TokenYouTube` verifica vigencia y AVISA si vence — nunca
     falla en silencio (regla 3). `PublicadorYouTube` tiene el cliente de red
     INYECTABLE (cableado pero pendiente del OAuth de Arturo, igual que el
     testnet de Binance en AT) y se NIEGA a subir sin `aprobado=True` explícito.

QUÉ NO HACE: no edita ni renderiza el video (eso es la skill de DaVinci, otro
bloque; DECISIONES 31 jul: edición creativa autónoma no se promete). No abre la
DB ni la red por su cuenta: registro y cliente son inyectables (B10, r.119).

Investigación que ancla los horarios (búsqueda web 02 ago 2026, fuentes 2025-2026,
hora local de Arturo — CDMX):
  - Picos: tarde 14-16h y 17:30-19:30 (after-work, ~+23% engagement, el más
    fuerte), noche 19-22h (pico de visionado móvil).
  - Fines de semana ~+60% más engagement que entre semana.
  - Lunes/martes y viernes son los mejores días para estrenar.
  (hopperhq.com, posteverywhere.ai, screenstory.io, wayin.ai — 2025/2026)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

# Reutiliza los marcadores y utilidades ya probados del motor de guiones (AU-1)
# en vez de duplicarlos: gancho/curiosidad y conteo de palabras son los mismos.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from motor_guiones import (  # noqa: E402
    REGLAS_RETENCION,
    _MARCA_OPEN_LOOP,
    _MARCA_CTA,
    _palabras,
)

# ── frontera del bloque: el clip NUNCA pasa de 2 min (r.48) ──────────────────
MAX_CLIP_SEG = 120        # tope DURO de 2 minutos
MIN_CLIP_SEG = 15         # menos de 15s no alcanza a enganchar (r.47)
UMBRAL_VALOR = 30         # piso de "valor de clip" para considerarlo publicable


# ── marcadores de un momento fuerte y autocontenido (formato podcast) ────────
# Emoción/tensión: un clip que se sostiene solo suele tener un pico emocional.
_MARCA_EMOCION = re.compile(
    r"\b(nunca|jamás|increíble|brutal|terrible|nadie sabe|la verdad|"
    r"me equivoqué|cambió todo|lo peor|lo mejor|impactante|no vas a creer|"
    r"traición|muerte|guerra|amor|miedo|secreto|escándalo)\b",
    re.IGNORECASE,
)
# Cierre de idea: una frase conclusiva hace el clip autocontenido.
_MARCA_REMATE = re.compile(
    r"\b(por eso|así que|al final|la lección|en conclusión|moraleja|"
    r"y eso|esto demuestra|lo que aprendí|resulta que)\b",
    re.IGNORECASE,
)


# ── modelo de datos ──────────────────────────────────────────────────────────
@dataclass
class SegmentoTranscrito:
    """Un tramo del transcripto del video largo, con tiempos en segundos.
    Materia prima real: lo exporta el editor/STT sobre el video grabado."""
    inicio: float
    fin: float
    texto: str

    @property
    def duracion(self) -> float:
        return self.fin - self.inicio


@dataclass
class ClipCandidato:
    """Un clip valioso ≤2 min recortado del video largo. `valor` es la puntuación
    (0-100) y `motivos` explica por qué es publicable (r.91: números + razón)."""
    inicio: float
    fin: float
    texto: str
    titulo: str = ""
    valor: int = 0
    motivos: list[str] = field(default_factory=list)

    @property
    def duracion(self) -> float:
        return round(self.fin - self.inicio, 1)

    def __post_init__(self) -> None:
        # La frontera del bloque se defiende en el propio dato: es imposible
        # construir un ClipCandidato que pase de 2 min (r.48).
        if self.duracion > MAX_CLIP_SEG + 1e-6:
            raise ValueError(
                f"Clip de {self.duracion}s > tope de {MAX_CLIP_SEG}s (2 min). "
                f"El extractor debe recortarlo antes de crear el candidato."
            )


@dataclass
class Publicacion:
    """Un clip agendado en un horario. Nace en 'propuesta': es el plan que
    Arturo aprueba antes de que algo salga a la calle (r.59)."""
    clip: ClipCandidato
    cuando: datetime
    plataforma: str = "youtube"
    estado: str = "propuesta"   # propuesta → aprobada → publicada | fallida
    franja_puntaje: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cuando"] = self.cuando.isoformat()
        return d


# ── 1. EXTRACCIÓN de clips ≤2 min (r.46/r.48) ────────────────────────────────
def _valor_texto(texto: str) -> tuple[int, list[str]]:
    """Puntúa qué tan 'clip valioso' es un tramo, con razones medibles."""
    puntaje = 0
    motivos: list[str] = []

    ganchos = len(_MARCA_OPEN_LOOP.findall(texto))
    if ganchos:
        puntaje += min(30, 15 * ganchos)
        motivos.append(f"{ganchos} gancho(s)/curiosidad")

    emociones = len(_MARCA_EMOCION.findall(texto))
    if emociones:
        puntaje += min(30, 15 * emociones)
        motivos.append(f"{emociones} pico(s) emocional(es)")

    if _MARCA_REMATE.search(texto):
        puntaje += 25
        motivos.append("remata la idea (autocontenido)")

    # Densidad: un clip con demasiado poco texto no sostiene el minuto.
    palabras = _palabras(texto)
    if palabras >= REGLAS_RETENCION["palabras_por_15s"]:
        puntaje += 15
        motivos.append(f"{palabras} palabras (cuerpo suficiente)")

    return min(100, puntaje), motivos


def _titulo_desde(texto: str, limite: int = 70) -> str:
    limpio = re.sub(r"\s+", " ", texto).strip()
    return (limpio[: limite - 1] + "…") if len(limpio) > limite else limpio


def extraer_clips(
    transcripto: list[SegmentoTranscrito],
    max_seg: float = MAX_CLIP_SEG,
    min_seg: float = MIN_CLIP_SEG,
    umbral: int = UMBRAL_VALOR,
) -> list[ClipCandidato]:
    """Encuentra los clips valiosos ≤`max_seg` del video largo.

    Ancla una ventana en cada segmento y la extiende mientras quepa en el tope
    de 2 min; puntúa cada ventana; luego elige codiciosamente por valor las que
    no se traslapan. Devuelve solo las que superan `umbral`, rankeadas (r.48: si
    hay 20 valiosas, son 20; si hay 3, son 3 — no rellena de paja).
    """
    n = len(transcripto)
    ventanas: list[ClipCandidato] = []
    for i in range(n):
        fin_idx = i
        # extiende mientras la ventana [i..fin_idx] no pase del tope
        while (fin_idx + 1 < n
               and transcripto[fin_idx + 1].fin - transcripto[i].inicio <= max_seg):
            fin_idx += 1
        inicio = transcripto[i].inicio
        fin = transcripto[fin_idx].fin
        dur = fin - inicio
        if dur < min_seg or dur > max_seg:
            continue
        texto = " ".join(s.texto for s in transcripto[i:fin_idx + 1]).strip()
        valor, motivos = _valor_texto(texto)
        if valor < umbral:
            continue
        ventanas.append(ClipCandidato(
            inicio=inicio, fin=fin, texto=texto,
            titulo=_titulo_desde(texto), valor=valor, motivos=motivos,
        ))

    # selección codiciosa sin traslape: primero las de mayor valor.
    ventanas.sort(key=lambda c: (-c.valor, c.inicio))
    elegidos: list[ClipCandidato] = []
    ocupado: list[tuple[float, float]] = []
    for c in ventanas:
        if any(not (c.fin <= a or c.inicio >= b) for a, b in ocupado):
            continue
        elegidos.append(c)
        ocupado.append((c.inicio, c.fin))
    elegidos.sort(key=lambda c: -c.valor)
    return elegidos


# ── 2. PROGRAMACIÓN en los mejores horarios (r.46) ───────────────────────────
# Pesos anclados en la investigación (hora local de Arturo). No es un gate
# ciego: es un CRITERIO numérico que Hermes puede ajustar cuando llegue el
# Analytics real del canal (memoria: "inteligencia, no jaulas").
_PESO_DIA = {0: 1.00, 1: 1.00, 2: 0.85, 3: 0.85, 4: 0.95, 5: 1.15, 6: 1.15}
#            lun     mar     mié     jue     vie     sáb     dom  (fin de semana +)
_HORAS_ENTRE_SEMANA = {14: 0.95, 17: 1.00, 18: 1.20, 19: 1.20, 21: 1.00}
_HORAS_FIN_SEMANA = {11: 0.85, 14: 1.00, 17: 1.05, 19: 1.15, 21: 1.00}


def _franjas_semana(inicio: datetime) -> list[tuple[datetime, float]]:
    """Todas las franjas de una semana desde `inicio`, con su puntaje de calidad,
    ordenadas de mejor a peor. `inicio` marca el día 0 de la ventana de 7 días."""
    base = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    franjas: list[tuple[datetime, float]] = []
    for d in range(7):
        dia = base + timedelta(days=d)
        dow = dia.weekday()
        horas = _HORAS_FIN_SEMANA if dow >= 5 else _HORAS_ENTRE_SEMANA
        for h, peso_h in horas.items():
            cuando = dia.replace(hour=h)
            if cuando < inicio:
                continue  # nunca agendar en el pasado
            franjas.append((cuando, round(_PESO_DIA[dow] * peso_h, 3)))
    franjas.sort(key=lambda f: (-f[1], f[0]))
    return franjas


def programar_semana(
    clips: list[ClipCandidato],
    inicio: datetime,
    max_por_dia: int = 4,
    plataforma: str = "youtube",
) -> list[Publicacion]:
    """Agenda los clips valiosos en la semana: el mejor clip al mejor horario,
    respetando un tope por día para no amontonar (r.46). Todo sale en estado
    'propuesta'; publicar sigue necesitando el 'sí' de Arturo (r.59).

    Si hay más clips que franjas buenas en la semana, los sobrantes quedan sin
    agendar y se reportan (nunca se pierden en silencio, regla 3)."""
    ranked = sorted(clips, key=lambda c: -c.valor)
    franjas = _franjas_semana(inicio)
    por_dia: dict = {}
    plan: list[Publicacion] = []
    fi = 0
    for clip in ranked:
        colocado = False
        while fi < len(franjas):
            cuando, peso = franjas[fi]
            dia_key = cuando.date()
            if por_dia.get(dia_key, 0) >= max_por_dia:
                fi += 1
                continue
            plan.append(Publicacion(clip=clip, cuando=cuando, plataforma=plataforma,
                                    estado="propuesta", franja_puntaje=peso))
            por_dia[dia_key] = por_dia.get(dia_key, 0) + 1
            fi += 1
            colocado = True
            break
        if not colocado:
            break  # no quedan franjas; el resto son sobrantes
    plan.sort(key=lambda p: p.cuando)
    return plan


def sobrantes(clips: list[ClipCandidato], plan: list[Publicacion]) -> list[ClipCandidato]:
    """Clips valiosos que no cupieron en la semana (para reprogramar, no perder)."""
    agendados = {id(p.clip) for p in plan}
    return [c for c in clips if id(c) not in agendados]


# ── 3. OAUTH + PUBLICACIÓN (r.59) — nunca automática, nunca en silencio ───────
@dataclass
class EstadoToken:
    """Diagnóstico del token de YouTube. `avisar` es True cuando Arturo debe
    hacer algo (reconectar/renovar). Nunca se falla callado (regla 3)."""
    valido: bool
    avisar: bool
    mensaje: str
    expira_en: Optional[datetime] = None


class TokenYouTube:
    """El OAuth vive en HERMES (no en Claude Code). Lee el token de un archivo
    de config de Hermes (ruta inyectable) y verifica vigencia. Si vence, o está
    por vencer, o no existe: AVISA — jamás falla en silencio (DECISIONES 31 jul,
    r.59). Renovar/reconectar lo hace Arturo (el OAuth de 5 min es su pendiente)."""

    def __init__(self, ruta: str | Path, margen_horas: int = 24,
                 logger: Optional[Callable[[str], None]] = None):
        self.ruta = Path(ruta)
        self.margen = timedelta(hours=margen_horas)
        self._log = logger or (lambda m: None)

    def verificar(self, ahora: Optional[datetime] = None) -> EstadoToken:
        ahora = ahora or datetime.now()
        if not self.ruta.exists():
            est = EstadoToken(
                valido=False, avisar=True, expira_en=None,
                mensaje="No hay token de YouTube en Hermes. Arturo: conecta el "
                        "OAuth (5 min) para que Hermes pueda preparar subidas.")
            self._log(f"[youtube-oauth] SIN TOKEN: {self.ruta}")
            return est
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            expira = datetime.fromisoformat(datos["expira_en"])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            est = EstadoToken(
                valido=False, avisar=True, expira_en=None,
                mensaje=f"Token de YouTube ilegible ({e}). Arturo: reconecta el OAuth.")
            self._log(f"[youtube-oauth] TOKEN ILEGIBLE: {e}")
            return est
        if expira <= ahora:
            est = EstadoToken(
                valido=False, avisar=True, expira_en=expira,
                mensaje=f"Token de YouTube VENCIDO el {expira:%d/%m %H:%M}. "
                        f"Arturo: reconéctalo para poder programar/subir.")
            self._log(f"[youtube-oauth] VENCIDO {expira.isoformat()}")
            return est
        if expira - ahora <= self.margen:
            est = EstadoToken(
                valido=True, avisar=True, expira_en=expira,
                mensaje=f"Token de YouTube vence pronto ({expira:%d/%m %H:%M}). "
                        f"Conviene reconectar antes de que caduque.")
            self._log(f"[youtube-oauth] POR VENCER {expira.isoformat()}")
            return est
        est = EstadoToken(valido=True, avisar=False, expira_en=expira,
                          mensaje=f"Token vigente hasta {expira:%d/%m %H:%M}.")
        self._log(f"[youtube-oauth] OK hasta {expira.isoformat()}")
        return est


@dataclass
class ResultadoPublicacion:
    """Todo intento loggea éxito Y fallo (regla 3). `ok=False` con `motivo`
    nunca es silencio."""
    ok: bool
    motivo: str
    publicacion: Publicacion
    video_id: Optional[str] = None


class PublicadorYouTube:
    """Prepara y (solo con aprobación explícita) sube clips. El `cliente` de red
    es INYECTABLE — la API real de YouTube Data se cablea aquí pero queda pendiente
    del OAuth de Arturo, igual que el testnet de Binance en AT (r.119: nada de red
    por su cuenta). Sin cliente, PREPARA pero no puede subir."""

    def __init__(self, token: TokenYouTube, cliente=None,
                 logger: Optional[Callable[[str], None]] = None):
        self.token = token
        self.cliente = cliente
        self._log = logger or (lambda m: None)

    def preparar(self, pub: Publicacion, ahora: Optional[datetime] = None) -> dict:
        """Arma la solicitud de subida SIN enviar nada. Incluye el aviso del
        token para que Hermes lo muestre junto con la propuesta."""
        estado_tok = self.token.verificar(ahora)
        return {
            "titulo": pub.clip.titulo,
            "descripcion": pub.clip.texto[:4900],
            "programado_para": pub.cuando.isoformat(),
            "plataforma": pub.plataforma,
            "privacidad": "private",   # sube privado; Arturo publica cuando quiera
            "token": {"valido": estado_tok.valido, "aviso": estado_tok.mensaje
                      if estado_tok.avisar else None},
            "listo_para_subir": estado_tok.valido and self.cliente is not None,
        }

    def publicar(self, pub: Publicacion, aprobado: bool,
                 ahora: Optional[datetime] = None) -> ResultadoPublicacion:
        """Sube el clip SOLO si Arturo lo aprobó explícitamente (r.59: "sí,
        súbelo"). Verifica el token antes; si algo falla, lo dice y lo loggea —
        nunca deja la publicación en un limbo callado (regla 3)."""
        if not aprobado:
            r = ResultadoPublicacion(
                ok=False, publicacion=pub,
                motivo="Publicar en YouTube NO es automático: falta el 'sí, "
                       "súbelo' de Arturo (r.59).")
            self._log(f"[youtube-publicar] BLOQUEADO sin aprobación: {pub.clip.titulo}")
            return r
        estado_tok = self.token.verificar(ahora)
        if not estado_tok.valido:
            r = ResultadoPublicacion(ok=False, publicacion=pub,
                                     motivo=f"Token inválido: {estado_tok.mensaje}")
            self._log(f"[youtube-publicar] SIN TOKEN VÁLIDO: {estado_tok.mensaje}")
            return r
        if self.cliente is None:
            r = ResultadoPublicacion(
                ok=False, publicacion=pub,
                motivo="Cliente de YouTube no cableado (pendiente del OAuth real).")
            self._log("[youtube-publicar] cliente ausente (pendiente OAuth)")
            return r
        try:
            video_id = self.cliente.subir(
                titulo=pub.clip.titulo,
                descripcion=pub.clip.texto[:4900],
                programado_para=pub.cuando,
            )
        except Exception as e:  # noqa: BLE001 — cualquier fallo se reporta, no se traga
            pub.estado = "fallida"
            r = ResultadoPublicacion(ok=False, publicacion=pub,
                                     motivo=f"Fallo al subir: {e}")
            self._log(f"[youtube-publicar] FALLO: {e}")
            return r
        pub.estado = "publicada"
        r = ResultadoPublicacion(ok=True, publicacion=pub, video_id=video_id,
                                 motivo="Subido en privado; Arturo publica cuando quiera.")
        self._log(f"[youtube-publicar] OK {video_id}: {pub.clip.titulo}")
        return r


# ── registro en la libreta (inyectable, nunca abre la DB solo — B10) ─────────
def registrar_plan(libreta, plan: list[Publicacion], estado: str = "grabado") -> list[int]:
    """Registra cada clip agendado como un guion 'grabado' en la tabla `guiones`
    (reutiliza el esquema de AU-1: el clip ES un guion corto ya grabado). Guarda
    el horario propuesto y el valor en la columna `nota`. `libreta` es inyectada."""
    ids: list[int] = []
    for pub in plan:
        payload = json.dumps({
            "clip": {"inicio": pub.clip.inicio, "fin": pub.clip.fin,
                     "duracion": pub.clip.duracion, "valor": pub.clip.valor,
                     "motivos": pub.clip.motivos},
            "programado_para": pub.cuando.isoformat(),
            "franja_puntaje": pub.franja_puntaje,
            "estado_publicacion": pub.estado,
        }, ensure_ascii=False)
        cur = libreta.con.execute(
            "INSERT INTO guiones (titulo, plataforma, estado, fecha, nota) "
            "VALUES (?,?,?,?,?)",
            (pub.clip.titulo or "clip", pub.plataforma, estado,
             pub.cuando.date().isoformat(), payload),
        )
        ids.append(cur.lastrowid)
    return ids


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Pipeline de clips ≤2 min + horarios (AU-2)")
    p.add_argument("transcripto", help="ruta a JSON [{inicio,fin,texto}, ...]")
    p.add_argument("--inicio", help="ISO datetime inicio de la semana (default: ahora)")
    p.add_argument("--max-por-dia", type=int, default=4)
    args = p.parse_args(argv)

    datos = json.loads(Path(args.transcripto).read_text(encoding="utf-8"))
    trans = [SegmentoTranscrito(**d) for d in datos]
    clips = extraer_clips(trans)
    inicio = datetime.fromisoformat(args.inicio) if args.inicio else datetime.now()
    plan = programar_semana(clips, inicio, max_por_dia=args.max_por_dia)
    fuera = sobrantes(clips, plan)

    print(f"Clips valiosos ≤2min: {len(clips)}  ·  Agendados: {len(plan)}  ·  "
          f"Sin cupo esta semana: {len(fuera)}")
    for pub in plan:
        print(f"  {pub.cuando:%a %d %H:%M}  (calidad {pub.franja_puntaje})  "
              f"[valor {pub.clip.valor}]  {pub.clip.titulo}")
    if fuera:
        print("Sobrantes (reprogramar la próxima semana):")
        for c in fuera:
            print(f"  [valor {c.valor}]  {c.titulo}")
    print("\nPublicar NO es automático: revisa y da el 'sí, súbelo' (r.59).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
