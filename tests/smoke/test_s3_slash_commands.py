"""S3 (HAS Fase 2, Bloque 4): slash commands propios de Hermes.

Reusa el arnes ya establecido de tests/e2e/conftest.py (make_runner,
make_adapter, send_and_capture), que dispara el pipeline real de
despacho de GatewayRunner._handle_message sin LLM. No repite el detalle
de tests/e2e/test_platform_commands.py -- solo confirma, como humo, que
tras el rebase el despacho de comandos propios de Hermes (no los de
Claude Code) sigue funcionando de punta a punta. Construye
runner/adapter directo (no via fixtures) porque tests/e2e/conftest.py
vive en otro directorio y sus fixtures no cruzan a tests/smoke/.
"""

from __future__ import annotations

import pytest

from gateway.config import Platform
from tests.e2e.conftest import make_adapter, make_runner, send_and_capture


@pytest.mark.asyncio
async def test_version_command_responds():
    runner = make_runner(Platform.TELEGRAM)
    adapter = make_adapter(Platform.TELEGRAM, runner)
    send = await send_and_capture(adapter, "/version", Platform.TELEGRAM)
    send.assert_called_once()


@pytest.mark.asyncio
async def test_whoami_command_responds():
    runner = make_runner(Platform.TELEGRAM)
    adapter = make_adapter(Platform.TELEGRAM, runner)
    send = await send_and_capture(adapter, "/whoami", Platform.TELEGRAM)
    send.assert_called_once()


@pytest.mark.asyncio
async def test_status_command_responds():
    runner = make_runner(Platform.TELEGRAM)
    adapter = make_adapter(Platform.TELEGRAM, runner)
    send = await send_and_capture(adapter, "/status", Platform.TELEGRAM)
    send.assert_called_once()
    response_text = send.call_args[1].get("content") or send.call_args[0][1]
    assert response_text
