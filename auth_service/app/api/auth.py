import uuid

from fastapi import APIRouter, status, Security

from app.dependencies import get_current_user
from app.schemas import UserRegister, UserCredentials, RefreshToken
from app.api.db_manager import create_user, login_user, get_user_info
from app.tokens import create_access_token, create_refresh_token, refresh_tokens

auth = APIRouter()

@auth.post('/auth/register', status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegister):
    return await create_user(payload)


# проверяем юзера, генерируем сессию с токенами, возвращаем токены с TTL access токена и данные юзера
@auth.post('/auth/login')
async def login(payload: UserCredentials):
    user = await login_user(payload)

    session_id = str(uuid.uuid4())

    access_token = await create_access_token(str(user.id), session_id)
    refresh_token = await create_refresh_token(str(user.id), session_id)

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


@auth.get('/auth/me')
async def user_info(current_user_id = Security(get_current_user)):
    return await get_user_info(current_user_id)


@auth.post('/auth/refresh')
async def token_refresh(payload: RefreshToken):
    new_access_token, new_refresh_token = await refresh_tokens(payload.refresh_token)
    return {
        'access_token': new_access_token,
        'refresh_token': new_refresh_token,
        'token_type': 'bearer',
        'expires_in': 15 * 60,
    }