#!/usr/bin/env python3
"""motor_guiones — Bloque AU-1 (HAS Fase 8 / OT-8, r.45-47, r.49-50).

De una nota de Obsidian (la materia prima: una idea, una biografía, un tema)
arma el ANDAMIAJE de un guion con las tres partes que Arturo pidió que Hermes
"siempre tenga en mente" (r.47): gancho / cierre / análisis de RETENCIÓN en
formato podcast. Y aplica ese análisis a cualquier borrador para proponer
mejoras medibles (r.91: números, no adjetivos).

QUÉ SÍ HACE (determinista, sin red, sin modelos de pago):
  - parsea la nota (frontmatter YAML + cuerpo);
  - la convierte en un ESQUELETO de guion: slot de gancho, promesa/payoff,
    N segmentos de desarrollo con open-loops y transiciones-microgancho,
    cierre y CTA — sembrados con las ideas reales de la nota como GUÍA;
  - analiza la retención de un borrador contra reglas ancladas en
    investigación real (ver REGLAS_RETENCION) y da recomendaciones numéricas;
  - registra el guion en la tabla `guiones` de la libreta (inyectable).

QUÉ NO HACE (decisión del bloque AU-1): NO promete edición creativa autónoma.
No inventa la prosa final del guion y la hace pasar por terminada — eso lo
escribe el modelo en runtime o Arturo. El motor pone el molde y mide; el
relleno creativo es de quien graba. Así aprendemos del proceso real antes de
prometer automatización.

Investigación que ancla las reglas de retención (búsqueda web 02 ago 2026,
priorizando fuentes 2025-2026):
  - Open loops → +32% de watch time; el cerebro busca cerrar el bucle
    (retentionrabbit.com, tubeai.app).
  - Gancho + payoff se escriben PRIMERO; todo lo de en medio es el puente
    entre ambos (overseeros.com).
  - Tras ~15s sin gancho, la retención cae debajo de 45%; las TRANSICIONES
    entre segmentos son donde más se van los espectadores → cada transición
    debe funcionar como micro-gancho (virvid.ai, retentionrabbit.com).
  - Podcast narrativo: la decisión de seguir o abandonar ocurre en los
    primeros minutos; las transiciones que resumen + anticipan evitan el
    abandono en cambios de tema (lowerstreet.co, propodcastsolutions.com).
"""

from __future__ import annotations

import json
import re
import sys
import textwrap
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── reglas de retención ancladas en investigación (formato podcast) ─────────
# Cada regla es un CRITERIO que Hermes razona, no un gate ciego (memoria:
# "inteligencia, no jaulas"). Los números vienen de la investigación de arriba.
REGLAS_RETENCION = {
    "gancho_primeras_palabras": 40,   # el gancho debe caber en ~15s hablados
    "palabras_por_15s": 40,           # ~150 ppm → ~40 palabras en 15s
    "ppm_habla": 150,                 # palabras por minuto al narrar
    "open_loops_min": 1,              # al menos 1 bucle abierto (+32% watch time)
    "segmentos_desarrollo_min": 3,    # arco: apertura, nudo, cierre como piso
    "cta_recomendado": True,
}


# ── modelo de datos ─────────────────────────────────────────────────────────
@dataclass
class NotaObsidian:
    """Una nota del vault ya parseada. `cuerpo` es el Markdown sin frontmatter."""
    titulo: str
    cuerpo: str
    tags: list[str] = field(default_factory=list)
    created: str = ""
    ruta: Optional[str] = None

    def ideas(self) -> list[str]:
        """Las 'ideas' de la nota = párrafos no vacíos del cuerpo.

        Cada párrafo separado por línea en blanco es una semilla de segmento.
        Las viñetas (- / *) se tratan como ideas sueltas dentro de su párrafo.
        """
        parrafos = [p.strip() for p in re.split(r"\n\s*\n", self.cuerpo) if p.strip()]
        return parrafos


