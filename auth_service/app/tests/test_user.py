from datetime import timezone, datetime
from unittest.mock import AsyncMock, MagicMock

import bcrypt
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.crud import user_crud
from app.routers.dependencies import get_current_user
from app.models import User
from app.schemas import UserRegister
from app.schemas.user import UserUpdate

TEST_PASSWORD = 'test_password'

@pytest.fixture()
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session

@pytest.fixture()
def mock_user():
    user = MagicMock(spec=User)
    user.id = '123e4567-e89b-12d3-a456-426614174000'
    user.name = 'test_name'
    user.email = "test@mail.ru"
    user.password_hash = bcrypt.hashpw(TEST_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.role_id = 1
    user.created_at = datetime.now(timezone.utc)
    return user

@pytest.fixture()
def mock_result():
    result = MagicMock()
    return result

class TestUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_db_session):
        user_data = UserRegister(
            email='test@mail.ru',
            password='test_password',
            name='test_name'
        )

        result = await user_crud.create(db=mock_db_session, user_in=user_data)

        assert result is not None
        mock_db_session.add.assert_called_once()

        added_object = mock_db_session.add.call_args[0][0]

        assert not hasattr(added_object, 'password')
        assert hasattr(added_object, 'password_hash')
        assert added_object.password_hash != 'test_password'
        assert bcrypt.checkpw('test_password'.encode('utf-8'), added_object.password_hash.encode('utf-8'))
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_exists(self, mock_db_session):
        existing_user_data = UserRegister(
            email='existing@mail.ru',
            password='test_password',
            name='test_name'
        )

        mock_db_session.commit.side_effect = IntegrityError(MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await user_crud.create(db=mock_db_session, user_in=existing_user_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == 'User with this email already exists'
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_fail(self, mock_db_session):
        user_data = UserRegister(
            email='test@mail.ru',
            password='test_password',
            name='test_name'
        )

        mock_db_session.add.side_effect = ConnectionError("Database connection error")

        with pytest.raises(HTTPException) as exc_info:
            await user_crud.create(db=mock_db_session, user_in=user_data)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == 'Registration failed'
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_not_called()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, mock_db_session, mock_user, mock_result):
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        user_info = (await user_crud.get_user_info(db=mock_db_session, user_id=mock_user.id))

        mock_db_session.execute.assert_called_once()
        mock_result.scalars.return_value.first.assert_called_once()
        assert hasattr(user_info, 'id')
        assert hasattr(user_info, 'name')
        assert hasattr(user_info, 'email')
        assert hasattr(user_info, 'role_id')
        assert hasattr(user_info, 'created_at')

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, mock_db_session, mock_user, mock_result):
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await user_crud.get_user_info(db=mock_db_session, user_id=mock_user.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'User not found'
        mock_db_session.execute.assert_called_once()
        mock_result.scalars.return_value.first.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_db_session, mock_user, mock_result):
        mock_request = MagicMock()
        mock_request.state.user_id = mock_user.id

        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        user = await get_current_user(request=mock_request, session=mock_db_session)

        assert user.id == mock_user.id
        assert user.email == mock_user.email
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, mock_db_session, mock_result):
        mock_request = MagicMock()
        mock_request.state.user_id = "wrong_user_id"

        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=mock_request, session=mock_db_session)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'User not found'

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, mock_db_session, mock_user, mock_result):
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        user = await user_crud.get_by_email(db=mock_db_session, email=mock_user.email)

        assert user.id == mock_user.id
        assert user.email == mock_user.email
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_success(self, mock_db_session, mock_user, mock_result):
        update_data = UserUpdate(
            name='new_name',
            email='new@email.ru',
        )

        updated_user = await user_crud.update(db=mock_db_session, db_obj=mock_user, obj_in=update_data)

        assert updated_user.name == 'new_name'
        assert updated_user.email == 'new@email.ru'
        mock_db_session.add.assert_called_once_with(mock_user)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_email_exists(self, mock_db_session, mock_user, mock_result):
        update_data = UserUpdate(email='existing@email.ru')

        mock_db_session.commit.side_effect = IntegrityError(MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await user_crud.update(db=mock_db_session, db_obj=mock_user, obj_in=update_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == 'User with this email already exists'
        mock_db_session.add.assert_called_once_with(mock_user)
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_success(self, mock_db_session, mock_user, mock_result):
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        result = await user_crud.delete(db=mock_db_session, user_id=mock_user.id)

        assert result == mock_user
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_db_session, mock_user, mock_result):
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await user_crud.delete(db=mock_db_session, user_id=mock_user.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'User not found'
        mock_db_session.commit.assert_not_called()
        mock_db_session.rollback.assert_called_once()

