"""Async PostgreSQL connection and tenant-scoped query primitives."""
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from app.core.tenant_context import TenantContext

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://t2d:t2d-saas-2026@localhost:5432/t2d_saas",
)


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=20,
            command_timeout=30,
            init=self._init_connection,
        )
        logger.info("Database connection pool created")

    @staticmethod
    async def _init_connection(connection: asyncpg.Connection) -> None:
        for type_name in ("json", "jsonb"):
            await connection.set_type_codec(
                type_name,
                schema="pg_catalog",
                encoder=json.dumps,
                decoder=json.loads,
                format="text",
            )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._pool

    @asynccontextmanager
    async def transaction(self):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def execute(self, query: str, *args: Any):
        return await self.pool.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        return [dict(row) for row in await self.pool.fetch(query, *args)]

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(query, *args)
        return dict(row) if row else None

    async def fetchval(self, query: str, *args: Any):
        return await self.pool.fetchval(query, *args)

    async def t_execute(self, query: str, *args: Any, tenant_id: int | None = None):
        return await self.execute(query, self._tenant_id(tenant_id), *args)

    async def t_fetch(
        self, query: str, *args: Any, tenant_id: int | None = None
    ) -> list[dict[str, Any]]:
        return await self.fetch(query, self._tenant_id(tenant_id), *args)

    async def t_fetchrow(
        self, query: str, *args: Any, tenant_id: int | None = None
    ) -> dict[str, Any] | None:
        return await self.fetchrow(query, self._tenant_id(tenant_id), *args)

    async def t_fetchval(self, query: str, *args: Any, tenant_id: int | None = None):
        return await self.fetchval(query, self._tenant_id(tenant_id), *args)

    @staticmethod
    def _tenant_id(explicit: int | None) -> int:
        return explicit if explicit is not None else TenantContext.require()


database = Database()
