"""Litestar application factory."""

from __future__ import annotations

import importlib
import json
import os
from typing import Any

from litestar import Litestar
from litestar.openapi import OpenAPIConfig

from semantic_api import registry
from semantic_api.auth import AuthController
from semantic_api.controllers import ViewsController


def _load_layer_module() -> None:
    """Import the configured semantic layer module so its ``@semantic_layer`` runs.

    The module path is read from ``SEMANTIC_LAYER_MODULE``. Importing the module
    is expected to trigger a ``@semantic_layer`` decorator that registers the
    layer class with :mod:`semantic_api.registry`.
    """
    module = os.environ.get("SEMANTIC_LAYER_MODULE")
    if not module:
        raise RuntimeError(
            "SEMANTIC_LAYER_MODULE is not set. Point it at a module whose import "
            "registers a semantic layer (e.g. "
            "'betodealmeida.pandas_semantic_layer.layer').",
        )
    importlib.import_module(module)


def _read_configuration() -> dict[str, Any]:
    raw = os.environ.get("SEMANTIC_LAYER_CONFIGURATION")
    return json.loads(raw) if raw else {}


def create_app() -> Litestar:
    _load_layer_module()
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
