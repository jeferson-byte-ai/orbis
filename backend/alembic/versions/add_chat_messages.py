"""add chat messages table

Revision ID: add_chat_messages
Revises: add_user_languages
Create Date: 2024-01-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'add_chat_messages'
down_revision = 'add_user_languages'
branch_labels = None
depends_on = None


def upgrade():
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('room_id', UUID(as_uuid=True), sa.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    # Drop chat_messages table
    op.drop_table('chat_messages')
