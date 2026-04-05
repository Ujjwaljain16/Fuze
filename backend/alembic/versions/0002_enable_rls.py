"""enable rls

Revision ID: 0002
Revises: 29ecdfbd1229
Create Date: 2026-04-05 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '29ecdfbd1229'
branch_labels = None
depends_on = None


def upgrade():
    # Only applied to tables that have 'user_id' column
    tables_with_user_id = [
        'saved_content', 
        'projects', 
        'tasks', 
        'subtasks', 
        'content_analysis', 
        'user_feedback'
    ]
    
    for table_name in tables_with_user_id:
        # ENABLE ROW LEVEL SECURITY
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
        
        # CREATE POLICY
        op.execute(f"""
            CREATE POLICY {table_name}_user_isolation
            ON {table_name}
            FOR ALL
            USING (user_id = current_setting('app.current_user_id', true)::uuid);
        """)


def downgrade():
    tables_with_user_id = [
        'saved_content', 
        'projects', 
        'tasks', 
        'subtasks', 
        'content_analysis', 
        'user_feedback'
    ]
    
    for table_name in tables_with_user_id:
        op.execute(f"DROP POLICY IF EXISTS {table_name}_user_isolation ON {table_name};")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")
