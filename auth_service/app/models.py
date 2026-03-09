import os

from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID

DUMMY_DB_URL = 'postgresql://user:pass@localhost:5432/testdb'
DATABASE_URL = os.getenv('DATABASE_URL', DUMMY_DB_URL)
MIGRATION_DATABASE_URL = os.getenv('MIGRATION_DATABASE_URL', DUMMY_DB_URL)

# для асинхронной работы
database = Database(DATABASE_URL)
# для миграций
engine = create_engine(MIGRATION_DATABASE_URL)
metadata = MetaData()

roles = Table(
    'roles',
    metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('name', String, unique=True, nullable=False),
    Column('description', String, nullable=True),
)

users = Table(
    'users',
    metadata,
    Column('id', UUID(as_uuid=True), unique=True, primary_key=True),
    Column('email', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False),
    Column('name', String, nullable=False),
    Column('role_id', Integer, ForeignKey('roles.id'), nullable=False, default=1, server_default='1'),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
)

permissions = Table(
    'permissions',
    metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('code', String, unique=True, nullable=False),
    Column('description', String, nullable=False)
)

roles_permissions = Table(
    'roles_permissions',
    metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)

