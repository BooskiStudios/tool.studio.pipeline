"""Application factory. Run with ``booski serve`` or ``uvicorn booski_core.main:create_app --factory``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from booski_core import __version__, health
from booski_core.config import Settings, get_settings
from booski_core.core.errors import install_error_handlers
from booski_core.core.origin import install_origin_check
from booski_core.core.request_id import install_request_id
from booski_core.db import create_db_engine, create_session_factory
from booski_core.modules.identity.router import router as auth_router
from booski_core.modules.workspaces.router import invitations_router, workspace_router, workspaces_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_db_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    # Interactive docs and the schema are for development; they are not served in production.
    show_docs = not settings.is_production
    app = FastAPI(
        title="Booski Core",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if show_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if show_docs else None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # Middleware added last runs first: request ids wrap everything, including origin rejections.
    install_origin_check(app, settings.allowed_origins)
    install_request_id(app)
    install_error_handlers(app)

    for router in (health.router, auth_router, workspaces_router, workspace_router, invitations_router):
        app.include_router(router, prefix=API_PREFIX)
    return app
