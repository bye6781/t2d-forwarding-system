from fastapi import APIRouter, Depends

from app.core.dependencies import get_platform_admin
from app.modules.platform.schemas import PlatformPlanUpdate, PlatformStatusUpdate
from app.modules.tenants.schemas import MemberCreate, MemberUpdate
from app.modules.platform.service import platform_service
from app.shared.responses import success


router = APIRouter(tags=["Platform"])


@router.get("/stats")
async def stats(user=Depends(get_platform_admin)):
    return success(await platform_service.stats())


@router.get("/tenants")
async def tenants(user=Depends(get_platform_admin)):
    return success(await platform_service.tenants())


@router.put("/tenants/{tenant_id}/plan")
async def update_plan(tenant_id: int, payload: PlatformPlanUpdate, user=Depends(get_platform_admin)):
    return success(await platform_service.update_plan(tenant_id, payload.plan))


@router.put("/tenants/{tenant_id}/status")
async def update_status(tenant_id: int, payload: PlatformStatusUpdate, user=Depends(get_platform_admin)):
    return success(await platform_service.update_status(tenant_id, payload.status))


@router.get("/tenants/{tenant_id}/members")
async def members(tenant_id: int, user=Depends(get_platform_admin)):
    return success(await platform_service.members(tenant_id))


@router.post("/tenants/{tenant_id}/members")
async def create_member(tenant_id: int, payload: MemberCreate, user=Depends(get_platform_admin)):
    return success(await platform_service.create_member(tenant_id, payload))


@router.put("/tenants/{tenant_id}/members/{member_id}")
async def update_member(tenant_id: int, member_id: int, payload: MemberUpdate, user=Depends(get_platform_admin)):
    return success(await platform_service.update_member(tenant_id, member_id, payload))


@router.delete("/tenants/{tenant_id}/members/{member_id}")
async def delete_member(tenant_id: int, member_id: int, user=Depends(get_platform_admin)):
    await platform_service.delete_member(tenant_id, member_id)
    return success({"message": "成员已删除"})
