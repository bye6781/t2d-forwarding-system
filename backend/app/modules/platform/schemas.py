from pydantic import BaseModel, Field


class PlatformPlanUpdate(BaseModel):
    plan: str = Field(pattern="^(free|basic|pro|enterprise)$")


class PlatformStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")
