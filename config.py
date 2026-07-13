"""
应用配置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "T2D SaaS"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    API_PORT: int = 8000
    LOGS_DIR: str = "/app/logs"

    # 数据库
    DATABASE_URL: str = "postgresql://t2d:t2d-saas-2026@localhost:5432/t2d_saas"

    # JWT
    SECRET_KEY: str = "t2d-saas-secret-key-2026-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # 管理员
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_TENANT_SLUG: str = "platform"

    # 免费版限制
    FREE_MESSAGE_QUOTA: int = 100
    FREE_TG_ACCOUNT_LIMIT: int = 1
    FREE_MAPPING_LIMIT: int = 3
    FREE_BOT_LIMIT: int = 2

    # 订阅套餐（仅两个版本：免费版 + 付费版）
    PLAN_LIMITS: dict = {
        "free": {"message_quota": 100, "tg_account_limit": 1, "mapping_limit": 3, "bot_limit": 2, "member_limit": 1},
        "paid": {"message_quota": 999999, "tg_account_limit": 999999, "mapping_limit": 999999, "bot_limit": 999999, "member_limit": 999999},
    }
    PLAN_PRICES: dict = {"free": 0, "paid": 99}

    class Config:
        env_file = ".env"


settings = Settings()
