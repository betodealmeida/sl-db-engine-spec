# Semantic Layer REST API

A Litestar reference implementation of the protocol described in [`SPEC.md`](../SPEC.md). This server speaks for the Pandas semantic layer from [`betodealmeida/pandas-semantic-layer`](https://github.com/betodealmeida/pandas-semantic-layer).

## Run

```bash
# https://github.com/apache/superset
pip install -e /path/to/superset/superset-core

# install the Pandas semantic layer implementation
# https://github.com/betodealmeida/pandas-semantic-layer
pip install -e /path/to/pandas-semantic-layer/backend

pip install -e .

# optional: pass the layer's configuration as JSON
export SEMANTIC_LAYER_CONFIGURATION='{"dataset": "sales"}'

semantic-api
# or
litestar --app semantic_api.app:app run
```

OpenAPI docs are served at `/schema`. Swagger UI at `/schema/swagger`.

## Quick start

```bash
# 1. list views
curl localhost:8000/views/ -H 'content-type: application/json' -d '{}'

# 2. inspect a view
curl localhost:8000/views/sales -H 'content-type: application/json' -d '{}'

# 3. query it
curl localhost:8000/views/sales/query \
    -H 'content-type: application/json' \
    -d '{
        "query": {
            "metrics":    ["sales.total_revenue"],
            "dimensions": ["sales.product_category"]
        }
    }'
```
