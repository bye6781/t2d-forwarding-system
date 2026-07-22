"""
翻译服务 - DeepSeek API（多租户版）
每个租户独立配置 API Key，按租户计费翻译字符数
"""
import logging
import re
from typing import Optional

import aiohttp

from app.core.tenant_context import TenantContext
from app.modules.policies.repository import policy_repository

logger = logging.getLogger(__name__)


def is_chinese(text: str) -> bool:
    if not text:
        return False
    chinese_chars = len(re.findall(r"[一-鿿]", text))
    total_chars = len(text.replace(" ", "").replace("\n", ""))
    if total_chars == 0:
        return False
    return chinese_chars / total_chars > 0.3


class TranslationService:
    """多租户翻译服务 - 按租户加载配置"""

    def __init__(self):
        self._cache = {}
        self._cache_max_size = 5000
        self._config_cache = {}  # tenant_id -> config dict

    async def _get_tenant_config(self, tenant_id: int) -> Optional[dict]:
        """获取租户翻译配置（带内存缓存）"""
        if tenant_id in self._config_cache:
            return self._config_cache[tenant_id]

        config = await policy_repository.translation(tenant_id)
        if config:
            self._config_cache[tenant_id] = config
        return config

    def invalidate_cache(self, tenant_id: int = None):
        """清除缓存（配置更新时调用）"""
        if tenant_id:
            self._config_cache.pop(tenant_id, None)
        else:
            self._config_cache.clear()

    async def translate(self, text: str, target_lang: str = "中文") -> Optional[str]:
        """翻译文本（自动使用当前租户的配置）"""
        tenant_id = TenantContext.get()

        config = await self._get_tenant_config(tenant_id)
        if not config or not config.get("api_key"):
            logger.debug(f"Translation not configured for tenant {tenant_id}")
            return text

        if not config.get("enabled", True):
            return text

        if target_lang in ("中文", "zh", "chinese", "zh-cn") and is_chinese(text):
            return text

        cache_key = f"{tenant_id}:{text}:{target_lang}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        api_key = config["api_key"]
        base_url = config.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        model = config.get("model", "deepseek-chat")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": f"你是一个专业翻译，请将以下内容翻译成{target_lang}。保留数字、符号、emoji不变。保持原文格式。"},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    result = await resp.json()
                    if not resp.ok:
                        logger.error(f"Translation API error: {resp.status}")
                        return text

                    choices = result.get("choices")
                    if not choices:
                        return text

                    translated = choices[0].get("message", {}).get("content", "")
                    if not translated:
                        return text

                    # 缓存
                    if len(self._cache) >= self._cache_max_size:
                        keys_to_remove = list(self._cache.keys())[:self._cache_max_size // 2]
                        for k in keys_to_remove:
                            del self._cache[k]
                    self._cache[cache_key] = translated

                    return translated

        except Exception as e:
            logger.error(f"Translation failed for tenant {tenant_id}: {e}")
            return text


translation_service = TranslationService()
