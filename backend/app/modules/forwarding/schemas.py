from pydantic import BaseModel, Field


class RouteCreate(BaseModel):
    source_chat_id: int
    target_bot_ids: list[int] = Field(min_length=1)
    translation_enabled: bool = True
    filter_enabled: bool = True
    enabled: bool = True


class RouteUpdate(BaseModel):
    source_chat_id: int | None = None
    target_bot_ids: list[int] | None = None
    translation_enabled: bool | None = None
    filter_enabled: bool | None = None
    enabled: bool | None = None
