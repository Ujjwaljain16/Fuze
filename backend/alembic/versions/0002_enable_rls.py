"""Enable RLS and set User Isolation Policies

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-22 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    # Helper to enable RLS and set policy
    tables_with_user_id = ['projects', 'saved_content', 'user_feedback']
    
    for table in tables_with_user_id:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY {table}_user_isolation ON {table}
            FOR ALL
            USING (user_id = current_setting('app.current_user_id', true)::integer);
        """)

    # Special case for 'users' table
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY users_self_isolation ON users
        FOR ALL
        USING (id = current_setting('app.current_user_id', true)::integer);
    """)

    # Transitive RLS for related tables
    
    # content_analysis (linked to saved_content)
    op.execute("ALTER TABLE content_analysis ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY content_analysis_user_isolation ON content_analysis
        FOR ALL
        USING (EXISTS (
            SELECT 1 FROM saved_content sc 
            WHERE sc.id = content_analysis.content_id 
            AND sc.user_id = current_setting('app.current_user_id', true)::integer
        ));
    """)

    # tasks (linked to projects)
    op.execute("ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tasks_user_isolation ON tasks
        FOR ALL
        USING (EXISTS (
            SELECT 1 FROM projects p 
            WHERE p.id = tasks.project_id 
            AND p.user_id = current_setting('app.current_user_id', true)::integer
        ));
    """)

    # subtasks (linked to tasks)
    op.execute("ALTER TABLE subtasks ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY subtasks_user_isolation ON subtasks
        FOR ALL
        USING (EXISTS (
            SELECT 1 FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.id = subtasks.task_id
            AND p.user_id = current_setting('app.current_user_id', true)::integer
        ));
    """)

def downgrade():
    tables = [
        'subtasks', 'tasks', 'content_analysis', 
        'users', 'user_feedback', 'saved_content', 'projects'
    ]
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_user_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_self_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
