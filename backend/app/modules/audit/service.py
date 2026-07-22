import csv
import io

from app.modules.audit.repository import audit_repository


class AuditService:
    async def export(self, tenant_id: int) -> str:
        rows, _ = await audit_repository.operations(tenant_id, 5000, 0)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["created_at", "username", "action", "target", "detail"])
        for row in rows:
            writer.writerow([row.get(key) for key in ("created_at", "username", "action", "target", "detail")])
        return "\ufeff" + output.getvalue()


audit_service = AuditService()
