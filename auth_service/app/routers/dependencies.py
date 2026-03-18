from fastapi import HTTPException, Depends, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, get_async_session, Role
from app.utils.exceptions import PermissionDeniedError


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


def permission_required(permission_code: str):
    async def check_permission(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.role:
            raise PermissionDeniedError('User has no role assigned')

        permission_codes = {p.code for p in current_user.role.permissions}

        if permission_code not in permission_codes:
            raise PermissionDeniedError(f'Missing permission {permission_code}')

        return current_user
    return check_permission