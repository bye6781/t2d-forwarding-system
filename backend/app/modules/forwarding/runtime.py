from typing import Protocol

from redis.asyncio import Redis

from app.core.config import settings


class RuntimeStore(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...
    async def set_once(self, key: str, value: str, ttl_seconds: int) -> bool: ...


class InMemoryRuntimeStore:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._values.get(key)

    async def set(self, key: str, value: str) -> None:
        self._values[key] = value

    async def set_once(self, key: str, value: str, ttl_seconds: int) -> bool:
        if key in self._values:
            return False
        self._values[key] = value
        return True


class RedisRuntimeStore:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def get(self, key: str) -> str | None:
        value = await self.client.get(key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    async def set(self, key: str, value: str) -> None:
        await self.client.set(key, value)

    async def set_once(self, key: str, value: str, ttl_seconds: int) -> bool:
        return bool(await self.client.set(key, value, nx=True, ex=ttl_seconds))


class TenantRuntimeState:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    @staticmethod
    def _key(tenant_id: int) -> str:
        return f"t2d:tenant:{tenant_id}:forwarding"

    async def start(self, tenant_id: int) -> None:
        await self.store.set(self._key(tenant_id), "running")

    async def stop(self, tenant_id: int) -> None:
        await self.store.set(self._key(tenant_id), "stopped")

    async def is_running(self, tenant_id: int) -> bool:
        return await self.store.get(self._key(tenant_id)) == "running"

    async def claim_message(self, tenant_id: int, chat_id: int, message_id: int) -> bool:
        key = f"t2d:dedupe:{tenant_id}:{chat_id}:{message_id}"
        return await self.store.set_once(key, "1", 86400)


redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
tenant_runtime = TenantRuntimeState(RedisRuntimeStore(redis_client))
