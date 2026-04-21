from datetime import timezone, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest

from app.utils import tokens
from app.utils.exceptions import TokenExpiredError, InvalidTokenError
from app.utils.tokens import create_access_token, JWT_ALGORITHM, create_refresh_token, refresh_tokens

TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"
TEST_SESSION_ID = "session-test-999"
TEST_JWT_SECRET = "test_secret_key_1234567890123456"
TEST_PERMISSIONS = ["test_permission"]

@pytest.fixture()
def mock_redis(mocker):
    tokens.JWT_SECRET = TEST_JWT_SECRET
    redis_mock = AsyncMock()
    mocker.patch('app.utils.tokens.redis_client', new=redis_mock)
    return redis_mock

@pytest.fixture()
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session

class TestTokens:
    @pytest.mark.asyncio
    async def test_create_access_token(self, mock_redis):
        token = await create_access_token(TEST_USER_ID, TEST_SESSION_ID, TEST_PERMISSIONS)

        assert token is not None
        mock_redis.setex.assert_called_once()

        payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])

        assert 'iat' in payload
        assert 'exp' in payload
        assert 'permissions' in payload
        lifetime = payload['exp'] - payload['iat']
        assert lifetime == 15 * 60      # 15 минут

        assert payload['user_id'] == TEST_USER_ID
        assert payload['session_id'] == TEST_SESSION_ID
        assert payload['type'] == 'access'

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, mock_redis):
        token = await create_refresh_token(TEST_USER_ID, TEST_SESSION_ID, TEST_PERMISSIONS)

        assert token is not None
        mock_redis.setex.assert_called_once()

        payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])


        assert 'iat' in payload
        assert 'exp' in payload
        assert 'role_id' in payload
        lifetime = payload['exp'] - payload['iat']
        assert lifetime == 7 * 24 * 60 * 60     # 7 дней
        assert payload['user_id'] == TEST_USER_ID
        assert payload['session_id'] == TEST_SESSION_ID
        assert payload['type'] == 'refresh'

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, mock_redis, mock_db_session):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'role_id': 1,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=7),
        }

        old_refresh_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
        expected_key = f'auth:refresh:{TEST_SESSION_ID}'

        mock_redis.get.return_value = old_refresh_token
        mock_permission = MagicMock()
        mock_permission.code = "test_permission"

        mock_role = MagicMock()
        mock_role.permissions = [mock_permission]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db_session.execute.return_value = mock_result

        new_access_token, new_refresh_token = await refresh_tokens(old_refresh_token, db=mock_db_session)

        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != old_refresh_token
        assert new_refresh_token != old_refresh_token
        assert new_refresh_token != new_access_token
        mock_redis.get.assert_called_once_with(expected_key)
        assert mock_redis.setex.call_count == 2

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
    async def test_refresh_tokens_expired(self, mock_redis, mock_db_session):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'refresh',
            'iat': (now - timedelta(seconds=100)),
            'exp': (now - timedelta(seconds=10)),
        }

        expired_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)

        with pytest.raises(TokenExpiredError) as exc_info:
            await refresh_tokens(expired_token, db=mock_db_session)

        assert str(exc_info.value) == 'Token expired'

    @pytest.mark.asyncio
    async def test_refresh_token_not_in_redis(self, mock_redis, mock_db_session):
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

        with pytest.raises(InvalidTokenError) as exc_info:
            await refresh_tokens(token, db=mock_db_session)

        assert str(exc_info.value) == 'Session revoked'

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, mock_redis, mock_db_session):
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': TEST_USER_ID,
            'session_id': TEST_SESSION_ID,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=7)
        }

        invalid_token = jwt.encode(payload, 'wrong_secret_key_wrong_secret_key', algorithm=JWT_ALGORITHM)

        with pytest.raises(InvalidTokenError) as exc_info:
            await refresh_tokens(invalid_token, db=mock_db_session)

        assert str(exc_info.value) == 'Invalid token'
