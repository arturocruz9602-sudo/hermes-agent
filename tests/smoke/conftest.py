"""Shared fixtures for the HAS Fase 2 / Bloque 4 smoke test suite.

Every smoke test runs against an ISOLATED HERMES_HOME (a fresh temp
directory), never the real ~/.hermes -- HAS's own spec for S2 says
"apuntando a un bot de prueba o modo dry-run", explicitly not
production. This is deliberately a different fixture than
tests/e2e/hermes_harness.py, which drives Arturo's REAL state.db and
REAL identity for manual/scripted review -- wrong tool for an automated
suite that may run repeatedly.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def isolated_hermes_home(monkeypatch):
    """A fresh, empty HERMES_HOME for one smoke test -- built-in defaults,
    zero real credentials, zero real state. Cleaned up after the test."""
    home = tempfile.mkdtemp(prefix="hermes_smoke_")
    hermes_dir = os.path.join(home, ".hermes")
    os.makedirs(hermes_dir)
    monkeypatch.setenv("HERMES_HOME", hermes_dir)
    try:
        yield Path(hermes_dir)
    finally:
        shutil.rmtree(home, ignore_errors=True)
