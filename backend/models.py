from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import TEXT
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship

# Initialize SQLAlchemy with enhanced configuration
db = SQLAlchemy()

# Configure SQLAlchemy to use our connection manager
def configure_database():
    """Configure database with enhanced SSL handling"""
    try:
        from utils.database_connection_manager import get_database_engine
        engine = get_database_engine()
        
        # Update the SQLAlchemy engine
        db.engine = engine
        
        # Configure session
        db.session.configure(bind=engine)
        
        # Ensure user_metadata column exists (migration helper)
        ensure_user_metadata_column()
        
        return True
    except Exception as e:
        print(f"Failed to configure database: {e}")
        return False

def ensure_user_metadata_column():
    """Ensure user_metadata column exists in users table (migration helper)"""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'user_metadata' not in columns:
            print("Adding missing 'user_metadata' column to users table...")
            try:
                # Try to add the column
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN user_metadata JSON;
                """))
                db.session.commit()
                print("✅ Column 'user_metadata' added successfully")
            except Exception as add_error:
                # If column already exists (race condition), that's fine
                error_str = str(add_error).lower()
                if 'already exists' in error_str or 'duplicate' in error_str:
                    print("✅ Column 'user_metadata' already exists")
                    db.session.rollback()
                else:
                    raise
    except Exception as e:
        # Don't fail if column already exists or can't be added
        print(f"Note: Could not ensure user_metadata column: {e}")
        try:
            db.session.rollback()
        except:
            pass

class Base(db.Model):
    __abstract__ = True
    def to_dict(self):
        excluded_fields = ['password_hash', 'embedding', 'extracted_text']
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name not in excluded_fields}


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    technology_interests = Column(TEXT)
    user_metadata = Column(JSON)  # Store user-specific data like API keys (encrypted) - renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=func.now())

    saved_content = relationship('SavedContent', backref='user', lazy=True, cascade='all, delete-orphan')
    projects = relationship('Project', backref='user', lazy=True, cascade='all, delete-orphan')

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(TEXT)
    technologies = Column(TEXT)
    created_at = Column(DateTime, default=func.now())

    # Intent analysis caching fields
    intent_analysis = Column(JSON)  # Store intent analysis results
    intent_analysis_updated = Column(DateTime)  # When analysis was last updated

    # Embedding field for semantic matching
    embedding = Column(Vector(384))  # Combined embedding for semantic matching

    tasks = relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

class SavedContent(Base):
    __tablename__ = 'saved_content'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    url = Column(TEXT, nullable=False)
    title = Column(String(200), nullable=False)
    source = Column(String(50))
    saved_at = Column(DateTime, default=func.now())
    extracted_text = Column(TEXT)
    embedding = Column(Vector(384))
    tags = Column(TEXT)
    category = Column(String(100))
    notes = Column(TEXT)
    quality_score = Column(Integer, default=10)

class ContentAnalysis(Base):
    __tablename__ = 'content_analysis'
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False)
    analysis_data = Column(JSON, nullable=False)  # Store Gemini analysis as JSON
    key_concepts = Column(TEXT)  # Extracted key concepts
    content_type = Column(String(100))  # e.g., 'tutorial', 'documentation', 'article'
    difficulty_level = Column(String(50))  # e.g., 'beginner', 'intermediate', 'advanced'
    technology_tags = Column(TEXT)  # Comma-separated technology tags
    relevance_score = Column(Integer, default=0)  # 0-100 relevance score
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to SavedContent
    content = relationship('SavedContent', backref='analyses')

    __table_args__ = (UniqueConstraint('content_id', name='_content_analysis_unique'),)

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False)
    feedback_type = Column(String(20), nullable=False)  # e.g., 'relevant', 'not_relevant'
    timestamp = Column(DateTime, default=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'project_id', 'content_id', name='_user_project_content_uc'),)

class UserFeedback(Base):
    """Enhanced feedback system for learning from user interactions"""
    __tablename__ = 'user_feedback'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content_id = Column(Integer, ForeignKey('saved_content.id', ondelete='CASCADE'), nullable=False)
    recommendation_id = Column(Integer, nullable=True)  # Optional: track recommendation session
    feedback_type = Column(String(20), nullable=False)  # 'clicked', 'saved', 'dismissed', 'not_relevant', 'helpful', 'completed'
    context_data = Column(JSON)  # Store query, project_id, etc.
    timestamp = Column(DateTime, default=func.now())
    
    # Indexes for faster queries
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
    embedding = Column(Vector(384))
    
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
    embedding = Column(Vector(384))  # Embedding for semantic matching in recommendations