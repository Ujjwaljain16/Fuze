from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func, UniqueConstraint
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
    password_hash = Column(String(256), nullable=False) # <--- CORRECTED: Increased length to 256
    technology_interests = Column(TEXT)
    created_at = Column(DateTime, default=func.now())

    saved_content = relationship('SavedContent', backref='user', lazy=True)
    projects = relationship('Project', backref='user', lazy=True)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(TEXT)
    technologies = Column(TEXT)
    created_at = Column(DateTime, default=func.now())

class SavedContent(Base):
    __tablename__ = 'saved_content'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    url = Column(TEXT, nullable=False)
    title = Column(String(200), nullable=False)
    source = Column(String(50))
    saved_at = Column(DateTime, default=func.now())
    extracted_text = Column(TEXT)
    embedding = Column(Vector(384))
    tags = Column(TEXT)
    category = Column(String(100))
    notes = Column(TEXT)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    content_id = db.Column(db.Integer, db.ForeignKey('saved_content.id'), nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False)  # e.g., 'relevant', 'not_relevant'
    timestamp = db.Column(db.DateTime, default=func.now())

    __table_args__ = (UniqueConstraint('user_id', 'project_id', 'content_id', name='_user_project_content_uc'),)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now())
    embedding = db.Column(Vector(384))