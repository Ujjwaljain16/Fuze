from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, func, UniqueConstraint, JSON, Boolean
from sqlalchemy.dialects.postgresql import TEXT, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy import event
from sqlalchemy.orm import column_property, relationship
from core.logging_config import get_logger

logger = get_logger(__name__)

# Schema is owned by Alembic (alembic/versions); these models must match it.
db = SQLAlchemy()


class Base(db.Model):
    __abstract__ = True

    def to_dict(self):
        excluded_fields = ['password_hash', 'embedding', 'extracted_text']
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name not in excluded_fields}


def _fit_strings_to_columns(mapper, connection, target):
    """Trim VARCHAR values to their column length before they reach the database.

    Request handlers reject over-long user input with a 400. This catches derived values (a
    scraped author list, a page title, a category from an import) that would otherwise make
    the INSERT/UPDATE fail: a 500 for a request, a permanently failing job for the pipeline.
    """
    for column in mapper.columns:
        length = getattr(column.type, 'length', None)
        if not length or not isinstance(column.type, String) or isinstance(column.type, Text):
            continue
        value = getattr(target, column.key, None)
        if isinstance(value, str) and len(value) > length:
            setattr(target, column.key, value[:length])


event.listen(Base, 'before_insert', _fit_strings_to_columns, propagate=True)
event.listen(Base, 'before_update', _fit_strings_to_columns, propagate=True)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    technology_interests = Column(TEXT)
    user_metadata = Column(JSON)  # Store user-specific data like API keys (encrypted)
    # OAuth provider info
    provider_name = Column(String(50), nullable=True, index=True)
    provider_user_id = Column(String(200), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now())
    # Account lockout fields
    failed_login_count  = Column(Integer, default=0, nullable=False, server_default='0')
    last_failed_login   = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)

    # Additional indexes for optimized username queries
    __table_args__ = (
        db.Index('idx_users_username_lower', func.lower(username)),  # Case-insensitive username search
        db.Index('idx_users_email_lower', func.lower(email)),  # Case-insensitive email search
        db.Index('idx_users_created_at', created_at),  # For user analytics
    )

    # What a user may see about their own account. Everything else (user_metadata holds the
    # encrypted Gemini key and its hash; lockout counters; provider ids) stays server-side.
    PUBLIC_FIELDS = ('id', 'username', 'email', 'technology_interests', 'provider_name', 'created_at')

    def to_dict(self):
        return {name: getattr(self, name) for name in self.PUBLIC_FIELDS}

    saved_content = relationship('SavedContent', backref='user', lazy=True, cascade='all, delete-orphan')
    projects = relationship('Project', backref='user', lazy=True, cascade='all, delete-orphan')
    token_families = relationship('TokenFamily', backref='user', lazy=True, cascade='all, delete-orphan')

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(TEXT)
    technologies = Column(TEXT)
    created_at = Column(DateTime, default=func.now())

    # (user_id, created_at) serves both "this user's projects" and "newest first"
    __table_args__ = (
        db.Index('idx_projects_user_created', 'user_id', 'created_at'),
    )

    tasks = relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

class SavedContent(Base):
    __tablename__ = 'saved_content'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)  # covered by _user_url_uc
    url = Column(TEXT, nullable=False)
    title = Column(String(200), nullable=False)
    source = Column(String(50))
    saved_at = Column(DateTime, default=func.now(), index=True)  # Indexed for sorting
    extracted_text = Column(TEXT)
    embedding = Column(Vector(384))
    tags = Column(TEXT)
    category = Column(String(100))
    notes = Column(TEXT)
    quality_score = Column(Integer, default=10)  # filtered per user via idx_saved_content_user_quality
    embedding_metadata = Column(JSON, nullable=True)
    
    # Stage status & timestamp fields for event-driven pipeline
    scrape_status = Column(String(20), default='PENDING', server_default='PENDING', index=True)
    embedding_status = Column(String(20), default='PENDING', server_default='PENDING', index=True)
    analysis_status = Column(String(20), default='PENDING', server_default='PENDING', index=True)
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    embedded_at = Column(DateTime(timezone=True), nullable=True)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    pipeline_version = Column(Integer, default=1, server_default='1')

    # Acquisition metadata & provenance fields
    author = Column(String(255), nullable=True)
    reading_time = Column(Integer, default=0)
    published_at = Column(DateTime(timezone=True), nullable=True)
    language = Column(String(10), nullable=True)
    content_hash = Column(String(64), nullable=True)
    strategy_used = Column(String(20), nullable=True)
    scrapling_version = Column(String(20), nullable=True)
    extractor_version = Column(String(20), nullable=True)

    # bool(extracted_text) computed in SQL, so list views can report it without loading the text.
    # Deferred: only queries that ask for it (undefer) pay for it.
    has_extracted_text = column_property(
        db.and_(extracted_text.isnot(None), extracted_text != ''), deferred=True
    )

    # Relationship to rich JSON metadata
    rich_metadata = relationship('BookmarkMetadata', backref='bookmark', uselist=False, cascade='all, delete-orphan')

    # Production indexes and unique constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'url', name='_user_url_uc'),
        db.Index('idx_saved_content_user_quality', 'user_id', 'quality_score'),
        db.Index('idx_saved_content_user_saved_at', 'user_id', 'saved_at'),
        # Matches the actual partial index created by alembic migration 0003
        # (CREATE INDEX CONCURRENTLY ... WHERE extracted_text IS NOT NULL AND
        # extracted_text != ''). Migration 0007 later tried to recreate this as
        # a non-partial index under the same name, which silently no-opped
        # (IF NOT EXISTS) since 0003 had already created it -- so the DB has
        # always had the partial version. This declaration previously didn't
        # include postgresql_where, which made Alembic autogenerate believe
        # there was schema drift that didn't actually exist.
        db.Index(
            'idx_saved_content_user_unanalyzed', 'user_id', 'id',
            postgresql_where=db.text("extracted_text IS NOT NULL AND extracted_text != ''")
        ),
        db.Index('idx_saved_content_content_hash', 'content_hash'),
        db.Index(
            'idx_saved_content_embedding_hnsw', 'embedding', postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'},
        ),
    )



