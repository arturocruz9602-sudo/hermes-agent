"""S2 (HAS Fase 2, Bloque 4): arranque de gateway en modo dry-run.

Construye un GatewayRunner REAL (constructor real, no bypass como
tests/e2e/conftest.py::make_runner) apuntando a un HERMES_HOME aislado
y vacio -- "bot de prueba o modo dry-run" segun la especificacion del
HAS, nunca produccion. __init__ no arranca conexiones de red por si
solo (eso lo hace el arranque explicito de adapters), asi que esto
verifica que la carga de config real + inicializacion interna real del
gateway funciona en el venv nuevo, sin tocar nada de produccion.
"""

from __future__ import annotations


def test_gateway_runner_constructs_with_isolated_config(isolated_hermes_home):
    from gateway.config import load_gateway_config
    from gateway.run import GatewayRunner

    config = load_gateway_config()
    runner = GatewayRunner(config)

    assert runner.config is config
    assert runner.adapters == {}, (
        "un GatewayRunner recien construido no debe tener adapters "
        "arrancados solo por __init__"
    )
    assert runner._shutdown_event is not None
    assert runner._running_agents == {}
    assert runner._pending_messages == {}
