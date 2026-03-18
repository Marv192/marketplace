from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Role, Permission
from app.schemas.roles import RoleUpdate, RoleCreate, RolePermissionsUpdate

class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: RoleCreate) -> Role:
        try:
            return await super().create(db=db, obj_in=obj_in)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Role with name '{obj_in.name}' already exists")


    async def get(self, db: AsyncSession, *, obj_id: int) -> Role:
        role = await super().get(db=db, obj_id=obj_id)

        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        return role


    async def update(self, db: AsyncSession, *, db_obj: Role, obj_in: RoleUpdate) -> Role:
        try:
            role = await super().update(db=db, db_obj=db_obj, obj_in=obj_in)
            await db.commit()
            return role
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Role with name '{obj_in.name}' already exists")


    async def delete(self, db: AsyncSession, *, obj_id: int) -> Optional[Role]:
        try:
            result = await super().delete(db=db, obj_id=obj_id)

            if not result:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Role not found")

            await db.commit()
            return result

        except HTTPException:
            raise

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


    async def add_permissions(self, db: AsyncSession, *, db_obj: Role, permissions: RolePermissionsUpdate) -> Role:
        permission_ids = permissions.permission_ids
        if not permission_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No permission ids provided")

        current_permission_ids = {p.id for p in db_obj.permissions}

        result = await db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
        valid_permissions = result.scalars().all()

        found_ids = {p.id for p in valid_permissions}
        missing_ids = set(permission_ids) - found_ids

        if missing_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Permissions with ids: '{missing_ids}' not found")

        for perm in valid_permissions:
            if perm.id not in current_permission_ids:
                db_obj.permissions.append(perm)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Permission already assigned to this role")
        return db_obj


    async def remove_permissions(self, db: AsyncSession, *, db_obj: Role,
                                 permissions: RolePermissionsUpdate) -> Role:
        permission_ids = set(permissions.permission_ids)
        if not permission_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No permission ids provided")

        db_obj.permissions[:] = [p for p in db_obj.permissions if p.id not in permission_ids]

        await db.commit()
        return db_obj


role_crud = CRUDRole(Role)
