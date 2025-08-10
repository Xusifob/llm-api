import uuid
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base

def _uuid() -> str:
    return uuid.uuid4().hex

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user")