@dataclass
class Segmento:
    """Un tramo del desarrollo. `guia` es la instrucción de qué contar aquí
    (sembrada desde la nota), NO la prosa final."""
    titulo: str
    guia: str
    open_loop: Optional[str] = None          # bucle que se abre aquí
    transicion_microgancho: str = ""         # puente hacia el siguiente segmento


@dataclass
class Guion:
    """El andamiaje del guion. Los campos de texto son SLOTS/GUÍAS a rellenar,
    salvo `borrador`, que si existe es la prosa ya escrita (por el LLM o Arturo)
    y es lo que analiza `analizar_retencion`."""
    titulo: str
    plataforma: str = "youtube"
    gancho: str = ""                 # guía del gancho (primeros ~15s)
    promesa: str = ""                # payoff prometido; el gancho lo abre
    segmentos: list[Segmento] = field(default_factory=list)
    cierre: str = ""                 # guía del cierre
    cta: str = ""                    # llamada a la acción
    fuente_nota: Optional[str] = None
    borrador: Optional[str] = None   # prosa final si ya se escribió

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class AnalisisRetencion:
    """Reporte medible del borrador contra las reglas de retención."""
    puntaje: int
    duracion_estimada_min: float
    palabras: int
    gancho_ok: bool
    open_loops: int
    payoff_resuelve_gancho: bool
    transiciones_microgancho: int
    segmentos_desarrollo: int
    cta_presente: bool
    recomendaciones: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── parseo de la nota ───────────────────────────────────────────────────────
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _parse_frontmatter(texto: str) -> tuple[dict, str]:
    """Extrae el frontmatter YAML simple (title/tags/created) sin depender de
    PyYAML: el formato lo escribe obsidian_note_tool.py y es plano."""
    m = _FRONTMATTER.match(texto)
    if not m:
        return {}, texto
    bloque, cuerpo = m.group(1), texto[m.end():]
    meta: dict = {}
    for linea in bloque.splitlines():
        if ":" not in linea:
            continue
        clave, _, valor = linea.partition(":")
        clave, valor = clave.strip(), valor.strip()
        if clave == "tags":
            # tags: ["a", "b"]  ó  tags: [a, b]  ó  tags: []
            crudos = re.findall(r'"([^"]*)"|\'([^\']*)\'|([^,\[\]\s][^,\[\]]*)', valor)
            meta["tags"] = [next(x for x in t if x).strip() for t in crudos
                            if any(x.strip() for x in t)]
        else:
            meta[clave] = valor.strip().strip('"').strip("'")
    return meta, cuerpo


def parse_nota(texto: str, ruta: Optional[str] = None) -> NotaObsidian:
    """Parsea una nota de Obsidian. Si no trae frontmatter, usa la primera
    línea (o encabezado #) como título."""
    meta, cuerpo = _parse_frontmatter(texto)
    cuerpo = cuerpo.strip()
    titulo = str(meta.get("title") or "").strip()
    if not titulo:
        # primera línea util del cuerpo; quita '#' de encabezado si lo hay
        primera = next((l.strip() for l in cuerpo.splitlines() if l.strip()), "guion")
        titulo = re.sub(r"^#+\s*", "", primera)[:120]
    return NotaObsidian(
        titulo=titulo,
        cuerpo=cuerpo,
        tags=list(meta.get("tags") or []),
        created=str(meta.get("created") or ""),
        ruta=ruta,
    )


def parse_nota_archivo(ruta: str | Path) -> NotaObsidian:
    ruta = Path(ruta)
    return parse_nota(ruta.read_text(encoding="utf-8"), ruta=str(ruta))


# ── armado del andamiaje ────────────────────────────────────────────────────
def _resumen(idea: str, limite: int = 90) -> str:
    """Una línea corta de la idea para usar de guía, sin viñetas ni saltos."""
    limpio = re.sub(r"\s+", " ", re.sub(r"^[\-\*•]\s*", "", idea)).strip()
    return textwrap.shorten(limpio, width=limite, placeholder="…") if limpio else ""


