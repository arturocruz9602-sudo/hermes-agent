"""Pruebas del orquestador restaurar_hermes.sh (HAS §E13, Bloque 2 paso 4).

`respaldar` coordina los 3 pasos ya construidos en un solo timestamp;
`restaurar` deliberadamente NO está implementado todavía y debe fallar
claro en vez de fingir que funciona -- eso también se prueba.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "restaurar_hermes.sh"


def _make_fake_hermes_home(base: Path) -> Path:
    home = base / "hermes_home"
    home.mkdir()

    con = sqlite3.connect(str(home / "state.db"))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE mensajes (id INTEGER PRIMARY KEY, texto TEXT)")
    con.execute("INSERT INTO mensajes (texto) VALUES ('hola')")
    con.commit()
    con.close()

    con = sqlite3.connect(str(home / "memoria_semantica.db"))
    con.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, texto TEXT)")
    con.commit()
    con.close()

    (home / "skills" / "skill-de-prueba").mkdir(parents=True)
    (home / "skills" / "skill-de-prueba" / "SKILL.md").write_text("# prueba\n")

    return home


def _make_fake_units_dir(base: Path) -> Path:
    units = base / "systemd_user"
    units.mkdir()
    (units / "hermes-gateway.service").write_text("[Unit]\n")
    return units


def _run_script(*args: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_restaurar_no_implementado_falla_claro(tmp_path):
    env = {**os.environ}
    result = _run_script("restaurar", env=env)

    assert result.returncode != 0, (
        "restaurar_hermes.sh restaurar NO debe salir con éxito -- "
        "todavía no está implementado, fallar claro es lo correcto"
    )
    assert "SIN IMPLEMENTAR" in result.stdout


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync no disponible")
def test_respaldar_coordina_un_solo_timestamp(tmp_path):
    home = _make_fake_hermes_home(tmp_path)
    units_src = _make_fake_units_dir(tmp_path)
    dest_base = tmp_path / "destino"

    env = {
        **os.environ,
        "HERMES_HOME": str(home),
        "HERMES_PYTHON": sys.executable,
        "HERMES_SYSTEMD_USER_DIR": str(units_src),
    }
    result = _run_script("respaldar", "--dest-dir", str(dest_base), env=env)

    assert result.returncode == 0, result.stdout + result.stderr

    subdirs = [p for p in dest_base.iterdir() if p.is_dir()]
    assert len(subdirs) == 1, (
        f"esperaba UN solo timestamp compartido, encontré: {subdirs}"
    )
    dest = subdirs[0]
    assert (dest / "state.db").is_file()
    assert (dest / "memoria_semantica.db").is_file()
    assert (dest / "skills" / "skill-de-prueba" / "SKILL.md").is_file()
    assert "SKIP" in result.stdout  # sin --con-credenciales, sin bóveda previa
    assert "RESPALDO COMPLETO" in result.stdout


def test_respaldar_reutiliza_credenciales_ya_cifradas_sin_pedir_passphrase(tmp_path):
    """Si ya existe una copia cifrada de .env de una corrida anterior con
    --con-credenciales, una corrida normal (sin esa bandera) la copia
    hacia adelante sin volver a pedir la passphrase -- el .env no cambia
    cada noche, no hace falta molestar a Arturo cada vez."""
    home = _make_fake_hermes_home(tmp_path)
    units_src = _make_fake_units_dir(tmp_path)
    dest_base = tmp_path / "destino"

    boveda_recuperacion = home / "boveda_recuperacion"
    boveda_recuperacion.mkdir()
    (boveda_recuperacion / "env.age").write_bytes(b"contenido-cifrado-de-prueba")

    env = {
        **os.environ,
        "HERMES_HOME": str(home),
        "HERMES_PYTHON": sys.executable,
        "HERMES_SYSTEMD_USER_DIR": str(units_src),
    }
    result = _run_script("respaldar", "--dest-dir", str(dest_base), env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    subdirs = [p for p in dest_base.iterdir() if p.is_dir()]
    assert len(subdirs) == 1
    dest = subdirs[0]
    assert (dest / "env.age").read_bytes() == b"contenido-cifrado-de-prueba"
    assert "sin re-pedir passphrase" in result.stdout