def processed_bookmark_clause():
    """A bookmark is processed once its content is fetched and it is embedded: searchable.
    The dashboard and the stats endpoint both count successes with this, so they agree."""
    return (SavedContent.scrape_status == 'SUCCESS') & (SavedContent.embedding_status == 'SUCCESS')

class ContentChunk(Base):
    """A passage of a bookmark (kind='passage') or its embedded content profile (kind='profile')."""
    __tablename__ = 'content_chunks'
    id = Column(BigInteger, primary_key=True)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, nullable=False)
    kind = Column(String(16), nullable=False, default='passage', server_default='passage')
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    # Vectors from different models live in different spaces and must never be compared.
    embedding_model = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('content_id', 'kind', 'chunk_index', name='uq_content_chunks_content_kind_idx'),
        db.Index('idx_content_chunks_user_model', 'user_id', 'embedding_model'),
        db.Index(
            'idx_content_chunks_embedding_hnsw', 'embedding', postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'},
        ),
    )


class BookmarkMetadata(Base):
    """Stores full provider raw JSON payloads (JSON-LD, OpenGraph, Breadcrumbs, etc.) for a bookmark."""
    __tablename__ = 'bookmark_metadata'
    bookmark_id = Column(BigInteger, ForeignKey('saved_content.id', ondelete='CASCADE'), primary_key=True)
    jsonb_payload = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        db.Index('idx_bookmark_metadata_jsonb', 'jsonb_payload', postgresql_using='gin'),
    )

class ContentAnalysis(Base):
    __tablename__ = 'content_analysis'
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False)
    analysis_data = Column(JSON, nullable=False)  # Store Gemini analysis as JSON
    key_concepts = Column(TEXT)  # Extracted key concepts
    content_type = Column(String(100))  # e.g., 'tutorial', 'documentation', 'article'
    difficulty_level = Column(String(50))  # e.g., 'beginner', 'intermediate', 'advanced'
    technology_tags = Column(TEXT)  # Comma-separated technology tags
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to SavedContent
    content = relationship('SavedContent', backref='analyses')

    # Production constraints
    __table_args__ = (
        UniqueConstraint('content_id', name='_content_analysis_unique'),
    )

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=True, index=True)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)  # 'like', 'dislike', 'bookmark', 'dismiss'
    timestamp = Column(DateTime, default=func.now())

    # Ensure one feedback per user per content
    __table_args__ = (
        UniqueConstraint('user_id', 'content_id', name='_user_content_feedback_uc'),
        db.Index('idx_feedback_lookup', 'user_id', 'content_id'),
    )

class UserFeedback(Base):
    """Stores detailed user feedback for recommendations to improve recommendation algorithms."""
    __tablename__ = 'user_feedback'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False)
    recommendation_id = Column(Integer, nullable=True)
    feedback_type = Column(String(20), nullable=False)
    context_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    __table_args__ = (
        db.Index('idx_user_feedback_user', 'user_id'),
        db.Index('idx_user_feedback_content', 'content_id'),
        db.Index('idx_user_feedback_timestamp', 'timestamp'),
    )

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        db.Index('idx_tasks_project_created', 'project_id', 'created_at'),
    )

    subtasks = relationship('Subtask', backref='task', lazy=True, cascade='all, delete-orphan', order_by='Subtask.created_at')

class Subtask(Base):
    __tablename__ = 'subtasks'
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    completed = Column(Integer, default=0)  # 0 = not completed, 1 = completed
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        db.Index('idx_subtasks_task_created', 'task_id', 'created_at'),
    )


class TokenFamily(Base):
    """
    Tracks refresh token rotation families.
    When a refresh token is used, its jti is compared against current_jti.
    If they differ, it means a previously-rotated token was replayed → revoke entire family.
    """
    __tablename__ = 'token_families'
    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    family_id      = Column(String(36), unique=True, nullable=False, index=True)
    current_jti    = Column(String(36), nullable=False)
    created_at     = Column(DateTime, default=func.now())
    last_used_at   = Column(DateTime, default=func.now())
    revoked        = Column(Boolean, default=False, nullable=False)
    revoked_reason = Column(String(50), nullable=True)  # 'logout', 'reuse_detected', 'expired'


class BookmarkEvent(Base):
    """Stores immutable audit and stage timeline events for pipeline execution."""
    __tablename__ = 'bookmark_events'
    # BIGSERIAL on Postgres. SQLite only auto-increments INTEGER primary keys, so with BigInteger
    # every event insert failed there (silently: publish_pipeline_event logs and moves on).
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    bookmark_id = Column(BigInteger, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    pipeline_run_id = Column(String(64), nullable=False)
    sequence = Column(Integer, default=1, nullable=False)
    type = Column(String(100), nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)
    data = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True)
    error = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True)
    metadata_json = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        db.Index('ix_bookmark_events_bookmark_seq', 'bookmark_id', 'sequence'),
        db.Index('ix_bookmark_events_user_created', 'user_id', 'created_at'),
    )