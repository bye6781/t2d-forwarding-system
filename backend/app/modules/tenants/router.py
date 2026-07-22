from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.modules.tenants.schemas import MemberCreate, MemberUpdate, PlanUpdate
from app.modules.tenants.service import tenant_service
from app.shared.responses import success


router = APIRouter(tags=["Tenant"])


@router.get("/profile")
async def profile(user=Depends(get_current_user)):
    return success(await tenant_service.profile(user))


@router.get("/members")
async def members(user=Depends(get_current_user)):
    return success(await tenant_service.members(user))


@router.post("/members")
async def create_member(payload: MemberCreate, user=Depends(get_current_user)):
    return success(await tenant_service.create_member(user, payload))


@router.put("/members/{member_id}")
async def update_member(member_id: int, payload: MemberUpdate, user=Depends(get_current_user)):
    return success(await tenant_service.update_member(user, member_id, payload))


@router.delete("/members/{member_id}")
async def delete_member(member_id: int, user=Depends(get_current_user)):
    await tenant_service.delete_member(user, member_id)
    return success({"message": "成员已删除"})


@router.get("/usage")
async def usage(user=Depends(get_current_user)):
    return success(await tenant_service.usage(user))


@router.put("/subscription")
async def subscription(payload: PlanUpdate, user=Depends(get_current_user)):
    return success(await tenant_service.update_plan(user, payload.plan))
