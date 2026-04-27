import uuid

from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_async_session
from app.routers.validators import check_password, check_email_duplicate
from app.schemas import UserRegister, UserLogin
from app.crud import user_crud
from app.utils.tokens import create_access_token, create_refresh_token, refresh_tokens, revoke_tokens, decode_token

auth = APIRouter()
security = HTTPBearer()


@auth.post('/auth/register', status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegister, session: AsyncSession = Depends(get_async_session)):
    if await check_email_duplicate(email=payload.email, session=session):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email already registered')
    return await user_crud.create(db=session, user_in=payload)


@auth.post('/auth/login')
async def login(payload: UserLogin, session: AsyncSession = Depends(get_async_session)):
    user = await user_crud.get_by_email(db=session, email=payload.email)
    check_password(payload.password, user.password_hash)

    session_id = str(uuid.uuid4())

    permissions = []
    if user.role and user.role.permissions:
        permissions = [p.code for p in user.role.permissions]

    access_token = await create_access_token(str(user.id), session_id, permissions)
    refresh_token = await create_refresh_token(str(user.id), session_id, user.role_id)

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'expires_in': 15 * 60,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role_id': user.role_id,
        }
    }


@auth.post('/auth/logout')
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token=token)

    session_id = payload.get('session_id')

    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='session_id missing')

    await revoke_tokens(session_id=session_id)
    return {'message': 'Successfully logged out'}


@auth.post('/auth/refresh')
async def token_refresh(db: AsyncSession = Depends(get_async_session),
                        credentials: HTTPAuthorizationCredentials = Depends(security)):
    refresh_token = credentials.credentials

    new_access_token, new_refresh_token = await refresh_tokens(refresh_token, db)

    return {
        'access_token': new_access_token,
        'refresh_token': new_refresh_token,
        'token_type': 'bearer',
        'expires_in': 15 * 60,
    }
