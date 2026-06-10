import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rent_manager.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rent Manager API",
        version="0.1.0",
        description="V1 backend per RENT_MANAGER_V1_SPEC.md",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from rent_manager.api.v1 import (
        auth,
        organizations,
        properties,
        units,
        tenants,
        leases,
        invoices,
        payments,
        dashboard,
        reminders,
        reports,
        subscriptions,
        webhooks,
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
    app.include_router(properties.router, prefix="/api/v1/properties", tags=["properties"])
    app.include_router(units.router, prefix="/api/v1", tags=["units"])
    app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
    app.include_router(leases.router, prefix="/api/v1/leases", tags=["leases"])
    app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
    app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(reminders.router, prefix="/api/v1/reminders", tags=["reminders"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.ENV}

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"name": "rent-manager-api", "docs": "/docs"}

    return app


app = create_app()
