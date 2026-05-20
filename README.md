# sl-db-engine-spec

Bundles the three pieces that let Apache Superset talk to a Semantic Layer
REST API server:

| Layer       | Module                            | Plugin host           |
| ----------- | --------------------------------- | --------------------- |
| HTTP client | `sl_db_engine_spec.adapter`       | Shillelagh            |
| SQL bridge  | `sl_db_engine_spec.dialect`       | SQLAlchemy            |
| Superset UI | `sl_db_engine_spec.engine_spec`   | Superset              |

Each piece is registered through the standard entry-point group for its host
(`shillelagh.adapter`, `sqlalchemy.dialects`, `superset.db_engine_specs`), so
installing this package is all that's needed — no patching, no manual import.

## Install

In your Superset environment:

```bash
pip install sl-db-engine-spec
```

Restart Superset and the **Semantic Layer API** entry will show up in the
"Connect a database" dialog.

## Connection parameters

The connection form asks for:

- **Host** (required) — e.g. `localhost`
- **Port** — optional
- **Secure** — toggle for HTTPS
- **Additional configuration** — JSON object forwarded to the server on every
  request (sent as `runtime_configuration` when listing views and as
  `additional_configuration` for each view).
- **OAuth2 client information** — `{id, secret, scope?}`. The
  `authorization_request_uri` and `token_request_uri` are auto-filled from
  the host:port as `http(s)://host:port/authorize` and `.../token`; explicit
  overrides are preserved.

## URL form

If you'd rather skip the form, the equivalent SQLAlchemy URL is:

```
semanticapi://<host>[:port]/?secure=<true|false>&additional_configuration=<urlencoded JSON>
```

## Standalone use (no Superset)

The adapter and dialect work without Superset:

```python
from sqlalchemy import create_engine, text

engine = create_engine("semanticapi://localhost:8000/")
with engine.connect() as c:
    print(c.execute(text("SELECT region, total_revenue FROM sales")).fetchall())
```

OAuth2 access tokens can be passed in the URL as `?access_token=...`.
