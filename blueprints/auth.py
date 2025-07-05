from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username') or data.get('email')  # Support both username and email
    password = data.get('password')
    name = data.get('name', '')  # Optional name field
    
    if not username or not password:
        return jsonify({'message': 'Username/email and password required'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 409
    
    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username') or data.get('email')  # Support both username and email
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username/email and password required'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': access_token}), 200 