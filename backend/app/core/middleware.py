"""Request context and audit middleware."""
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token
from app.core.tenant_context import TenantContext
from app.modules.audit.repository import audit_repository


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        finally:
            TenantContext.clear()


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Record authenticated V2 calls without affecting request success."""

    async def dispatch(self, request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        authorization = request.headers.get("authorization", "")
        if request.url.path.startswith("/api/v2/") and authorization.startswith("Bearer "):
            payload = decode_access_token(authorization[7:])
            if payload and payload.get("tenant_id") is not None and payload.get("sub"):
                try:
                    await audit_repository.record_api_request(
                        tenant_id=int(payload["tenant_id"]),
                        user_id=int(payload["sub"]),
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        duration_ms=int((time.monotonic() - started) * 1000),
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                    )
                except Exception:
                    pass
        return response
