from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, get_async_session, Role
from app.utils.exceptions import PermissionDeniedError
from app.utils.tokens import decode_token


async def get_current_user(request: Request, session: AsyncSession = Depends(get_async_session)) -> User:
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    stmt = select(User).where(User.id == user_id).options(selectinload(User.role).selectinload(Role.permissions))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    return user


security = HTTPBearer()

def permission_required(permission_code: str):
    async def check_permission(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
        token = credentials.credentials
        payload = decode_token(token)

        permission_codes = payload.get('permissions', [])

        if permission_code not in permission_codes:
            raise PermissionDeniedError(f'Missing permission {permission_code}')

        return True
    return check_permission