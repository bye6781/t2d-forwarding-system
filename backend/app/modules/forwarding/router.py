from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.modules.forwarding.repository import forwarding_repository
from app.modules.forwarding.schemas import RouteCreate, RouteUpdate
from app.modules.forwarding.service import forwarding_domain_service
from app.modules.tenants.entitlements import require_feature
from app.shared.responses import page, success


router = APIRouter(tags=["Forwarding"])


@router.get("/runtime")
async def runtime(user=Depends(get_current_user)):
    return success(await forwarding_domain_service.status(user))


@router.post("/runtime/start")
async def start(user=Depends(get_current_user)):
    await forwarding_domain_service.start(user)
    return success({"message": "当前租户转发已启动"})


@router.post("/runtime/stop")
async def stop(user=Depends(get_current_user)):
    await forwarding_domain_service.stop(user)
    return success({"message": "当前租户转发已停止"})


@router.get("/routes")
async def routes(user=Depends(get_current_user)):
    return success(await forwarding_domain_service.routes(user))


@router.post("/routes")
async def create_route(payload: RouteCreate, user=Depends(get_current_user)):
    return success(await forwarding_domain_service.create_route(user, payload))


@router.put("/routes/{route_id}")
async def update_route(route_id: int, payload: RouteUpdate, user=Depends(get_current_user)):
    return success(await forwarding_domain_service.update_route(user, route_id, payload))


@router.delete("/routes/{route_id}")
async def delete_route(route_id: int, user=Depends(get_current_user)):
    await forwarding_domain_service.delete_route(user, route_id)
    return success({"message": "转发线路已删除"})


@router.get("/records")
async def records(
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
    status: str | None = None, user=Depends(get_current_user),
):
    require_feature(user, "runtime")
    rows, total = await forwarding_repository.records(user["tenant_id"], limit, offset, status)
    return page(rows, total=total, limit=limit, offset=offset)


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    return success(await forwarding_domain_service.dashboard(user))
