"""Uniform error responses using RFC 9457 problem details (``application/problem+json``)."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"

logger = logging.getLogger("booski_core.errors")


class ProblemError(Exception):
    """Raise from services and dependencies to return a problem+json response.

    ``detail`` is shown to the caller, so it must explain the problem without revealing internals.
    """

    def __init__(
        self, status: int, detail: str | None = None, *, headers: dict[str, str] | None = None, **extra: Any
    ) -> None:
        super().__init__(detail or HTTPStatus(status).phrase)
        self.status = status
        self.detail = detail
        self.headers = headers
        self.extra = extra


def problem_response(
    request: Request,
    status: int,
    *,
    detail: str | None = None,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": HTTPStatus(status).phrase, "status": status}
    if detail:
        body["detail"] = detail
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        body["request_id"] = request_id
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # registered for this type only
        raise exc
    detail = (
        exc.detail
        if isinstance(exc.detail, str) and exc.detail != HTTPStatus(exc.status_code).phrase
        else None
    )
    return problem_response(request, exc.status_code, detail=detail, headers=getattr(exc, "headers", None))


async def _validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # registered for this type only
        raise exc
    # Only location, message and type: never echo submitted values (they may be passwords or secrets).
    errors = [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in exc.errors()
    ]
    return problem_response(request, 422, detail="The request is invalid.", errors=errors)


async def _problem_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ProblemError):  # registered for this type only
        raise exc
    return problem_response(request, exc.status, detail=exc.detail, headers=exc.headers, **exc.extra)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled error (request_id=%s)", getattr(request.state, "request_id", "-"), exc_info=exc
    )
    return problem_response(
        request, 500, detail="An unexpected error occurred. Quote the request_id when reporting it."
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ProblemError, _problem_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
