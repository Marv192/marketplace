from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.utils.password import verify_password


async def check_email_duplicate(email: str, session: AsyncSession) -> bool:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    return user is not None

def check_password(password: str, password_hash: str):
    if not verify_password(password, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect password')

