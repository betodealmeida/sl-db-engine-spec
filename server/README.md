# Semantic Layer REST API

A Litestar reference implementation of the protocol described in
[`SPEC.md`](./SPEC.md). A server speaks for exactly one already-configured
`SemanticLayer` instance; this build is wired up to the Pandas semantic
layer.

## Run

```bash
pip install -e ../../superset/superset-core
pip install -e ../backend
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