def armar_guion(nota: NotaObsidian, plataforma: str = "youtube",
                segmentos_min: int = 3) -> Guion:
    """Convierte la nota en el ESQUELETO del guion (formato podcast de Arturo).

    Cada slot lleva una GUÍA sembrada con la idea real de la nota: es el molde
    que el modelo (o Arturo) rellena, no la prosa final. Garantiza las partes
    obligatorias de r.47 (gancho, cierre, retención) y un piso de segmentos
    para que el arco narrativo exista aunque la nota sea corta.
    """
    ideas = nota.ideas()
    tema = nota.titulo

    # El gancho abre el bucle principal; la promesa/payoff es lo que el gancho
    # promete resolver (se escriben juntos, según la investigación).
    gancho = (
        f"Abre con una tensión o pregunta sobre «{tema}» en los primeros ~15s "
        f"(≤{REGLAS_RETENCION['gancho_primeras_palabras']} palabras). Nada de "
        f"«hola, bienvenidos»: entra con lo más fuerte o con la promesa."
    )
    promesa = (
        f"Payoff: qué se lleva quien aguanta hasta el final de «{tema}». "
        f"El gancho abre este bucle; el cierre lo cierra."
    )

    # Los segmentos de desarrollo salen de las ideas de la nota. Si la nota
    # trae menos que el piso, se completan con slots vacíos para forzar el arco.
    semillas = ideas if ideas else [tema]
    segmentos: list[Segmento] = []
    for i, idea in enumerate(semillas):
        resumen = _resumen(idea)
        seg = Segmento(
            titulo=f"Segmento {i + 1}",
            guia=resumen or f"Desarrolla un punto de «{tema}».",
            # abre un open-loop en segmentos intermedios (no en el último):
            open_loop=(f"Deja una pregunta abierta que se resuelve más adelante."
                       if i < len(semillas) - 1 else None),
            transicion_microgancho=(
                "Cierra este tramo resumiendo en 1 frase y anticipa el siguiente "
                "(la transición es donde más se va la gente: hazla micro-gancho)."
                if i < len(semillas) - 1 else ""
            ),
        )
        segmentos.append(seg)

    # Completa hasta el piso de segmentos para garantizar arco (apertura/nudo/cierre).
    j = len(segmentos)
    while len(segmentos) < segmentos_min:
        segmentos.append(Segmento(
            titulo=f"Segmento {j + 1}",
            guia=f"(vacío) desarrolla otro ángulo de «{tema}».",
            open_loop=None,
            transicion_microgancho="",
        ))
        j += 1

    cierre = (
        f"Cierra resolviendo el bucle del gancho sobre «{tema}» (paga la "
        f"promesa) y deja una idea memorable final."
    )
    cta = "Invita a suscribirse / al siguiente video, ligado al tema (no genérico)."

    return Guion(
        titulo=tema,
        plataforma=plataforma,
        gancho=gancho,
        promesa=promesa,
        segmentos=segmentos,
        cierre=cierre,
        cta=cta,
        fuente_nota=nota.ruta,
    )


# ── análisis de retención (r.47, formato podcast) ───────────────────────────
_MARCA_OPEN_LOOP = re.compile(
    r"\b(pero antes|más adelante|lo veremos|te lo cuento|en un momento|"
    r"al final|espera|guarda esta|¿por qué|¿qué pasó|¿cómo|¿sabías|"
    r"lo que nadie|el secreto|hay un problema|aquí viene lo bueno)\b",
    re.IGNORECASE,
)
_MARCA_TRANSICION = re.compile(
    r"\b(ahora|pero primero|antes de|pasemos a|lo siguiente|sigamos|"
    r"volvamos|recapitulando|hasta aquí|resumiendo|dicho esto|y entonces)\b",
    re.IGNORECASE,
)
_MARCA_CTA = re.compile(
    r"\b(suscr\w+|dale like|comenta|comparte|activa la campana|"
    r"sígueme|siguiente video|no te pierdas)\b", re.IGNORECASE,
)


def _palabras(texto: str) -> int:
    return len([w for w in re.findall(r"\w+", texto, re.UNICODE)])


