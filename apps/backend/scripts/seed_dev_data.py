"""Seed a small but realistic dev dataset.

Run inside the api container:
    docker compose exec api python -m scripts.seed_dev_data
"""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from rent_manager.db.models import (
    Invoice,
    Lease,
    Organization,
    Property,
    Tenant,
    Unit,
    User,
)
from rent_manager.db.session import SyncSessionLocal


def main() -> None:
    today = date.today()
    month_start = today.replace(day=1)

    with SyncSessionLocal() as db:
        existing = db.execute(select(Organization).limit(1)).scalar_one_or_none()
        if existing is not None:
            print(f"Database already seeded (found org: {existing.name}). Exiting.")
            return

        org = Organization(
            name="Sunrise Properties",
            phone_e164="+919876543210",
            email="owner@example.com",
            default_language="en",
            tier="pilot",
        )
        db.add(org)
        db.flush()

        owner = User(
            organization_id=org.id,
            role="owner",
            name="Ayush",
            phone_e164=org.phone_e164,
            email=org.email,
            language="en",
        )
        db.add(owner)
        db.flush()

        prop = Property(
            organization_id=org.id,
            name="Saraswati Nilaya",
            type="apartment_building",
            address_line="12, 5th Main",
            area="HSR Layout",
            city="Bengaluru",
            pincode="560102",
        )
        db.add(prop)
        db.flush()

        units = []
        for i, ident in enumerate(["Flat 101", "Flat 102", "Flat 201", "Flat 202", "Flat 301"]):
            u = Unit(
                organization_id=org.id,
                property_id=prop.id,
                type="flat",
                identifier=ident,
                default_rent=Decimal(20000 + i * 1000),
            )
            db.add(u)
            units.append(u)
        db.flush()

        tenants = []
        names_phones = [
            ("Priya Sharma", "+919812340001", "hi"),
            ("Rahul Iyer", "+919812340002", "en"),
            ("Ananya Rao", "+919812340003", "kn"),
            ("Karthik Menon", "+919812340004", "en"),
            ("Meera Joshi", "+919812340005", "hi"),
        ]
        for (name, phone, lang), unit in zip(names_phones, units):
            t = Tenant(
                organization_id=org.id,
                name=name,
                phone_e164=phone,
                email=f"{name.split()[0].lower()}@example.com",
                language=lang,
            )
            db.add(t)
            tenants.append((t, unit))
        db.flush()

        for (t, unit) in tenants:
            lease = Lease(
                organization_id=org.id,
                unit_id=unit.id,
                tenant_id=t.id,
                start_date=today - timedelta(days=180),
                end_date=today + timedelta(days=185),
                monthly_rent=unit.default_rent,
                security_deposit=unit.default_rent * 2,
                billing_day=1,
                status="active",
            )
            db.add(lease)
            db.flush()
            for offset in (0, 1, 2):
                year = month_start.year
                month_num = month_start.month - offset
                while month_num <= 0:
                    month_num += 12
                    year -= 1
                month = date(year, month_num, 1)
                due_day = min(lease.billing_day, monthrange(month.year, month.month)[1])
                due = month.replace(day=due_day)
                paid = offset > 0  # only past months are paid
                inv = Invoice(
                    organization_id=org.id,
                    lease_id=lease.id,
                    tenant_id=t.id,
                    unit_id=unit.id,
                    billing_month=month,
                    due_date=due,
                    amount_due=lease.monthly_rent,
                    amount_paid=lease.monthly_rent if paid else Decimal("0"),
                    status="paid" if paid else "pending",
                )
                db.add(inv)
        db.commit()
        print(f"Seeded org {org.id} with {len(units)} units, {len(tenants)} tenants, ~15 invoices.")
        print("Login with phone +919876543210 and OTP 123456.")


if __name__ == "__main__":
    main()
