"""add files and message_files tables

Revision ID: 0003_files
Revises: 0002_archive_fields
Create Date: 2025-08-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_files"
down_revision = "0002_archive_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("owner", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "message_files",
        sa.Column("message_id", sa.String(length=32), sa.ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("file_id", sa.String(length=32), sa.ForeignKey("files.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("message_files")
    op.drop_table("files")
