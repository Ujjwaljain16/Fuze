import os
print("DATABASE_URL:", os.environ.get("DATABASE_URL"))
from flask import Flask
from flask_jwt_extended import JWTManager
from datetime import timedelta
from dotenv import load_dotenv
from models import db
from sqlalchemy import text
from flask_cors import CORS
# Remove embedding_model and get_embedding from here
# If needed, import from embedding_utils
import numpy as np

# Import blueprints
from blueprints.auth import auth_bp
from blueprints.projects import projects_bp
from blueprints.tasks import tasks_bp
from blueprints.bookmarks import bookmarks_bp
from blueprints.recommendations import recommendations_bp
from blueprints.feedback import feedback_bp
from blueprints.profile import profile_bp
from blueprints.search import search_bp

# Load environment variables
load_dotenv()
print("DATABASE_URL:", os.environ.get("DATABASE_URL"))

# Global embedding model
# embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# def get_embedding(text):
#     if not text:
#         return np.zeros(384)
#     return embedding_model.encode([text])[0]

def create_app():
    """Application factory pattern for better testing and modularity"""
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.Config')
    app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this in production
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=14)
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
    app.config['JWT_COOKIE_SECURE'] = True  # Set to True in production (HTTPS)
    app.config['JWT_COOKIE_SAMESITE'] = 'Strict'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Set to True and handle CSRF in production
    
    # Enable CORS for all origins (development only)
    CORS(app)
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)
    
    # Basic route
    @app.route('/')
    def index():
        return {'message': 'Fuze API running', 'version': '1.0.0'}
    
    # Health check endpoint for Chrome extension
    @app.route('/api/health')
    def health_check():
        try:
            # Test database connection using proper SQLAlchemy syntax
            db.session.execute(text('SELECT 1'))
            return {
                'status': 'healthy',
                'message': 'Fuze API is running',
                'version': '1.0.0',
                'database': 'connected'
            }, 200
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': 'Database connection failed',
                'error': str(e)
            }, 500
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return {'message': 'Bad request'}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'message': 'Unauthorized'}, 401
    
    @app.errorhandler(404)
    def not_found(error):
        return {'message': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return {'message': 'Internal server error'}, 500
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 