import uuid
from datetime import datetime

from sqlalchemy import Column, UUID, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.db import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    role = relationship("Role", lazy="selectin", back_populates="users")