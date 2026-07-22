from fastapi import APIRouter, Depends, Request

from app.core.dependencies import get_current_user
from app.modules.auth.schemas import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.modules.auth.service import auth_service
from app.shared.responses import success


router = APIRouter(tags=["Authentication"])


@router.post("/register")
async def register(payload: RegisterRequest):
    return success(await auth_service.register(payload))


@router.post("/login")
async def login(payload: LoginRequest, request: Request):
    return success(await auth_service.login(
        payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return success(await auth_service.me(user))


@router.put("/password")
async def change_password(payload: ChangePasswordRequest, user=Depends(get_current_user)):
    await auth_service.change_password(user, payload)
    return success({"message": "密码已更新"})
