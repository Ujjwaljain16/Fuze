import os
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text # Needed for CREATE EXTENSION and pgvector operators
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import numpy as np # For handling embeddings
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import requests
from readability import Document
from bs4 import BeautifulSoup
from sqlalchemy import func # Needed for func.now()

# Import the SentenceTransformer model
# This model will be downloaded the first time it's initialized.
# 'all-Min-dimensionaiLM-L6-v2' outputs 384l embeddings.
from sentence_transformers import SentenceTransformer

# Import database and models from models.py
# Make sure models.py is in the same directory as app.py
from models import db, User, Project, SavedContent, Feedback, Task

# Load environment variables from .env file
load_dotenv()

# --- Flask Application Initialization ---
app = Flask(__name__)

# Load configuration from config.py
# This will set up SQLALCHEMY_DATABASE_URI and SECRET_KEY
app.config.from_object('config.Config')

# Initialize SQLAlchemy with the Flask app
db.init_app(app)

# Initialize JWT
jwt = JWTManager(app)

# --- Global Variables ---
# Initialize the SentenceTransformer model
# It's good practice to load this once globally to avoid re-loading on every request.
# Ensure the dimension (384) matches the VECTOR dimension in models.py
try:
    sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("SentenceTransformer model loaded successfully.")
except Exception as e:
    print(f"Error loading SentenceTransformer model: {e}")
    sbert_model = None # Set to None if loading fails, handle in functions

# --- Database Initialization Function ---
def init_db():
    """
    Initializes the database: ensures pgvector extension is enabled and creates tables.
    This function should be called within an application context.
    """
    try:
        # Ensure pgvector extension is enabled
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        db.session.commit()
        print("pgvector extension ensured to be enabled.")

        # Create all tables defined in models.py
        db.create_all()
        print("Database tables created/checked.")
    except Exception as e:
        print(f"Error during database initialization: {e}")

# --- Helper Function for Embedding Generation ---
def get_embedding(text_input: str) -> np.ndarray:
    """
    Generates a vector embedding for a given text string using the SBERT model.
    Handles cases where the model might not be loaded.
    """
    if sbert_model is None:
        print("Warning: SentenceTransformer model not loaded. Cannot generate embedding.")
        return np.zeros(384) # Return a zero vector or handle error appropriately
    try:
        # Encode the text to get its embedding
        # .tolist() is important for pgvector.sqlalchemy to handle the array correctly
        return sbert_model.encode(text_input).tolist()
    except Exception as e:
        print(f"Error generating embedding for text: '{text_input}' - {e}")
        return np.zeros(384) # Return a zero vector on error

