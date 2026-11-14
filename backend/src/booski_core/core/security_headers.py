"""Security headers on every response.

API responses are data, never pages: they forbid everything a browser could do with them (no scripts,
no framing, no caching). Web-app pages get a Content Security Policy that only allows this origin's own
scripts, plus the Google Fonts stylesheet and HTTPS images the design uses.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

API_PREFIX = "/api/"
# Interactive API docs (development only) load Swagger UI from a CDN, so they keep the browser defaults.
DOCS_PATHS = frozenset({"/api/docs", "/api/docs/oauth2-redirect", "/api/openapi.json"})

COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",  # for browsers without CSP frame-ancestors support
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

APP_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        # Inline style attributes are used by the animation library and for computed colours/sizes.
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

# Built assets have content hashes in their names, so they never change and can be cached for a year.
IMMUTABLE_PREFIX = "/assets/"
HSTS = "max-age=31536000; includeSubDomains"


def install_security_headers(app: FastAPI, *, production: bool) -> None:
    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        path = request.url.path
        headers = response.headers
        for name, value in COMMON_HEADERS.items():
            headers.setdefault(name, value)
        if path in DOCS_PATHS:
            pass
        elif path.startswith(API_PREFIX):
            headers["Content-Security-Policy"] = API_CSP
            # Authenticated data must never be stored by the browser or an intermediate proxy.
            headers["Cache-Control"] = "no-store"
        else:
            headers["Content-Security-Policy"] = APP_CSP
            if path.startswith(IMMUTABLE_PREFIX) and response.status_code == 200:
                headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                headers["Cache-Control"] = "no-cache"  # always revalidate index.html, so deploys take effect
        if production:
            # Production is only supported behind HTTPS (the session cookie is Secure-only).
            headers["Strict-Transport-Security"] = HSTS
        return response
