"""Boots and holds the single ``SemanticLayer`` instance the server speaks for.

The Superset host normally replaces ``superset_core.semantic_layers.decorators.semantic_layer``
at startup with a real implementation. When running standalone we install our
own — a single-slot binder — *before* the layer module is imported. The
server then materialises one instance of that class via
:func:`configure` and holds it for the process lifetime.
"""

from __future__ import annotations

from typing import Any

from litestar.exceptions import InternalServerException
from superset_core.semantic_layers import decorators
from superset_core.semantic_layers.layer import SemanticLayer

_CLS: type[SemanticLayer] | None = None
_LAYER: SemanticLayer | None = None


def semantic_layer(id: str, name: str, description: str | None = None):  # noqa: A002, ARG001
    def register(cls: type[SemanticLayer]) -> type[SemanticLayer]:
        global _CLS
        _CLS = cls
        return cls

    return register


decorators.semantic_layer = semantic_layer


def configure(configuration: dict[str, Any]) -> SemanticLayer:
    """Instantiate the registered layer with ``configuration`` and cache it."""
    global _LAYER
    if _CLS is None:
        raise InternalServerException(detail="No semantic layer is registered.")
    _LAYER = _CLS.from_configuration(configuration)
    return _LAYER


def layer() -> SemanticLayer:
    if _LAYER is None:
        raise InternalServerException(detail="Semantic layer not configured.")
    return _LAYER
