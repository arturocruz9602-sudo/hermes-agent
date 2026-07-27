"""S8 (HAS Fase 2, Bloque 4): lectura de MEMORY/USER.

Escribe una entrada real via MemoryStore.add() + save_to_disk(), luego
la lee de vuelta con una instancia FRESCA (load_from_disk(), el mismo
camino que un proceso nuevo de Hermes usa al arrancar) y confirma que
aparece en el snapshot congelado que se inyecta al system prompt.
HERMES_HOME aislado -- nunca toca el MEMORY.md/USER.md real de Arturo.
"""

from __future__ import annotations

from tools.memory_tool import MemoryStore


def test_memory_entry_roundtrips_through_disk(isolated_hermes_home):
    writer = MemoryStore()
    writer.load_from_disk()
    result = writer.add("memory", "Arturo prefiere respuestas breves y directas.")
    assert result.get("success") is True, f"add() fallo: {result}"

    reader = MemoryStore()
    reader.load_from_disk()
    block = reader.format_for_system_prompt("memory")
    assert block is not None
    assert "Arturo prefiere respuestas breves y directas." in block


def test_user_entry_roundtrips_through_disk(isolated_hermes_home):
    writer = MemoryStore()
    writer.load_from_disk()
    result = writer.add("user", "Arturo es maestro de formación.")
    assert result.get("success") is True, f"add() fallo: {result}"

    reader = MemoryStore()
    reader.load_from_disk()
    block = reader.format_for_system_prompt("user")
    assert block is not None
    assert "Arturo es maestro de formación." in block


def test_empty_memory_snapshot_is_none(isolated_hermes_home):
    store = MemoryStore()
    store.load_from_disk()
    assert store.format_for_system_prompt("memory") is None
