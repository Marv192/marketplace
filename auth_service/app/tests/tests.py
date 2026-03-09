from datetime import timezone, datetime, timedelta
from unittest.mock import AsyncMock, patch

import bcrypt
import jwt
import pytest
from asyncpg import UniqueViolationError
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.dialects import postgresql

from app import tokens
from app.api.db_manager import create_user, login_user, get_user_info
from app.dependencies import get_current_user
from app.schemas import UserRegister, UserCredentials
from app.tokens import create_access_token, JWT_ALGORITHM, create_refresh_token, refresh_tokens

TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"
TEST_SESSION_ID = "session-test-999"
TEST_JWT_SECRET = "test_secret_key_1234567890123456"

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    tokens.JWT_SECRET = TEST_JWT_SECRET

    redis_mock = AsyncMock()

    mocker.patch('app.tokens.redis_client', new=redis_mock)
    mocker.patch('app.dependencies.redis_client', new=redis_mock)

    return redis_mock

@pytest.fixture(autouse=True)
def mock_db(mocker):
    db_mock = AsyncMock()
    mocker.patch('app.api.db_manager.database', new = db_mock)
    return db_mock

class TestTokens:
    @pytest.mark.asyncio
    async def test_create_access_token(self, mock_redis):
        token = await create_access_token(TEST_USER_ID, TEST_SESSION_ID)

        assert token is not None
        mock_redis.setex.assert_called_once()

        payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])

        assert 'iat' in payload
        assert 'exp' in payload
        lifetime = payload['exp'] - payload['iat']
        assert lifetime == 15 * 60      # 15 минут

        assert payload['user_id'] == TEST_USER_ID
        assert payload['session_id'] == TEST_SESSION_ID
        assert payload['type'] == 'access'

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, mock_redis):
        token = await create_refresh_token(TEST_USER_ID, TEST_SESSION_ID)

        assert token is not None
        mock_redis.setex.assert_called_once()

        payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])


        assert 'iat' in payload
        assert 'exp' in payload
        lifetime = payload['exp'] - payload['iat']
        assert lifetime == 7 * 24 * 60 * 60     # 7 дней
        assert payload['user_id'] == TEST_USER_ID
        assert payload['session_id'] == TEST_SESSION_ID
        assert payload['type'] == 'refresh'

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=7),
        }

        old_refresh_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
        expected_key = f'auth:refresh:{TEST_SESSION_ID}'

        mock_redis.get.return_value = old_refresh_token

        new_access_token, new_refresh_token = await refresh_tokens(old_refresh_token)

        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != old_refresh_token
        assert new_refresh_token != old_refresh_token
        assert new_refresh_token != new_access_token
        mock_redis.get.assert_called_once_with(expected_key)

        new_access_payload = jwt.decode(new_access_token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert new_access_payload['user_id'] == TEST_USER_ID
        assert new_access_payload['session_id'] == TEST_SESSION_ID
        lifetime = new_access_payload['exp'] - new_access_payload['iat']
        assert lifetime == 15 * 60  # 15 минут

        new_refresh_payload = jwt.decode(new_refresh_token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert new_refresh_payload['user_id'] == TEST_USER_ID
        assert new_refresh_payload['session_id'] == TEST_SESSION_ID
        lifetime = new_refresh_payload['exp'] - new_refresh_payload['iat']
        assert lifetime == 7 * 24 * 60 * 60     # 7 дней

    @pytest.mark.asyncio
    async def test_refresh_tokens_expired(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'refresh',
            'iat': (now - timedelta(seconds=100)),
            'exp': (now - timedelta(seconds=10)),
        }

        expired_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens(expired_token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Token is expired'

    @pytest.mark.asyncio
    async def test_refresh_token_not_in_redis(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=7)
        }

        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
        mock_redis.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens(token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Token is expired'

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=7)
        }

        invalid_token = jwt.encode(payload, 'wrong_secret_key_wrong_secret_key', algorithm=JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens(invalid_token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Invalid token'

class TestUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_db):
        user_data = UserRegister(
            email='test@mail.ru',
            password='test_password',
            name='test_name'
        )

        result = await create_user(user_data)
        assert result == "User registered"
        mock_db.execute.assert_called_once()

        # получаем данные, передаваемые БД в запросе
        query_obj = mock_db.execute.call_args[0][0]
        compiled_query = query_obj.compile(dialect=postgresql.dialect())
        params = compiled_query.params

        assert 'password' not in params
        assert 'password_hash' in params
        assert bcrypt.checkpw('test_password'.encode('utf-8'), params['password_hash'].encode('utf-8'))

    @pytest.mark.asyncio
    async def test_create_user_exists(self, mock_db):
        existing_user_data = UserRegister(
            email='existing@mail.ru',
            password='test_password',
            name='test_name'
        )

        mock_db.execute.side_effect = UniqueViolationError()

        with pytest.raises(HTTPException) as exc_info:
            await create_user(existing_user_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == 'User with this email already exists'
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_fail(self, mock_db):
        user_data = UserRegister(
            email='test@mail.ru',
            password='test_password',
            name='test_name'
        )

        mock_db.execute.side_effect = ConnectionError("Database connection error")

        with pytest.raises(HTTPException) as exc_info:
            await create_user(user_data)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == 'Registration failed'

    @pytest.mark.asyncio
    async def test_login_success(self, mock_db):
        credentials = UserCredentials(email='test@mail.ru', password='test_password')

        password_hash = (bcrypt.hashpw(credentials.password.encode('utf-8'), bcrypt.gensalt())).decode('utf-8')

        db_user = {
            'id': TEST_USER_ID,
            'name': 'test_name',
            'email': 'test@mail.ru',
            'password_hash': password_hash,
            'role_id': 1,
            'created_at': datetime.now(timezone.utc)
        }

        mock_db.fetch_one = AsyncMock(return_value=db_user)

        result = (await login_user(credentials)).model_dump()

        mock_db.fetch_one.assert_called_once()
        assert 'id' in result
        assert 'name' in result
        assert 'email' in result
        assert 'password_hash' not in result
        assert 'role_id' in result

    @pytest.mark.asyncio
    async def test_login_wrong_email(self, mock_db):
        credentials = UserCredentials(email='wrong@mail.ru', password='test_password')

        mock_db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await login_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Incorrect email or password'
        mock_db.fetch_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_db):
        credentials = UserCredentials(email='test@mail.ru', password='wrong_password')

        real_password_hash = bcrypt.hashpw(b'real_password', bcrypt.gensalt()).decode('utf-8')

        db_user = {
            'id': TEST_USER_ID,
            'name': 'test_name',
            'email': 'test@mail.ru',
            'password_hash': real_password_hash,
            'role_id': 1,
        }
        mock_db.fetch_one = AsyncMock(return_value=db_user)

        with pytest.raises(HTTPException) as exc_info:
            await login_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Incorrect email or password'
        mock_db.fetch_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, mock_db):
        db_user = {
            'id': TEST_USER_ID,
            'email': 'test@mail.ru',
            'name': 'test_name',
            'role_id': 1,
            'created_at': datetime.now(timezone.utc)
        }

        mock_db.fetch_one = AsyncMock(return_value=db_user)

        user_info = (await get_user_info(TEST_USER_ID)).model_dump()

        mock_db.fetch_one.assert_called_once()
        assert 'id' in user_info
        assert 'name' in user_info
        assert 'email' in user_info
        assert 'role_id' in user_info
        assert 'created_at' in user_info
        assert 'password_hash' not in user_info

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, mock_db):
        mock_db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_user_info(TEST_USER_ID)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'User not found'

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'exp': now + timedelta(minutes=15),
            'iat': now,
            'type': 'access'
        }

        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm='HS256')
        credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
        mock_redis.get.return_value = f"auth:access:{TEST_SESSION_ID}"

        with patch('app.dependencies.JWT_SECRET', TEST_JWT_SECRET):
            result = await get_current_user(credentials)

        assert result == TEST_USER_ID
        mock_redis.get.assert_called_once_with(f'auth:access:{TEST_SESSION_ID}')

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'access',
            'iat': now,
            'exp': now - timedelta(days=7)
        }

        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
        credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
        mock_redis.get.return_value = None

        with patch('app.dependencies.JWT_SECRET', TEST_JWT_SECRET):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)


        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Token is expired'
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_user_not_in_redis(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(days=7)
        }

        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
        credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
        mock_redis.get.return_value = None

        with patch('app.dependencies.JWT_SECRET', TEST_JWT_SECRET):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)


        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Token is expired'
        mock_redis.get.assert_called_once_with(f"auth:access:{TEST_SESSION_ID}")

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_redis):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(days=7)
        }

        invalid_token = jwt.encode(payload, 'wrong_secret_key_wrong_secret_key', algorithm=JWT_ALGORITHM)
        credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=invalid_token)

        with patch('app.dependencies.JWT_SECRET', TEST_JWT_SECRET):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == 'Invalid token'
        mock_redis.get.assert_not_called()