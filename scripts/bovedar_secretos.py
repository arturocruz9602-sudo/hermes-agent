#!/usr/bin/env python3
"""Bóveda cifrada de credenciales con `age` (HAS §E13, Bloque 2 paso 2/5).

Por qué `age` y no `gpg`: investigado en el plan nocturno del 29-30 jul
2026 (ver docs/ESTADO.md, Bloque 2) -- `age` es ~100x más simple, sin
servidor de llaves ni modelo de confianza, y `age -p` cifra con una
sola passphrase memorizada por Arturo en vez de un par de llaves que
habría que resguardar por separado. Fuentes: sumguy.com age-vs-gpg,
gerowen.substack.com.

**La passphrase es el único secreto no automatizable, a propósito**
(HAS §E13-a) -- por eso este script NUNCA la acepta como argumento de
línea de comandos (quedaría en el historial de shell y en `ps`) ni la
lee de una variable de entorno o de stdin de este proceso. Siempre deja
que `age` mismo la pida de forma interactiva en la terminal real --
este script solo hereda los descriptores estándar del proceso que lo
invoca, nunca los redirige.

Uso:
    python3 scripts/bovedar_secretos.py cifrar RUTA_ORIGEN [--dest RUTA]
    python3 scripts/bovedar_secretos.py descifrar RUTA_CIFRADA [--dest RUTA]

Requiere `age` instalado (`sudo apt install age` -- ver el prerrequisito
en docs/ESTADO.md). Este script es solo el mecanismo de cifrar/descifrar
un archivo; decidir QUÉ credenciales reales meter a la bóveda (`.env`,
etc.) y dónde vivir el archivo `.age` resultante es un paso aparte,
deliberadamente no automatizado sin que Arturo lo revise primero
(CLAUDE.md: tocar `.env`/credenciales reales siempre se pregunta).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


class AgeNotInstalled(RuntimeError):
    pass


def _require_age() -> None:
    if shutil.which("age") is None:
        raise AgeNotInstalled(
            "age no está instalado -- 'sudo apt install age' (HAS §E13)"
        )


def encrypt_file(src: Path, dest: Path) -> None:
    """Cifra *src* a *dest* con ``age -p``.

    Hereda stdin/stdout/stderr del proceso actual sin tocarlos -- el
    prompt de passphrase de `age` (pide dos veces: escribir + confirmar)
    llega directo a la terminal real de quien lo corre.
    """
    _require_age()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["age", "-p", "-o", str(dest), str(src)], check=True)


def decrypt_file(src: Path, dest: Path) -> None:
    """Descifra *src* a *dest* con ``age -d``. Misma política de
    passphrase interactiva que :func:`encrypt_file` (una sola vez)."""
    _require_age()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["age", "-d", "-o", str(dest), str(src)], check=True)


def _default_encrypted_dest(origen: Path) -> Path:
    return origen.with_name(origen.name + ".age")


def _default_decrypted_dest(origen: Path) -> Path:
    if origen.suffix == ".age":
        return origen.with_suffix("")
    return origen.with_name(origen.name + ".descifrado")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="accion", required=True)

    p_cifrar = sub.add_parser("cifrar", help="cifra un archivo con age -p")
    p_cifrar.add_argument("origen", type=Path)
    p_cifrar.add_argument("--dest", type=Path, default=None)

    p_descifrar = sub.add_parser("descifrar", help="descifra un archivo .age")
    p_descifrar.add_argument("origen", type=Path)
    p_descifrar.add_argument("--dest", type=Path, default=None)

    args = parser.parse_args(argv)

    if args.accion == "cifrar":
        dest = args.dest or _default_encrypted_dest(args.origen)
        try:
            encrypt_file(args.origen, dest)
        except subprocess.CalledProcessError:
            print(f"[FAIL] cifrado de {args.origen} falló", file=sys.stderr)
            return 1
        except AgeNotInstalled as exc:
            print(f"[FAIL] {exc}", file=sys.stderr)
            return 1
        print(f"[OK] {args.origen} -> {dest}")
        return 0

    if args.accion == "descifrar":
        dest = args.dest or _default_decrypted_dest(args.origen)
        try:
            decrypt_file(args.origen, dest)
        except subprocess.CalledProcessError:
            print(
                f"[FAIL] descifrado de {args.origen} falló -- "
                f"¿passphrase correcta?",
                file=sys.stderr,
            )
            return 1
        except AgeNotInstalled as exc:
            print(f"[FAIL] {exc}", file=sys.stderr)
            return 1
        print(f"[OK] {args.origen} -> {dest}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
