from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.db import Base


roles_permissions = Table(
    'roles_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'),
           primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'),
           primary_key=True),
)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)
    users = relationship('User', back_populates='role')
    permissions = relationship('Permission', secondary=roles_permissions, lazy='selectin',
                               back_populates='roles')

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    roles = relationship('Role', secondary=roles_permissions, lazy='selectin',
                         back_populates='permissions')

