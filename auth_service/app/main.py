from contextlib import asynccontextmanager

from fastapi import FastAPI, Security, Request
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette import status

from app.routers.auth import auth
from app.models import engine
from app.routers.middleware import AuthMiddleware
from app.routers.permissions import permissions
from app.routers.roles import roles
from app.routers.users import users
from app.utils.exceptions import PermissionDeniedError, InvalidTokenError, TokenExpiredError


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await engine.connect()
        print("Database connected")
    except Exception as e:
        print(f"Ошибка во время подключения к БД: {e}")
        raise
    yield
    try:
        await engine.disconnect()
    except Exception as e:
        print(f"Ошибка при отключении БД: {e}")


security = HTTPBearer()

app = FastAPI(lifespan=lifespan)

Instrumentator().instrument(app).expose(app)


@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "Permission denied",
            "detail": str(exc)
        }
    )


@app.exception_handler(InvalidTokenError)
async def invalid_token_handler(request: Request, exc: InvalidTokenError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Invalid token",
            "detail": str(exc)
        }
    )


@app.exception_handler(TokenExpiredError)
async def token_expired_handler(request: Request, exc: TokenExpiredError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Token expired",
            "detail": str(exc)
        }
    )


app.add_middleware(AuthMiddleware)
app.include_router(auth, tags=["Auth"])
app.include_router(users, tags=["Users"], dependencies=[Security(security)])
app.include_router(roles, tags=["Roles"], dependencies=[Security(security)])
app.include_router(permissions, tags=["Permissions"], dependencies=[Security(security)])
