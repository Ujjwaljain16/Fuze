from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent
import numpy as np
import os
from utils.embedding_utils import get_embedding
import logging

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")

# Only create Supabase client if credentials are provided
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase connected successfully")
    except Exception as e:
        logger.warning(f"Supabase connection failed: {e}")
        supabase_client = None
else:
    logger.warning("Supabase credentials not provided - Supabase features disabled")

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
    
    # Check if Supabase is configured and available
    if not supabase_client:
        # Fallback to local semantic search
        return fallback_semantic_search(user_id, query, limit)
    
    try:
        # Generate query embedding
        query_embedding = get_embedding(query)
        if hasattr(query_embedding, 'tolist'):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = list(query_embedding)
        
        logger.debug(f"Query embedding dimensions: {len(query_embedding_list)}")
        
        # Get all bookmarks for the user with embeddings
        response = supabase_client.table(SUPABASE_TABLE).select(
            'id, user_id, url, title, notes, extracted_text, embedding'
        ).eq('user_id', user_id).not_.is_("embedding", "null").execute()
        
        bookmarks = response.data
        logger.debug(f"Found {len(bookmarks)} bookmarks with embeddings")
        
        if not bookmarks:
            return jsonify({
                'query': query,
                'results': [],
                'total': 0,
                'source': 'supabase',
                'message': 'No bookmarks with embeddings found'
            }), 200
        
        # Calculate similarities using our working approach
        similarities = []
        
        for bookmark in bookmarks:
            try:
                embedding_str = bookmark.get('embedding')
                if not embedding_str:
                    continue
                
                # Parse the embedding string (JSON format)
                import json
                bookmark_embedding = json.loads(embedding_str) if isinstance(embedding_str, str) else embedding_str
                
                if not bookmark_embedding or len(bookmark_embedding) != len(query_embedding_list):
                    continue
                
                # Calculate cosine similarity
                vec1 = np.array(query_embedding_list)
                vec2 = np.array(bookmark_embedding)
                
                dot_product = np.dot(vec1, vec2)
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                
                if norm1 == 0 or norm2 == 0:
                    similarity = 0
                else:
                    similarity = dot_product / (norm1 * norm2)
                
                # Convert similarity to percentage (0-100)
                similarity_percentage = max(0, min(100, (similarity + 1) * 50))  # Convert from [-1,1] to [0,100]
                
                similarities.append({
                    'id': bookmark['id'],
                    'user_id': bookmark['user_id'],
                    'url': bookmark['url'],
                    'title': bookmark['title'],
                    'notes': bookmark.get('notes', ''),
                    'content_snippet': bookmark.get('extracted_text', '')[:200] + '...' if bookmark.get('extracted_text') and len(bookmark.get('extracted_text', '')) > 200 else bookmark.get('extracted_text', ''),
                    'similarity': similarity,
                    'similarity_percentage': similarity_percentage,
                    'relevance_score': similarity_percentage,
                    'search_type': 'AI Vector Similarity'
                })
                
            except Exception as e:
                logger.warning(f"Error processing bookmark {bookmark.get('id')}: {str(e)}")
                continue
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Take top results
        top_results = similarities[:limit]
        
        # Format results for frontend
        results = []
        for item in top_results:
            results.append({
                'id': item['id'],
                'user_id': item['user_id'],
                'url': item['url'],
                'title': item['title'],
                'content_snippet': item['content_snippet'],
                'similarity': item['similarity'],
                'similarity_percentage': item['similarity_percentage'],
                'relevance_score': item['relevance_score'],
                'search_type': item['search_type']
            })
        
        logger.info(f"Vector search completed with {len(results)} results")
        return jsonify({
            'query': query,
            'results': results,
            'total': len(results),
            'source': 'supabase',
            'message': 'AI-powered semantic search completed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Supabase semantic search failed: {str(e)}")
        # Fallback to local semantic search
        return fallback_semantic_search(user_id, query, limit)

def fallback_semantic_search(user_id, query, limit):
    """Fallback semantic search using local database"""
    try:
        # Get all user's bookmarks
        bookmarks = db.session.query(SavedContent).filter_by(user_id=user_id).limit(limit * 2).all()
        
        if not bookmarks:
            return jsonify({
                'query': query,
                'results': [],
                'total': 0,
                'source': 'fallback',
                'message': 'No bookmarks found'
            }), 200
        
        # Simple text similarity ranking
        def calculate_similarity(bookmark):
            text = f"{bookmark.title or ''} {bookmark.notes or ''} {bookmark.extracted_text or ''}"
            text = text.lower()
            query_lower = query.lower()
            
            # Calculate word overlap
            query_words = set(query_lower.split())
            text_words = set(text.split())
            word_overlap = len(query_words.intersection(text_words))
            
            # Calculate substring matches
            substring_score = 0
            for word in query_words:
                if word in text:
                    substring_score += 1
            
            # Calculate exact phrase matches
            phrase_score = 0
            if query_lower in text:
                phrase_score = 10
            
            # Weighted scoring
            total_score = (word_overlap * 2) + substring_score + phrase_score
            
            return total_score
        
        # Score and sort bookmarks
        scored_bookmarks = [(bookmark, calculate_similarity(bookmark)) for bookmark in bookmarks]
        scored_bookmarks.sort(key=lambda x: x[1], reverse=True)
        
        # Take top results
        top_bookmarks = scored_bookmarks[:limit]
        
        results = []
        for bookmark, score in top_bookmarks:
            if score > 0:  # Only include relevant results
                results.append({
                    'id': bookmark.id,
                    'user_id': bookmark.user_id,
                    'url': bookmark.url,
                    'title': bookmark.title,
                    'content_snippet': bookmark.extracted_text[:200] + '...' if bookmark.extracted_text and len(bookmark.extracted_text) > 200 else bookmark.extracted_text,
                    'distance': 1.0 - (score / 20.0),  # Convert score to distance (0-1)
                    'relevance_score': score
                })
        
        return jsonify({
            'query': query,
            'results': results,
            'total': len(results),
            'source': 'fallback',
            'message': 'Using fallback search (Supabase unavailable)'
        }), 200
        
    except Exception as e:
        logger.error(f"Fallback semantic search error: {str(e)}")
        return jsonify({
            'query': query,
            'results': [],
            'total': 0,
            'source': 'error',
            'message': 'Search service temporarily unavailable'
        }), 503 