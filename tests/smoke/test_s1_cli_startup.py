"""S1 (HAS Fase 2, Bloque 4): arranque de CLI.

Verifica que el binario de Hermes (via `python -m hermes_cli.main`) arranca
como proceso real, sin mocks, e imprime algo con forma de version -- no solo
"corrio sin excepcion". Este es el primer smoke test del venv nuevo (0.19.x
rebasado) antes de tocar produccion (HAS Fase 2).
"""

from __future__ import annotations

import re
import subprocess
import sys


def test_cli_version_starts_and_prints_version_string():
    result = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "--version"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"hermes --version salio con codigo {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert re.search(r"\d+\.\d+\.\d+", combined), (
        f"no se encontro un numero de version (X.Y.Z) en la salida: {combined!r}"
    )


def test_cli_help_lists_core_commands():
    result = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"hermes --help salio con codigo {result.returncode}\nstderr: {result.stderr}"
    )
    out = result.stdout
    for cmd in ("gateway", "doctor", "cron"):
        assert cmd in out, f"comando esperado {cmd!r} no aparece en --help"
