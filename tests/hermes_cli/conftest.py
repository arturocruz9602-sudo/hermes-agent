"""Fixtures shared across hermes_cli kanban tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def all_assignees_spawnable(monkeypatch):
    """Pretend every assignee maps to a real Hermes profile.

    Most dispatcher tests use synthetic assignees ("alice", "bob") that
    don't correspond to actual profile directories on disk. Without this
    patch, the dispatcher's profile-exists guard (PR #20105) routes
    those tasks into ``skipped_nonspawnable`` instead of spawning, which
    would break tests that assert spawn behavior.
    """
    from hermes_cli import profiles
    monkeypatch.setattr(profiles, "profile_exists", lambda name: True)


@pytest.fixture(autouse=True)
def _suppress_concurrent_hermes_gate(request, monkeypatch):
    """Default ``_detect_concurrent_hermes_instances`` to ``[]`` for every test.

    The Windows update path now refuses to proceed when another
    ``hermes.exe`` is detected (issue #26670). On a developer's Windows
    machine running the test suite via ``hermes`` itself, this would
    flag the running agent as a concurrent instance and abort every
    ``cmd_update`` test. Tests that want to exercise the gate explicitly
    re-patch ``_detect_concurrent_hermes_instances`` with their own
    return value — autouse here gives a clean default without touching
    the rest of the suite.

    Tests that need to call the REAL function (e.g. unit tests for the
    helper itself) opt out with ``@pytest.mark.real_concurrent_gate``.
    """
    if request.node.get_closest_marker("real_concurrent_gate"):
        return
    try:
        from hermes_cli import main as _cli_main
    except Exception:
        return
    # raising=False: under pytest's per-test spawn isolation, a concurrent
    # xdist worker importing a module that transitively touches hermes_cli.main
    # can briefly expose a partially-initialized module object here — one where
    # _detect_concurrent_hermes_instances isn't defined yet. A bare setattr
    # would raise AttributeError and error the (unrelated) test. The attribute
    # always exists once main.py finishes importing, so a no-op when it's
    # transiently absent is the correct, race-free default.
    monkeypatch.setattr(
        _cli_main,
        "_detect_concurrent_hermes_instances",
        lambda *_a, **_k: [],
        raising=False,
    )


@pytest.fixture(autouse=True)
def _no_real_network(request, monkeypatch):
    """Block real outbound network connections during hermes_cli tests.

    Found the hard way (26 Jul 2026, faulthandler.dump_traceback_later(),
    ptrace unavailable in this sandbox): 3 confirmed hangs, all under
    tests/hermes_cli/ -- doctor.py's real ``npm audit`` subprocess (see
    tests/conftest.py's npm-audit guard) and an unmocked
    fetch_github_model_catalog() in test_model_switch_copilot_api_mode.py,
    both stuck in socket.getaddrinfo()/communicate() well past their own
    timeouts because this sandbox has no outbound internet. Scoped to
    this directory rather than the repo-wide tests/conftest.py: applying
    it globally surfaced ~5 unrelated pre-existing missing-mock gaps in
    tests/tools/ (e.g. test_skills_hub.py hitting skills.sh for real)
    that were never part of this investigation's verified scope --
    each of those needs its own deliberate mock + test run, not a
    blanket guard applied where the actual problem wasn't confirmed.

    Loopback (127.0.0.1 / ::1 / localhost) is exempted so tests using a
    real local test server keep working. Opt out with
    ``@pytest.mark.live_system_guard_bypass`` for a test that
    legitimately needs real network.
    """
    if request.node.get_closest_marker("live_system_guard_bypass"):
        yield
        return

    import socket as _socket

    _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

    def _block(host):
        raise RuntimeError(
            f"tests/hermes_cli/conftest.py live-system guard: blocked "
            f"a real network connection to {host!r}. This sandbox has "
            "no outbound internet -- an unmocked call here would hang "
            "instead of failing fast. Mock the function making this "
            "call in the test, or mark with "
            "@pytest.mark.live_system_guard_bypass if this test "
            "genuinely needs real network."
        )

    real_create_connection = _socket.create_connection

    def _guarded_create_connection(address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK_HOSTS:
            _block(host)
        return real_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(_socket, "create_connection", _guarded_create_connection)

    # requests/urllib3 don't call socket.create_connection -- urllib3
    # builds the socket itself (getaddrinfo + socket.socket().connect())
    # and only funnels through socket.socket.connect at the very end.
    # Confirmed live (27 jul 2026): test_run_doctor_flags_missing_
    # credentials_for_active_openrouter_provider hung in
    # socket.getaddrinfo() via requests -> models_dev.fetch_models_dev,
    # unaffected by the create_connection patch above. Patching connect
    # itself catches every library uniformly regardless of how it built
    # the socket.
    real_connect = _socket.socket.connect

    def _guarded_connect(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK_HOSTS:
            _block(host)
        return real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(_socket.socket, "connect", _guarded_connect)

    # The actual hang is one frame earlier than connect(): urllib3 calls
    # socket.getaddrinfo() to resolve the hostname BEFORE it ever builds a
    # socket to connect() with, and DNS resolution to an unreachable
    # resolver hangs on its own. Block here too so a real hostname never
    # even gets to the connect stage.
    real_getaddrinfo = _socket.getaddrinfo

    def _guarded_getaddrinfo(host, *args, **kwargs):
        if host not in _LOOPBACK_HOSTS:
            _block(host)
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(_socket, "getaddrinfo", _guarded_getaddrinfo)

    yield
