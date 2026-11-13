"""Gives every request an id (``X-Request-ID``) for logs, error bodies and, later, activity events."""

import re
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

HEADER = "X-Request-ID"
_VALID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def install_request_id(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(HEADER, "")
        request_id = incoming if _VALID.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[HEADER] = request_id
        return response
