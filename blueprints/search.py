from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent
import numpy as np
import os
from supabase import create_client
import os
from embedding_utils import get_embedding

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xyzcompany.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "your-supabase-service-role-key")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")  # Use saved_content table
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if we're using PostgreSQL (for pgvector support)
def is_postgresql():
    database_url = os.environ.get('DATABASE_URL', '')
    return 'postgresql' in database_url or 'postgres' in database_url

# Check if vector is available
VECTOR_AVAILABLE = is_postgresql()

search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route('/semantic', methods=['POST'])
@jwt_required()
def semantic_search():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    query = data.get('query', '').strip()
    limit = data.get('limit', 10)
    
    if not query:
        return jsonify({'message': 'Query is required'}), 400
    
    # Generate embedding for search query
    query_embedding = get_embedding(query)
    
    if VECTOR_AVAILABLE:
        # PostgreSQL with pgvector - semantic search
        results = db.session.query(SavedContent).filter_by(user_id=user_id).order_by(
            SavedContent.embedding.op('<=>')(query_embedding)
        ).limit(limit).all()
    else:
        # SQLite fallback - text search
        results = db.session.query(SavedContent).filter_by(user_id=user_id).limit(limit).all()
        
        # Simple text similarity ranking
        def text_similarity(content):
            text = f"{content.title} {content.notes or ''} {content.extracted_text or ''}"
            query_words = set(query.lower().split())
            content_words = set(text.lower().split())
            return len(query_words.intersection(content_words))
        
        results.sort(key=text_similarity, reverse=True)
    
    search_results = [{
        'id': content.id,
        'title': content.title,
        'url': content.url,
        'description': content.notes,
        'saved_at': content.saved_at.isoformat(),
        'has_content': bool(content.extracted_text)
    } for content in results]
    
    return jsonify({
        'query': query,
        'results': search_results,
        'total': len(search_results)
    }), 200

@search_bp.route('/text', methods=['GET'])
@jwt_required()
def text_search():
    user_id = int(get_jwt_identity())
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({'message': 'Query parameter "q" is required'}), 400
    
    # Simple text search across title, notes, and extracted text
    results = db.session.query(SavedContent).filter_by(user_id=user_id).filter(
        db.or_(
            SavedContent.title.ilike(f'%{query}%'),
            SavedContent.notes.ilike(f'%{query}%'),
            SavedContent.extracted_text.ilike(f'%{query}%')
        )
    ).limit(limit).all()
    
    search_results = [{
        'id': content.id,
        'title': content.title,
        'url': content.url,
        'description': content.notes,
        'saved_at': content.saved_at.isoformat(),
        'has_content': bool(content.extracted_text)
    } for content in results]
    
    return jsonify({
        'query': query,
        'results': search_results,
        'total': len(search_results)
    }), 200 

@search_bp.route('/supabase-semantic', methods=['POST'])
@jwt_required()
def supabase_semantic_search():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    query = data.get('query', '').strip()
    limit = data.get('limit', 10)
    if not query:
        return jsonify({'message': 'Query is required'}), 400
    query_emb = get_embedding(query)
    query_emb_list = query_emb.tolist() if hasattr(query_emb, 'tolist') else list(query_emb)
    # Updated SQL for saved_content table
    sql = f"""
        SELECT id, user_id, url, title, extracted_text as content_snippet, 
               embedding <=> ARRAY{query_emb_list} AS distance
        FROM {SUPABASE_TABLE}
        WHERE user_id = {user_id}
        ORDER BY distance ASC
        LIMIT {limit};
    """
    resp = supabase_client.rpc('execute_sql', {"sql": sql}).execute()
    if resp.status_code == 200:
        results = resp.data
        return jsonify({
            'query': query,
            'results': results,
            'total': len(results)
        }), 200
    else:
        return jsonify({'message': f'Semantic search failed: {resp.status_code} {resp.data}'}), 500 