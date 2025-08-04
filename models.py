from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import TEXT
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship

db = SQLAlchemy()

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

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    embedding = Column(Vector(384))