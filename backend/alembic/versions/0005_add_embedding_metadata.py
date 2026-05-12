"""Add embedding metadata column for provenance tracking

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-12 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    # Add embedding_metadata JSON column to all embedding-aware tables
    op.add_column('saved_content', sa.Column('embedding_metadata', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('embedding_metadata', sa.JSON(), nullable=True))
    op.add_column('tasks', sa.Column('embedding_metadata', sa.JSON(), nullable=True))
    op.add_column('subtasks', sa.Column('embedding_metadata', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('subtasks', 'embedding_metadata')
    op.drop_column('tasks', 'embedding_metadata')
    op.drop_column('projects', 'embedding_metadata')
    op.drop_column('saved_content', 'embedding_metadata')
