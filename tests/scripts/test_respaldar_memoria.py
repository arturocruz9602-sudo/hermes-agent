"""Pruebas del respaldo de memoria (HAS §E13, Bloque 2 paso 1).

Cubre el caso que de verdad importa: un respaldo de una DB en modo WAL
que sigue recibiendo escrituras EN VIVO durante la copia debe abrir
limpio y no perder ninguna fila que ya estaba commiteada antes de
empezar -- eso es lo que la Backup API garantiza y `cp` no.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import respaldar_memoria as rm  # noqa: E402


def _make_wal_db(path: Path, n_rows: int) -> None:
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE mensajes (id INTEGER PRIMARY KEY, texto TEXT)")
    con.executemany(
        "INSERT INTO mensajes (texto) VALUES (?)",
        [(f"hecho real {i}",) for i in range(n_rows)],
    )
    con.commit()
    con.close()


def test_backup_and_verify_static_db(tmp_path):
    src = tmp_path / "state.db"
    _make_wal_db(src, n_rows=50)

    dest = tmp_path / "respaldo" / "state.db"
    rm.backup_db(src, dest)

    assert dest.is_file()
    ok, detalles = rm.verify_backup(src, dest)
    assert ok, detalles
    assert any("50/50 filas, OK" in d for d in detalles)

    # El .db restaurado abre y tiene las filas esperadas (HAS §E13-b).
    con = sqlite3.connect(str(dest))
    rows = con.execute("SELECT texto FROM mensajes ORDER BY id").fetchall()
    con.close()
    assert len(rows) == 50
    assert rows[0][0] == "hecho real 0"
    assert rows[-1][0] == "hecho real 49"


def test_verify_backup_flags_missing_table(tmp_path):
    src = tmp_path / "state.db"
    _make_wal_db(src, n_rows=5)

    dest = tmp_path / "respaldo" / "state.db"
    dest.parent.mkdir(parents=True)
    sqlite3.connect(str(dest)).close()  # DB vacía, sin la tabla

    ok, detalles = rm.verify_backup(src, dest)
    assert not ok
    assert any("no existe en el respaldo" in d for d in detalles)


def test_backup_survives_concurrent_writes(tmp_path):
    """El caso real que motiva usar la Backup API en vez de `cp`: el
    gateway sigue escribiendo mientras corre el respaldo nocturno."""
    src = tmp_path / "state.db"
    _make_wal_db(src, n_rows=20)

    stop_writing = threading.Event()
    rows_written = {"count": 20}

    def _writer():
        con = sqlite3.connect(str(src), timeout=5)
        i = 20
        while not stop_writing.is_set():
            con.execute(
                "INSERT INTO mensajes (texto) VALUES (?)", (f"hecho real {i}",)
            )
            con.commit()
            i += 1
            rows_written["count"] = i
            time.sleep(0.01)
        con.close()

    writer_thread = threading.Thread(target=_writer, daemon=True)
    writer_thread.start()
    try:
        time.sleep(0.05)  # deja que el escritor arranque de verdad
        dest = tmp_path / "respaldo" / "state.db"
        rm.backup_db(src, dest)
    finally:
        stop_writing.set()
        writer_thread.join(timeout=5)

    assert dest.is_file()

    # El respaldo debe abrir limpio y nunca tener MÁS filas que el origen
    # final -- verify_backup ya encapsula esa regla.
    ok, detalles = rm.verify_backup(src, dest)
    assert ok, detalles

    con = sqlite3.connect(str(dest))
    (integrity,) = con.execute("PRAGMA integrity_check").fetchone()
    n_dest = con.execute("SELECT COUNT(*) FROM mensajes").fetchone()[0]
    con.close()
    assert integrity == "ok"
    # Debe haber capturado al menos las 20 filas que ya existían antes
    # de que arrancara el escritor concurrente -- ninguna se pierde.
    assert n_dest >= 20
    assert n_dest <= rows_written["count"]


def test_main_cli_backs_up_and_reports(tmp_path, capsys):
    src = tmp_path / "state.db"
    _make_wal_db(src, n_rows=3)
    dest_dir = tmp_path / "destino"

    exit_code = rm.main(["--dest-dir", str(dest_dir), "--db", str(src)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "RESPALDO COMPLETO" in out
    backups = list(dest_dir.glob("*/state.db"))
    assert len(backups) == 1


def test_main_cli_reports_missing_db(tmp_path, capsys):
    missing = tmp_path / "no_existe.db"
    exit_code = rm.main(["--dest-dir", str(tmp_path), "--db", str(missing)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "[FAIL]" in out
    assert "RESPALDO CON PROBLEMAS" in out


def test_main_cli_no_timestamp_usa_dest_dir_tal_cual(tmp_path):
    """--no-timestamp es lo que usa restaurar_hermes.sh para coordinar un
    solo timestamp entre memoria, skills y systemd en la misma corrida."""
    src = tmp_path / "state.db"
    _make_wal_db(src, n_rows=2)
    dest_dir = tmp_path / "corrida_coordinada"

    exit_code = rm.main(
        ["--dest-dir", str(dest_dir), "--db", str(src), "--no-timestamp"]
    )

    assert exit_code == 0
    assert (dest_dir / "state.db").is_file()
    # Sin --no-timestamp habría un subdirectorio extra de timestamp --
    # aquí NO debe haber nada más que el archivo mismo.
    assert list(dest_dir.iterdir()) == [dest_dir / "state.db"]
