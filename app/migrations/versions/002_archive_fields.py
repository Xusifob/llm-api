"""add archived fields to conversations

Revision ID: 0002_archive_fields
Revises: 0001_init
Create Date: 2025-08-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_archive_fields"
down_revision = "0001_init"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("conversations", sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("conversations", sa.Column("archived_at", sa.DateTime(timezone=False), nullable=True))

def downgrade() -> None:
    op.drop_column("conversations", "archived_at")
    op.drop_column("conversations", "archived")
