from __future__ import annotations

import pytest
from litestar.exceptions import InternalServerException

from semantic_api import registry


def test_layer_raises_before_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "_LAYER", None)

    with pytest.raises(InternalServerException, match="Semantic layer not configured"):
        registry.layer()


def test_configure_uses_pandas_semantic_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "_LAYER", None)

    layer = registry.configure({})

    assert isinstance(layer, registry.PandasSemanticLayer)
    assert registry.layer() is layer


def test_create_app_does_not_require_semantic_layer_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SEMANTIC_LAYER_MODULE", raising=False)
    monkeypatch.delenv("SEMANTIC_LAYER_CONFIGURATION", raising=False)

    from semantic_api.app import create_app

    assert create_app() is not None
