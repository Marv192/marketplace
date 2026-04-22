from datetime import datetime, timezone, timedelta

import jwt
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud import role_crud
from app.utils.exceptions import TokenExpiredError, InvalidTokenError

redis_client = aioredis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


async def create_access_token(user_id: str, session_id: str, permissions: list[str],
                              time_delta_minutes: int = 15):
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'session_id': session_id,
        'permissions': permissions,
        'exp': now + timedelta(minutes=time_delta_minutes),
        'iat': now,
        'type': 'access'
    }

    access_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    await redis_client.setex(f"auth:access:{session_id}", time_delta_minutes * 60, access_token)

    return access_token


async def create_refresh_token(user_id: str, session_id, role_id, time_delta_days=7):
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'session_id': session_id,
        'role_id': role_id,
        'exp': now + timedelta(days=time_delta_days),
        'iat': now,
        'type': 'refresh'
    }

    refresh_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    await redis_client.setex(f"auth:refresh:{session_id}", time_delta_days * 24 * 60 * 60, refresh_token)

    return refresh_token


async def refresh_tokens(token: str, db: AsyncSession):
    payload = await validate_token(token, token_type='refresh')

    permissions = await role_crud.get_permissions(db=db, role_id=payload['role_id'])

    new_access_token = await create_access_token(payload['user_id'], payload['session_id'], permissions)
    new_refresh_token = await create_refresh_token(payload['user_id'], payload['session_id'], payload['role_id'])

    return new_access_token, new_refresh_token


def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise InvalidTokenError()


async def validate_token(token: str, token_type: str = 'access'):
    payload = decode_token(token)

    if payload.get('type') != token_type:
        raise InvalidTokenError(f'Invalid token type. Expected {token_type}')

    session_id = payload.get('session_id')
    stored_token = await redis_client.get(f"auth:{token_type}:{session_id}")

    if not stored_token:
        raise InvalidTokenError('Session revoked')

    return payload
