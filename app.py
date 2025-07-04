import os
from flask import Flask
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from models import db

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

def create_app():
    """Application factory pattern for better testing and modularity"""
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.Config')
    
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