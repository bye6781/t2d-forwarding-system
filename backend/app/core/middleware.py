"""
租户上下文中间件
确保请求结束后清理上下文，避免 contextvars 泄漏
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.tenant_context import TenantContext


class TenantContextMiddleware(BaseHTTPMiddleware):
    """在每个请求结束时清理租户上下文"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        finally:
            TenantContext.clear()


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS 中间件"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
