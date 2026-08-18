"""A toy OAuth2 identity provider for the reference semantic-layer server.

Enabled by setting ``SEMANTIC_LAYER_REQUIRE_AUTH=1`` before starting the
server. It implements just enough of an OAuth2 authorisation-code flow to
drive real client integrations through the dance:

1. ``GET /authorize?response_type=code&client_id=…&redirect_uri=…&state=…``
   returns a one-button HTML consent page.
2. Submitting it (``GET /authorize?…&confirmed=yes``) redirects to the
   client's ``redirect_uri`` with ``?code=<one-shot-code>&state=<state>``.
3. ``POST /token`` (form-encoded body, RFC 6749 §4.1.3) exchanges that code
   for the hard-coded bearer token.

After step 3, every request to ``/views/*`` must carry
``Authorization: Bearer <access-token>``. Otherwise the server responds
``401`` with an RFC 9457 Problem Details body the client can branch on::

    {"type": "https://semantic-layer.example/problems/oauth-required",
     "title": "Authentication required", "status": 401,
     "detail": "Bearer token required.", "code": "OAUTH_REQUIRED"}
"""

from __future__ import annotations

import os
import secrets
from typing import Annotated, Any
from urllib.parse import urlencode

from litestar import Controller, MediaType, Response, get, post
from litestar.connection import ASGIConnection
from litestar.enums import RequestEncodingType
from litestar.handlers.base import BaseRouteHandler
from litestar.params import Body, Parameter
from litestar.plugins.problem_details import ProblemDetailsException
from litestar.response import Redirect

# Hard-coded credentials for the toy IdP. These would never live in source
# code on a real server.
CLIENT_ID = "demo-client"
CLIENT_SECRET = "demo-secret"  # noqa: S105
ACCESS_TOKEN = "demo-access-token"  # noqa: S105
REFRESH_TOKEN = "demo-refresh-token"  # noqa: S105
TOKEN_LIFETIME = 3600

# Codes are single-use; we keep them in-memory.
_PENDING_CODES: set[str] = set()
_PROBLEM_TYPE_BASE = "https://semantic-layer.example/problems"


def auth_problem(
    *,
    detail: str,
    code: str,
    title: str = "Authentication required",
) -> ProblemDetailsException:
    """Build an RFC 9457 auth problem response."""
    return ProblemDetailsException(
        detail=detail,
        status_code=401,
        title=title,
        type_=f"{_PROBLEM_TYPE_BASE}/{code.lower().replace('_', '-')}",
        extra={"code": code},
        headers={"WWW-Authenticate": "Bearer"},
    )


def auth_required() -> bool:
    """Whether the server is configured to require a bearer token."""
    return os.environ.get("SEMANTIC_LAYER_REQUIRE_AUTH", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def require_bearer(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Litestar guard: enforce the ``Authorization`` header on view routes."""
    if not auth_required():
        return
    header = connection.headers.get("authorization", "")
    if header != f"Bearer {ACCESS_TOKEN}":
        raise auth_problem(
            detail="Bearer token required.",
            code="OAUTH_REQUIRED",
        )


class AuthController(Controller):
    """The ``/authorize`` and ``/token`` endpoints."""

    tags = ["oauth2"]

    @get("/authorize", media_type=MediaType.HTML, status_code=200)
    async def authorize(
        self,
        response_type: str = "code",
        client_id: str = "",
        redirect_uri: str = "",
        oauth_state: Annotated[str, Parameter(query="state")] = "",
        oauth_scope: Annotated[str, Parameter(query="scope")] = "",
        confirmed: str = "",
    ) -> Response[Any]:
        if response_type != "code":
            raise auth_problem(
                detail=f"Unsupported response_type {response_type!r}.",
                code="UNSUPPORTED_RESPONSE_TYPE",
            )

        if confirmed.lower() not in {"yes", "true", "1"}:
            params = urlencode(
                {
                    "response_type": response_type,
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "state": oauth_state,
                    "scope": oauth_scope,
                    "confirmed": "yes",
                },
            )
            body = (
                "<!doctype html><html><body>"
                f"<h1>Authorize {client_id or 'client'}?</h1>"
                f"<p>Scope: {oauth_scope or '(none)'}.</p>"
                f'<p><a href="/authorize?{params}">Authorize</a></p>'
                "</body></html>"
            )
            return Response(content=body, media_type=MediaType.HTML)

        code = secrets.token_urlsafe(16)
        _PENDING_CODES.add(code)
        separator = "&" if "?" in redirect_uri else "?"
        location = (
            f"{redirect_uri}{separator}"
            f"{urlencode({'code': code, 'state': oauth_state})}"
        )
        return Redirect(path=location)

    @post("/token", status_code=200)
    async def token(
        self,
        data: Annotated[
            dict[str, str],
            Body(media_type=RequestEncodingType.URL_ENCODED),
        ],
    ) -> dict[str, Any]:
        grant_type = data.get("grant_type", "")
        if grant_type == "authorization_code":
            code = data.get("code", "")
            if code not in _PENDING_CODES:
                raise auth_problem(
                    detail="Invalid authorization code.",
                    code="INVALID_AUTHORIZATION_CODE",
                )
            _PENDING_CODES.discard(code)
        elif grant_type == "refresh_token":
            if data.get("refresh_token") != REFRESH_TOKEN:
                raise auth_problem(
                    detail="Invalid refresh token.",
                    code="INVALID_REFRESH_TOKEN",
                )
        else:
            raise auth_problem(
                detail=f"Unsupported grant_type {grant_type!r}.",
                code="UNSUPPORTED_GRANT_TYPE",
            )

        if data.get("client_id") != CLIENT_ID or data.get("client_secret") != CLIENT_SECRET:
            raise auth_problem(
                detail="Invalid client credentials.",
                code="INVALID_CLIENT_CREDENTIALS",
            )

        return {
            "access_token": ACCESS_TOKEN,
            "token_type": "Bearer",
            "expires_in": TOKEN_LIFETIME,
            "refresh_token": REFRESH_TOKEN,
        }
