from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent, User
import requests
from readability import Document
from bs4 import BeautifulSoup
import numpy as np
from sqlalchemy.exc import IntegrityError

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
        
        # Try to use readability-lxml if available
        try:
            doc = Document(response.text)
            summary_html = doc.summary()
            soup = BeautifulSoup(summary_html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
        except (ImportError, NameError):
            # Fallback to simple extraction if readability is not available
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
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
    category = data.get('category', 'other')
    tags = data.get('tags', [])
    
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    # Check if bookmark already exists
    existing_bookmark = SavedContent.query.filter_by(user_id=user_id, url=url).first()
    if existing_bookmark:
        # Update existing bookmark
        existing_bookmark.title = title.strip() if title else existing_bookmark.title
        existing_bookmark.notes = description.strip() if description else existing_bookmark.notes
        db.session.commit()
        return jsonify({
            'message': 'Bookmark updated',
            'bookmark': {'id': existing_bookmark.id, 'url': existing_bookmark.url},
            'wasDuplicate': True
        }), 200
    
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
            'bookmark': {'id': new_bm.id, 'url': new_bm.url},
            'content_extracted': len(extracted_text) > 0,
            'wasDuplicate': False
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@bookmarks_bp.route('/import', methods=['POST'])
@jwt_required()
def bulk_import_bookmarks():
    """Bulk import bookmarks from Chrome extension"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not isinstance(data, list):
        return jsonify({'message': 'Expected array of bookmarks'}), 400
    
    added_count = 0
    updated_count = 0
    errors = []
    
    for bookmark_data in data:
        try:
            url = bookmark_data.get('url', '').strip()
            title = bookmark_data.get('title', '').strip()
            category = bookmark_data.get('category', 'other')
            
            if not url:
                continue
                
            # Check if bookmark already exists
            existing_bookmark = SavedContent.query.filter_by(user_id=user_id, url=url).first()
            
            if existing_bookmark:
                # Update existing bookmark
                existing_bookmark.title = title if title else existing_bookmark.title
                updated_count += 1
            else:
                # Create new bookmark
                extracted_text = extract_article_content(url)
                content_for_embedding = f"{title} {extracted_text}"
                embedding = get_embedding(content_for_embedding)
                
                new_bm = SavedContent(
                    user_id=user_id,
                    url=url,
                    title=title if title else 'Untitled Bookmark',
                    notes='',
                    extracted_text=extracted_text,
                    embedding=embedding
                )
                db.session.add(new_bm)
                added_count += 1
                
        except Exception as e:
            errors.append(f"Error processing {url}: {str(e)}")
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Bulk import completed',
            'added': added_count,
            'updated': updated_count,
            'errors': errors
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Bulk import failed: {str(e)}'}), 500

@bookmarks_bp.route('', methods=['GET'])
@jwt_required()
def list_bookmarks():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    
    # Build query
    query = SavedContent.query.filter_by(user_id=user_id)
    
    # Add search filter
    if search:
        query = query.filter(
            db.or_(
                SavedContent.title.ilike(f'%{search}%'),
                SavedContent.notes.ilike(f'%{search}%'),
                SavedContent.url.ilike(f'%{search}%')
            )
        )
    
    # Add category filter
    if category and category != 'all':
        query = query.filter(SavedContent.category == category)
    
    # Order by saved date and paginate
    pagination = query.order_by(SavedContent.saved_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    bookmarks = [{
        'id': b.id,
        'url': b.url,
        'title': b.title,
        'description': b.notes,  # Map 'notes' to 'description' for API consistency
        'saved_at': b.saved_at.isoformat(),
        'category': b.category,
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

@bookmarks_bp.route('/url/<path:url>', methods=['DELETE'])
@jwt_required()
def delete_bookmark_by_url(url):
    """Delete bookmark by URL (for Chrome extension compatibility)"""
    user_id = int(get_jwt_identity())
    from urllib.parse import unquote
    decoded_url = unquote(url)
    
    bm = SavedContent.query.filter_by(user_id=user_id, url=decoded_url).first()
    if not bm:
        return jsonify({'message': 'Bookmark not found'}), 404
    try:
        db.session.delete(bm)
        db.session.commit()
        return jsonify({'message': 'Bookmark deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@bookmarks_bp.route('/extract-url', methods=['POST'])
@jwt_required()
def extract_url_content():
    """Extract content from a URL for preview purposes"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    try:
        # Extract content from URL
        extracted_text = extract_article_content(url)
        
        # Try to get title from the page
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; FuzeBot/1.0)"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find('title')
            page_title = title.get_text().strip() if title else 'Untitled'
        except Exception as e:
            print(f"Error getting title: {e}")
            page_title = 'Untitled'
        
        return jsonify({
            'title': page_title,
            'description': extracted_text[:1000],  # Limit preview content
            'url': url,
            'success': True
        }), 200
        
    except Exception as e:
        print(f"Error in extract_url_content: {e}")
        return jsonify({
            'title': 'Untitled',
            'description': '',
            'url': url,
            'success': False,
            'message': f'Error extracting content: {str(e)}'
        }), 200  # Return 200 instead of 500 to avoid breaking the frontend 