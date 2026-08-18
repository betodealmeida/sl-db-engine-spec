"""Conversion between PyArrow tables and JSON-friendly dicts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

import pyarrow as pa
from pyarrow import types as pa_types

if TYPE_CHECKING:
    from superset_core.semantic_layers.types import Dimension, Metric, SemanticResult

_CORE_METADATA_KEYS = {
    "display_name",
    "semantic_type",
    "unit",
    "attributes",
    "format",
    "filter",
    "extensions",
}

_CORE_FORMAT_KEYS = {"preset", "precision", "scale"}
_CORE_FILTER_KEYS = {"kind", "operators", "default_operator", "multi"}


def _matches(predicate_name: str, type_: pa.DataType) -> bool:
    predicate = getattr(pa_types, predicate_name, None)
    return bool(predicate and predicate(type_))


def arrow_type_name(type_: pa.DataType) -> str:
    """Return the Arrow JSON type object's family name."""
    if pa_types.is_boolean(type_):
        return "bool"
    if pa_types.is_integer(type_):
        return "int"
    if pa_types.is_floating(type_):
        return "floating"
    if pa_types.is_string(type_) or pa_types.is_large_string(type_):
        return "utf8"
    if pa_types.is_binary(type_) or pa_types.is_large_binary(type_):
        return "binary"
    if pa_types.is_date(type_):
        return "date"
    if pa_types.is_time(type_):
        return "time"
    if pa_types.is_timestamp(type_):
        return "timestamp"
    if pa_types.is_decimal(type_):
        return "decimal"
    if pa_types.is_dictionary(type_):
        return arrow_type_name(type_.value_type)
    if (
        pa_types.is_list(type_)
        or pa_types.is_large_list(type_)
        or _matches("is_fixed_size_list", type_)
        or _matches("is_list_view", type_)
        or _matches("is_large_list_view", type_)
    ):
        return "list"
    if pa_types.is_map(type_):
        return "map"
    if pa_types.is_struct(type_):
        return "struct"
    if pa_types.is_null(type_):
        return "null"
    if pa_types.is_duration(type_):
        return "duration"
    if pa_types.is_interval(type_):
        return "interval"
    if pa_types.is_fixed_size_binary(type_):
        return "binary"
    return str(type_).split("[", maxsplit=1)[0].split("(", maxsplit=1)[0]


def field(name: str, type_: pa.DataType) -> dict[str, str]:
    return {"name": name, "type": arrow_type_name(type_)}


def column_metadata(column: Any) -> dict[str, Any] | None:
    metadata = getattr(column, "metadata", None)
    raw_metadata = dict(metadata) if isinstance(metadata, Mapping) else {}
    result: dict[str, Any] = {}
    extensions: dict[str, Any] = {}

    if isinstance(raw_metadata.get("extensions"), Mapping):
        extensions.update(raw_metadata["extensions"])

    unknown_metadata = {
        key: value
        for key, value in raw_metadata.items()
        if key not in _CORE_METADATA_KEYS
    }
    if unknown_metadata:
        _merge_extension(extensions, "custom", unknown_metadata)

    display_name = raw_metadata.get("display_name")
    if display_name is None:
        display_name = getattr(column, "verbose_name", None)
    if display_name is None:
        display_name = getattr(column, "display_name", None)
    if isinstance(display_name, str):
        result["display_name"] = display_name

    semantic_type = raw_metadata.get(
        "semantic_type",
        getattr(column, "semantic_type", None),
    )
    if isinstance(semantic_type, str):
        result["semantic_type"] = semantic_type

    unit = raw_metadata.get("unit", getattr(column, "unit", None))
    if isinstance(unit, Mapping):
        result["unit"] = dict(unit)
    elif unit is not None:
        _merge_extension(extensions, "custom", {"unit": unit})

    raw_attributes = raw_metadata.get("attributes")
    attributes = _string_list(raw_attributes) if raw_attributes is not None else (
        _column_attributes(column)
    )
    if attributes:
        result["attributes"] = attributes

    format_metadata = raw_metadata.get(
        "format",
        getattr(column, "format_metadata", None),
    )
    if isinstance(format_metadata, Mapping):
        format_result, format_extensions = _split_format_metadata(format_metadata)
        if format_result:
            result["format"] = format_result
        _merge_extensions(extensions, format_extensions)

    d3format = getattr(column, "d3format", None)
    if isinstance(d3format, str) and d3format:
        _merge_extension(extensions, "superset", {"d3format": d3format})

    filter_metadata = raw_metadata.get(
        "filter",
        getattr(column, "filter_metadata", None),
    )
    if isinstance(filter_metadata, Mapping):
        filter_result = _filter_metadata(filter_metadata)
        if filter_result:
            result["filter"] = filter_result

    if extensions:
        result["extensions"] = extensions

    if not result:
        return None

    json.dumps(result)
    return result


