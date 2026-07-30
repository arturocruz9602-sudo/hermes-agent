"""Pruebas de la bóveda cifrada con age (HAS §E13, Bloque 2 paso 2).

`age -p` solo pide la passphrase por una terminal real (`/dev/tty`),
nunca por stdin de un pipe -- verificado en vivo, ver docs/ESTADO.md.
Por eso estas pruebas manejan el CLI real (`scripts/bovedar_secretos.py`)
dentro de una pseudo-terminal (`pty`) y le escriben la passphrase ahí,
exactamente como Arturo lo haría a mano en su propia terminal -- el
código de producción nunca toca stdin/stdout, solo age.
"""

from __future__ import annotations

import os
import pty
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import bovedar_secretos as bs  # noqa: E402

_SCRIPT = str(
    Path(__file__).resolve().parents[2] / "scripts" / "bovedar_secretos.py"
)

pytestmark = pytest.mark.skipif(
    shutil.which("age") is None, reason="age no está instalado en este entorno"
)


def _run_with_pty(args: list[str], passphrases: list[str], timeout: float = 10.0):
    """Corre `python3 scripts/bovedar_secretos.py <args>` dentro de un pty,
    escribiendo cada passphrase de *passphrases* (una por cada prompt que
    `age` haga, en orden) y regresa (returncode, salida_completa)."""
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        [sys.executable, _SCRIPT, *args],
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)
    try:
        for p in passphrases:
            time.sleep(0.3)
            os.write(master, (p + "\n").encode())

        out = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        proc.wait(timeout=timeout)
    finally:
        try:
            os.close(master)
        except OSError:
            pass
    return proc.returncode, out.decode(errors="replace")


def test_encrypt_decrypt_roundtrip(tmp_path):
    secreto = tmp_path / "credenciales.env"
    secreto.write_text("GEMINI_API_KEY=clave-de-prueba-no-real\n")

    cifrado = tmp_path / "credenciales.env.age"
    code, out = _run_with_pty(
        ["cifrar", str(secreto), "--dest", str(cifrado)],
        passphrases=["passphrase-de-prueba", "passphrase-de-prueba"],
    )
    assert code == 0, out
    assert cifrado.is_file()
    # El cifrado no debe contener el secreto en claro.
    assert b"clave-de-prueba-no-real" not in cifrado.read_bytes()

    descifrado = tmp_path / "credenciales.recuperado.env"
    code, out = _run_with_pty(
        ["descifrar", str(cifrado), "--dest", str(descifrado)],
        passphrases=["passphrase-de-prueba"],
    )
    assert code == 0, out
    assert descifrado.read_text() == "GEMINI_API_KEY=clave-de-prueba-no-real\n"


def test_decrypt_wrong_passphrase_fails(tmp_path):
    secreto = tmp_path / "credenciales.env"
    secreto.write_text("GROQ_API_KEY=otra-clave-de-prueba\n")

    cifrado = tmp_path / "credenciales.env.age"
    code, _ = _run_with_pty(
        ["cifrar", str(secreto), "--dest", str(cifrado)],
        passphrases=["passphrase-correcta", "passphrase-correcta"],
    )
    assert code == 0

    descifrado = tmp_path / "no_deberia_existir.env"
    code, out = _run_with_pty(
        ["descifrar", str(cifrado), "--dest", str(descifrado)],
        passphrases=["passphrase-incorrecta"],
    )
    assert code != 0
    assert not descifrado.exists()


def test_default_destination_names(tmp_path):
    origen = tmp_path / "secreto.txt"
    assert bs._default_encrypted_dest(origen) == tmp_path / "secreto.txt.age"

    cifrado = tmp_path / "secreto.txt.age"
    assert bs._default_decrypted_dest(cifrado) == tmp_path / "secreto.txt"

    sin_sufijo_age = tmp_path / "algo_raro"
    assert (
        bs._default_decrypted_dest(sin_sufijo_age)
        == tmp_path / "algo_raro.descifrado"
    )


def test_age_not_installed_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(bs.shutil, "which", lambda _name: None)
    with pytest.raises(bs.AgeNotInstalled):
        bs.encrypt_file(tmp_path / "a.txt", tmp_path / "a.txt.age")
    with pytest.raises(bs.AgeNotInstalled):
        bs.decrypt_file(tmp_path / "a.txt.age", tmp_path / "a.txt")
