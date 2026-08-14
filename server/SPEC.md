# Semantic Layer REST API

A protocol for exposing one already-configured
[`SemanticLayer`](../../superset/superset-core/src/superset_core/semantic_layers/layer.py)
— together with the
[`SemanticView`](../../superset/superset-core/src/superset_core/semantic_layers/view.py)s
it produces — over HTTP. The layer's static configuration (credentials,
project, dataset, …) is provided to the server out of band; clients only
discover and query views.

The mapping is one-to-one with the Python interface; nothing more is invented.

## Concepts

| Python                  | REST resource                              |
| ----------------------- | ------------------------------------------ |
| `SemanticView`          | `/views/{view_name}`                       |
| `Dimension`, `Metric`   | Embedded objects, keyed by stable `id`     |
| `SemanticQuery`         | Request body of `/views/{view_name}/query` |
| `SemanticResult`        | Response wrapping `requests` + tabular data |

`runtime_configuration` (per-request, used when listing views) and
`additional_configuration` (per-request, used when materialising a specific
view) follow the same JSON shape they have in Python — the server defines
what is valid; clients pass them through unmodified.

## Media types

All payloads are JSON (`application/json`). Tabular results use:

```json
{
    "schema": [{"name": "<col>", "type": "<arrow-type-name>"}],
    "rows":   [{"<col>": <value>, ...}]
}
```

Arrow types are reported using the Arrow JSON type object's `name` value
(`int`, `float`, `utf8`, `date`, `timestamp`, …), without precision or unit
parameters. Temporal values are serialised as ISO 8601 strings.

## Errors

Errors follow [RFC 7807](https://datatracker.ietf.org/doc/html/rfc7807):

```json
{"status_code": 404, "detail": "Semantic view 'foo' does not exist."}
```

| Status | Meaning                                            |
| ------ | -------------------------------------------------- |
| 400    | Malformed payload, unknown metric/dimension id, …  |
| 404    | View does not exist                                |
| 422    | The request body failed schema validation          |
| 500    | Layer raised an unexpected exception               |

## Endpoints

### `POST /views/` (`POST /views/list` supported but deprecated)

Lists semantic views. `POST` is used because the runtime configuration is a
free-form JSON object.

Request:

```json
{"runtime_configuration": {}}
```

Response:

```json
[
    {"name": "sales", "uid": "pandas.sales", "features": ["GROUP_LIMIT"]}
]
```

### `POST /views/{view_name}`

Returns a view's metadata. The body carries any `additional_configuration` the
view needs to materialise (often `{}`).

Request:

```json
{"additional_configuration": {}}
```

Response:

```json
{
    "name": "sales",
    "uid": "pandas.sales",
    "features": ["GROUP_LIMIT"],
    "dimensions": [
        {
            "id": "sales.product_category",
            "name": "product_category",
            "type": "utf8",
            "metadata": {
                "filter": {
                    "operators": ["=", "!=", "IN", "NOT IN", "IS NULL", "IS NOT NULL"],
                    "control": "select",
                    "value_type": "utf8",
                    "values": {"type": "endpoint", "endpoint": "values"}
                }
            },
            "definition": "product_category",
            "description": "The product category dimension.",
            "grain": null
        }
    ],
    "metrics": [
        {
            "id": "sales.total_revenue",
            "name": "total_revenue",
            "type": "float",
            "metadata": {
                "unit": "usd",
                "filter": {
                    "operators": ["=", "!=", ">", ">=", "<", "<=", "IS NULL", "IS NOT NULL"],
                    "control": "number",
                    "value_type": "float"
                }
            },
            "definition": "SUM(revenue)",
            "description": "Total sales revenue.",
            "aggregation": null
        }
    ]
}
```

`metadata` is optional and omitted when empty. Servers should preserve unknown
metadata keys so clients can adopt new annotations incrementally. Standard keys
are:

| Key | Meaning |
| --- | ------- |
| `unit` | Display unit code, such as `usd`, `percent`, or `seconds`. |
| `filter` | UI hints for building filter controls; query semantics still use the `filters` request payload. |

`metadata.filter.values` can point at the existing values endpoint with
`{"type": "endpoint", "endpoint": "values"}`.

### `POST /views/{view_name}/query`

Run a semantic query and return the resulting table.

Request — mirrors `SemanticQuery`, identifying metrics and dimensions by
stable id:

```json
{
    "additional_configuration": {},
    "query": {
        "metrics":    ["sales.total_revenue"],
        "dimensions": ["sales.product_category"],
        "filters": [
            {
                "type":     "WHERE",
                "column":   "sales.region",
                "operator": "=",
                "value":    "North"
            }
        ],
        "order": [{"by": "sales.total_revenue", "direction": "DESC"}],
        "limit":  100,
        "offset": 0,
        "group_limit": {
            "dimensions":   ["sales.product_category"],
            "top":          5,
            "metric":       "sales.total_revenue",
            "direction":    "DESC",
            "group_others": false,
            "filters":      []
        }
    }
}
```

Filter `column` is an id; if `type` is `HAVING` it references a metric, if
`WHERE` it references a dimension. `value` is a literal, a list (for `IN` /
`NOT IN`), or `null` (for `IS NULL` / `IS NOT NULL`).

Response — a `SemanticResult`:

```json
{
    "requests": [{"type": "pandas", "definition": "SELECT METRICS ..."}],
    "results": {
        "schema": [
            {"name": "product_category", "type": "utf8"},
            {"name": "total_revenue",    "type": "float"}
        ],
        "rows": [
            {"product_category": "Electronics", "total_revenue": 5126.5}
        ]
    }
}
```

Result schemas intentionally include only `name` and `type`; column metadata is
discoverable from `POST /views/{view_name}`.

### `POST /views/{view_name}/row-count`

Identical request body to `…/query`; returns a single-row table with a
`COUNT` column.

### `POST /views/{view_name}/values`

Distinct values for a dimension, optionally filtered.

Request:

```json
{
    "additional_configuration": {},
    "dimension": "sales.region",
    "filters":   []
}
```

Response: a `SemanticResult` whose `rows` contain the unique values.

### `POST /views/{view_name}/compatible-metrics`

Request:

```json
{
    "additional_configuration": {},
    "selected_metrics":    ["sales.total_revenue"],
    "selected_dimensions": ["sales.region"]
}
```

Response: an array of metric objects.

### `POST /views/{view_name}/compatible-dimensions`

Same shape as `compatible-metrics`, returning dimensions.

## Changelog

### Unreleased

- Column metadata may now be exposed on dimension and metric objects returned
  by `POST /views/{view_name}`. The optional `metadata` object currently
  standardises `unit` for display units and `filter` for UI filter-building
  hints, while allowing unknown keys for future extension.
- Result schemas remain metadata-free. Clients should discover column metadata
  from `POST /views/{view_name}` and use `results.schema` only for tabular
  output column names and Arrow type names.
- Arrow types are reported using the Arrow JSON type object's `name` value
  (`int`, `float`, `utf8`, `date`, `timestamp`, …), not PyArrow's canonical
  string representation (`int64`, `double`, `string`, `date32[day]`, …).

## Conformance

A server is conformant if, for every method on `SemanticView`, the
corresponding endpoint:

1. resolves metric/dimension references by id against the view's
   `get_metrics()` / `get_dimensions()` before invoking the underlying call;
2. returns `SemanticResult` payloads with the request log preserved verbatim.
