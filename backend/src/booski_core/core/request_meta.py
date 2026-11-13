"""Who is calling: request id, client address and user agent, for sessions and activity events."""

import ipaddress
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
USER_AGENT_MAX = 256


@dataclass(frozen=True)
class RequestMeta:
    request_id: str | None
    ip: IpAddress | None
    user_agent: str | None


def get_request_meta(request: Request) -> RequestMeta:
    # The direct peer address. Proxy headers (X-Forwarded-For) are not trusted until a reverse proxy is
    # deliberately configured in a deployment PR; otherwise callers could forge their address.
    host = request.client.host if request.client else None
    try:
        ip: IpAddress | None = ipaddress.ip_address(host) if host else None
    except ValueError:
        ip = None
    user_agent = request.headers.get("user-agent", "")[:USER_AGENT_MAX] or None
    return RequestMeta(request_id=getattr(request.state, "request_id", None), ip=ip, user_agent=user_agent)


SYSTEM_META = RequestMeta(request_id=None, ip=None, user_agent=None)


def utcnow() -> datetime:
    return datetime.now(UTC)
