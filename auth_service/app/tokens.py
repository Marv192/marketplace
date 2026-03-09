import os
from datetime import datetime, timezone, timedelta

import redis.asyncio as aioredis
import jwt
from fastapi import HTTPException

redis_client = aioredis.Redis(host=os.environ.get('REDIS_HOST'), port=6379, decode_responses=True)
JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = 'HS256'


# создает токен с TTL, пишет в редис с сессией и TTL, возвращает токен
async def create_access_token(user_id, session_id, time_delta_minutes = 15):
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'session_id': session_id,
        'exp': now + timedelta(minutes=time_delta_minutes),
        'iat': now,
        'type': 'access'
    }

    access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    await redis_client.setex(f"auth:access:{session_id}", time_delta_minutes * 60, access_token)

    return access_token


async def create_refresh_token(user_id, session_id, time_delta_days = 7):
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'session_id': session_id,
        'exp': now + timedelta(days=time_delta_days),
        'iat': now,
        'type': 'refresh'
    }

    refresh_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    await redis_client.setex(f"auth:refresh:{session_id}", time_delta_days * 24 * 60 * 60, refresh_token)

    return refresh_token


# проверяет валидность токена (при декодировании), проверяет наличие токена в редисе, генерирует
# и возвращает новые токены
async def refresh_tokens(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        stored_token = await redis_client.get(f"auth:refresh:{payload['session_id']}")
        if not stored_token:
            raise HTTPException(status_code=401, detail="Token is expired")

        new_access_token = await create_access_token(payload['user_id'], payload['session_id'])
        new_refresh_token = await create_refresh_token(payload['user_id'], payload['session_id'])

        return new_access_token, new_refresh_token

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
