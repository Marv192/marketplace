import jwt
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.tokens import JWT_ALGORITHM, JWT_SECRET, redis_client


security = HTTPBearer()

# получение user_id из токена для user_info
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload['user_id']
        session_id = payload['session_id']

        stored_token = await redis_client.get(f'auth:access:{session_id}')

        if not stored_token:
            raise HTTPException(status_code=401, detail='Token is expired')

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token is expired')

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')

