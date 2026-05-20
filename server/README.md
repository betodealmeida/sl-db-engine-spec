# Semantic Layer REST API

A Litestar reference implementation of the protocol described in
[`SPEC.md`](./SPEC.md). A server speaks for exactly one already-configured
`SemanticLayer` instance; the layer implementation is supplied by the
operator at startup.

## Run

```bash
pip install -e /path/to/superset/superset-core
pip install -e .

# also install whichever semantic layer implementation you want to serve, e.g.
pip install -e /path/to/pandas-semantic-layer/backend

# required: module whose import triggers a @semantic_layer registration
export SEMANTIC_LAYER_MODULE=betodealmeida.pandas_semantic_layer.layer

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
curl localhost:8000/views/list -H 'content-type: application/json' -d '{}'

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