def analizar_retencion(guion: Guion, ppm: int = REGLAS_RETENCION["ppm_habla"]
                       ) -> AnalisisRetencion:
    """Puntúa la retención del BORRADOR del guion contra las reglas ancladas.

    Si no hay borrador (solo el andamiaje), analiza el texto de las guías —
    útil para verificar que el esqueleto ya cubre las partes obligatorias.
    Todo es medible (r.91): duración, #open-loops, #transiciones, payoff.
    """
    texto = guion.borrador
    solo_andamiaje = texto is None
    if solo_andamiaje:
        # concatena las guías del esqueleto para chequear cobertura estructural
        partes = [guion.gancho, guion.promesa]
        for s in guion.segmentos:
            partes += [s.guia, s.open_loop or "", s.transicion_microgancho]
        partes += [guion.cierre, guion.cta]
        texto = "\n".join(p for p in partes if p)

    palabras = _palabras(texto)
    duracion = round(palabras / ppm, 1) if ppm else 0.0

    # gancho: ¿hay contenido de gancho y cabe en los primeros ~15s?
    gancho_palabras = _palabras(guion.gancho)
    gancho_ok = bool(guion.gancho.strip()) and (
        gancho_palabras <= REGLAS_RETENCION["gancho_primeras_palabras"] or solo_andamiaje
    )

    # open loops: marcas explícitas en el borrador + los declarados en segmentos
    loops_texto = len(_MARCA_OPEN_LOOP.findall(texto))
    loops_declarados = sum(1 for s in guion.segmentos if s.open_loop)
    open_loops = max(loops_texto, loops_declarados)

    payoff_resuelve = bool(guion.promesa.strip()) and bool(guion.cierre.strip())

    transiciones = max(
        len(_MARCA_TRANSICION.findall(texto)),
        sum(1 for s in guion.segmentos if s.transicion_microgancho),
    )
    cta_presente = bool(_MARCA_CTA.search(texto)) or bool(guion.cta.strip())
    n_segmentos = len(guion.segmentos)

    # ── puntaje: cada regla suma; 100 = cumple todo ──────────────────────────
    puntaje = 0
    recomendaciones: list[str] = []

    if gancho_ok:
        puntaje += 25
    else:
        recomendaciones.append(
            f"Gancho: {gancho_palabras} palabras > "
            f"{REGLAS_RETENCION['gancho_primeras_palabras']}; recórtalo para que "
            f"entre en los primeros ~15s (tras 15s sin gancho la retención cae <45%)."
        )

    if open_loops >= REGLAS_RETENCION["open_loops_min"]:
        puntaje += 25
    else:
        recomendaciones.append(
            "Sin bucles abiertos: agrega ≥1 open-loop (pregunta/tensión que se "
            "resuelve después) — sube el watch time ~32%."
        )

    if payoff_resuelve:
        puntaje += 20
    else:
        recomendaciones.append(
            "Falta que el cierre PAGUE la promesa del gancho: escribe gancho y "
            "payoff juntos y que el cierre cierre ese bucle."
        )

    if transiciones >= max(0, n_segmentos - 1) and n_segmentos > 1:
        puntaje += 15
    else:
        recomendaciones.append(
            f"Transiciones-microgancho: hay {transiciones} para {n_segmentos} "
            f"segmentos; cada cambio de tema es un punto de fuga, resúmelo y "
            f"anticipa el siguiente."
        )

    if n_segmentos >= REGLAS_RETENCION["segmentos_desarrollo_min"]:
        puntaje += 10
    else:
        recomendaciones.append(
            f"Solo {n_segmentos} segmentos: el arco narrativo pide ≥"
            f"{REGLAS_RETENCION['segmentos_desarrollo_min']} (apertura/nudo/cierre)."
        )

    if cta_presente:
        puntaje += 5
    else:
        recomendaciones.append("Agrega un CTA ligado al tema, no genérico.")

    return AnalisisRetencion(
        puntaje=puntaje,
        duracion_estimada_min=duracion,
        palabras=palabras,
        gancho_ok=gancho_ok,
        open_loops=open_loops,
        payoff_resuelve_gancho=payoff_resuelve,
        transiciones_microgancho=transiciones,
        segmentos_desarrollo=n_segmentos,
        cta_presente=cta_presente,
        recomendaciones=recomendaciones,
    )


