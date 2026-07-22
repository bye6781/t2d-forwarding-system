from typing import Any

from pydantic import BaseModel, Field


class FilterRuleWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rule_type: str = Field(pattern="^(keyword_include|keyword_exclude|regex|message_type|sender|chat|legacy_config)$")
    config: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    priority: int = Field(default=10, ge=0, le=100)
    enabled: bool = True


class FilterTest(BaseModel):
    text: str = ""
    sender: str = ""
    user_id: str = ""
    message_type: str = "text"
    chat_id: str = ""


class TemplateWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    template_text: str = Field(min_length=1)
    time_format: str = "%Y-%m-%d %H:%M"
    enabled: bool = True
    is_default: bool = False


class TemplatePreview(BaseModel):
    template_id: int | None = None
    template_text: str | None = None


class MediaPolicyWrite(BaseModel):
    max_file_size_bytes: int = Field(default=52428800, ge=1, le=104857600)
    allowed_types: list[str] = Field(default_factory=lambda: ["photo", "video", "document"])
    thumbnail_enabled: bool = True
    thumbnail_max_width: int = Field(default=320, ge=64, le=4096)
    thumbnail_quality: int = Field(default=75, ge=1, le=100)
    forward_as_link: bool = False


class MediaPolicyTest(BaseModel):
    media_type: str
    file_size_bytes: int = Field(ge=0)


class TranslationPolicyWrite(BaseModel):
    enabled: bool = False
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
