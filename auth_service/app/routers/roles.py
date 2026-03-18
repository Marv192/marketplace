from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import role_crud
from app.routers.dependencies import permission_required
from app.models import get_async_session, User
from app.schemas import RoleCreate, RoleDB
from app.schemas.roles import RoleUpdate, RolePermissionsUpdate

roles = APIRouter()


@roles.post('/roles', status_code=status.HTTP_201_CREATED, response_model=RoleDB)
async def create_role(role_in: RoleCreate, session: AsyncSession = Depends(get_async_session),
                      current_user: User = Depends(permission_required('role.create'))):
    return await role_crud.create(db=session, obj_in=role_in)

@roles.get('/roles/{role_id}', response_model=RoleDB)
async def get_role(role_id: int, session: AsyncSession = Depends(get_async_session),
                   current_user: User = Depends(permission_required('role.read'))):
    role = await role_crud.get(db=session, obj_id=role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Role not found')

    return role

@roles.get('/roles', response_model=list[RoleDB])
async def get_all_roles(session: AsyncSession = Depends(get_async_session),
                        current_user: User = Depends(permission_required('role.read'))):
    return await role_crud.get_multi(db=session)

@roles.patch('/roles/{role_id}', response_model=RoleDB)
async def update_role(role_id: int, role_in: RoleUpdate,
                      session: AsyncSession = Depends(get_async_session),
                      current_user: User = Depends(permission_required('role.update'))):
    db_role = await role_crud.get(db=session, obj_id=role_id)

    if not db_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Role not found')

    return await role_crud.update(db=session, db_obj=db_role, obj_in=role_in)

@roles.delete('/roles/{role_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: int, session: AsyncSession = Depends(get_async_session),
                      current_user: User = Depends(permission_required('role.delete'))):
    deleted_role = await role_crud.delete(db=session, obj_id=role_id)
    if not deleted_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Role not found')
    return None

@roles.get('/roles/{role_id}/permissions', response_model=list[dict])
async def get_role_permissions(role_id: int, session: AsyncSession = Depends(get_async_session),
                               current_user: User = Depends(permission_required('role.read'))):
    role = await role_crud.get(db=session, obj_id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Role not found')
    return [{'id': p.id, 'code': p.code, 'description': p.description} for p in role.permissions]

@roles.patch('/roles/{role_id}/permissions', response_model=RoleDB)
async def add_permissions(role_id: int, permissions_data: RolePermissionsUpdate,
                             session: AsyncSession = Depends(get_async_session),
                             current_user: User = Depends(permission_required('role.assign_permission'))):
    role = await role_crud.get(db=session, obj_id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Role not found')
    return await role_crud.add_permissions(db=session, db_obj=role, permissions=permissions_data)

@roles.delete('/roles/{role_id}/permissions', response_model=RoleDB)
async def remove_permissions(role_id: int, permissions_data: RolePermissionsUpdate,
                             session: AsyncSession = Depends(get_async_session),
                             current_user: User = Depends(permission_required('role.assign_permission'))):
    role = await role_crud.get(db=session, obj_id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Role not found')
    return await role_crud.remove_permissions(db=session, db_obj=role, permissions=permissions_data)