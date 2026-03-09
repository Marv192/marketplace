from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import auth
from app.models import database

#подключаемся к БД и отключаемся при выключении
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await database.connect()
        print("Database connected")
    except Exception as e:
        print(f"Ошибка во время подключения к БД: {e}")
        raise
    yield
    try:
        await database.disconnect()
    except Exception as e:
        print(f"Ошибка при отключении БД: {e}")




app = FastAPI(lifespan=lifespan)

app.include_router(auth)