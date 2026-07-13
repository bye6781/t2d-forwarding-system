"""
应用配置
"""
import os
from typing import Optional


class Settings:
    """应用配置"""

    # 数据库
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://t2d:t2d-saas-2026@localhost:5432/t2d_saas"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "t2d-saas-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # 路径
    DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "/app/logs")

    # 服务端口
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # 免费套餐配额
    FREE_MESSAGE_QUOTA: int = 100       # 每日消息数
    FREE_TG_ACCOUNT_LIMIT: int = 1      # TG 账号数
    FREE_MAPPING_LIMIT: int = 3         # 映射规则数
    FREE_BOT_LIMIT: int = 2             # 钉钉 Bot 数

    # 套餐配额
    PLAN_LIMITS: dict = {
        "free": {
            "message_quota": 100,
            "tg_account_limit": 1,
            "mapping_limit": 3,
            "bot_limit": 2,
            "member_limit": 1,
        },
        "basic": {
            "message_quota": 1000,
            "tg_account_limit": 2,
            "mapping_limit": 10,
            "bot_limit": 5,
            "member_limit": 5,
        },
        "pro": {
            "message_quota": 10000,
            "tg_account_limit": 5,
            "mapping_limit": 50,
            "bot_limit": 20,
            "member_limit": 20,
        },
        "enterprise": {
            "message_quota": 100000,
            "tg_account_limit": 20,
            "mapping_limit": 500,
            "bot_limit": 100,
            "member_limit": 100,
        },
    }

    # 套餐价格（月，美元）
    PLAN_PRICES: dict = {
        "free": 0,
        "basic": 29,
        "pro": 99,
        "enterprise": 499,
    }


settings = Settings()
