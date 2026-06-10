from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from rent_manager.db.models import Lease, NotificationLog, Tenant, Unit, User
from rent_manager.db.session import SyncSessionLocal
from rent_manager.integrations.whatsapp import send_whatsapp_message
from rent_manager.workers.celery_app import celery_app


@celery_app.task(name="rent_manager.workers.tasks.leases.send_lease_expiry_alerts")
def send_lease_expiry_alerts() -> dict:
    target_date = date.today() + timedelta(days=45)
    sent = 0
    with SyncSessionLocal() as db:
        rows = db.execute(
            select(Lease, Tenant, Unit)
            .join(Tenant, Tenant.id == Lease.tenant_id)
            .join(Unit, Unit.id == Lease.unit_id)
            .where(Lease.status == "active", Lease.end_date == target_date)
        ).all()
        for lease, tenant, unit in rows:
            owner = db.execute(
                select(User).where(User.organization_id == lease.organization_id, User.role == "owner")
            ).scalar_one_or_none()
            if owner is None:
                continue
            variables = {
                "tenant": tenant.name,
                "unit": unit.identifier,
                "end_date": lease.end_date.isoformat(),
            }
            res = send_whatsapp_message(
                to_phone_e164=owner.phone_e164,
                template_key="owner_lease_expiring",
                language=owner.language,
                variables=variables,
            )
            stmt = (
                insert(NotificationLog)
                .values(
                    organization_id=lease.organization_id,
                    user_id=owner.id,
                    channel="whatsapp",
                    purpose="lease_expiring",
                    language=owner.language,
                    template_key="owner_lease_expiring",
                    payload_snapshot={"variables": variables, "body": res.get("body")},
                    external_id=res["external_id"],
                    status="sent",
                    idempotency_key=f"lease_expiring:{lease.id}:{target_date.isoformat()}",
                )
                .on_conflict_do_nothing(constraint="uq_notifications_org_idempotency")
                .returning(NotificationLog.id)
            )
            if db.execute(stmt).scalar_one_or_none() is not None:
                sent += 1
        db.commit()
    return {"alerts_sent": sent}