def _merge_extension(
    extensions: dict[str, Any],
    namespace: str,
    values: Mapping[str, Any],
) -> None:
    existing = extensions.get(namespace)
    if isinstance(existing, Mapping):
        merged = dict(values)
        merged.update(existing)
        extensions[namespace] = merged
    else:
        extensions[namespace] = dict(values)


def _merge_extensions(
    extensions: dict[str, Any],
    values: Mapping[str, Mapping[str, Any]],
) -> None:
    for namespace, namespace_values in values.items():
        _merge_extension(extensions, namespace, namespace_values)


def _split_format_metadata(
    format_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    result: dict[str, Any] = {}
    extensions: dict[str, dict[str, Any]] = {}

    preset = format_metadata.get("preset")
    if isinstance(preset, str):
        result["preset"] = preset

    precision = format_metadata.get("precision")
    if isinstance(precision, int) and not isinstance(precision, bool) and precision >= 0:
        result["precision"] = precision

    scale = format_metadata.get("scale")
    if isinstance(scale, (int, float)) and not isinstance(scale, bool):
        result["scale"] = scale

    d3format = format_metadata.get("d3") or format_metadata.get("d3format")
    if isinstance(d3format, str) and d3format:
        extensions["superset"] = {"d3format": d3format}

    google_sheets = format_metadata.get("google_sheets")
    if isinstance(google_sheets, Mapping):
        number_format = google_sheets.get("numberFormat", google_sheets)
        if isinstance(number_format, Mapping):
            extensions["google_sheets"] = {"numberFormat": dict(number_format)}

    unknown_format = {
        key: value
        for key, value in format_metadata.items()
        if key
        not in {
            *_CORE_FORMAT_KEYS,
            "d3",
            "d3format",
            "google_sheets",
        }
    }
    if unknown_format:
        extensions["custom"] = {"format": unknown_format}

    return result, extensions


def _filter_metadata(filter_metadata: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        key: filter_metadata[key]
        for key in _CORE_FILTER_KEYS
        if key in filter_metadata
    }

    if "kind" in result and not isinstance(result["kind"], str):
        result.pop("kind")

    operators = _string_list(result.get("operators"))
    if operators:
        result["operators"] = operators
    else:
        result.pop("operators", None)

    default_operator = result.get("default_operator")
    if default_operator is not None and not isinstance(default_operator, str):
        result.pop("default_operator")
        default_operator = None
    if (
        default_operator is not None
        and operators
        and default_operator not in operators
    ):
        result.pop("default_operator")

    if "multi" in result and not isinstance(result["multi"], bool):
        result.pop("multi")

    return result


def _column_attributes(column: Any) -> list[str]:
    attributes = getattr(column, "attributes", None)
    if callable(attributes):
        attributes = attributes()
    if attributes is None:
        attribute_names = getattr(column, "attribute_names", None)
        if callable(attribute_names):
            attributes = attribute_names()
    return _string_list(attributes)


def _string_list(values: Any) -> list[str]:
    if isinstance(values, (str, bytes)):
        return []
    if isinstance(values, Mapping):
        values = values.keys()
    if isinstance(values, (set, frozenset)):
        values = sorted(values)
    try:
        return [str(value) for value in values or []]
    except TypeError:
        return []


def table_to_payload(table: pa.Table) -> dict[str, Any]:
    return {
        "schema": [field(f.name, f.type) for f in table.schema],
        "rows": table.to_pylist(),
    }


def result_to_payload(result: SemanticResult) -> dict[str, Any]:
    return {
        "requests": [
            {"type": request.type, "definition": request.definition}
            for request in result.requests
        ],
        "results": table_to_payload(result.results),
    }


def dimension_to_payload(dimension: Dimension) -> dict[str, Any]:
    payload = {
        "id": dimension.id,
        "name": dimension.name,
        "type": arrow_type_name(dimension.type),
        "definition": dimension.definition,
        "description": dimension.description,
        "grain": (
            {"name": dimension.grain.name, "representation": dimension.grain.representation}
            if dimension.grain
            else None
        ),
    }
    if metadata := column_metadata(dimension):
        payload["metadata"] = metadata
    return payload


def metric_to_payload(metric: Metric) -> dict[str, Any]:
    aggregation = getattr(metric, "aggregation", None)
    payload = {
        "id": metric.id,
        "name": metric.name,
        "type": arrow_type_name(metric.type),
        "definition": metric.definition,
        "description": metric.description,
        "aggregation": aggregation.value if aggregation else None,
    }
    if metadata := column_metadata(metric):
        payload["metadata"] = metadata
    return payload
