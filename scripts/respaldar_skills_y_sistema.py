#!/usr/bin/env python3
"""Respaldo de skills + timers/servicios systemd (HAS §E13, Bloque 2 paso 3/5).

A diferencia de `state.db`/`memoria_semantica.db` (paso 1, ver
`respaldar_memoria.py`), skills y unidades systemd NO son bases de datos
vivas -- copia directa (`rsync -a`) es segura, sin necesitar la Backup
API. "Índices" (la otra parte del paso 3 original) no tiene archivo
aparte que respaldar: la búsqueda semántica vive DENTRO de
`memoria_semantica.db` (tabla virtual `chunks_vec`,
`agent/memory_semantic.py`), ya cubierta por el paso 1 -- confirmado
revisando el código antes de asumirlo, no hay `.index`/embeddings sueltos
en `HERMES_HOME`.

**Nota importante para no confundir vaults:** `~/.hermes/boveda/
entries.json.enc` (gestionado por `tools/vault_tool.py`, Bloque T, 23
jul 2026) es un mecanismo YA EXISTENTE y separado -- credenciales que
Arturo pide a Hermes recordar en conversación, cifradas con
scrypt+AES-256-GCM en Python puro (no `age`, porque `age` no estaba
instalado cuando se construyó). Es DISTINTO de `bovedar_secretos.py`
(paso 2 de este mismo bloque, para cifrar `.env`/credenciales del
sistema con `age` de cara a la recuperación total). Este script NO
toca `~/.hermes/boveda/` -- ni lo respalda ni escribe ahí, a propósito,
para no mezclar los dos mecanismos hasta que quede una decisión
explícita de Arturo sobre si conviene unificarlos.

Uso:
    python3 scripts/respaldar_skills_y_sistema.py [--dest-dir RUTA]

Por defecto respalda `HERMES_HOME/skills` y las unidades systemd de
usuario relacionadas con Hermes (`hermes-*.service`, `hermes-*.timer`,
`litellm.service`, `media-saver.service`, y el directorio de overrides
`hermes-gateway.service.d/`) hacia un subdirectorio con timestamp
dentro de `--dest-dir` (default: `/mnt/seagate/hermes_backups`).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERMES_HOME = Path(os.getenv("HERMES_HOME", str(Path.home() / ".hermes")))
DEFAULT_DEST = Path("/mnt/seagate/hermes_backups")
SYSTEMD_USER_DIR = Path(
    os.getenv("HERMES_SYSTEMD_USER_DIR", str(Path.home() / ".config" / "systemd" / "user"))
)

# Coincide con lo que ya vive en ~/.config/systemd/user/ en esta HP
# (verificado con `ls` antes de escribir esta lista -- son exactamente
# las unidades relacionadas con Hermes, sin nada ajeno mezclado).
_SYSTEMD_UNIT_GLOBS = (
    "hermes-*.service",
    "hermes-*.timer",
    "litellm.service",
    "media-saver.service",
)
_SYSTEMD_OVERRIDE_DIRS = ("hermes-gateway.service.d",)


def respaldar_skills(dest_dir: Path, skills_src: "Path | None" = None) -> tuple[bool, str]:
    """rsync -a de *skills_src* a ``dest_dir/skills``. Regresa (ok, detalle).

    ``skills_src`` se resuelve en tiempo de llamada (no como default de
    argumento) para que ``HERMES_HOME`` pueda cambiar por invocación
    (variable de entorno, pruebas) sin quedar congelado al importar el
    módulo.
    """
    if skills_src is None:
        skills_src = HERMES_HOME / "skills"
    if not skills_src.is_dir():
        return False, f"no existe: {skills_src}"
    dest = dest_dir / "skills"
    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["rsync", "-a", "--delete", f"{skills_src}/", f"{dest}/"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"rsync exit={result.returncode}: {result.stderr.strip()[:300]}"

    n_src = sum(1 for _ in skills_src.rglob("*") if _.is_file())
    n_dest = sum(1 for _ in dest.rglob("*") if _.is_file())
    if n_dest != n_src:
        return False, f"{n_dest}/{n_src} archivos -- no coincide"
    return True, f"{n_dest}/{n_src} archivos, OK ({dest})"


def respaldar_systemd_units(dest_dir: Path, units_src: "Path | None" = None) -> tuple[bool, list[str]]:
    """Copia las unidades systemd de Hermes (servicios/timers/overrides)
    a ``dest_dir/systemd``. Regresa (ok, detalles). Mismo motivo que
    :func:`respaldar_skills` para resolver el default en tiempo de
    llamada en vez de como default de argumento."""
    if units_src is None:
        units_src = SYSTEMD_USER_DIR
    detalles: list[str] = []
    if not units_src.is_dir():
        return False, [f"no existe: {units_src}"]

    dest = dest_dir / "systemd"
    dest.mkdir(parents=True, exist_ok=True)

    copiados = []
    for patron in _SYSTEMD_UNIT_GLOBS:
        for archivo in sorted(units_src.glob(patron)):
            shutil.copy2(archivo, dest / archivo.name)
            copiados.append(archivo.name)

    for nombre_dir in _SYSTEMD_OVERRIDE_DIRS:
        origen = units_src / nombre_dir
        if origen.is_dir():
            destino = dest / nombre_dir
            shutil.copytree(origen, destino, dirs_exist_ok=True)
            copiados.append(f"{nombre_dir}/ (directorio de overrides)")

    if not copiados:
        return False, [f"ninguna unidad encontrada en {units_src} con los patrones esperados"]

    detalles.append(f"{len(copiados)} unidad(es)/override(s) copiados a {dest}:")
    detalles.extend(f"  - {c}" for c in copiados)
    return True, detalles


# Archivos de configuracion que SI se respaldan: solo traen placeholders
# ${VAR}, nunca el secreto en claro (verificado el 30 jul 2026 --
# `grep -E "(api_key|token|secret|password):" config.yaml` sin `${` = 0
# resultados). Los secretos reales viven en .env y en ~/.hermes/boveda/,
# y ninguno de los dos se toca aqui a proposito (ver nota del encabezado).
_CONFIG_FILES = ("config.yaml", "config.yaml.known-good")


def respaldar_scripts_y_config(
    dest_dir: Path,
    scripts_src: "Path | None" = None,
    config_src: "Path | None" = None,
) -> tuple[bool, list[str]]:
    """Copia ``HERMES_HOME/scripts`` y los config.yaml a *dest_dir*.

    Agregado el 30 jul 2026 tras el incidente del Bloque AH: el watchdog
    sobrescribio config.yaml y no habia respaldo de donde recuperarlo --
    `find /mnt/seagate -name "config.yaml*"` daba 0 resultados, y hubo
    que reconstruirlo a mano desde una copia del 17 jul que ademas era
    YAML invalido. `scripts/` tenia el mismo hueco: 26 scripts de
    produccion (incluido watchdog.sh) sin respaldo ni control de
    versiones.

    Mismo motivo que :func:`respaldar_skills` para resolver los defaults
    en tiempo de llamada y no como default de argumento.
    """
    if scripts_src is None:
        scripts_src = HERMES_HOME / "scripts"
    if config_src is None:
        config_src = HERMES_HOME
    detalles: list[str] = []
    ok = True

    if scripts_src.is_dir():
        dest_scripts = dest_dir / "scripts"
        dest_scripts.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "rsync", "-a", "--delete",
                "--exclude", "__pycache__",
                f"{scripts_src}/", f"{dest_scripts}/",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            ok = False
            detalles.append(f"scripts: rsync exit={result.returncode}: {result.stderr.strip()[:200]}")
        else:
            n = sum(1 for p in dest_scripts.rglob("*") if p.is_file())
            detalles.append(f"scripts: {n} archivo(s) -> {dest_scripts}")
    else:
        ok = False
        detalles.append(f"scripts: no existe {scripts_src}")

    dest_config = dest_dir / "config"
    dest_config.mkdir(parents=True, exist_ok=True)
    copiados = []
    for nombre in _CONFIG_FILES:
        origen = config_src / nombre
        if origen.is_file():
            shutil.copy2(origen, dest_config / nombre)
            copiados.append(nombre)
    if not copiados:
        ok = False
        detalles.append(f"config: ninguno de {_CONFIG_FILES} encontrado en {config_src}")
    else:
        detalles.append(f"config: {', '.join(copiados)} -> {dest_config}")

    return ok, detalles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest-dir", type=Path, default=DEFAULT_DEST)
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help=(
            "usa --dest-dir tal cual, sin agregarle un subdirectorio de "
            "timestamp -- para cuando un orquestador (restaurar_hermes.sh) "
            "ya calculó un timestamp compartido con otros pasos del respaldo"
        ),
    )
    parser.add_argument(
        "--skills-src",
        type=Path,
        default=None,
        help="override de dónde vienen las skills (default: HERMES_HOME/skills)",
    )
    parser.add_argument(
        "--units-src",
        type=Path,
        default=None,
        help="override de dónde viven las unidades systemd de usuario",
    )
    parser.add_argument(
        "--scripts-src",
        type=Path,
        default=None,
        help="override de dónde vienen los scripts (default: HERMES_HOME/scripts)",
    )
    parser.add_argument(
        "--config-src",
        type=Path,
        default=None,
        help="override de dónde vienen los config.yaml (default: HERMES_HOME)",
    )
    args = parser.parse_args(argv)

    if args.no_timestamp:
        dest_dir = args.dest_dir
    else:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dest_dir = args.dest_dir / stamp

    resultado_general = True

    ok_skills, detalle_skills = respaldar_skills(dest_dir, skills_src=args.skills_src)
    print(f"[{'OK' if ok_skills else 'FAIL'}] skills: {detalle_skills}")
    resultado_general = resultado_general and ok_skills

    ok_systemd, detalles_systemd = respaldar_systemd_units(dest_dir, units_src=args.units_src)
    estado_systemd = "OK" if ok_systemd else "FAIL"
    print(f"[{estado_systemd}] systemd:")
    for d in detalles_systemd:
        print(f"        {d}")
    resultado_general = resultado_general and ok_systemd

    ok_sc, detalles_sc = respaldar_scripts_y_config(
        dest_dir, scripts_src=args.scripts_src, config_src=args.config_src,
    )
    print(f"[{'OK' if ok_sc else 'FAIL'}] scripts+config:")
    for d in detalles_sc:
        print(f"        {d}")
    resultado_general = resultado_general and ok_sc

    estado_final = "COMPLETO" if resultado_general else "CON PROBLEMAS"
    print(f"\n=== RESPALDO {estado_final}: {dest_dir} ===")
    return 0 if resultado_general else 1


if __name__ == "__main__":
    raise SystemExit(main())
