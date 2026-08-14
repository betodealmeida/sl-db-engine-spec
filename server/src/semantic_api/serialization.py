"""Conversion between PyArrow tables and JSON-friendly dicts."""

from __future__ import annotations

from typing import Any

import pyarrow as pa
from pyarrow import types as pa_types
from superset_core.semantic_layers.types import Dimension, Metric, SemanticResult


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
        return "float"
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
    return {
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


def metric_to_payload(metric: Metric) -> dict[str, Any]:
    aggregation = getattr(metric, "aggregation", None)
    return {
        "id": metric.id,
        "name": metric.name,
        "type": arrow_type_name(metric.type),
        "definition": metric.definition,
        "description": metric.description,
        "aggregation": aggregation.value if aggregation else None,
    }
