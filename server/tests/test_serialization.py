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
    assert arrow_type_name(pa.float32()) == "float"
    assert arrow_type_name(pa.float64()) == "float"
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
        {"name": "amount", "type": "float"},
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
        metadata={"display": {"label": "Revenue"}},
        unit="usd",
        filter_metadata={
            "operators": ["=", "!=", ">", ">="],
            "control": "number",
            "value_type": "float",
        },
    )

    payload = metric_to_payload(metric)

    assert payload["metadata"] == {
        "display": {"label": "Revenue"},
        "unit": "usd",
        "filter": {
            "operators": ["=", "!=", ">", ">="],
            "control": "number",
            "value_type": "float",
        },
    }


def test_existing_metadata_keys_take_precedence() -> None:
    metric = SimpleNamespace(
        id="sales.total_revenue",
        name="total_revenue",
        type=pa.float64(),
        definition="SUM(revenue)",
        description=None,
        aggregation=None,
        metadata={
            "unit": "eur",
            "filter": {"operators": ["="], "control": "number", "value_type": "float"},
        },
        unit="usd",
        filter_metadata={
            "operators": [">"],
            "control": "number",
            "value_type": "float",
        },
    )

    payload = metric_to_payload(metric)

    assert payload["metadata"] == {
        "unit": "eur",
        "filter": {"operators": ["="], "control": "number", "value_type": "float"},
    }
