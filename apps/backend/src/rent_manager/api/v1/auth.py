import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from rent_manager.config import settings
from rent_manager.db.models import Organization, User
from rent_manager.deps import CurrentUserDep, DbSession
from rent_manager.schemas.auth import (
    MeOut,
    OrganizationOut,
    OtpSendIn,
    OtpSendOut,
    OtpVerifyIn,
    OtpVerifyOut,
    RefreshIn,
    TokenPairOut,
    UpdateMeIn,
    UserOut,
)
from rent_manager.utils.phone import normalize_indian_phone
from rent_manager.utils.security import create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/otp/send", response_model=OtpSendOut)
async def send_otp(body: OtpSendIn) -> OtpSendOut:
    try:
        phone = normalize_indian_phone(body.phone_e164)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    request_id = str(uuid.uuid4())
    logger.info("dev OTP for %s: %s (request_id=%s)", phone, settings.OTP_FIXED, request_id)
    return OtpSendOut(
        request_id=request_id,
        dev_otp_hint=settings.OTP_FIXED if settings.ENV != "production" else None,
    )


@router.post("/otp/verify", response_model=OtpVerifyOut)
async def verify_otp(body: OtpVerifyIn, db: DbSession) -> OtpVerifyOut:
    if body.otp != settings.OTP_FIXED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")
    try:
        phone = normalize_indian_phone(body.phone_e164)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    org = (await db.execute(select(Organization).where(Organization.phone_e164 == phone))).scalar_one_or_none()
    user: User | None = None

    if org is None:
        org = Organization(
            name=body.organization_name or body.name or "My Properties",
            phone_e164=phone,
            default_language=body.default_language,
        )
        db.add(org)
        await db.flush()
        user = User(
            organization_id=org.id,
            role="owner",
            name=body.name or "Owner",
            phone_e164=phone,
            language=body.default_language,
        )
        db.add(user)
        await db.flush()
    else:
        user = (
            await db.execute(
                select(User).where(User.organization_id == org.id, User.phone_e164 == phone)
            )
        ).scalar_one_or_none()
        if user is None:
            user = User(
                organization_id=org.id,
                role="owner",
                name=body.name or "Owner",
                phone_e164=phone,
                language=org.default_language,
            )
            db.add(user)
            await db.flush()
        elif body.name and body.name != user.name:
            # Returning user supplied a different name — keep their profile in
            # sync. The org keeps its existing name (don't clobber it on relogin).
            user.name = body.name

    user.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)

    access = create_access_token(
        user_id=user.id, organization_id=org.id, role=user.role, language=user.language
    )
    refresh = create_refresh_token(user_id=user.id)
    return OtpVerifyOut(
        access_token=access,
        refresh_token=refresh,
        user=UserOut.model_validate(user),
        organization=OrganizationOut.model_validate(org),
    )


@router.post("/refresh", response_model=TokenPairOut)
async def refresh_tokens(body: RefreshIn, db: DbSession) -> TokenPairOut:
    try:
        payload = decode_token(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")
    user_id = uuid.UUID(payload["sub"])
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenPairOut(
        access_token=create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            language=user.language,
        ),
        refresh_token=create_refresh_token(user_id=user.id),
    )


@router.post("/logout")
async def logout() -> dict[str, bool]:
    return {"ok": True}


@router.get("/me", response_model=MeOut)
async def me(current: CurrentUserDep, db: DbSession) -> MeOut:
    user = (await db.execute(select(User).where(User.id == current.user_id))).scalar_one()
    org = (
        await db.execute(select(Organization).where(Organization.id == current.organization_id))
    ).scalar_one()
    return MeOut(user=UserOut.model_validate(user), organization=OrganizationOut.model_validate(org))


@router.patch("/me", response_model=UserOut)
async def update_me(body: UpdateMeIn, current: CurrentUserDep, db: DbSession) -> UserOut:
    user = (await db.execute(select(User).where(User.id == current.user_id))).scalar_one()
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)
