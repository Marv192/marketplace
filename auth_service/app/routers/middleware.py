from fastapi import Request, HTTPException
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.tokens import validate_token


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.public_paths = [
            '/auth/login',
            '/auth/register',
            '/auth/refresh',
            '/docs',
            '/openapi.json',
        ]

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)

        auth_header = request.headers.get('Authorization')

        if not auth_header:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Missing Authorization header")

        if auth_header.startswith('Bearer '):
            parts = auth_header.split()
            if len(parts) != 2:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Invalid Authorization header")
            token = parts[1]
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Authorization header")

        try:
            payload = await validate_token(token, token_type='access')
            request.state.user_id = payload['user_id']
            request.state.session_id = payload['session_id']
            request.state.token_payload = payload
        except HTTPException as e:
            raise e
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Authorization error")

        response = await call_next(request)
        return response
