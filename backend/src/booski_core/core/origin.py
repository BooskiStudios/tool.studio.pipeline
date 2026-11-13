"""Blocks state-changing browser requests sent from other websites (cross-site request forgery).

This is the first CSRF layer and the only one for endpoints used before a session exists (sign-in,
accepting an invitation). Signed-in requests are also checked against a per-session CSRF token.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from booski_core.core.errors import problem_response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def install_origin_check(app: FastAPI, allowed_origins: list[str]) -> None:
    allowed = {origin.rstrip("/") for origin in allowed_origins}

    @app.middleware("http")
    async def origin_check(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        origin = request.headers.get("origin")
        # Browsers always send Origin on cross-site POST/PATCH/DELETE. Non-browser clients often omit it;
        # they cannot ride on a victim's cookies, so there is nothing to forge.
        if request.method not in SAFE_METHODS and origin is not None:
            own = f"{request.url.scheme}://{request.headers.get('host', '')}"
            if origin != own and origin not in allowed:
                return problem_response(
                    request, 403, detail="This request came from a site that isn't allowed."
                )
        return await call_next(request)
