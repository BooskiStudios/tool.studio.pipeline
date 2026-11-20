"""Application factory. Run with ``booski serve`` or ``uvicorn booski_core.main:create_app --factory``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from booski_core import __version__, health
from booski_core.config import Settings, get_settings
from booski_core.core.errors import install_error_handlers
from booski_core.core.frontend import install_frontend
from booski_core.core.origin import install_origin_check
from booski_core.core.request_id import install_request_id
from booski_core.core.security_headers import install_security_headers
from booski_core.db import create_db_engine, create_session_factory
from booski_core.modules.activity.router import router as activity_router
from booski_core.modules.agents.router import agents_router, runs_router, tools_router
from booski_core.modules.ai.providers import build_providers
from booski_core.modules.ai.router import router as ai_router
from booski_core.modules.approvals.router import router as approvals_router
from booski_core.modules.decisions.router import router as decisions_router
from booski_core.modules.departments.router import router as departments_router
from booski_core.modules.identity.router import router as auth_router
from booski_core.modules.knowledge.router import router as documents_router
from booski_core.modules.memory.router import router as memory_router
from booski_core.modules.milestones.router import router as milestones_router
from booski_core.modules.projects.router import router as projects_router
from booski_core.modules.retrieval.router import context_router, search_router
from booski_core.modules.tasks.router import router as tasks_router
from booski_core.modules.workspaces.router import invitations_router, workspace_router, workspaces_router

ROUTERS = (
    health.router,
    auth_router,
    workspaces_router,
    workspace_router,
    invitations_router,
    departments_router,
    projects_router,
    milestones_router,
    tasks_router,
    documents_router,
    decisions_router,
    approvals_router,
    activity_router,
    ai_router,
    memory_router,
    search_router,
    context_router,
    agents_router,
    runs_router,
    tools_router,
)

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
    # AI providers with a key on this server (PR 3.2). Tests replace this with fakes.
    app.state.ai_providers = build_providers(settings)

    # Middleware added last runs first: request ids wrap everything, including origin rejections.
    install_origin_check(app, settings.allowed_origins)
    install_request_id(app)
    install_security_headers(app, production=settings.is_production)
    install_error_handlers(app)

    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    # Last, so its catch-all route never shadows an API route.
    if settings.frontend_dist is not None:
        install_frontend(app, settings.frontend_dist)
    return app
