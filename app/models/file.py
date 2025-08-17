import uuid
from sqlalchemy import (
    String,
    DateTime,
    func,
    ForeignKey,
    Integer,
    Table,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


message_files = Table(
    "message_files",
    Base.metadata,
    Column("message_id", String(32), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
    Column("file_id", String(32), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True),
)


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    upload_date: Mapped[str] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        "Message", secondary=message_files, back_populates="files"
    )

    @property
    def public_url(self) -> str:
        """Return a publicly accessible URL for this file."""
        from ..services import file_service

        return file_service.public_url(self.path)
