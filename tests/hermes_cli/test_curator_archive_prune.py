"""Tests for `hermes curator archive` and `hermes curator prune`.

Covers:
- archive refuses pinned skills with an `unpin` hint
- archive returns 0/1 based on archive_skill() success
- prune filters pinned and already-archived, applies --days threshold
- prune falls back to created_at when last_activity_at is null
- prune --dry-run makes no state changes
- prune --yes skips confirmation
- prune --days validation
"""

from __future__ import annotations

from types import SimpleNamespace


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


# ─── archive ────────────────────────────────────────────────────────────────


def test_archive_refuses_pinned(monkeypatch, capsys):
    import hermes_cli.curator as curator_cli
    import tools.skill_usage as skill_usage

    monkeypatch.setattr(skill_usage, "get_record", lambda name, skill_dir=None: {"pinned": True})
    called = []
    monkeypatch.setattr(
        skill_usage, "archive_skill",
        lambda name: called.append(name) or (True, "should not get here"),
    )

    rc = curator_cli._cmd_archive(_ns(skill="pinned-skill"))
    assert rc == 1
    assert called == []
    out = capsys.readouterr().out
    assert "pinned" in out.lower()
    assert "hermes curator unpin" in out


def test_archive_calls_archive_skill(monkeypatch, capsys):
    import hermes_cli.curator as curator_cli
    import tools.skill_usage as skill_usage

    monkeypatch.setattr(skill_usage, "get_record", lambda name, skill_dir=None: {"pinned": False})
    monkeypatch.setattr(
        skill_usage, "archive_skill",
        lambda name: (True, f"archived to .archive/{name}"),
    )
    rc = curator_cli._cmd_archive(_ns(skill="my-skill"))
    assert rc == 0
    assert "archived to .archive/my-skill" in capsys.readouterr().out


def test_archive_reports_failure(monkeypatch, capsys):
    import hermes_cli.curator as curator_cli
    import tools.skill_usage as skill_usage

    monkeypatch.setattr(skill_usage, "get_record", lambda name, skill_dir=None: {"pinned": False})
    monkeypatch.setattr(
        skill_usage, "archive_skill",
        lambda name: (False, f"skill '{name}' is bundled or hub-installed; never archive"),
    )
    rc = curator_cli._cmd_archive(_ns(skill="hub-slug"))
    assert rc == 1
    assert "bundled or hub-installed" in capsys.readouterr().out


# ─── prune ──────────────────────────────────────────────────────────────────


def _mk_record(name, *, idle_days=0, pinned=False, state="active", created_idle_days=None):
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    last_activity = (now - _dt.timedelta(days=idle_days)).isoformat() if idle_days else None
    created_delta = created_idle_days if created_idle_days is not None else idle_days
    created = (now - _dt.timedelta(days=created_delta)).isoformat()
    return {
        "name": name,
        "state": state,
        "pinned": pinned,
        "last_activity_at": last_activity,
        "created_at": created,
        "activity_count": 0 if idle_days == 0 and last_activity is None else 1,
    }








# ─── argparse wiring ────────────────────────────────────────────────────────


def test_archive_and_prune_registered():
    import argparse
    import hermes_cli.curator as curator_cli

    parser = argparse.ArgumentParser(prog="hermes curator")
    curator_cli.register_cli(parser)

    args = parser.parse_args(["archive", "my-skill"])
    assert args.skill == "my-skill"
    assert args.func.__name__ == "_cmd_archive"

    args = parser.parse_args(["prune", "--days", "45", "--yes", "--dry-run"])
    assert args.days == 45
    assert args.yes is True
    assert args.dry_run is True
    assert args.func.__name__ == "_cmd_prune"


