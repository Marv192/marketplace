import uuid

import bcrypt
from asyncpg import UniqueViolationError
from fastapi import HTTPException, status

from app.models import users, database
from app.schemas import UserRegister, UserCredentials, UserInfo, UserFullInfo


# Кодирует пароль в байты для bcrypt, хэширует с солью, декодирует обратно в строку и регистрирует
async def create_user(user: UserRegister):
    try:
        user_data = user.model_dump()

        password_bytes = user_data.pop('password').encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt)

        user_data['password_hash'] = password_hash.decode('utf-8')
        user_data['id'] = uuid.uuid4()

        if 'role_id' not in user_data:
            user_data['role_id'] = 1

        query = users.insert().values(**user_data)

        await database.execute(query)

        return 'User registered'

    except UniqueViolationError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='User with this email already exists')

    except Exception as err:
        print(f"Registration error: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Registration failed')


# Получает юзера по email, проверяет email и пароль, возвращает юзера без password_hash
async def login_user(log_user: UserCredentials):
    query = "SELECT * FROM users WHERE email = :email"
    db_user = await database.fetch_one(query, {'email': log_user.email})


    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')
    password_bytes = log_user.password.encode('utf-8')
    password_hash = db_user['password_hash'].encode('utf-8')


    if not bcrypt.checkpw(password_bytes, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

    return UserInfo(
        id=db_user['id'],
        email=db_user['email'],
        name=db_user['name'],
        role_id=db_user['role_id']
    )


async def get_user_info(user_id):
    query = "SELECT id, email, name, role_id, created_at FROM users WHERE id = :id"

    user_info = await database.fetch_one(query, {'id': user_id})
    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    return UserFullInfo.model_validate(user_info)
