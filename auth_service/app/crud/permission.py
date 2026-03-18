from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import Permission
from app.schemas.permissions import PermissionUpdate, PermissionCreate


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: PermissionCreate) -> Permission:
        try:
            return await super().create(db=db, obj_in=obj_in)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Permission with code '{obj_in.code}' already exists")


    async def get(self, db: AsyncSession, *, obj_id: int) -> Permission:
        perm = await super().get(db=db, obj_id=obj_id)

        if not perm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

        return perm


    async def update(self, db: AsyncSession, *, db_obj: Permission, obj_in: PermissionUpdate) -> Permission:
        try:
            perm = await super().update(db=db, db_obj=db_obj, obj_in=obj_in)
            await db.commit()
            return perm
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Permission with code '{obj_in.code}' already exists")


    async def delete(self, db: AsyncSession, *, obj_id: int) -> Optional[Permission]:
        try:
            result = await super().delete(db=db, obj_id=obj_id)

            if not result:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Permission not found")
            await db.commit()
            return result

        except HTTPException:
            raise

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


permission_crud = CRUDPermission(Permission)