"""Glue between request DTOs and the abstract semantic layer interface."""

from __future__ import annotations

from typing import Any

from litestar.exceptions import NotFoundException, ValidationException
from superset_core.semantic_layers.types import (
    Dimension,
    Filter,
    GroupLimit,
    Metric,
    Operator,
    OrderTuple,
    PredicateType,
    SemanticQuery,
)
from superset_core.semantic_layers.view import SemanticView

from semantic_api import registry
from semantic_api.schemas import (
    FilterPayload,
    GroupLimitPayload,
    OrderPayload,
    QueryPayload,
)


def fetch_view(name: str, additional_configuration: dict[str, Any]) -> SemanticView:
    try:
        return registry.layer().get_semantic_view(name, additional_configuration)
    except ValueError as exc:
        raise NotFoundException(detail=str(exc)) from exc


def build_query(view: SemanticView, payload: QueryPayload) -> SemanticQuery:
    metrics_by_id = {m.id: m for m in view.get_metrics()}
    dimensions_by_id = {d.id: d for d in view.get_dimensions()}

    return SemanticQuery(
        metrics=[_lookup_metric(metrics_by_id, mid) for mid in payload.metrics],
        dimensions=[_lookup_dimension(dimensions_by_id, did) for did in payload.dimensions],
        filters=_build_filters(payload.filters, metrics_by_id, dimensions_by_id) or None,
        order=_build_order(payload.order, metrics_by_id, dimensions_by_id) or None,
        limit=payload.limit,
        offset=payload.offset,
        group_limit=_build_group_limit(
            payload.group_limit, metrics_by_id, dimensions_by_id
        ),
    )


def _lookup_metric(metrics_by_id: dict[str, Metric], metric_id: str) -> Metric:
    if metric_id not in metrics_by_id:
        raise ValidationException(detail=f"Unknown metric {metric_id!r}.")
    return metrics_by_id[metric_id]


def _lookup_dimension(
    dimensions_by_id: dict[str, Dimension],
    dimension_id: str,
) -> Dimension:
    if dimension_id not in dimensions_by_id:
        raise ValidationException(detail=f"Unknown dimension {dimension_id!r}.")
    return dimensions_by_id[dimension_id]


_LIST_OPERATORS = {Operator.IN, Operator.NOT_IN}
_NULL_OPERATORS = {Operator.IS_NULL, Operator.IS_NOT_NULL}


def _build_filters(
    payloads: list[FilterPayload],
    metrics_by_id: dict[str, Metric],
    dimensions_by_id: dict[str, Dimension],
) -> set[Filter]:
    return {_build_filter(p, metrics_by_id, dimensions_by_id) for p in payloads}


def _build_filter(
    payload: FilterPayload,
    metrics_by_id: dict[str, Metric],
    dimensions_by_id: dict[str, Dimension],
) -> Filter:
    column: Metric | Dimension | None
    if payload.column is None:
        column = None
    elif payload.type is PredicateType.HAVING:
        column = _lookup_metric(metrics_by_id, payload.column)
    else:
        column = _lookup_dimension(dimensions_by_id, payload.column)

    if payload.operator in _NULL_OPERATORS:
        value: Any = None
    elif payload.operator in _LIST_OPERATORS:
        if not isinstance(payload.value, (list, tuple, set, frozenset)):
            raise ValidationException(
                detail=f"Operator {payload.operator.value} requires a list value.",
            )
        value = frozenset(payload.value)
    else:
        value = payload.value

    return Filter(type=payload.type, column=column, operator=payload.operator, value=value)


def _build_order(
    payloads: list[OrderPayload],
    metrics_by_id: dict[str, Metric],
    dimensions_by_id: dict[str, Dimension],
) -> list[OrderTuple]:
    order: list[OrderTuple] = []
    for payload in payloads:
        element: Metric | Dimension
        if payload.by in metrics_by_id:
            element = metrics_by_id[payload.by]
        elif payload.by in dimensions_by_id:
            element = dimensions_by_id[payload.by]
        else:
            raise ValidationException(detail=f"Unknown order target {payload.by!r}.")
        order.append((element, payload.direction))
    return order


def _build_group_limit(
    payload: GroupLimitPayload | None,
    metrics_by_id: dict[str, Metric],
    dimensions_by_id: dict[str, Dimension],
) -> GroupLimit | None:
    if payload is None:
        return None
    return GroupLimit(
        dimensions=[_lookup_dimension(dimensions_by_id, d) for d in payload.dimensions],
        top=payload.top,
        metric=_lookup_metric(metrics_by_id, payload.metric) if payload.metric else None,
        direction=payload.direction,
        group_others=payload.group_others,
        filters=_build_filters(payload.filters, metrics_by_id, dimensions_by_id) or None,
    )
