from pydantic import BaseModel, Field


class TelegramAccountCreate(BaseModel):
    name: str = Field(default="default", min_length=1, max_length=100)
    api_id: int
    api_hash: str = Field(min_length=8)
    phone: str = Field(min_length=5, max_length=32)


class TelegramAccountAction(BaseModel):
    code: str | None = None
    password: str | None = None


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    webhook: str = Field(min_length=10)
    secret: str = ""
    enabled: bool = True


class BotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    webhook: str | None = Field(default=None, min_length=10)
    secret: str | None = None
    enabled: bool | None = None


class BotTest(BaseModel):
    message: str = "T2D Cloud 测试消息"
