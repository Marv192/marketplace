from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import user_crud
from app.routers.dependencies import get_current_user, permission_required
from app.models import get_async_session, User
from app.schemas import UserInfo
from app.schemas.user import UserUpdate

users = APIRouter()

security = HTTPBearer()

@users.get('/users/me', response_model=UserInfo)
async def user_info(current_user: User = Depends(get_current_user)):
    return current_user

@users.get('/users/{id}', response_model=UserInfo)
async def get_user(user_id: UUID, session: AsyncSession = Depends(get_async_session),
                   current_user: User = Depends(permission_required('user.read'))):
    user = await user_crud.get(db=session, obj_id=user_id)

    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    return user

@users.patch('/users/me', response_model=UserInfo)
async def update_user(obj_in: UserUpdate, current_user: User = Depends(get_current_user),
                      session: AsyncSession = Depends(get_async_session)):
    return await user_crud.update(db=session, db_obj=current_user, obj_in=obj_in)

@users.delete('/users/me', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(current_user: User = Depends(get_current_user),
                      session: AsyncSession = Depends(get_async_session)):
    deleted_user = await user_crud.delete(db=session, user_id=current_user.id)

    if not deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    return None