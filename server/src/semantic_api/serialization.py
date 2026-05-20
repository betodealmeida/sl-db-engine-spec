"""Conversion between PyArrow tables and JSON-friendly dicts."""

from __future__ import annotations

from typing import Any

import pyarrow as pa
from superset_core.semantic_layers.types import Dimension, Metric, SemanticResult


def field(name: str, type_: pa.DataType) -> dict[str, str]:
    return {"name": name, "type": str(type_)}


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
        "type": str(dimension.type),
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
        "type": str(metric.type),
        "definition": metric.definition,
        "description": metric.description,
        "aggregation": aggregation.value if aggregation else None,
    }
