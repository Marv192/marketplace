from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.crud import role_crud
from app.models import Role, Permission
from app.schemas import RoleCreate
from app.schemas.roles import RoleUpdate, RolePermissionsUpdate


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
def mock_role():
    role = MagicMock(spec=Role)
    role.id = 1
    role.name = 'test role'
    role.description = 'test description'
    role.permissions = []
    return role

@pytest.fixture()
def mock_result():
    result = MagicMock()
    return result

class TestRole:
    @pytest.mark.asyncio
    async def test_create_role_success(self, mock_db_session):
        role_data = RoleCreate(name='test name', description='test description')

        result = await role_crud.create(db=mock_db_session, obj_in=role_data)

        assert result.name == 'test name'
        assert result.description == 'test description'
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role_exists(self, mock_db_session):
        role_data = RoleCreate(name='existing name', description='test description')

        mock_db_session.commit.side_effect = IntegrityError(MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await role_crud.create(db=mock_db_session, obj_in=role_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Role with name 'existing name' already exists"
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_success(self, mock_db_session, mock_role, mock_result):
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db_session.execute.return_value = mock_result

        result = await role_crud.get(db=mock_db_session, obj_id=mock_role.id)

        assert result.name == mock_role.name
        assert result.description == mock_role.description
        assert result.id == mock_role.id
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_not_found(self, mock_db_session, mock_role, mock_result):
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await role_crud.get(db=mock_db_session, obj_id=mock_role.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Role not found"
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_role_success(self, mock_db_session, mock_role, mock_result):
        update_data = RoleUpdate(name='new name', description='new description')

        result = await role_crud.update(db=mock_db_session, db_obj=mock_role, obj_in=update_data)

        assert result.name == 'new name'
        assert result.description == 'new description'
        assert result.id == mock_role.id
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_role_integrity_error(self, mock_db_session, mock_role, mock_result):
        update_data = RoleUpdate(name='existing name', description='new description')

        mock_db_session.commit.side_effect = IntegrityError(MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await role_crud.update(db=mock_db_session, db_obj=mock_role, obj_in=update_data)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Role with name 'existing name' already exists"
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_role_success(self, mock_db_session, mock_role, mock_result):
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db_session.execute.return_value = mock_result

        result = await role_crud.delete(db=mock_db_session, obj_id=mock_role.id)

        assert result == mock_role
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_role_not_found(self, mock_db_session, mock_role, mock_result):
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await role_crud.delete(db=mock_db_session, obj_id=mock_role.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Role not found"
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_permissions_success(self, mock_db_session, mock_role, mock_result):
        permission_ids = [1, 2]
        update_data = RolePermissionsUpdate(permission_ids=permission_ids)
        mock_perm1, mock_perm2 = MagicMock(spec=Permission), MagicMock(spec=Permission)
        mock_perm1.id = 1
        mock_perm2.id = 2

        mock_result.scalars.return_value.all.return_value = [mock_perm1, mock_perm2]
        mock_db_session.execute.return_value = mock_result

        result = await role_crud.add_permissions(db=mock_db_session, db_obj=mock_role, permissions=update_data)

        assert mock_perm1 in result.permissions
        assert mock_perm2 in result.permissions
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_permissions_not_found(self, mock_db_session, mock_role, mock_result):
        permission_ids = [1, 2]
        update_data = RolePermissionsUpdate(permission_ids=permission_ids)
        mock_perm1 = MagicMock(spec=Permission)
        mock_perm1.id = 1

        mock_result.scalars.return_value.all.return_value = [mock_perm1]
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await role_crud.add_permissions(db=mock_db_session, db_obj=mock_role, permissions=update_data)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Permissions with ids: '{2}' not found"
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_permissions_success(self, mock_db_session, mock_role, mock_result):
        perm1, perm2 = MagicMock(spec=Permission), MagicMock(spec=Permission)
        perm1.id = 1
        perm2.id = 2
        mock_role.permissions = [perm1, perm2]

        update_data = RolePermissionsUpdate(permission_ids=[1])

        result = await role_crud.remove_permissions(db=mock_db_session, db_obj=mock_role, permissions=update_data)

        assert perm1 not in result.permissions
        assert perm2 in result.permissions
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()

