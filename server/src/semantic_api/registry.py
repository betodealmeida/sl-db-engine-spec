"""Boots and holds the Pandas semantic layer instance the server speaks for."""

from __future__ import annotations

from typing import Any

from litestar.exceptions import InternalServerException
from superset_core.semantic_layers import decorators
from superset_core.semantic_layers.layer import SemanticLayer


def _standalone_semantic_layer(
    id: str,  # noqa: A002
    name: str,
    description: str | None = None,
):
    _ = (id, name, description)

    def register(cls: type[SemanticLayer]) -> type[SemanticLayer]:
        return cls

    return register


decorators.semantic_layer = _standalone_semantic_layer

from betodealmeida.pandas_semantic_layer.layer import PandasSemanticLayer  # noqa: E402

_LAYER: SemanticLayer | None = None


def configure(configuration: dict[str, Any]) -> SemanticLayer:
    """Instantiate the Pandas layer with ``configuration`` and cache it."""
    global _LAYER
    _LAYER = PandasSemanticLayer.from_configuration(configuration)
    return _LAYER


def layer() -> SemanticLayer:
    if _LAYER is None:
        raise InternalServerException(detail="Semantic layer not configured.")
    return _LAYER
