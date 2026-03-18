from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import permission_crud
from app.routers.dependencies import permission_required
from app.models import get_async_session, User
from app.schemas import PermissionDB, PermissionCreate
from app.schemas.permissions import PermissionUpdate

permissions = APIRouter()

@permissions.post('/permissions', status_code=status.HTTP_201_CREATED,
                  response_model=PermissionDB)
async def create_permission(perm_in: PermissionCreate, session: AsyncSession = Depends(get_async_session),
                            current_user: User = Depends(permission_required('permission.create'))):
    return await permission_crud.create(db=session, obj_in=perm_in)

@permissions.get('/permissions/{perm_id}', response_model=PermissionDB)
async def get_permission(perm_id: int, session: AsyncSession = Depends(get_async_session),
                         current_user: User = Depends(permission_required('permission.read'))):
    permission = await permission_crud.get(db=session, obj_id=perm_id)

    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    return permission

@permissions.get('/permissions', response_model=list[PermissionDB])
async def get_all_permissions(session: AsyncSession = Depends(get_async_session),
                              current_user: User = Depends(permission_required('permission.read'))):
    return await permission_crud.get_multi(db=session)

@permissions.patch('/permissions/{perm_id}', response_model=PermissionDB)
async def update_permission(perm_id: int, perm_in: PermissionUpdate,
                            session: AsyncSession = Depends(get_async_session),
                            current_user: User = Depends(permission_required('permission.update'))):
    db_perm = await permission_crud.get(db=session, obj_id=perm_id)

    if not db_perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    return await permission_crud.update(db=session, db_obj=db_perm, obj_in=perm_in)

@permissions.delete('/permissions/{perm_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(perm_id: int, session: AsyncSession = Depends(get_async_session),
                            current_user: User = Depends(permission_required('permission.delete'))):
    deleted_perm =  await permission_crud.delete(db=session, obj_id=perm_id)
    if not deleted_perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return None