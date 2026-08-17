from datetime import date
from types import SimpleNamespace

import pyarrow as pa

from semantic_api.serialization import (
    arrow_type_name,
    dimension_to_payload,
    metric_to_payload,
    table_to_payload,
)


def test_arrow_type_name_returns_family_name() -> None:
    assert arrow_type_name(pa.int8()) == "int"
    assert arrow_type_name(pa.int64()) == "int"
    assert arrow_type_name(pa.uint32()) == "int"
    assert arrow_type_name(pa.float32()) == "floating"
    assert arrow_type_name(pa.float64()) == "floating"
    assert arrow_type_name(pa.string()) == "utf8"
    assert arrow_type_name(pa.large_string()) == "utf8"
    assert arrow_type_name(pa.date32()) == "date"
    assert arrow_type_name(pa.timestamp("us")) == "timestamp"
    assert arrow_type_name(pa.decimal128(18, 2)) == "decimal"
    assert arrow_type_name(pa.list_(pa.int64())) == "list"
    assert arrow_type_name(pa.map_(pa.string(), pa.int64())) == "map"


def test_table_to_payload_uses_type_family_names() -> None:
    table = pa.table(
        {
            "id": pa.array([1], type=pa.int64()),
            "amount": pa.array([1.5], type=pa.float64()),
            "created": pa.array([date(2026, 8, 14)], type=pa.date32()),
        },
    )

    payload = table_to_payload(table)

    assert payload["schema"] == [
        {"name": "id", "type": "int"},
        {"name": "amount", "type": "floating"},
        {"name": "created", "type": "date"},
    ]


def test_column_payload_omits_empty_metadata() -> None:
    dimension = SimpleNamespace(
        id="sales.region",
        name="region",
        type=pa.string(),
        definition="region",
        description=None,
        grain=None,
    )

    payload = dimension_to_payload(dimension)

    assert "metadata" not in payload


def test_column_payload_includes_metadata_and_compatibility_attrs() -> None:
    metric = SimpleNamespace(
        id="sales.total_revenue",
        name="total_revenue",
        type=pa.float64(),
        definition="SUM(revenue)",
        description=None,
        aggregation=None,
        metadata={"source_owner": "finance"},
        verbose_name="Revenue",
        d3format="$,.2f",
        semantic_type="currency",
        unit={"kind": "currency", "code": "USD"},
        attributes=["certified", "core"],
        format_metadata={
            "preset": "currency",
            "precision": 2,
            "google_sheets": {"type": "CURRENCY", "pattern": "$#,##0.00"},
        },
        filter_metadata={
            "kind": "range",
            "operators": ["=", "!=", ">", ">=", "<", "<=", "between"],
            "default_operator": "between",
        },
    )

    payload = metric_to_payload(metric)

    assert payload["metadata"] == {
        "display_name": "Revenue",
        "semantic_type": "currency",
        "unit": {"kind": "currency", "code": "USD"},
        "attributes": ["certified", "core"],
        "format": {
            "preset": "currency",
            "precision": 2,
        },
        "filter": {
            "kind": "range",
            "operators": ["=", "!=", ">", ">=", "<", "<=", "between"],
            "default_operator": "between",
        },
        "extensions": {
            "custom": {"source_owner": "finance"},
            "superset": {"d3format": "$,.2f"},
            "google_sheets": {
                "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"},
            },
        },
    }


def test_existing_metadata_keys_take_precedence_and_are_normalized() -> None:
    metric = SimpleNamespace(
        id="sales.total_revenue",
        name="total_revenue",
        type=pa.float64(),
        definition="SUM(revenue)",
        description=None,
        aggregation=None,
        metadata={
            "unit": "eur",
            "display_name": "Net revenue",
            "semantic_type": "number",
            "attributes": ["sensitive"],
            "format": {"d3": ",.0f"},
            "filter": {
                "kind": "range",
                "operators": ["="],
                "default_operator": "=",
            },
        },
        display_name="Revenue",
        verbose_name="Gross revenue",
        d3format="$,.2f",
        semantic_type="currency",
        attributes=["certified", "core"],
        format_metadata={"d3": "$,.2f"},
        unit="usd",
        filter_metadata={
            "operators": [">"],
            "kind": "range",
            "default_operator": ">",
        },
    )

    payload = metric_to_payload(metric)

    assert payload["metadata"] == {
        "display_name": "Net revenue",
        "semantic_type": "number",
        "attributes": ["sensitive"],
        "filter": {
            "kind": "range",
            "operators": ["="],
            "default_operator": "=",
        },
        "extensions": {
            "custom": {"unit": "eur"},
            "superset": {"d3format": ",.0f"},
        },
    }


def test_column_payload_reads_attribute_names_method() -> None:
    dimension = SimpleNamespace(
        id="sales.region",
        name="region",
        type=pa.string(),
        definition="region",
        description=None,
        grain=None,
        attribute_names=lambda: {"certified", "core"},
    )

    payload = dimension_to_payload(dimension)

    assert payload["metadata"] == {"attributes": ["certified", "core"]}


def test_column_payload_keeps_extensions_and_moves_unknown_keys() -> None:
    dimension = SimpleNamespace(
        id="sales.region",
        name="region",
        type=pa.string(),
        definition="region",
        description=None,
        grain=None,
        metadata={
            "extensions": {"dj": {"node": "sales"}},
            "owner": "analytics",
        },
    )

    payload = dimension_to_payload(dimension)

    assert payload["metadata"] == {
        "extensions": {
            "custom": {"owner": "analytics"},
            "dj": {"node": "sales"},
        },
    }
