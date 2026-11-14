"""Serves the built web app (``npm run build`` → ``dist/``) from the same origin as the API.

One origin means the session cookie and CSRF protection work without any cross-origin configuration.
Unknown paths return ``index.html`` so the app's own router can handle deep links such as
``/projects/horizon`` (a "single-page app fallback"). Paths under ``/api/`` are never answered here.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response

from booski_core.core.errors import problem_response


class FrontendNotBuiltError(RuntimeError):
    pass


def install_frontend(app: FastAPI, dist: Path) -> None:
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise FrontendNotBuiltError(
            f"BOOSKI_FRONTEND_DIST is {dist}, but it has no index.html. Run `npm run build` first."
        )

    @app.get("/{path:path}", include_in_schema=False)
    async def web_app(path: str, request: Request) -> Response:
        if path == "api" or path.startswith("api/"):
            return problem_response(request, 404)
        candidate = (root / path).resolve()
        # Only files inside dist/ (no "../" escapes, no directories).
        if path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        if Path(path).suffix:  # a missing file such as /assets/old-1234.js: don't answer it with HTML
            return problem_response(request, 404)
        return FileResponse(index, media_type="text/html")
