from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent, User
import requests
from readability import Document
from bs4 import BeautifulSoup
import numpy as np

# Import embedding function
try:
    from app_old import get_embedding
except ImportError:
    def get_embedding(text):
        return np.zeros(384)

bookmarks_bp = Blueprint('bookmarks', __name__, url_prefix='/api/bookmarks')

def extract_article_content(url):
    """Extract main content from a URL"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FuzeBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        doc = Document(response.text)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        
        return text[:5000]  # Limit to 5000 chars
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return ""

@bookmarks_bp.route('', methods=['POST'])
@jwt_required()
def save_bookmark():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    url = data.get('url')
    title = data.get('title', '')
    description = data.get('description', '')  # Keep for API compatibility
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    # Ensure title is not empty (required field)
    if not title or not title.strip():
        title = 'Untitled Bookmark'
    
    # Extract content from URL
    extracted_text = extract_article_content(url)
    
    # Generate embedding for semantic search
    content_for_embedding = f"{title} {description} {extracted_text}"
    embedding = get_embedding(content_for_embedding)
    
    new_bm = SavedContent(
        user_id=user_id,
        url=url.strip(),
        title=title.strip(),
        notes=description.strip() if isinstance(description, str) else '',
        extracted_text=extracted_text,
        embedding=embedding
    )
    try:
        db.session.add(new_bm)
        db.session.commit()
        return jsonify({
            'message': 'Bookmark saved', 
            'bookmark_id': new_bm.id,
            'content_extracted': len(extracted_text) > 0
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@bookmarks_bp.route('', methods=['GET'])
@jwt_required()
def list_bookmarks():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    pagination = SavedContent.query.filter_by(user_id=user_id).order_by(SavedContent.saved_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    bookmarks = [{
        'id': b.id,
        'url': b.url,
        'title': b.title,
        'description': b.notes,  # Map 'notes' to 'description' for API consistency
        'saved_at': b.saved_at.isoformat(),
        'has_content': bool(b.extracted_text)
    } for b in pagination.items]
    return jsonify({
        'bookmarks': bookmarks,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    }), 200

@bookmarks_bp.route('/<int:bookmark_id>', methods=['DELETE'])
@jwt_required()
def delete_bookmark(bookmark_id):
    user_id = int(get_jwt_identity())
    bm = SavedContent.query.get(bookmark_id)
    if not bm or bm.user_id != user_id:
        return jsonify({'message': 'Bookmark not found or unauthorized'}), 404
    try:
        db.session.delete(bm)
        db.session.commit()
        return jsonify({'message': 'Bookmark deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500 