from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from gateway.readiness import _probe_disk, collect_runtime_readiness


def test_collect_runtime_readiness_reports_healthy_local_runtime(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        "model:\n  provider: openrouter\n  model: test/model\n",
        encoding="utf-8",
    )
    with sqlite3.connect(home / "state.db") as conn:
        conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
    monkeypatch.setenv("HERMES_HOME", str(home))

    result = collect_runtime_readiness(
        configured_model="test/model",
        runtime_status={
            "gateway_state": "running",
            "platforms": {"telegram": {"state": "connected"}},
            "updated_at": "2026-07-09T00:00:00Z",
        },
        active_api_runs=2,
    )

    assert result["status"] == "ok"
    assert result["checks"]["state_db"]["status"] == "ok"
    assert result["checks"]["config"]["status"] == "ok"
    assert result["checks"]["model"]["status"] == "ok"
    assert result["checks"]["gateway"]["status"] == "ok"
    assert result["checks"]["background_queues"]["active_api_runs"] == 2
    assert result["checks"]["disk"]["status"] in {"ok", "degraded"}


def test_collect_runtime_readiness_degrades_on_invalid_config_and_stopped_gateway(
    tmp_path, monkeypatch
):
    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model: [unterminated", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))

    result = collect_runtime_readiness(
        configured_model="",
        runtime_status={"gateway_state": "stopped", "platforms": {}},
    )

    assert result["status"] == "degraded"
    assert result["checks"]["config"]["status"] == "degraded"
    assert result["checks"]["model"]["status"] == "degraded"
    assert result["checks"]["gateway"]["status"] == "degraded"
    # Readiness is diagnostic data, not an exception or a destructive repair.
    assert (home / "config.yaml").read_text(encoding="utf-8") == "model: [unterminated"


def test_collect_runtime_readiness_marks_corrupt_state_db_degraded(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text("{}\n", encoding="utf-8")
    (home / "state.db").write_bytes(b"not sqlite")
    monkeypatch.setenv("HERMES_HOME", str(home))

    result = collect_runtime_readiness(configured_model="configured-model", runtime_status={})

    assert result["status"] == "degraded"
    assert result["checks"]["state_db"]["status"] == "degraded"
    assert "detail" in result["checks"]["state_db"]


def test_collect_runtime_readiness_never_exposes_config_values(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    secret = "do-not-return-this-value"
    (home / "config.yaml").write_text(
        f"model:\n  provider: openrouter\nprivate_value: {secret}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))

    result = collect_runtime_readiness(configured_model="model", runtime_status={})

    assert secret not in json.dumps(result)
    assert str(home) not in json.dumps(result)
    assert result["checks"]["config"]["status"] == "ok"


def test_collect_runtime_readiness_uses_active_profile_home(tmp_path, monkeypatch):
    profile_home = tmp_path / "profiles" / "coder"
    profile_home.mkdir(parents=True)
    (profile_home / "config.yaml").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(profile_home))

    result = collect_runtime_readiness(configured_model="model", runtime_status={})

    assert result["checks"]["config"]["status"] == "ok"
    assert not (tmp_path / ".hermes" / "state.db").exists()
    assert os.environ["HERMES_HOME"] == str(profile_home)


# HAS GUION_PRUEBAS.md R.10 (disco lleno) -- plan nocturno 30 jul 2026,
# Bloque 8. El caso real (24-25 jul: /tmp lleno tumbo Bash 3 horas) motiva
# probar el umbral de _probe_disk con precision en vez de aceptar "ok o
# degraded" como ya hacia el test de arriba (linea 38, sin control real
# del uso de disco). pyfakefs permite fijar el tamano total del "disco"
# y llenarlo de forma deterministica -- sin arriesgar el disco real de la
# HP, a diferencia de intentar llenar /tmp de verdad.
#
# Alcance real de esta prueba, marcado a proposito: _probe_disk() es un
# probe DE SOLO LECTURA (expuesto via un endpoint de salud) -- reporta
# "degraded" al pasar el umbral, pero NO bloquea escrituras activamente.
# R.10 pide algo mas fuerte ("detecta espacio bajo ANTES de escribir, no
# se corrompe ni pierde datos a medio escribir") -- eso implicaria un
# guard activo en las rutas de escritura reales (state.db, audio/imagen
# cache, etc.), que hoy no existe como mecanismo unificado. Esa brecha de
# diseno queda documentada en docs/ESTADO.md para que Arturo decida su
# prioridad -- esta prueba cierra la parte que SI existe hoy (el umbral
# de deteccion), no inventa un mecanismo de bloqueo que no esta construido.
def test_probe_disk_reports_degraded_when_over_threshold(fs):
    home = Path("/fake_home")
    fs.create_dir(home)
    fs.set_disk_usage(total_size=100_000_000, path=str(home))
    fs.create_file(str(home / "llenador.bin"), st_size=95_000_000)

    result = _probe_disk(home)

    assert result["status"] == "degraded"
    assert result["used_percent"] >= 90.0


def test_probe_disk_reports_ok_when_under_threshold(fs):
    home = Path("/fake_home")
    fs.create_dir(home)
    fs.set_disk_usage(total_size=100_000_000, path=str(home))
    fs.create_file(str(home / "poquito.bin"), st_size=10_000_000)

    result = _probe_disk(home)

    assert result["status"] == "ok"
    assert result["used_percent"] < 90.0
