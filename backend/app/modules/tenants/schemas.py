from pydantic import BaseModel, Field


class MemberCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)
    email: str | None = None
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class MemberUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|member|viewer)$")
    is_active: bool | None = None


class PlanUpdate(BaseModel):
    plan: str = Field(pattern="^(free|basic|pro|enterprise)$")
