from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.crud import permission_crud
from app.models import Permission
from app.schemas import PermissionCreate
from app.schemas.permissions import PermissionUpdate


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
def mock_permission():
    perm = MagicMock(spec=Permission)
    perm.id = 1
    perm.code = 'test.code'
    perm.description = 'test description'
    return perm

@pytest.fixture()
def mock_result():
    result = MagicMock()
    return result


class TestPermission:
    @pytest.mark.asyncio
    async def test_create_permission_success(self, mock_db_session):
        permission_data = PermissionCreate(code='test.code', description='test description')

        result = await permission_crud.create(db=mock_db_session, obj_in=permission_data)

        assert result.code == 'test.code'
        assert result.description == 'test description'
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_permission_exists(self, mock_db_session):
        permission_data = PermissionCreate(code='existing.code', description='test description')

        mock_db_session.commit.side_effect = IntegrityError(MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await permission_crud.create(db=mock_db_session, obj_in=permission_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Permission with code 'existing.code' already exists"
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_permission_success(self, mock_db_session, mock_permission, mock_result):
        mock_result.scalars.return_value.first.return_value = mock_permission
        mock_db_session.execute.return_value = mock_result

        result = await permission_crud.get(db=mock_db_session, obj_id=mock_permission.id)

        assert result.id == mock_permission.id
        assert result.code == mock_permission.code
        assert result.description == mock_permission.description
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_permission_not_found(self, mock_db_session, mock_permission, mock_result):
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await permission_crud.get(db=mock_db_session, obj_id=mock_permission.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Permission not found"
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_permission_success(self, mock_db_session, mock_permission, mock_result):
        update_data = PermissionUpdate(code='new.code', description='new description')

        updated_perm = await permission_crud.update(db=mock_db_session, db_obj=mock_permission, obj_in=update_data)

        assert updated_perm.code == 'new.code'
        assert updated_perm.description == 'new description'
        assert updated_perm.id == mock_permission.id
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_permission_integrity_error(self, mock_db_session, mock_permission, mock_result):
        update_data = PermissionUpdate(code='existing.code', description='new description')

        mock_db_session.commit.side_effect = IntegrityError(MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await permission_crud.update(db=mock_db_session, db_obj=mock_permission, obj_in=update_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Permission with code 'existing.code' already exists"
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_permission_success(self, mock_db_session, mock_permission, mock_result):
        mock_result.scalars.return_value.first.return_value = mock_permission
        mock_db_session.execute.return_value = mock_result

        result = await permission_crud.delete(db=mock_db_session, obj_id=mock_permission.id)

        assert result == mock_permission
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_permission_not_found(self, mock_db_session, mock_permission, mock_result):
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await permission_crud.delete(db=mock_db_session, obj_id=mock_permission.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Permission not found"
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_not_called()