# --- Helper Function to Extract Article Text from URL ---
def extract_article_text_from_url(url: str) -> str:
    """
    Fetches the web page at the given URL and extracts the main article text.
    Returns an empty string if extraction fails.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FuzeBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        doc = Document(response.text)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return text
    except Exception as e:
        print(f"Error extracting article text from {url}: {e}")
        return ""

# --- API Endpoints ---

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    username = data.get('username')
    password = data.get('password')
    technology_interests = data.get('technology_interests', '')

    # Input Validation for Registration
    if not isinstance(username, str) or not username.strip():
        return jsonify({"message": "Username is required and must be a non-empty string"}), 400
    if len(username.strip()) < 3 or len(username.strip()) > 80:
        return jsonify({"message": "Username must be between 3 and 80 characters"}), 400
    if not isinstance(password, str) or not password.strip():
        return jsonify({"message": "Password is required and must be a non-empty string"}), 400
    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters long"}), 400
    if technology_interests is not None and not isinstance(technology_interests, str):
        return jsonify({"message": "Technology interests must be a string"}), 400

    hashed_password = generate_password_hash(password)

    new_user = User(
        username=username.strip(),
        password_hash=hashed_password,
        technology_interests=technology_interests.strip() if isinstance(technology_interests, str) else ''
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully", "user_id": new_user.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Username already exists"}), 409
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error registering user: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred during registration"}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    username = data.get('username')
    password = data.get('password')

    # Input Validation for Login
    if not isinstance(username, str) or not username.strip():
        return jsonify({"message": "Username is required and must be a non-empty string"}), 400
    if not isinstance(password, str) or not password.strip():
        return jsonify({"message": "Password is required and must be a non-empty string"}), 400

    user = User.query.filter_by(username=username.strip()).first()

    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401

@app.route('/api/projects', methods=['POST'])
@jwt_required()
def create_project():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    title = data.get('title')
    description = data.get('description')
    technologies = data.get('technologies', '')

    # Input Validation for Project Creation
    if not isinstance(title, str) or not title.strip():
        return jsonify({"message": "Project title is required and must be a non-empty string"}), 400
    if len(title.strip()) > 100:
        return jsonify({"message": "Project title cannot exceed 100 characters"}), 400
    if not isinstance(description, str) or not description.strip():
        return jsonify({"message": "Project description is required and must be a non-empty string"}), 400
    if technologies is not None and not isinstance(technologies, str):
        return jsonify({"message": "Technologies must be a string"}), 400
    if isinstance(technologies, str) and len(technologies) > 255:
        return jsonify({"message": "Technologies string too long"}), 400

    user = User.query.get(int(current_user_id))
    if not user:
        return jsonify({"message": "User not found"}), 404

    new_project = Project(
        user_id=user.id,
        title=title.strip(),
        description=description.strip(),
        technologies=technologies.strip() if isinstance(technologies, str) else ''
    )

    try:
        db.session.add(new_project)
        db.session.commit()
        return jsonify({"message": "Project created successfully", "project_id": new_project.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating project: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred during project creation"}), 500

@app.route('/api/projects/<int:user_id>', methods=['GET'])
def get_user_projects(user_id):
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    pagination = Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    projects_data = [{
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "technologies": project.technologies,
        "created_at": project.created_at.isoformat()
    } for project in pagination.items]
    return jsonify({
        "projects": projects_data,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200

@app.route('/api/save_content', methods=['POST'])
@jwt_required()
def save_content():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    url = data.get('url')
    title = data.get('title')
    notes = data.get('notes', '')
    source = data.get('source', 'Manual')
    tags = data.get('tags', '')
    category = data.get('category', '')

    # Input Validation for Save Content
    if not isinstance(url, str) or not url.strip():
        return jsonify({"message": "URL is required and must be a non-empty string"}), 400
    if not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({"message": "URL must start with http:// or https://"}), 400
    if len(url) > 500:
        return jsonify({"message": "URL cannot exceed 500 characters"}), 400

    if title is not None and (not isinstance(title, str) or len(title.strip()) == 0):
        return jsonify({"message": "Title must be a non-empty string if provided"}), 400
    if isinstance(title, str) and len(title.strip()) > 200:
        return jsonify({"message": "Title cannot exceed 200 characters"}), 400

    if not isinstance(notes, str):
        return jsonify({"message": "Notes must be a string"}), 400
    if len(notes) > 10000:
        return jsonify({"message": "Notes too long"}), 400

    if not isinstance(source, str):
        return jsonify({"message": "Source must be a string"}), 400
    if len(source) > 50:
        return jsonify({"message": "Source string too long"}), 400

    if not isinstance(tags, str):
        return jsonify({"message": "Tags must be a string"}), 400
    if len(tags) > 255:
        return jsonify({"message": "Tags string too long"}), 400

    if not isinstance(category, str):
        return jsonify({"message": "Category must be a string"}), 400
    if len(category) > 100:
        return jsonify({"message": "Category string too long"}), 400

    user = User.query.get(int(current_user_id))
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Extract main article text from the URL
    article_text = extract_article_text_from_url(url)
    # Combine extracted article text with user notes for embedding
    extracted_text = f"{article_text}\n{notes}" if article_text else f"{title}. {notes}"
    embedding = get_embedding(extracted_text)

    new_content = SavedContent(
        user_id=int(current_user_id),
        url=url.strip(),
        title=title.strip() if title else url.strip(),
        source=source.strip(),
        extracted_text=extracted_text,
        embedding=embedding,
        tags=tags.strip(),
        category=category.strip(),
        notes=notes.strip()
    )

    try:
        db.session.add(new_content)
        db.session.commit()
        return jsonify({"message": "Content saved successfully", "content_id": new_content.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving content: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred during content saving"}), 500

@app.route('/api/recommendations/project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project_recommendations(project_id):
    """
    Generates content recommendations based on a specific project's context.
    Performs a semantic search using pgvector.
    """
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404

    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""

    # Fallback logic: if project description and technologies are empty, use user interests or project title
    if (not project.description or not project.description.strip()) and (not project.technologies or not project.technologies.strip()):
        query_context = user_interests or project.title or ""
    else:
        query_context = (
            f"Project Title: {project.title}. "
            f"Project Description: {project.description}. "
            f"Project Technologies: {project.technologies}. "
            f"User Interests: {user_interests}"
        )

    # Generate embedding for the query context
    query_embedding = get_embedding(query_context)

    # Check if embedding generation failed
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        return jsonify({"message": "Failed to generate query embedding or empty embedding."}), 500

    # Perform vector similarity search using pgvector's cosine distance operator (<=>)
    recommendations = db.session.query(SavedContent).filter_by(user_id=user_id).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all() # Get top 10 recommendations

    if not recommendations:
        return jsonify({"message": "No recommendations found for this project."}), 200

    # In get_project_recommendations, after getting recommendations, sort by feedback:
    # 1. Boost 'relevant', 2. Demote 'not_relevant', 3. Others as is.
    # (Pseudo-code, actual implementation may require a join or post-processing)

    recommendations_data = [{
        "id": content.id,
        "title": content.title,
        "url": content.url,
        "source": content.source,
        "notes": content.notes,
        "saved_at": content.saved_at.isoformat(),
        # For simplicity, we don't return the raw embedding here
    } for content in recommendations]

    return jsonify(recommendations_data), 200

@app.route('/api/recommendations/task/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_recommendations(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    project = Project.query.get(task.project_id)
    user = User.query.get(project.user_id) if project else None
    user_interests = user.technology_interests if user else ""
    # Fallback logic: if task description is empty, use project and user context
    if (not task.description or not task.description.strip()):
        context = f"{task.title}. {project.title if project else ''}. {project.description if project else ''}. {project.technologies if project else ''}. {user_interests}"
    else:
        context = f"Task: {task.title}. {task.description}. Project: {project.title if project else ''}. {project.description if project else ''}. {project.technologies if project else ''}. {user_interests}"
    query_embedding = get_embedding(context)
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        return jsonify({"message": "Failed to generate query embedding or empty embedding."}), 500
    results = db.session.query(SavedContent).filter_by(user_id=project.user_id if project else None).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all()
    output = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in results]
    return jsonify(output), 200

@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def give_feedback():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    project_id = data.get('project_id')
    content_id = data.get('content_id')
    feedback_type = data.get('feedback_type')

    if not content_id or feedback_type not in ['relevant', 'not_relevant']:
        return jsonify({"message": "content_id and valid feedback_type are required"}), 400

    feedback = Feedback.query.filter_by(user_id=user_id, project_id=project_id, content_id=content_id).first()
    if feedback:
        feedback.feedback_type = feedback_type
        feedback.timestamp = func.now()
    else:
        feedback = Feedback(user_id=user_id, project_id=project_id, content_id=content_id, feedback_type=feedback_type)
        db.session.add(feedback)
    try:
        db.session.commit()
        return jsonify({"message": "Feedback recorded"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error saving feedback: {str(e)}"}), 500

@app.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_access_token():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify({"access_token": new_access_token}), 200

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    if str(project.user_id) != current_user_id:
        return jsonify({"message": "Unauthorized: Project does not belong to user"}), 403

    title = data.get('title')
    description = data.get('description')
    technologies = data.get('technologies')

    if title is not None:
        if not isinstance(title, str) or not title.strip():
            return jsonify({"message": "Project title must be a non-empty string if provided"}), 400
        if len(title.strip()) > 100:
            return jsonify({"message": "Project title cannot exceed 100 characters"}), 400
        project.title = title.strip()

    if description is not None:
        if not isinstance(description, str) or not description.strip():
            return jsonify({"message": "Project description must be a non-empty string if provided"}), 400
        project.description = description.strip()

    if technologies is not None:
        if not isinstance(technologies, str):
            return jsonify({"message": "Technologies must be a string"}), 400
        if len(technologies) > 255:
            return jsonify({"message": "Technologies string too long"}), 400
        project.technologies = technologies.strip()

    try:
        db.session.commit()
        return jsonify({"message": "Project updated successfully", "project_id": project.id}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating project {project_id}: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred during project update"}), 500

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    user_id = int(get_jwt_identity())
    project = Project.query.get(project_id)
    if not project or project.user_id != user_id:
        return jsonify({"message": "Project not found or unauthorized"}), 404
    try:
        db.session.delete(project)
        db.session.commit()
        return jsonify({"message": "Project deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route('/api/save_content/<int:content_id>', methods=['PUT'])
@jwt_required()
def update_saved_content(content_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    content = SavedContent.query.get(content_id)
    if not content:
        return jsonify({"message": "Saved content not found"}), 404
    if str(content.user_id) != current_user_id:
        return jsonify({"message": "Unauthorized: Content does not belong to user"}), 403

    old_extracted_text = content.extracted_text

    url = data.get('url')
    title = data.get('title')
    notes = data.get('notes')
    source = data.get('source')
    tags = data.get('tags')
    category = data.get('category')

    if url is not None:
        if not isinstance(url, str) or not url.strip():
            return jsonify({"message": "URL must be a non-empty string if provided"}), 400
        if not (url.startswith('http://') or url.startswith('https://')):
            return jsonify({"message": "URL must start with http:// or https://"}), 400
        if len(url) > 500:
            return jsonify({"message": "URL cannot exceed 500 characters"}), 400
        content.url = url.strip()

    if title is not None:
        if not isinstance(title, str) or not title.strip():
            return jsonify({"message": "Title must be a non-empty string if provided"}), 400
        if len(title.strip()) > 200:
            return jsonify({"message": "Title cannot exceed 200 characters"}), 400
        content.title = title.strip()

    if notes is not None:
        if not isinstance(notes, str):
            return jsonify({"message": "Notes must be a string"}), 400
        if len(notes) > 10000:
            return jsonify({"message": "Notes too long"}), 400
        content.notes = notes.strip()

    if source is not None:
        if not isinstance(source, str):
            return jsonify({"message": "Source must be a string"}), 400
        if len(source) > 50:
            return jsonify({"message": "Source string too long"}), 400
        content.source = source.strip()

    if tags is not None:
        if not isinstance(tags, str):
            return jsonify({"message": "Tags must be a string"}), 400
        if len(tags) > 255:
            return jsonify({"message": "Tags string too long"}), 400
        content.tags = tags.strip()

    if category is not None:
        if not isinstance(category, str):
            return jsonify({"message": "Category must be a string"}), 400
        if len(category) > 100:
            return jsonify({"message": "Category string too long"}), 400
        content.category = category.strip()

    # Regenerate extracted_text for embedding, and the embedding itself if relevant fields changed
    new_extracted_text = f"{content.title}. {content.notes}"
    if new_extracted_text != old_extracted_text:
        # If URL was provided and changed, re-extract from URL
        if url is not None and url != content.url:
            extracted_full_text = extract_article_text_from_url(url)
            if extracted_full_text:
                text_for_embedding = f"{content.title}. {extracted_full_text}. User Notes: {content.notes}"
            else:
                text_for_embedding = f"{content.title}. User Notes: {content.notes}"
        else:
            text_for_embedding = f"{content.title}. User Notes: {content.notes}"
        content.extracted_text = text_for_embedding
        content.embedding = get_embedding(text_for_embedding)

    try:
        db.session.commit()
        return jsonify({"message": "Content updated successfully", "content_id": content.id}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating content {content_id}: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred during content update"}), 500

@app.route('/api/save_content/<int:content_id>', methods=['DELETE'])
@jwt_required()
def delete_saved_content(content_id):
    user_id = int(get_jwt_identity())
    content = SavedContent.query.get(content_id)
    if not content or content.user_id != user_id:
        return jsonify({"message": "Content not found or unauthorized"}), 404
    try:
        db.session.delete(content)
        db.session.commit()
        return jsonify({"message": "Saved content deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route('/api/technology/<tech_name>/content', methods=['GET'])
@jwt_required()
def get_content_by_technology(tech_name):
    user_id = int(get_jwt_identity())
    if not tech_name or not isinstance(tech_name, str) or not tech_name.strip():
        return jsonify({"message": "Technology name is required and must be a non-empty string"}), 400
    tech_name = tech_name.strip().lower()
    # Find all saved content for the user where tags, category, or title/notes mention the technology
    contents = SavedContent.query.filter(
        SavedContent.user_id == user_id,
        (
            SavedContent.tags.ilike(f"%{tech_name}%") |
            SavedContent.category.ilike(f"%{tech_name}%") |
            SavedContent.title.ilike(f"%{tech_name}%") |
            SavedContent.notes.ilike(f"%{tech_name}%")
        )
    ).order_by(SavedContent.saved_at.desc()).all()
    results = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in contents]
    return jsonify(results), 200

@app.route('/api/search_content', methods=['POST'])
@jwt_required()
def search_saved_content():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400
    keyword = data.get('keyword', '').strip()
    tags = data.get('tags', '').strip()
    category = data.get('category', '').strip()
    notes = data.get('notes', '').strip()
    query = SavedContent.query.filter(SavedContent.user_id == user_id)
    if keyword:
        query = query.filter(
            SavedContent.title.ilike(f"%{keyword}%") |
            SavedContent.url.ilike(f"%{keyword}%") |
            SavedContent.notes.ilike(f"%{keyword}%") |
            SavedContent.tags.ilike(f"%{keyword}%") |
            SavedContent.category.ilike(f"%{keyword}%")
        )
    if tags:
        query = query.filter(SavedContent.tags.ilike(f"%{tags}%"))
    if category:
        query = query.filter(SavedContent.category.ilike(f"%{category}%"))
    if notes:
        query = query.filter(SavedContent.notes.ilike(f"%{notes}%"))
    results = query.order_by(SavedContent.saved_at.desc()).all()
    output = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in results]
    return jsonify(output), 200

@app.route('/api/semantic_search', methods=['POST'])
@jwt_required()
def semantic_search():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or 'query' not in data or not isinstance(data['query'], str) or not data['query'].strip():
        return jsonify({"message": "A non-empty 'query' string is required."}), 400
    query_text = data['query'].strip()
    # Generate embedding for the search query
    query_embedding = get_embedding(query_text)
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        return jsonify({"message": "Failed to generate embedding for the query."}), 500
    # Perform vector similarity search using pgvector's cosine distance operator (<=>)
    results = db.session.query(SavedContent).filter_by(user_id=user_id).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all()
    output = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in results]
    return jsonify(output), 200

@app.route('/api/search', methods=['GET'])
@jwt_required()
def semantic_search_get():
    user_id = int(get_jwt_identity())
    query_text = request.args.get('q', '').strip()
    if not query_text:
        return jsonify({"message": "A non-empty 'q' query parameter is required."}), 400
    query_embedding = get_embedding(query_text)
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        return jsonify({"message": "Failed to generate embedding for the query."}), 500
    results = db.session.query(SavedContent).filter_by(user_id=user_id).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all()
    output = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in results]
    return jsonify(output), 200

@app.route('/api/saved_content', methods=['GET'])
@jwt_required()
def get_user_saved_content():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    pagination = SavedContent.query.filter_by(user_id=user_id).order_by(SavedContent.saved_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    content_data = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in pagination.items]
    return jsonify({
        "saved_content": content_data,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200

@app.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    tech_interests = data.get('technology_interests')
    if tech_interests is not None:
        if not isinstance(tech_interests, str):
            return jsonify({"message": "technology_interests must be a string"}), 400
        if len(tech_interests) > 500:
            return jsonify({"message": "technology_interests too long"}), 400
        user.technology_interests = tech_interests.strip()
    # Add more profile fields here as needed
    try:
        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating profile for user {user_id}: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred during profile update"}), 500

@app.route('/api/tasks', methods=['POST'])
@jwt_required()
def create_task():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    project_id = data.get('project_id')
    title = data.get('title')
    description = data.get('description', '')
    if not project_id or not title or not isinstance(title, str) or not title.strip():
        return jsonify({"message": "project_id and non-empty title are required"}), 400
    project = Project.query.get(project_id)
    if not project or project.user_id != user_id:
        return jsonify({"message": "Project not found or unauthorized"}), 404
    # Generate embedding for the task
    context = f"Task: {title}. {description}. Project: {project.title}. {project.description}. {project.technologies}."
    embedding = get_embedding(context)
    new_task = Task(project_id=project_id, title=title.strip(), description=description.strip(), embedding=embedding)
    try:
        db.session.add(new_task)
        db.session.commit()
        return jsonify({"message": "Task created successfully", "task_id": new_task.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    project = Project.query.get(task.project_id)
    if not project or project.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    title = data.get('title', task.title)
    description = data.get('description', task.description)
    task.title = title.strip()
    task.description = description.strip()
    # Regenerate embedding
    context = f"Task: {task.title}. {task.description}. Project: {project.title}. {project.description}. {project.technologies}."
    task.embedding = get_embedding(context)
    try:
        db.session.commit()
        return jsonify({"message": "Task updated successfully", "task_id": task.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

# --- Centralized HTTP Error Handlers ---
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"message": "Bad Request", "details": str(error)}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"message": "Unauthorized", "details": str(error)}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({"message": "Forbidden", "details": str(error)}), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Not Found", "details": str(error)}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"message": "Method Not Allowed", "details": str(error)}), 405

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error(f"Internal Server Error: {error}", exc_info=True)
    return jsonify({"message": "Internal Server Error", "details": "An unexpected error occurred on the server."}), 500

# --- Flask-JWT-Extended Specific Error Handlers ---
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, JWTDecodeError

@jwt.unauthorized_loader
def unauthorized_response(callback):
    return jsonify({"message": "Missing Authorization Header"}), 401

@jwt.invalid_token_loader
def invalid_token_response(callback):
    return jsonify({"message": "Invalid token signature or format"}), 401

@jwt.expired_token_loader
def expired_token_response(callback):
    return jsonify({"message": "Token has expired"}), 401

@jwt.revoked_token_loader
def revoked_token_response(callback):
    return jsonify({"message": "Token has been revoked"}), 401

@jwt.needs_fresh_token_loader   
def needs_fresh_token_response(callback):
    return jsonify({"message": "Fresh token required"}), 401

# --- Main entry point for running the Flask app ---
if __name__ == '__main__':
    # Call init_db() within the application context when app.py is run directly
    with app.app_context():
        init_db()
    # When running directly, Flask's debug mode is useful.
    # In production, you would use a WSGI server like Gunicorn or uWSGI.
    app.run(debug=True)
