"""Validation for the ``platform_toolsets`` config section.

Pure, side-effect-free helpers so the logic is unit-testable without importing
the tool registry or launching Hermes (mirrors the decoupled-helper pattern used
elsewhere in the CLI).

Motivated by #38798: a config migration silently rewrote the valid toolset name
``hermes-cli`` to the non-existent ``hermes``. ``resolve_toolset('hermes')``
returns an empty list, so every tool silently disappeared with no error, warning,
or log entry — the agent degraded to text-only replies and the cause took
significant debugging to find. Surfacing invalid toolset names (and the
zero-tools end state) loudly turns that silent failure into an actionable one.
"""

from typing import Callable, Dict, List


def validate_platform_toolsets(
    platform_toolsets: object,
    is_valid_toolset: Callable[[str], bool],
) -> List[str]:
    """Return human-readable warnings for a ``platform_toolsets`` mapping.

    Two failure modes are reported:

    1. A toolset name that ``is_valid_toolset`` rejects — usually a corrupted or
       renamed entry. When ``hermes-<platform>`` would have been valid (the exact
       #38798 shape, where ``cli`` held ``hermes`` instead of ``hermes-cli``),
       the warning includes that as a suggestion.
    2. The mapping is non-empty but resolves to *zero* valid toolsets, so the
       agent would start with no tools at all.

    ``is_valid_toolset`` is injected (normally :func:`toolsets.validate_toolset`)
    so this function performs no imports or I/O and is testable in isolation.

    Args:
        platform_toolsets: The raw ``platform_toolsets`` value from config. Only
            ``dict`` values carry toolset entries; anything else yields no
            warnings (nothing to validate).
        is_valid_toolset: Predicate returning ``True`` for a known toolset name.

    Returns:
        A list of warning strings (empty when everything is valid).
    """
    warnings: List[str] = []
    if not isinstance(platform_toolsets, dict) or not platform_toolsets:
        return warnings

    valid_count = 0
    for platform, raw in platform_toolsets.items():
        names = raw if isinstance(raw, list) else [raw]
        for name in names:
            if not isinstance(name, str) or not name:
                continue
            if is_valid_toolset(name):
                valid_count += 1
                continue
            suggestion = f"hermes-{platform}"
            hint = (
                f" — did you mean '{suggestion}'?"
                if is_valid_toolset(suggestion)
                else ""
            )
            warnings.append(
                f"platform '{platform}' references unknown toolset "
                f"'{name}'{hint}"
            )

    if valid_count == 0:
        warnings.append(
            "platform_toolsets resolves to zero valid toolsets — the agent will "
            "have no tools. Run `hermes tools` to reconfigure."
        )
    return warnings


def validate_kanban_gate_consistency(
    platform_toolsets: object,
    toolsets: object,
) -> List[str]:
    """Warn when kanban's two independent gates disagree.

    Kanban tools require BOTH gates to be set to work: ``kanban`` in the
    top-level ``toolsets:`` list (checked by ``_check_kanban_mode`` in
    ``tools/kanban_tools.py``, gates each individual tool call) AND
    ``kanban`` in a platform's ``platform_toolsets.<platform>`` list
    (checked by ``_get_platform_tools`` in ``hermes_cli/tools_config.py``,
    gates whether the tool schema is even offered to that platform). They
    are independent gates, not alternatives — setting only one silently
    half-enables kanban with no error (tools appear in the schema but
    every call is rejected, or tools never appear in the schema at all).
    Reverting one gate while assuming the other is sufficient is a real
    mistake that was made and only caught by reading transcripts.
    """
    warnings: List[str] = []
    top_level_has_kanban = isinstance(toolsets, list) and "kanban" in toolsets

    plat_map = platform_toolsets if isinstance(platform_toolsets, dict) else {}
    platforms_with_kanban = sorted(
        platform
        for platform, raw in plat_map.items()
        if isinstance(raw, list) and "kanban" in raw
    )

    if platforms_with_kanban and not top_level_has_kanban:
        warnings.append(
            "kanban is enabled in platform_toolsets for "
            f"{', '.join(platforms_with_kanban)} but missing from the "
            "top-level 'toolsets:' list — kanban tools will appear in the "
            "schema but every call will be rejected. Add 'kanban' to "
            "toolsets: as well."
        )
    elif top_level_has_kanban and not platforms_with_kanban:
        warnings.append(
            "kanban is enabled in the top-level 'toolsets:' list but is "
            "missing from platform_toolsets for every platform — kanban "
            "tools will never appear in the schema for any platform. Add "
            "'kanban' to platform_toolsets.<platform> as well."
        )
    return warnings
