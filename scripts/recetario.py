#!/usr/bin/env python3
"""
recetario.py — Biblioteca de soluciones (HAS §F10, `docs/recetario/`).

Una receta = un problema real ya resuelto, en formato reusable, para
que la próxima vez que aparezca algo parecido no haya que razonarlo
desde cero. El formato exacto (front-matter + 5 secciones) está
descrito en `docs/recetario/README.md`; este módulo es el candado que
lo hace cumplir y la puerta que Hermes usa para consultarlo.

Tres operaciones, las tres piezas del ciclo de F10:

    buscar(consulta)     — Hermes consulta ANTES de razonar desde cero
                            (F10-b). CLI: `recetario.py buscar "texto"`.
    validar_receta(ruta) — candado de formato; usado por nueva_receta()
                            y por la prueba de humo de cierre de sesión.
    nueva_receta(...)    — obligación de cierre de Claude (F10-a) y de
                            Hermes cuando resuelve algo nuevo (F10-c);
                            no escribe nada que no pase validar primero.

USO
    from recetario import buscar, nueva_receta, validar_todas

    for ruta, score in buscar("telethon phone code expired"):
        print(ruta.name, score)

    nueva_receta(
        autor="claude-code", nombre="mi-problema-nuevo",
        sintoma_corto="...", componente="...",
        sintoma="...", diagnostico="...", solucion="...",
        verificacion="...", cuando_no_aplica="...",
    )
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIR_RECETARIO = REPO_ROOT / "docs" / "recetario"

SECCIONES_REQUERIDAS = [
    "Síntoma",
    "Diagnóstico",
    "Solución paso a paso",
    "Verificación",
    "Cuándo NO aplica",
]

CAMPOS_FRONTMATTER_REQUERIDOS = ["fecha", "autor", "sintoma_corto", "componente"]
AUTORES_VALIDOS = {"claude-code", "hermes"}

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_PALABRA_RE = re.compile(r"\w+", re.UNICODE)


class RecetaInvalida(ValueError):
    """Front-matter o secciones no cumplen el formato de docs/recetario/README.md."""


@dataclass
class Receta:
    ruta: Path
    frontmatter: dict
    cuerpo: str

    @property
    def nombre(self) -> str:
        return self.ruta.stem


def _parsear_frontmatter(texto: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(texto)
    if not m:
        raise RecetaInvalida("falta front-matter YAML delimitado por '---' al inicio del archivo")
    datos: dict[str, str] = {}
    for linea in m.group(1).splitlines():
        if not linea.strip():
            continue
        if ":" not in linea:
            raise RecetaInvalida(f"línea de front-matter sin ':': {linea!r}")
        clave, _, valor = linea.partition(":")
        datos[clave.strip()] = valor.strip()
    return datos, texto[m.end():]


def cargar_receta(ruta: Path) -> Receta:
    frontmatter, cuerpo = _parsear_frontmatter(ruta.read_text(encoding="utf-8"))
    return Receta(ruta=ruta, frontmatter=frontmatter, cuerpo=cuerpo)


def _validar_frontmatter_y_cuerpo(frontmatter: dict, cuerpo: str, nombre_archivo: str) -> list[str]:
    problemas = []

    for campo in CAMPOS_FRONTMATTER_REQUERIDOS:
        if not frontmatter.get(campo):
            problemas.append(f"falta '{campo}' en el front-matter (o está vacío)")

    autor = frontmatter.get("autor")
    if autor and autor not in AUTORES_VALIDOS:
        problemas.append(f"autor {autor!r} no es válido (debe ser 'claude-code' o 'hermes')")

    fecha = frontmatter.get("fecha")
    if fecha:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            problemas.append(f"fecha {fecha!r} no tiene formato AAAA-MM-DD")

    posiciones = {seccion: cuerpo.find(f"## {seccion}") for seccion in SECCIONES_REQUERIDAS}
    for seccion, pos in posiciones.items():
        if pos == -1:
            problemas.append(f"falta la sección '## {seccion}'")

    if all(p != -1 for p in posiciones.values()):
        orden_encontrado = sorted(posiciones, key=lambda s: posiciones[s])
        if orden_encontrado != SECCIONES_REQUERIDAS:
            problemas.append(
                "las secciones no están en el orden esperado "
                "(Síntoma → Diagnóstico → Solución paso a paso → Verificación → Cuándo NO aplica)"
            )

    if nombre_archivo.startswith("receta-") or nombre_archivo.startswith("receta_"):
        problemas.append("nombre de archivo no descriptivo (usar kebab-case del síntoma, no 'receta-N')")

    return problemas


def validar_receta(ruta: Path) -> list[str]:
    """Devuelve la lista de problemas encontrados en una receta (vacía = válida)."""
    try:
        receta = cargar_receta(ruta)
    except RecetaInvalida as e:
        return [str(e)]
    return _validar_frontmatter_y_cuerpo(receta.frontmatter, receta.cuerpo, ruta.stem)


def listar_recetas() -> list[Path]:
    if not DIR_RECETARIO.is_dir():
        return []
    return sorted(p for p in DIR_RECETARIO.glob("*.md") if p.name != "README.md")


def validar_todas() -> dict[str, list[str]]:
    """Valida todo `docs/recetario/*.md` (menos README). Solo entradas con problemas."""
    resultado = {}
    for ruta in listar_recetas():
        problemas = validar_receta(ruta)
        if problemas:
            resultado[ruta.name] = problemas
    return resultado


def _texto_buscable(receta: Receta) -> str:
    return " ".join([
        receta.frontmatter.get("sintoma_corto", ""),
        receta.frontmatter.get("componente", ""),
        receta.cuerpo,
    ]).lower()


def buscar(consulta: str, limite: int = 5) -> list[tuple[Path, int]]:
    """Busca recetas por palabras clave (F10-b: consultar ANTES de razonar
    desde cero). Recetas con front-matter roto se ignoran en silencio aquí
    -- `validar_todas()` es quien las reporta como problema de formato.

    Devuelve [(ruta, score), ...] ordenado por score descendente; score=0
    nunca aparece (sin coincidencia = fuera de la lista, no al final).
    """
    palabras = [p for p in _PALABRA_RE.findall(consulta.lower()) if len(p) > 2]
    if not palabras:
        return []
    resultados = []
    for ruta in listar_recetas():
        try:
            receta = cargar_receta(ruta)
        except RecetaInvalida:
            continue
        texto = _texto_buscable(receta)
        score = sum(texto.count(palabra) for palabra in palabras)
        if score > 0:
            resultados.append((ruta, score))
    resultados.sort(key=lambda par: par[1], reverse=True)
    return resultados[:limite]


def nueva_receta(
    *,
    autor: str,
    nombre: str,
    sintoma_corto: str,
    componente: str,
    sintoma: str,
    diagnostico: str,
    solucion: str,
    verificacion: str,
    cuando_no_aplica: str,
    fecha: str | None = None,
) -> Path:
    """Escribe una receta nueva ya validada (obligación de cierre F10-a/c).

    Nunca escribe un archivo que no pase `validar_receta` -- si algo
    falta, lanza `RecetaInvalida` antes de tocar disco.
    """
    fecha = fecha or date.today().isoformat()
    frontmatter = {
        "fecha": fecha,
        "autor": autor,
        "sintoma_corto": sintoma_corto,
        "componente": componente,
    }
    cuerpo = (
        f"\n## Síntoma\n\n{sintoma}\n\n"
        f"## Diagnóstico\n\n{diagnostico}\n\n"
        f"## Solución paso a paso\n\n{solucion}\n\n"
        f"## Verificación\n\n{verificacion}\n\n"
        f"## Cuándo NO aplica\n\n{cuando_no_aplica}\n"
    )
    problemas = _validar_frontmatter_y_cuerpo(frontmatter, cuerpo, nombre)
    if problemas:
        raise RecetaInvalida("; ".join(problemas))

    ruta = DIR_RECETARIO / f"{nombre}.md"
    if ruta.exists():
        raise RecetaInvalida(f"ya existe una receta en {ruta}")

    contenido_frontmatter = "---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido_frontmatter + cuerpo, encoding="utf-8")
    return ruta


def _leer_campo(valor: str | None, archivo: str | None) -> str:
    if archivo:
        return Path(archivo).read_text(encoding="utf-8").strip()
    return (valor or "").strip()


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recetario de soluciones (HAS §F10)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_buscar = sub.add_parser("buscar", help="consultar el recetario antes de razonar desde cero")
    p_buscar.add_argument("consulta")
    p_buscar.add_argument("--limite", type=int, default=5)

    p_validar = sub.add_parser("validar", help="validar el formato de una o todas las recetas")
    p_validar.add_argument("archivos", nargs="*", help="rutas específicas; sin argumentos = todas")

    p_nueva = sub.add_parser("nueva", help="crear una receta nueva ya validada")
    p_nueva.add_argument("--nombre", required=True)
    p_nueva.add_argument("--autor", required=True, choices=sorted(AUTORES_VALIDOS))
    p_nueva.add_argument("--sintoma-corto", required=True)
    p_nueva.add_argument("--componente", required=True)
    p_nueva.add_argument("--fecha")
    for campo in ("sintoma", "diagnostico", "solucion", "verificacion", "cuando-no-aplica"):
        p_nueva.add_argument(f"--{campo}")
        p_nueva.add_argument(f"--{campo}-archivo")

    args = parser.parse_args(argv)

    if args.comando == "buscar":
        resultados = buscar(args.consulta, limite=args.limite)
        if not resultados:
            print(f"Sin coincidencias en el recetario para: {args.consulta!r}")
            return 0
        for ruta, score in resultados:
            print(f"{score:3d}  {ruta.relative_to(REPO_ROOT)}")
        return 0

    if args.comando == "validar":
        rutas = [Path(a) for a in args.archivos] if args.archivos else listar_recetas()
        hubo_problemas = False
        for ruta in rutas:
            problemas = validar_receta(ruta)
            if problemas:
                hubo_problemas = True
                print(f"{ruta.name}:")
                for p in problemas:
                    print(f"  - {p}")
            else:
                print(f"{ruta.name}: OK")
        return 1 if hubo_problemas else 0

    if args.comando == "nueva":
        try:
            ruta = nueva_receta(
                autor=args.autor,
                nombre=args.nombre,
                sintoma_corto=args.sintoma_corto,
                componente=args.componente,
                fecha=args.fecha,
                sintoma=_leer_campo(args.sintoma, args.sintoma_archivo),
                diagnostico=_leer_campo(args.diagnostico, args.diagnostico_archivo),
                solucion=_leer_campo(args.solucion, args.solucion_archivo),
                verificacion=_leer_campo(args.verificacion, args.verificacion_archivo),
                cuando_no_aplica=_leer_campo(args.cuando_no_aplica, args.cuando_no_aplica_archivo),
            )
        except RecetaInvalida as e:
            print(f"No se creó la receta: {e}", file=sys.stderr)
            return 1
        print(f"Receta creada: {ruta.relative_to(REPO_ROOT)}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
