from __future__ import annotations

from litestar.testing import TestClient

from semantic_api.app import create_app


def test_missing_bearer_token_returns_problem_details(monkeypatch) -> None:
    monkeypatch.setenv("SEMANTIC_LAYER_REQUIRE_AUTH", "1")

    with TestClient(create_app()) as client:
        response = client.post("/views/list", json={"runtime_configuration": {}})

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "type": "https://semantic-layer.example/problems/oauth-required",
        "title": "Authentication required",
        "status": 401,
        "detail": "Bearer token required.",
        "code": "OAUTH_REQUIRED",
    }


def test_invalid_token_request_returns_problem_details(monkeypatch) -> None:
    monkeypatch.delenv("SEMANTIC_LAYER_REQUIRE_AUTH", raising=False)

    with TestClient(create_app()) as client:
        response = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": "unknown-code",
                "client_id": "demo-client",
                "client_secret": "demo-secret",
            },
        )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": (
            "https://semantic-layer.example/problems/"
            "invalid-authorization-code"
        ),
        "title": "Authentication required",
        "status": 401,
        "detail": "Invalid authorization code.",
        "code": "INVALID_AUTHORIZATION_CODE",
    }
