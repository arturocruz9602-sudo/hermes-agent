"""Pruebas del lanzador usb_llave/start-linux.sh (HAS §B8 / §OT-11 punto 2).

No hay VeraCrypt/Tailscale/hardware real disponible en esta corrida --
en vez de eso, se inyectan binarios FALSOS por PATH (mismo principio de
"puerto inyectable" que scripts/reglas_recordatorio.py) que registran su
invocación en un log, para verificar el FLUJO real del script:

  (1) exige veracrypt/tailscale/ssh instalados, o falla claro.
  (2) exige que exista la bóveda (`VAULT_FILE`), o falla claro señalando
      que OT-11 punto 1 (particionar el USB) sigue pendiente.
  (3) monta, LEE `config.env` de DENTRO de la bóveda ya montada (nunca de
      la partición sin cifrar), valida las variables obligatorias.
  (4) si tailscale ya está `Running`, NO vuelve a levantarlo; si no, lo
      levanta con el authkey de la bóveda y lo registra para bajarlo al
      salir.
  (5) abre ssh -i <llave-de-la-bóveda> arturo@TARGET -- hermes.
  (6) SIEMPRE limpia al salir (desmonta la bóveda; baja tailscale solo si
      lo levantó él mismo) -- incluso cuando algo falla a medio camino.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "usb_llave" / "start-linux.sh"


def _stub(path: Path, body: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _make_vault(vault_dir: Path, *, con_authkey: bool = False, config_extra: str = "") -> Path:
    """Contenido que el veracrypt-falso "revela" al montar -- simula lo
    que habría DENTRO de la bóveda real ya descifrada."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    (vault_dir / "ssh").mkdir(exist_ok=True)
    llave = vault_dir / "ssh" / "hermes-portable"
    llave.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfalsa\n-----END OPENSSH PRIVATE KEY-----\n")
    config = (
        "HERMES_TS_TARGET=100.101.21.60\n"
        "HERMES_SSH_KEY=ssh/hermes-portable\n"
        + config_extra
    )
    if con_authkey:
        (vault_dir / "tailscale-authkey").write_text("tskey-fake-123\n")
        config += "HERMES_TS_AUTHKEY_FILE=tailscale-authkey\n"
    (vault_dir / "config.env").write_text(config)
    return vault_dir


@pytest.fixture
def entorno(tmp_path):
    """PATH con binarios falsos + rutas de bóveda/mount aisladas.

    El veracrypt falso "monta" copiando `--fake-source` (que apunta al
    contenido preparado por _make_vault) a `$2` -- así el resto del script
    ve exactamente lo que vería con una bóveda real ya descifrada."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "invocaciones.log"

    vault_content = tmp_path / "vault_content_por_defecto"
    _make_vault(vault_content)

    _stub(bin_dir / "veracrypt", f"""
echo "veracrypt $*" >> "{log}"
if [ "$1" = "--text" ] && [ "$2" = "--mount" ]; then
    mkdir -p "$4"
    cp -r "{vault_content}"/. "$4"/
    exit 0
fi
if [ "$1" = "--text" ] && [ "$2" = "--non-interactive" ] && [ "$3" = "--dismount" ]; then
    rm -rf "$4"/*
    exit 0
fi
exit 1
""")

    _stub(bin_dir / "tailscale", f"""
echo "tailscale $*" >> "{log}"
if [ "$1" = "status" ]; then
    echo '{{"BackendState":"'"${{FAKE_TS_STATE:-Running}}"'"}}'
    exit 0
fi
exit 0
""")

    _stub(bin_dir / "ssh", f"""echo "ssh $*" >> "{log}"; exit "${{FAKE_SSH_EXIT:-0}}"\n""")

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["VAULT_FILE"] = str(tmp_path / "hermes-vault.hc")
    env["VAULT_MOUNT"] = str(tmp_path / "mount")
    (tmp_path / "hermes-vault.hc").write_text("contenedor-falso")

    return {"env": env, "log": log, "vault_content": vault_content, "mount": tmp_path / "mount"}


def _run(entorno, extra_env=None):
    env = dict(entorno["env"])
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(_SCRIPT)], env=env, capture_output=True, text=True, timeout=20)


def test_falla_claro_si_falta_un_binario(entorno, tmp_path):
    # PATH sin los stubs -> ningún binario requerido existe.
    env = dict(os.environ)
    env["VAULT_FILE"] = entorno["env"]["VAULT_FILE"]
    env["VAULT_MOUNT"] = entorno["env"]["VAULT_MOUNT"]
    env["PATH"] = "/usr/bin:/bin"  # sin veracrypt real ni el stub
    r = subprocess.run(["bash", str(_SCRIPT)], env=env, capture_output=True, text=True, timeout=20)
    assert r.returncode != 0
    assert "no está instalado" in r.stderr


def test_falla_claro_si_no_existe_la_boveda(entorno, tmp_path):
    os.remove(entorno["env"]["VAULT_FILE"])
    r = _run(entorno)
    assert r.returncode != 0
    assert "OT-11 punto 1" in r.stderr


def test_flujo_completo_tailscale_ya_corriendo(entorno):
    r = _run(entorno, {"FAKE_TS_STATE": "Running"})
    assert r.returncode == 0, r.stderr

    lineas = entorno["log"].read_text().strip().splitlines()
    # monta, consulta status, NO vuelve a levantar tailscale, abre ssh, desmonta.
    assert any(l.startswith("veracrypt --text --mount") for l in lineas)
    assert any(l == "tailscale status --json" for l in lineas)
    assert not any(l.startswith("tailscale up") for l in lineas)
    assert any("ssh -i" in l and "arturo@100.101.21.60" in l and "hermes" in l for l in lineas)
    assert any(l.startswith("veracrypt --text --non-interactive --dismount") for l in lineas)


def test_levanta_tailscale_si_no_estaba_corriendo_y_hay_authkey(entorno):
    vault = entorno["vault_content"]
    import shutil
    shutil.rmtree(vault)
    _make_vault(vault, con_authkey=True)

    r = _run(entorno, {"FAKE_TS_STATE": "NeedsLogin"})
    assert r.returncode == 0, r.stderr
    lineas = entorno["log"].read_text().strip().splitlines()
    assert any(l.startswith("tailscale up --authkey=file:") for l in lineas)
    # como lo levantamos nosotros, la limpieza debe bajarlo:
    assert any(l == "tailscale down" for l in lineas)


def test_sin_tailscale_corriendo_y_sin_authkey_falla_claro(entorno):
    r = _run(entorno, {"FAKE_TS_STATE": "NeedsLogin"})
    assert r.returncode != 0
    assert "tailscale no está corriendo" in r.stderr


def test_config_env_sin_ts_target_falla_claro(entorno):
    vault = entorno["vault_content"]
    (vault / "config.env").write_text("HERMES_SSH_KEY=ssh/hermes-portable\n")
    r = _run(entorno)
    assert r.returncode != 0
    assert "HERMES_TS_TARGET" in r.stderr


def test_siempre_desmonta_aunque_ssh_falle(entorno):
    r = _run(entorno, {"FAKE_SSH_EXIT": "3"})
    assert r.returncode != 0
    lineas = entorno["log"].read_text().strip().splitlines()
    assert any(l.startswith("veracrypt --text --non-interactive --dismount") for l in lineas)
