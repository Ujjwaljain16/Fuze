"""Initial database schema creation (idempotent)

Revision ID: 0001
Revises: None
Create Date: 2026-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Enable pgvector extension (idempotent)
    try:
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    except Exception as e:
        print(f"Note: pgvector extension creation skipped or unsupported: {e}")

    # 2. Base tables creation (idempotent with IF NOT EXISTS)
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(256) NOT NULL,
            technology_interests TEXT,
            user_metadata JSON,
            provider_name VARCHAR(50),
            provider_user_id VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            failed_login_count INTEGER NOT NULL DEFAULT 0,
            last_failed_login TIMESTAMP,
            account_locked_until TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            technologies TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            intent_analysis JSON,
            intent_analysis_updated TIMESTAMP,
            embedding vector(384)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS saved_content (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            title VARCHAR(200) NOT NULL,
            source VARCHAR(50),
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            extracted_text TEXT,
            embedding vector(384),
            tags TEXT,
            category VARCHAR(100),
            notes TEXT,
            quality_score INTEGER DEFAULT 10
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS content_analysis (
            id SERIAL PRIMARY KEY,
            content_id INTEGER NOT NULL REFERENCES saved_content(id) ON DELETE CASCADE,
            analysis_data JSON NOT NULL,
            key_concepts TEXT,
            content_type VARCHAR(100),
            difficulty_level VARCHAR(50),
            technology_tags TEXT,
            relevance_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT _content_analysis_unique UNIQUE (content_id)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            content_id INTEGER NOT NULL REFERENCES saved_content(id) ON DELETE CASCADE,
            feedback_type VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT _user_content_feedback_uc UNIQUE (user_id, content_id)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content_id INTEGER NOT NULL REFERENCES saved_content(id) ON DELETE CASCADE,
            recommendation_id INTEGER,
            feedback_type VARCHAR(20) NOT NULL,
            context_data JSON,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            embedding vector(384)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS subtasks (
            id SERIAL PRIMARY KEY,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            embedding vector(384)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS token_families (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            family_id VARCHAR(36) NOT NULL UNIQUE,
            current_jti VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN NOT NULL DEFAULT FALSE,
            revoked_reason VARCHAR(50)
        );
    """)

    # 3. Base Indexes (matching models.py)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_provider_name ON users (provider_name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_provider_user_id ON users (provider_user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users (lower(username));")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (lower(email));")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_user_id ON projects (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_created_at ON projects (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_user_created ON projects (user_id, created_at);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_saved_content_user_id ON saved_content (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_saved_content_saved_at ON saved_content (saved_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_saved_content_quality_score ON saved_content (quality_score);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_saved_content_user_quality ON saved_content (user_id, quality_score);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_saved_content_user_saved_at ON saved_content (user_id, saved_at);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_user_id ON feedback (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_project_id ON feedback (project_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_content_id ON feedback (content_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedback_lookup ON feedback (user_id, content_id);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON user_feedback (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_content ON user_feedback (content_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback (timestamp);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_token_families_user_id ON token_families (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_token_families_family_id ON token_families (family_id);")

def downgrade():
    # Non-destructive downgrade stub to prevent accidental schema drop in production
    pass
