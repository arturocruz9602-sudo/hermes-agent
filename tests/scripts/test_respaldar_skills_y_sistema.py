"""Pruebas del respaldo de skills + unidades systemd (HAS §E13, Bloque 2
paso 3). No son bases de datos vivas -- copia directa basta, pero de
todas formas se verifica cuenta de archivos y contenido, no solo que
`rsync`/`copy2` regresaron 0."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import respaldar_skills_y_sistema as rs  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("rsync") is None, reason="rsync no está instalado en este entorno"
)


def _make_fake_skills(base: Path) -> Path:
    skills = base / "skills"
    (skills / "ejemplo-skill").mkdir(parents=True)
    (skills / "ejemplo-skill" / "SKILL.md").write_text("# skill de prueba\n")
    (skills / "otra-skill" / "sub").mkdir(parents=True)
    (skills / "otra-skill" / "sub" / "datos.json").write_text("{}")
    return skills


def test_respaldar_skills_copia_todo(tmp_path):
    skills_src = _make_fake_skills(tmp_path / "origen")
    dest_dir = tmp_path / "destino"

    ok, detalle = rs.respaldar_skills(dest_dir, skills_src=skills_src)

    assert ok, detalle
    assert (dest_dir / "skills" / "ejemplo-skill" / "SKILL.md").read_text() == "# skill de prueba\n"
    assert (dest_dir / "skills" / "otra-skill" / "sub" / "datos.json").is_file()


def test_respaldar_skills_falla_si_no_existe(tmp_path):
    ok, detalle = rs.respaldar_skills(tmp_path / "destino", skills_src=tmp_path / "no_existe")
    assert not ok
    assert "no existe" in detalle


def test_respaldar_systemd_units_copia_solo_lo_esperado(tmp_path):
    units_src = tmp_path / "systemd_user"
    units_src.mkdir()
    (units_src / "hermes-gateway.service").write_text("[Unit]\n")
    (units_src / "hermes-watchdog.timer").write_text("[Timer]\n")
    (units_src / "litellm.service").write_text("[Unit]\n")
    (units_src / "media-saver.service").write_text("[Unit]\n")
    # unidad ajena, no relacionada con Hermes -- NO debe copiarse
    (units_src / "otra-cosa-no-relacionada.service").write_text("[Unit]\n")
    override_dir = units_src / "hermes-gateway.service.d"
    override_dir.mkdir()
    (override_dir / "override.conf").write_text("[Service]\nEnvironment=X=1\n")

    dest_dir = tmp_path / "destino"
    ok, detalles = rs.respaldar_systemd_units(dest_dir, units_src=units_src)

    assert ok, detalles
    dest = dest_dir / "systemd"
    assert (dest / "hermes-gateway.service").is_file()
    assert (dest / "hermes-watchdog.timer").is_file()
    assert (dest / "litellm.service").is_file()
    assert (dest / "media-saver.service").is_file()
    assert (dest / "hermes-gateway.service.d" / "override.conf").read_text() == (
        "[Service]\nEnvironment=X=1\n"
    )
    assert not (dest / "otra-cosa-no-relacionada.service").exists()


def test_respaldar_systemd_units_falla_si_no_existe(tmp_path):
    ok, detalles = rs.respaldar_systemd_units(tmp_path / "destino", units_src=tmp_path / "no_existe")
    assert not ok
    assert any("no existe" in d for d in detalles)


def _add_scripts_y_config(base: Path) -> None:
    """Completa un HERMES_HOME de prueba con scripts/ y config.yaml.

    Desde el 30 jul 2026 main() tambien los respalda y reporta FAIL si
    faltan (Bloque AH), asi que un origen de prueba sin ellos ya no
    representa una instalacion valida.
    """
    scripts = base / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "watchdog.sh").write_text("#!/bin/bash\necho check\n")
    (base / "config.yaml").write_text("model:\n  default: chat-primary\n")
    (base / "config.yaml.known-good").write_text("model:\n  default: chat-primary\n")


def test_main_cli_reporta_ambos_pasos(tmp_path, capsys, monkeypatch):
    _make_fake_skills(tmp_path / "origen")
    _add_scripts_y_config(tmp_path / "origen")
    monkeypatch.setattr(rs, "HERMES_HOME", tmp_path / "origen")

    units_src = tmp_path / "systemd_user"
    units_src.mkdir()
    (units_src / "hermes-gateway.service").write_text("[Unit]\n")
    monkeypatch.setattr(rs, "SYSTEMD_USER_DIR", units_src)

    dest_dir = tmp_path / "destino"
    exit_code = rs.main(["--dest-dir", str(dest_dir)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "[OK] skills:" in out
    assert "RESPALDO COMPLETO" in out
    # main() mete un subdirectorio con timestamp dentro de --dest-dir.
    skill_files = list(dest_dir.glob("*/skills/ejemplo-skill/SKILL.md"))
    unit_files = list(dest_dir.glob("*/systemd/hermes-gateway.service"))
    assert len(skill_files) == 1
    assert len(unit_files) == 1


def test_main_cli_no_timestamp_usa_dest_dir_tal_cual(tmp_path, monkeypatch):
    """--no-timestamp es lo que usa restaurar_hermes.sh para coordinar un
    solo timestamp entre memoria, skills y systemd en la misma corrida."""
    _make_fake_skills(tmp_path / "origen")
    _add_scripts_y_config(tmp_path / "origen")
    monkeypatch.setattr(rs, "HERMES_HOME", tmp_path / "origen")

    units_src = tmp_path / "systemd_user"
    units_src.mkdir()
    (units_src / "hermes-gateway.service").write_text("[Unit]\n")
    monkeypatch.setattr(rs, "SYSTEMD_USER_DIR", units_src)

    dest_dir = tmp_path / "corrida_coordinada"
    exit_code = rs.main(["--dest-dir", str(dest_dir), "--no-timestamp"])

    assert exit_code == 0
    assert (dest_dir / "skills" / "ejemplo-skill" / "SKILL.md").is_file()
    assert (dest_dir / "systemd" / "hermes-gateway.service").is_file()


# ── scripts/ + config.yaml (agregado 30 jul 2026, Bloque AH) ───────────
# El watchdog sobrescribio config.yaml y no habia respaldo de donde
# sacarlo: `find /mnt/seagate -name "config.yaml*"` = 0 resultados. Estas
# pruebas fijan que ambos queden cubiertos de aqui en adelante.


def _make_fake_home(base: Path) -> Path:
    home = base / "hermes_home"
    scripts = home / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "watchdog.sh").write_text("#!/bin/bash\necho check\n")
    (scripts / "has_progress.py").write_text("print('ok')\n")
    (scripts / "__pycache__").mkdir()
    (scripts / "__pycache__" / "basura.pyc").write_text("no copiar")
    (home / "config.yaml").write_text("model:\n  default: chat-primary\n")
    (home / "config.yaml.known-good").write_text("model:\n  default: chat-primary\n")
    return home


def test_respaldar_scripts_y_config_copia_ambos(tmp_path):
    home = _make_fake_home(tmp_path)
    dest_dir = tmp_path / "destino"

    ok, detalles = rs.respaldar_scripts_y_config(
        dest_dir, scripts_src=home / "scripts", config_src=home,
    )

    assert ok, detalles
    assert (dest_dir / "scripts" / "watchdog.sh").read_text() == "#!/bin/bash\necho check\n"
    assert (dest_dir / "scripts" / "has_progress.py").is_file()
    assert (dest_dir / "config" / "config.yaml").is_file()
    assert (dest_dir / "config" / "config.yaml.known-good").is_file()


def test_respaldar_scripts_excluye_pycache(tmp_path):
    """__pycache__ es ruido regenerable; copiarlo infla el respaldo y
    puede traer .pyc de una version de Python distinta."""
    home = _make_fake_home(tmp_path)
    dest_dir = tmp_path / "destino"

    ok, detalles = rs.respaldar_scripts_y_config(
        dest_dir, scripts_src=home / "scripts", config_src=home,
    )

    assert ok, detalles
    assert not (dest_dir / "scripts" / "__pycache__").exists()


def test_respaldar_scripts_falla_si_no_hay_scripts(tmp_path):
    """Un origen ausente debe reportarse como FAIL, no pasar en silencio
    -- el respaldo que "sale bien" sin copiar nada es justo el modo de
    falla que dejo a Arturo sin config de donde recuperar (HAS F9-L6/L14)."""
    home = _make_fake_home(tmp_path)
    dest_dir = tmp_path / "destino"

    ok, detalles = rs.respaldar_scripts_y_config(
        dest_dir, scripts_src=tmp_path / "no_existe", config_src=home,
    )

    assert not ok
    assert any("no existe" in d for d in detalles)


def test_respaldar_config_falla_si_no_hay_ninguno(tmp_path):
    home = _make_fake_home(tmp_path)
    (home / "config.yaml").unlink()
    (home / "config.yaml.known-good").unlink()
    dest_dir = tmp_path / "destino"

    ok, detalles = rs.respaldar_scripts_y_config(
        dest_dir, scripts_src=home / "scripts", config_src=home,
    )

    assert not ok
    assert any("config" in d for d in detalles)
