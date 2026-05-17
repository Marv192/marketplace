import logging
import uuid
from typing import Optional, Union, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import User
from app.schemas import UserRegister
from app.schemas.user import UserUpdate, UserCreate
from app.utils.password import generate_password_hash

logger = logging.getLogger(__name__)


class CRUDUser(CRUDBase[User, UserRegister, UserUpdate]):
    async def create(self, db: AsyncSession, *, user_in: UserRegister) -> User:
        try:
            user_data = user_in.model_dump()
            user_data['id'] = uuid.uuid4()
            user_data['password_hash'] = generate_password_hash(user_data.pop('password'))
            user_data.setdefault('role_id', 1)

            db_user = UserCreate(**user_data)

            return await super().create(db=db, obj_in=db_user)

        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='User with this email already exists')

        except Exception as err:
            await db.rollback()
            logger.error(f"Registration error: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Registration failed')

    async def get_user_info(self, db: AsyncSession, *, user_id: UUID) -> User:
        user_info = await self.get(db, obj_id=user_id)

        if not user_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

        return user_info

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

        return user

    async def update(self, db: AsyncSession, *, db_obj: User,
                     obj_in: Union[UserUpdate, Dict[str, Any]]) -> User:
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)

            if "password" in update_data:
                update_data["password_hash"] = generate_password_hash(update_data.pop("password"))

            user = await super().update(db, db_obj=db_obj, obj_in=update_data)
            await db.commit()
            return user

        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='User with this email already exists')

        except Exception as err:
            await db.rollback()
            logger.error(f"Update error: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Update failed')

    async def delete(self, db: AsyncSession, *, user_id: UUID) -> Optional[User]:
        try:
            deleted_user = await super().delete(db=db, obj_id=user_id)

            if not deleted_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

            await db.commit()
            return deleted_user

        except HTTPException:
            await db.rollback()
            raise

        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='Cannot delete user with related records')

        except Exception as err:
            await db.rollback()
            logger.error(f"Delete error: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Delete failed')


user_crud = CRUDUser(User)