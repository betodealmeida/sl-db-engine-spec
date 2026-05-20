"""Litestar application factory."""

from __future__ import annotations

import json
import os
from typing import Any

from litestar import Litestar
from litestar.openapi import OpenAPIConfig

from semantic_api import registry
from semantic_api.auth import AuthController
from semantic_api.controllers import ViewsController


def _load_pandas_layer() -> None:
    """Import the Pandas semantic layer so its ``@semantic_layer`` runs."""
    import betodealmeida.pandas_semantic_layer.layer  # noqa: F401


def _read_configuration() -> dict[str, Any]:
    raw = os.environ.get("SEMANTIC_LAYER_CONFIGURATION")
    return json.loads(raw) if raw else {}


def create_app() -> Litestar:
    _load_pandas_layer()
    registry.configure(_read_configuration())

    return Litestar(
        route_handlers=[AuthController, ViewsController],
        openapi_config=OpenAPIConfig(
            title="Semantic Layer API",
            version="0.1.0",
            description="REST interface for a Superset semantic layer.",
        ),
        logging_config=None,
    )


app = create_app()
