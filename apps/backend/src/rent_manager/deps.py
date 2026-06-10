from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rent_manager.db.session import get_async_session
from rent_manager.utils.security import decode_token


class CurrentUser:
    def __init__(self, user_id: UUID, organization_id: UUID, role: str, language: str) -> None:
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role
        self.language = language


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    try:
        return CurrentUser(
            user_id=UUID(payload["sub"]),
            organization_id=UUID(payload["organization_id"]),
            role=payload.get("role", "owner"),
            language=payload.get("language", "en"),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token") from exc


DbSession = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