# ── render legible ──────────────────────────────────────────────────────────
def guion_a_markdown(guion: Guion, analisis: Optional[AnalisisRetencion] = None) -> str:
    """El esqueleto como Markdown que Arturo puede abrir y rellenar."""
    L = [f"# Guion — {guion.titulo}", ""]
    if guion.fuente_nota:
        L.append(f"> Fuente: `{guion.fuente_nota}`  ·  Plataforma: {guion.plataforma}")
        L.append("")
    L += ["## 🎣 Gancho (primeros ~15s)", guion.gancho, "",
          "## 🎯 Promesa / payoff", guion.promesa, "", "## 📖 Desarrollo", ""]
    for s in guion.segmentos:
        L.append(f"### {s.titulo}")
        L.append(f"- **Qué contar:** {s.guia}")
        if s.open_loop:
            L.append(f"- **Bucle abierto:** {s.open_loop}")
        if s.transicion_microgancho:
            L.append(f"- **Transición:** {s.transicion_microgancho}")
        L.append("")
    L += ["## 🔚 Cierre", guion.cierre, "", "## 📢 CTA", guion.cta, ""]
    if analisis:
        L += ["---", "## 📊 Análisis de retención",
              f"- Puntaje: **{analisis.puntaje}/100**",
              f"- Duración estimada: ~{analisis.duracion_estimada_min} min "
              f"({analisis.palabras} palabras)",
              f"- Gancho ok: {analisis.gancho_ok} · Open-loops: {analisis.open_loops} "
              f"· Payoff cierra gancho: {analisis.payoff_resuelve_gancho}",
              f"- Transiciones-microgancho: {analisis.transiciones_microgancho} "
              f"· Segmentos: {analisis.segmentos_desarrollo} · CTA: {analisis.cta_presente}"]
        if analisis.recomendaciones:
            L.append("- Mejoras:")
            L += [f"  - {r}" for r in analisis.recomendaciones]
    return "\n".join(L)


# ── registro en la libreta (inyectable, nunca abre la DB solo) ──────────────
def registrar_en_libreta(libreta, guion: Guion,
                         analisis: Optional[AnalisisRetencion] = None,
                         estado: str = "escribiendo") -> int:
    """Inserta el guion en la tabla `guiones`. `libreta` es una Libreta ya
    abierta (dependency injection, mismo patrón que cola_v2/trading): el motor
    no decide entorno ni toca producción por su cuenta.

    Guarda el andamiaje + análisis como JSON en la columna `nota`, para que
    Notion/Hermes lo puedan releer sin re-derivarlo.
    """
    payload = {"guion": json.loads(guion.to_json())}
    if analisis is not None:
        payload["analisis"] = analisis.to_dict()
    cur = libreta.con.execute(
        "INSERT INTO guiones (titulo, plataforma, estado, fecha, nota) "
        "VALUES (?,?,?,?,?)",
        (guion.titulo, guion.plataforma, estado, libreta.hoy(),
         json.dumps(payload, ensure_ascii=False)),
    )
    return cur.lastrowid


# ── CLI ─────────────────────────────────────────────────────────────────────
def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Motor de guiones desde Obsidian (AU-1)")
    p.add_argument("nota", help="ruta a la nota .md de Obsidian")
    p.add_argument("--plataforma", default="youtube")
    p.add_argument("--json", action="store_true", help="salida JSON en vez de Markdown")
    args = p.parse_args(argv)

    nota = parse_nota_archivo(args.nota)
    guion = armar_guion(nota, plataforma=args.plataforma)
    analisis = analizar_retencion(guion)
    if args.json:
        print(json.dumps({"guion": json.loads(guion.to_json()),
                          "analisis": analisis.to_dict()}, ensure_ascii=False, indent=2))
    else:
        print(guion_a_markdown(guion, analisis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
