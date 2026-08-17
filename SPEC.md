# Semantic Layer REST API

This specification describes a simple REST API for accessing a semantic layer and associated semantic views (models/cubes/etc., depending on the terminology used). It was built in order to integrate [Apache Superset](https://superset.apache.org/) with [DataJunction](https://datajunction.io/), but is generic enough to be implemented in other semantic layers and accessed by other clients.

Because it was built with Superset as its first client, it maps the Python interface 1:1 with the REST calls:

## Concepts

| Python                  | REST resource                               |
| ----------------------- | ------------------------------------------- |
| `SemanticView`          | `/views/{view_name}`                        |
| `Dimension`, `Metric`   | Embedded objects, keyed by stable `id`      |
| `SemanticQuery`         | Request body of `/views/{view_name}/query`  |
| `SemanticResult`        | Response wrapping `requests` + tabular data |

The API assumes the semantic layer is already properly configured. Some semantic layers, like Snowflake, might require additional runtime configuration. For example, Snowflake might have been configured without a default schema, so when listing semantic views it's necessary to pass additional configuration specifying the schema. This information is usually provided through a sidechannel. For Snowflake the Superset semantic layer extension uses the stored credentials and stored configuration to figure out which schemas are available, and prompts the user to choose one when browsing available views. I assume most semantic layers will ignore the extra configuration until the day additional complexity makes it necessary.

The extra configuration payload is called `runtime_configuration` when exploring views (since the configuration is transient), and `additional_configuration` when querying a specific semantic view (since the information is likely stored in the client). In retrospect, from the point of view of the semantic layer the difference is inconsequential, and we should have used `extra_configuration` for both. We might simplify it in the future.

## Media types

All payloads are JSON (`application/json`). Tabular results use:

```json
{
    "schema": [{"name": "<col>", "type": "<arrow-type-name>"}],
    "rows":   [{"<col>": <value>, ...}]
}
```

Arrow types are reported using the Arrow JSON type object's `name` value (`int`, `floating`, `utf8`, `date`, `timestamp`, …), without precision or unit parameters. Temporal values are serialised as ISO 8601 strings.

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

Lists semantic views. `POST` is used because the runtime configuration is a free-form JSON object.

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

Superset has the concept of [features](https://github.com/apache/superset/blob/97eafd6140085f81ec3e70c85215cd5e6a5608fb/superset-core/src/superset_core/semantic_layers/view.py#L33-L40) for semantic layers. They currently include:

- `ADHOC_EXPRESSIONS_IN_ORDERBY`
- `GROUP_LIMIT`
- `GROUP_OTHERS`

`GROUP_LIMIT` is a feature that allows specifying separate filter constraints for the group limit subquery. This is useful when you want to determine the top N groups using different criteria (e.g., a different time range) than the main query. For example, you might want to find the top 10 products by sales over the last 30 days, but then show daily sales for those products over the last 7 days. `GROUP_OTHERS` is an additional feature that allows the remaining categories to be grouped together in an "others" bucket. Since the implementation of these features is not trivial, they are considered optional.

(`ADHOC_EXPRESSIONS_IN_ORDERBY` should be self-explanatory.)

### `POST /views/{view_name}`

Returns a view's metadata. The body carries any `additional_configuration` the view needs to materialise (often `{}`).

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
                "display_name": "Product category",
                "semantic_type": "category",
                "filter": {
                    "kind": "select",
                    "operators": ["=", "!=", "IN", "NOT IN", "IS NULL", "IS NOT NULL"],
                    "default_operator": "IN",
                    "multi": true
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
            "type": "floating",
            "metadata": {
                "display_name": "Total revenue",
                "semantic_type": "currency",
                "unit": {"kind": "currency", "code": "USD"},
                "attributes": ["certified", "core"],
                "format": {
                    "preset": "currency",
                    "precision": 2,
                    "scale": 1
                },
                "filter": {
                    "kind": "range",
                    "operators": ["=", "!=", ">", ">=", "<", "<=", "between"],
                    "default_operator": "between"
                },
                "extensions": {
                    "superset": {"d3format": "$,.2f"},
                    "google_sheets": {
                        "numberFormat": {
                            "type": "CURRENCY",
                            "pattern": "$#,##0.00"
                        }
                    }
                }
            },
            "definition": "SUM(revenue)",
            "description": "Total sales revenue.",
            "aggregation": null
        }
    ]
}
```

The `metadata` attribute is optional and omitted when empty. Top-level metadata is strict: servers should emit only the documented keys below. Producer-specific, experimental, and client-native annotations belong under `extensions`.

| Key | Meaning |
| --- | ------- |
| `display_name` | Human-readable label for the column. |
| `semantic_type` | Optional business classification, such as `currency`, `percentage`, `proportion`, `count`, `duration`, `data_size`, `date`, `timestamp`, `identifier`, `category`, `url`, `boolean`, `number`, or `string`. |
| `unit` | Semantic unit object. |
| `attributes` | String tags or classifications associated with the column. |
| `format` | Presentation hints for clients that render values. |
| `filter` | UI hints for building filter controls; query semantics still use the `filters` request payload. |
| `extensions` | Namespaced objects for producer-specific, experimental, or client-native metadata. |

Units support atomic units and compound rate units:

```json
{"kind": "currency", "code": "USD"}
{"kind": "percentage"}
{"kind": "time", "code": "ms"}
{"kind": "count", "code": "clicks"}
{
    "numerator": {"kind": "data_size", "code": "MB"},
    "denominator": {"kind": "time", "code": "s"}
}
```

Known atomic unit kinds are `currency`, `time`, `data_size`, `percentage`, `proportion`, `count`, and `unitless`. `code` is optional for `currency` and `count`, required for `time` and `data_size`, and omitted for `percentage`, `proportion`, and `unitless`. Consumers that do not understand structured units may fall back to displaying the `code` if present, otherwise the `kind`.

The `metadata.format` attribute is portable and contains only `preset`, `precision`, and `scale`. `format.preset` is one of `smart_number`, `number`, `currency`, `percentage`, `duration`, or `data_size`. `format.precision` is a non-negative integer describing decimal places. `format.scale` is a numeric display multiplier; omitted means no scaling.

Native client formats live under `metadata.extensions`, for example `extensions.superset.d3format` for Superset and `extensions.google_sheets.numberFormat` for Google Sheets/Coefficient. Extension namespaces are objects keyed by stable producer or client names. Unknown top-level producer metadata should be moved under `extensions.custom`.

The `metadata.filter` attribute is advisory metadata for query builders. Initial filter hints describe controls only; dynamic value loading is intentionally outside the metadata payload. Known filter `kind` values are `text`, `number`, `range`, `date`, `datetime`, `boolean`, and `select`. Common fields are `operators`, `default_operator`, and `multi`. When present, `default_operator` must be one of `operators`; `multi` is only meaningful for `select`.

### `POST /views/{view_name}/query`

Run a semantic query and return the resulting table.

Request mirrors `SemanticQuery`, identifying metrics and dimensions by stable id:

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

Filter `column` is an id; if `type` is `HAVING` it references a metric, if `WHERE` it references a dimension. `value` is a literal, a list (for `IN` / `NOT IN`), or `null` (for `IS NULL` / `IS NOT NULL`).

The response is a `SemanticResult`:

```json
{
    "requests": [{"type": "pandas", "definition": "SELECT METRICS ..."}],
    "results": {
        "schema": [
            {"name": "product_category", "type": "utf8"},
            {"name": "total_revenue", "type": "floating"}
        ],
        "rows": [
            {"product_category": "Electronics", "total_revenue": 5126.5}
        ]
    }
}
```

Result schemas intentionally include only `name` and `type`; column metadata is discoverable from `POST /views/{view_name}`.

### `POST /views/{view_name}/row-count`

Identical request body to `…/query`; returns a single-row table with a `COUNT` column.

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

In some semantic layers not all metrics and dimensions in a given semantic view are compatible. This is true for MetricFlow, but not for Snowflake or DataJunction. When building charts in Superset this endpoint and the `compatible-dimensions` endpoint are called as metrics or dimensions are selected, narrowing down the set of valid metrics and dimensions.

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

- Column metadata may now be exposed on dimension and metric objects returned by `POST /views/{view_name}`. The optional `metadata` object now has a strict top-level contract: `display_name`, `semantic_type`, `unit`, `attributes`, `format`, `filter`, and `extensions`.
- `metadata.unit` is documented as an object-only atomic or compound unit. Consumers may tolerate legacy string units during migration, but conforming servers should not emit string units.
- Added portable `metadata.format` for presentation hints with `preset`/`precision`/`scale` fields. Native client formats such as Superset D3 and Google Sheets number formats belong under namespaced `metadata.extensions`.
- Clarified that `metadata.filter` is advisory query-builder metadata. The first version describes controls/operators/defaults only and does not embed dynamic value endpoint references.
- Result schemas remain metadata-free. Clients should discover column metadata from `POST /views/{view_name}` and use `results.schema` only for tabular output column names and Arrow type names.
- Arrow types are reported using the Arrow JSON type object's `name` value (`int`, `floating`, `utf8`, `date`, `timestamp`, …), not PyArrow's canonical string representation (`int64`, `double`, `string`, `date32[day]`, …).

## Conformance

A server is conformant if, for every method on `SemanticView`, the
corresponding endpoint:

1. resolves metric/dimension references by id against the view's `get_metrics()` / `get_dimensions()` before invoking the underlying call;
2. returns `SemanticResult` payloads with the request log preserved verbatim.
