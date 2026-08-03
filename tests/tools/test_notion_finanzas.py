"""Vista "Finanzas" en Notion (tools/notion_finanzas.py, HAS Fase 5 OT-5
Bloque 2, Bloque F5-1 "Tablero único" -- 02 ago 2026) -- mismo patrón de
pruebas que tests/tools/test_notion_avance_has.py: Notion mockeado contra
_notion_request, la libreta es real pero aislada en tmp_path (mismo
fixture ``entorno`` de tests/scripts/test_libreta.py, para no reinventar
el aislamiento real/simulación).
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import libreta as libreta_mod  # noqa: E402

from tools import notion_finanzas as nf  # noqa: E402


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_DISCO_PRUEBAS", str(tmp_path / "externo"))
    monkeypatch.delenv("HERMES_FECHA_SIMULADA", raising=False)
    monkeypatch.delenv("HERMES_ENTORNO", raising=False)
    (tmp_path / "externo").mkdir(parents=True, exist_ok=True)
    importlib.reload(libreta_mod)
    monkeypatch.setattr(libreta_mod, "_verificar_disco_de_pruebas", lambda: None)

    entorno_hijo = {"HOME": str(tmp_path), "HERMES_HOME": str(tmp_path),
                    "HERMES_DISCO_PRUEBAS": str(tmp_path / "externo"),
                    "PATH": "/usr/bin:/bin"}
    for ent in ("real", "simulacion"):
        r = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "libreta_migrar.py"),
             "--entorno", ent],
            capture_output=True, text=True, env=entorno_hijo,
        )
        assert r.returncode == 0, r.stderr
    yield dict(libreta_mod.RUTAS)
    importlib.reload(libreta_mod)


@pytest.fixture(autouse=True)
def _clean_notion_cache(monkeypatch, tmp_path):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.setattr(nf, "_PAGE_ID_CACHE_PATH", tmp_path / "finanzas_page_id")


def _fake_search_result(title: str) -> dict:
    return {
        "results": [
            {
                "id": "3acc1df3-4107-8033-899f-f7a7c3c8ef76",
                "object": "page",
                "properties": {"title": {"title": [{"plain_text": title}]}},
            }
        ]
    }


def test_missing_api_key_is_fail_safe_not_fatal(entorno):
    result = nf.sync_finanzas(entorno="real")
    assert result["success"] is False
    assert "NOTION_API_KEY" in result["error"]


def test_read_libreta_snapshot_reflects_real_movements(entorno):
    # La migración v4 (Bloque AR) ya siembra "capital_principal" y los
    # pagos recurrentes reconciliados (gym, gasolina, etc.) en toda BD
    # migrada -- por eso no arrancan en cero (ver docs/DECISIONES.md,
    # "la migración v4 NO se edita tras aplicarse").
    with libreta_mod.Libreta("real") as lib:
        lib.registrar_ingreso(1000, "chamba")
        lib.registrar_gasto(150, "comida")
        lib.registrar_gasto(50, "comida")
        lib.abonar_meta("capital_principal", 500)
        lib.registrar_pago_recurrente("renta_coworking", 300, frecuencia_meses=1)

    snapshot = nf._read_libreta_snapshot("real")
    assert snapshot["balance"]["ingresos"] == 1000
    assert snapshot["balance"]["gastos"] == 200
    assert snapshot["balance"]["saldo"] == 800
    categorias = {c["categoria"]: c["total"] for c in snapshot["categorias"]}
    assert categorias["comida"] == 200
    metas_por_nombre = {m["nombre"]: m for m in snapshot["metas"]}
    assert metas_por_nombre["capital_principal"]["acumulado_mxn"] == 500
    # Sin ultimo_pago -> se reporta igual (es la señal de "falta
    # confirmar día de pago", no se filtra como en el brief de audio).
    pagos_por_nombre = {p["nombre"]: p for p in snapshot["pagos"]}
    assert pagos_por_nombre["renta_coworking"]["proximo_pago"] is None


def test_build_blocks_reports_zero_state_without_crashing(entorno):
    snapshot = nf._read_libreta_snapshot("real")
    blocks = nf._build_blocks(snapshot)
    assert len(blocks) <= nf._BLOCK_COUNT_LIMIT
    texto = " ".join(
        b[b["type"]]["rich_text"][0]["text"]["content"]
        for b in blocks if "rich_text" in b.get(b["type"], {})
    )
    # Sin movimientos propios: gastos en cero, pero metas/pagos vienen de
    # la siembra base de la migración v4 (nunca están vacíos de verdad).
    assert "Sin gastos registrados" in texto
    assert "capital_principal" in texto
    assert "por confirmar" in texto  # los 6 recurrentes sembrados sin ultimo_pago


def test_build_blocks_reports_empty_metas_and_pagos_explicitly():
    snapshot = {
        "balance": {"desde": "2026-08-01", "hasta": "2026-08-03",
                    "ingresos": 0, "gastos": 0, "saldo": 0},
        "categorias": [], "pagos": [], "metas": [],
    }
    blocks = nf._build_blocks(snapshot)
    texto = " ".join(
        b[b["type"]]["rich_text"][0]["text"]["content"]
        for b in blocks if "rich_text" in b.get(b["type"], {})
    )
    assert "Sin metas activas" in texto
    assert "Ningún pago recurrente activo" in texto


def test_sync_creates_page_once_then_caches_id(entorno):
    with libreta_mod.Libreta("real") as lib:
        lib.registrar_gasto(50, "comida")

    calls = []

    def fake_request(method, path, payload=None, timeout=15):
        calls.append((method, path, payload))
        if path == "search":
            return _fake_search_result("Hermes")
        if path == "pages":
            return {"id": "page-fin-1"}
        if path.startswith("blocks/") and "/children" in path:
            return {"results": []}
        raise AssertionError(f"unexpected path {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request), \
         patch.dict("os.environ", {"NOTION_API_KEY": "secret_fake"}):
        result = nf.sync_finanzas(entorno="real")

    assert result["success"] is True
    assert result["page_id"] == "page-fin-1"
    page_creates = [c for c in calls if c[1] == "pages"]
    assert len(page_creates) == 1

    calls.clear()
    with patch("tools.notion_mirror._notion_request", side_effect=fake_request), \
         patch.dict("os.environ", {"NOTION_API_KEY": "secret_fake"}):
        result2 = nf.sync_finanzas(entorno="real")
    assert result2["success"] is True
    assert not [c for c in calls if c[1] in ("search", "pages")]


def test_sync_clears_existing_blocks_before_appending_new(entorno):
    nf._save_cached_page_id("page-fin-ya-existe")
    deleted = []
    appended = []

    def fake_request(method, path, payload=None, timeout=15):
        if path == "blocks/page-fin-ya-existe/children?page_size=100":
            return {"results": [{"id": "old-block-1"}]}
        if method == "DELETE" and path.startswith("blocks/old-block"):
            deleted.append(path)
            return {}
        if method == "PATCH" and path == "blocks/page-fin-ya-existe/children":
            appended.append(payload)
            return {}
        raise AssertionError(f"unexpected call {method} {path}")

    with patch("tools.notion_mirror._notion_request", side_effect=fake_request), \
         patch.dict("os.environ", {"NOTION_API_KEY": "secret_fake"}):
        result = nf.sync_finanzas(entorno="real")

    assert result["success"] is True
    assert len(deleted) == 1
    assert len(appended) == 1
    assert len(appended[0]["children"]) >= 1


def test_libreta_missing_is_fail_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "secret_fake")
    monkeypatch.setattr(libreta_mod, "RUTAS", {"real": tmp_path / "no-existe.db"})
    result = nf.sync_finanzas(entorno="real")
    assert result["success"] is False
