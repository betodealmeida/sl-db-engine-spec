"""Helpers for interpreting semantic column metadata."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def precision(format_metadata: Mapping[str, Any], default: int) -> int:
    value = format_metadata.get("precision")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


def unit_kind_and_code(unit: Any) -> tuple[str | None, str | None]:
    if not isinstance(unit, Mapping):
        return None, None
    kind = unit.get("kind")
    code = unit.get("code")
    return (
        kind if isinstance(kind, str) else None,
        code if isinstance(code, str) else None,
    )


def d3format_from_metadata(metadata: Mapping[str, Any]) -> str | None:
    """Return the Superset D3 format implied by semantic metadata, if any."""
    extensions = metadata.get("extensions")
    if isinstance(extensions, Mapping):
        superset = extensions.get("superset")
        if isinstance(superset, Mapping):
            d3format = superset.get("d3format")
            if isinstance(d3format, str) and d3format:
                return d3format

    format_metadata = metadata.get("format")
    if not isinstance(format_metadata, Mapping):
        return None

    # Backwards compatibility for early metadata drafts that put native client
    # formats directly in the portable format object.
    d3format = format_metadata.get("d3")
    if isinstance(d3format, str) and d3format:
        return d3format

    preset = format_metadata.get("preset")
    if not isinstance(preset, str):
        return None

    normalized = preset.lower()
    decimal_places = precision(format_metadata, 2)
    if normalized in {"smart_number", "smart-number", "smart"}:
        return "SMART_NUMBER"
    if normalized in {"number", "decimal"}:
        return f",.{decimal_places}f"
    if normalized in {"percentage", "percent"}:
        return f".{decimal_places}%"
    if normalized == "currency":
        kind, code = unit_kind_and_code(metadata.get("unit"))
        symbol = "$" if kind == "currency" and code == "USD" else ""
        return f"{symbol},.{decimal_places}f"

    return None
