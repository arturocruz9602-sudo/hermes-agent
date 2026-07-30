#!/usr/bin/env python3
"""Respaldo consistente de las bases de memoria de Hermes (HAS §E13, paso 1/5).

Usa la Backup API de ``sqlite3`` (nunca ``cp``): en modo WAL, copiar el
archivo directo puede dejar fuera escrituras recientes que siguen en
``state.db-wal``, o dejar una copia inconsistente si el gateway escribe
a mitad de la copia. La Backup API produce un snapshot consistente
página por página aunque el origen siga recibiendo escrituras en vivo.
Investigado en el plan nocturno del 29-30 jul 2026 (ver docs/ESTADO.md,
Bloque 2) -- fuentes: sqlite.org/wal.html, oldmoe.blog backup strategies.

Uso:
    python3 scripts/respaldar_memoria.py [--dest-dir RUTA] [--db RUTA ...]

Por defecto respalda ``state.db`` y ``memoria_semantica.db`` de
``HERMES_HOME`` hacia un subdirectorio con timestamp dentro de
``--dest-dir`` (default: ``/mnt/seagate/hermes_backups``). Cada respaldo
se verifica: abre en modo lectura, corre ``PRAGMA integrity_check``, y
compara el conteo de filas por tabla contra el origen (el respaldo puede
tener MENOS filas que el origen si el origen siguió escribiendo durante
el respaldo -- eso es esperado bajo carga real; MÁS filas que el origen
sí sería un error real).

Este script es el paso 1/5 de HAS §E13 (respaldo de memoria solamente).
Bóveda de llaves (age), skills/índices, y timers/servicios systemd
quedan para los siguientes pasos antes de ensamblar
``restaurar_hermes.sh`` completo -- ver docs/ESTADO.md para el plan.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

HERMES_HOME = Path(os.getenv("HERMES_HOME", str(Path.home() / ".hermes")))
DEFAULT_DEST = Path("/mnt/seagate/hermes_backups")
DEFAULT_DB_NAMES = ("state.db", "memoria_semantica.db")

# Copiar en trozos chicos (no todo en un solo `backup()` sin pausas) para
# que la Backup API reintente sola si choca con un escritor activo
# (SQLITE_BUSY) en vez de fallar de inmediato -- el patrón recomendado
# para respaldar una DB SQLite que sigue en uso.
_BACKUP_PAGES_PER_STEP = 1024
_BACKUP_SLEEP_SECS = 0.25


def _connect(path: Path) -> sqlite3.Connection:
    """Conecta y, si está disponible, carga la extensión sqlite-vec.

    ``memoria_semantica.db`` usa una tabla virtual ``vec0`` (búsqueda
    semántica, ``agent/memory_semantic.py``) que una conexión sin la
    extensión no puede ni siquiera contar filas. Cargarla es inofensivo
    para DBs que no la usan (``state.db``) -- mismo patrón que ya usa
    ``agent/memory_semantic.py::_connect``. Si ``sqlite_vec`` no está
    instalado, se sigue sin ella (afecta solo a la verificación de
    tablas vec0, no al respaldo en sí -- la Backup API copia páginas,
    no depende de que el módulo de la tabla virtual esté cargado).
    """
    con = sqlite3.connect(str(path))
    try:
        import sqlite_vec

        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
    except ImportError:
        pass
    return con


def backup_db(src: Path, dest: Path) -> None:
    """Copia consistente de *src* a *dest* vía la Backup API de sqlite3."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_con = sqlite3.connect(str(src))
    try:
        dest_con = sqlite3.connect(str(dest))
        try:
            src_con.backup(
                dest_con,
                pages=_BACKUP_PAGES_PER_STEP,
                sleep=_BACKUP_SLEEP_SECS,
            )
        finally:
            dest_con.close()
    finally:
        src_con.close()


def _table_names(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [r[0] for r in rows]


def verify_backup(src: Path, dest: Path) -> tuple[bool, list[str]]:
    """Verifica que *dest* abre, pasa integrity_check, y tiene las filas
    esperadas frente a *src* (mismo conteo o menos por tabla -- nunca más).

    Regresa ``(ok, detalles)`` -- ``detalles`` siempre se llena, pase o
    falle (silencio nunca es un estado válido de fallo, HAS L14).
    """
    detalles: list[str] = []
    ok = True

    dest_con = _connect(dest)
    try:
        (integrity,) = dest_con.execute("PRAGMA integrity_check").fetchone()
        if integrity != "ok":
            ok = False
            detalles.append(f"integrity_check falló: {integrity}")
        else:
            detalles.append("integrity_check: ok")

        src_con = _connect(src)
        try:
            for tabla in _table_names(src_con):
                (n_src,) = src_con.execute(
                    f'SELECT COUNT(*) FROM "{tabla}"'
                ).fetchone()
                try:
                    (n_dest,) = dest_con.execute(
                        f'SELECT COUNT(*) FROM "{tabla}"'
                    ).fetchone()
                except sqlite3.OperationalError as exc:
                    ok = False
                    detalles.append(
                        f"tabla {tabla}: no existe en el respaldo ({exc})"
                    )
                    continue
                if n_dest > n_src:
                    ok = False
                    detalles.append(
                        f"tabla {tabla}: respaldo tiene MÁS filas que el "
                        f"origen ({n_dest} > {n_src}) -- inesperado, revisar"
                    )
                elif n_dest < n_src:
                    detalles.append(
                        f"tabla {tabla}: {n_dest}/{n_src} filas (origen "
                        f"siguió escribiendo durante el respaldo, esperado "
                        f"bajo carga real)"
                    )
                else:
                    detalles.append(f"tabla {tabla}: {n_dest}/{n_src} filas, OK")
        finally:
            src_con.close()
    finally:
        dest_con.close()

    return ok, detalles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest-dir", type=Path, default=DEFAULT_DEST)
    parser.add_argument(
        "--db",
        action="append",
        dest="dbs",
        default=None,
        help=(
            "ruta a una DB a respaldar (repetible); default: "
            "state.db + memoria_semantica.db de HERMES_HOME"
        ),
    )
    args = parser.parse_args(argv)

    dbs = (
        [Path(p) for p in args.dbs]
        if args.dbs
        else [HERMES_HOME / n for n in DEFAULT_DB_NAMES]
    )
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest_dir = args.dest_dir / stamp

    resultado_general = True
    for src in dbs:
        if not src.is_file():
            print(f"[FAIL] {src}: no existe, se omite")
            resultado_general = False
            continue
        dest = dest_dir / src.name
        try:
            backup_db(src, dest)
        except Exception as exc:  # noqa: BLE001 - reportar, no tronar el respaldo completo
            print(f"[FAIL] {src} -> {dest}: error durante el respaldo: {exc}")
            resultado_general = False
            continue
        try:
            ok, detalles = verify_backup(src, dest)
        except Exception as exc:  # noqa: BLE001 - reportar, no tronar el resto de la corrida
            print(f"[FAIL] {src} -> {dest}: error durante la verificación: {exc}")
            resultado_general = False
            continue
        estado = "OK" if ok else "FAIL"
        print(f"[{estado}] {src} -> {dest}")
        for d in detalles:
            print(f"        {d}")
        resultado_general = resultado_general and ok

    estado_final = "COMPLETO" if resultado_general else "CON PROBLEMAS"
    print(f"\n=== RESPALDO {estado_final}: {dest_dir} ===")
    return 0 if resultado_general else 1


if __name__ == "__main__":
    raise SystemExit(main())
