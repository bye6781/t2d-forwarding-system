from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.dependencies import get_current_user, require_feature_access
from app.modules.audit.repository import audit_repository
from app.modules.audit.service import audit_service
from app.shared.responses import page, success


router = APIRouter(tags=["Audit"], dependencies=[Depends(require_feature_access("audit"))])


@router.get("/operations")
async def operations(
    limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0),
    action: str | None = None, user=Depends(get_current_user),
):
    rows, total = await audit_repository.operations(user["tenant_id"], limit, offset, action)
    return page(rows, total=total, limit=limit, offset=offset)


@router.get("/logins")
async def logins(
    limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    rows, total = await audit_repository.logins(user["tenant_id"], limit, offset)
    return page(rows, total=total, limit=limit, offset=offset)


@router.get("/requests")
async def requests(
    limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    rows, total = await audit_repository.api(user["tenant_id"], limit, offset)
    return page(rows, total=total, limit=limit, offset=offset)


@router.get("/summary")
async def summary(days: int = Query(default=7, ge=1, le=90), user=Depends(get_current_user)):
    return success(await audit_repository.summary(user["tenant_id"], days))


@router.get("/export")
async def export(user=Depends(get_current_user)):
    return Response(
        await audit_service.export(user["tenant_id"]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
