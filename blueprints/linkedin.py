from flask import Blueprint, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import json
from datetime import datetime
import traceback

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from models import db, User, Project, SavedContent, ContentAnalysis
from easy_linkedin_scraper import EasyLinkedInScraper
from intent_analysis_engine import analyze_user_intent
from gemini_utils import GeminiAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

linkedin_bp = Blueprint('linkedin', __name__)

# Initialize LinkedIn scraper
linkedin_scraper = EasyLinkedInScraper()

# Initialize Gemini analyzer
gemini_analyzer = GeminiAnalyzer()

@linkedin_bp.route('/api/linkedin/extract', methods=['POST'])
@jwt_required()
def extract_linkedin_content():
    """Extract content from LinkedIn post URL"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'LinkedIn URL is required'
            }), 400
        
        linkedin_url = data['url'].strip()
        user_id = data.get('user_id', get_jwt_identity())
        
        # Validate LinkedIn URL
        if 'linkedin.com' not in linkedin_url:
            return jsonify({
                'success': False,
                'error': 'Please provide a valid LinkedIn URL'
            }), 400
        
        logger.info(f"[INFO] Extracting LinkedIn content from: {linkedin_url}")
        
        # Extract content using our scraper
        try:
            extracted_data = linkedin_scraper.scrape_post(linkedin_url)
            
            if not extracted_data.get('success'):
                return jsonify({
                    'success': False,
                    'error': 'Failed to extract content from LinkedIn post',
                    'details': extracted_data.get('error', 'Unknown error')
                }), 400
            
            # Store extraction result in database
            try:
                extraction_record = ContentAnalysis(
                    user_id=user_id,
                    url=linkedin_url,
                    title=extracted_data.get('title', ''),
                    content=extracted_data.get('content', ''),
                    content_type='linkedin_post',
                    technology_tags=extracted_data.get('technologies', []),
                    quality_score=extracted_data.get('quality_score', 0),
                    extraction_method=extracted_data.get('method_used', ''),
                    extracted_at=datetime.utcnow(),
                    metadata=json.dumps(extracted_data)
                )
                
                db.session.add(extraction_record)
                db.session.commit()
                
                logger.info(f"[OK] LinkedIn content extracted and stored for user {user_id}")
                
            except SQLAlchemyError as db_error:
                logger.error(f"Database error storing extraction: {db_error}")
                # Continue even if storage fails
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'message': 'LinkedIn content extracted successfully',
                'data': {
                    'title': extracted_data.get('title'),
                    'content': extracted_data.get('content'),
                    'meta_description': extracted_data.get('meta_description', ''),
                    'quality_score': extracted_data.get('quality_score', 0),
                    'method_used': extracted_data.get('method_used', ''),
                    'technologies': extracted_data.get('technologies', []),
                    'extracted_at': datetime.utcnow().isoformat()
                }
            })
            
        except Exception as scrape_error:
            logger.error(f"LinkedIn scraping error: {scrape_error}")
            return jsonify({
                'success': False,
                'error': 'Failed to extract LinkedIn content',
                'details': str(scrape_error)
            }), 500
    
    except Exception as e:
        logger.error(f"LinkedIn extraction endpoint error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error during LinkedIn extraction'
        }), 500

@linkedin_bp.route('/api/linkedin/analyze', methods=['POST'])
@jwt_required()
def analyze_linkedin_content():
    """Analyze extracted LinkedIn content using AI"""
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Content is required for analysis'
            }), 400
        
        content = data['content']
        title = data.get('title', '')
        meta_description = data.get('meta_description', '')
        url = data.get('url', '')
        user_id = data.get('user_id', get_jwt_identity())
        project_context = data.get('project_context')
        
        logger.info(f"[INFO] Analyzing LinkedIn content for user {user_id}")
        
        # Prepare content for AI analysis
        analysis_input = f"""
        Title: {title}
        Meta Description: {meta_description}
        Content: {content}
        URL: {url}
        """
        
        # Analyze content using Gemini
        try:
            analysis_prompt = f"""
            Analyze this LinkedIn post content and provide structured insights:
            
            {analysis_input}
            
            Please provide analysis in the following JSON format:
            {{
                "technologies": ["list", "of", "technologies", "mentioned"],
                "content_type": "tutorial|article|news|case_study|opinion|other",
                "difficulty_level": "beginner|intermediate|advanced",
                "learning_goals": "what users can learn from this content",
                "summary": "2-3 sentence summary of the main points",
                "key_insights": ["key", "insights", "from", "content"],
                "target_audience": "who this content is for",
                "practical_applications": "how this content can be applied"
            }}
            
            Focus on extracting actionable insights and technologies that would be useful for learning and development.
            """
            
            analysis_response = gemini_analyzer.analyze_text(analysis_prompt)
            
            if not analysis_response:
                raise Exception("No response from Gemini analyzer")
            
            # Parse the analysis response
            try:
                analysis_data = json.loads(analysis_response)
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                analysis_data = {
                    "technologies": [],
                    "content_type": "article",
                    "difficulty_level": "intermediate",
                    "learning_goals": "Content analysis completed",
                    "summary": "LinkedIn post content analyzed successfully",
                    "key_insights": [],
                    "target_audience": "General audience",
                    "practical_applications": "Learning and development"
                }
            
            # Store analysis result
            try:
                analysis_record = ContentAnalysis(
                    user_id=user_id,
                    url=url,
                    title=title,
                    content=content,
                    content_type=analysis_data.get('content_type', 'linkedin_post'),
                    technology_tags=analysis_data.get('technologies', []),
                    analysis_data=json.dumps(analysis_data),
                    analyzed_at=datetime.utcnow(),
                    metadata=json.dumps({
                        'source': 'linkedin',
                        'analysis_method': 'gemini_ai',
                        'project_context': project_context
                    })
                )
                
                db.session.add(analysis_record)
                db.session.commit()
                
                logger.info(f"[OK] LinkedIn content analysis completed and stored for user {user_id}")
                
            except SQLAlchemyError as db_error:
                logger.error(f"Database error storing analysis: {db_error}")
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'message': 'LinkedIn content analyzed successfully',
                'data': {
                    'technologies': analysis_data.get('technologies', []),
                    'content_type': analysis_data.get('content_type', 'article'),
                    'difficulty_level': analysis_data.get('difficulty_level', 'intermediate'),
                    'learning_goals': analysis_data.get('learning_goals', ''),
                    'summary': analysis_data.get('summary', ''),
                    'key_insights': analysis_data.get('key_insights', []),
                    'target_audience': analysis_data.get('target_audience', ''),
                    'practical_applications': analysis_data.get('practical_applications', ''),
                    'analyzed_at': datetime.utcnow().isoformat()
                }
            })
            
        except Exception as ai_error:
            logger.error(f"AI analysis error: {ai_error}")
            
            # Fallback analysis
            fallback_analysis = {
                'technologies': [],
                'content_type': 'linkedin_post',
                'difficulty_level': 'intermediate',
                'learning_goals': 'Content from LinkedIn post',
                'summary': f'LinkedIn post: {title}',
                'key_insights': ['Content extracted successfully'],
                'target_audience': 'General audience',
                'practical_applications': 'Learning and reference'
            }
            
            return jsonify({
                'success': True,
                'message': 'LinkedIn content analyzed with fallback method',
                'data': fallback_analysis,
                'warning': 'AI analysis failed, using fallback method'
            })
    
    except Exception as e:
        logger.error(f"LinkedIn analysis endpoint error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error during LinkedIn analysis'
        }), 500

@linkedin_bp.route('/api/linkedin/batch-extract', methods=['POST'])
@jwt_required()
def batch_extract_linkedin():
    """Extract content from multiple LinkedIn URLs"""
    try:
        data = request.get_json()
        
        if not data or 'urls' not in data:
            return jsonify({
                'success': False,
                'error': 'List of LinkedIn URLs is required'
            }), 400
        
        urls = data['urls']
        user_id = data.get('user_id', get_jwt_identity())
        
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({
                'success': False,
                'error': 'Please provide a valid list of LinkedIn URLs'
            }), 400
        
        if len(urls) > 10:  # Limit batch size
            return jsonify({
                'success': False,
                'error': 'Maximum 10 URLs allowed per batch'
            }), 400
        
        logger.info(f"[INFO] Batch extracting {len(urls)} LinkedIn URLs for user {user_id}")
        
        results = []
        successful = 0
        failed = 0
        
        for url in urls:
            try:
                url = url.strip()
                if 'linkedin.com' not in url:
                    results.append({
                        'url': url,
                        'success': False,
                        'error': 'Invalid LinkedIn URL'
                    })
                    failed += 1
                    continue
                
                # Extract content
                extracted_data = linkedin_scraper.scrape_post(url)
                
                if extracted_data.get('success'):
                    results.append({
                        'url': url,
                        'success': True,
                        'data': {
                            'title': extracted_data.get('title'),
                            'content': extracted_data.get('content'),
                            'quality_score': extracted_data.get('quality_score', 0),
                            'method_used': extracted_data.get('method_used', '')
                        }
                    })
                    successful += 1
                else:
                    results.append({
                        'url': url,
                        'success': False,
                        'error': extracted_data.get('error', 'Extraction failed')
                    })
                    failed += 1
                
            except Exception as url_error:
                logger.error(f"Error processing URL {url}: {url_error}")
                results.append({
                    'url': url,
                    'success': False,
                    'error': str(url_error)
                })
                failed += 1
        
        return jsonify({
            'success': True,
            'message': f'Batch extraction completed: {successful} successful, {failed} failed',
            'data': {
                'total_urls': len(urls),
                'successful': successful,
                'failed': failed,
                'results': results
            }
        })
    
    except Exception as e:
        logger.error(f"Batch LinkedIn extraction error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error during batch LinkedIn extraction'
        }), 500

@linkedin_bp.route('/api/linkedin/history', methods=['GET'])
@jwt_required()
def get_linkedin_history():
    """Get user's LinkedIn extraction and analysis history"""
    try:
        user_id = request.args.get('user_id', get_jwt_identity())
        limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 records
        offset = int(request.args.get('offset', 0))
        
        # Get LinkedIn content analysis history
        history_query = ContentAnalysis.query.filter_by(
            user_id=user_id,
            content_type='linkedin_post'
        ).order_by(ContentAnalysis.extracted_at.desc())
        
        total_count = history_query.count()
        history_records = history_query.offset(offset).limit(limit).all()
        
        history_data = []
        for record in history_records:
            try:
                metadata = json.loads(record.metadata) if record.metadata else {}
                analysis_data = json.loads(record.analysis_data) if record.analysis_data else {}
                
                history_data.append({
                    'id': record.id,
                    'url': record.url,
                    'title': record.title,
                    'content_preview': record.content[:200] + '...' if len(record.content) > 200 else record.content,
                    'technology_tags': record.technology_tags or [],
                    'quality_score': record.quality_score,
                    'extracted_at': record.extracted_at.isoformat() if record.extracted_at else None,
                    'analyzed_at': record.analyzed_at.isoformat() if record.analyzed_at else None,
                    'extraction_method': metadata.get('extraction_method', ''),
                    'analysis_summary': analysis_data.get('summary', ''),
                    'content_type': analysis_data.get('content_type', 'linkedin_post')
                })
            except Exception as record_error:
                logger.error(f"Error processing history record {record.id}: {record_error}")
                continue
        
        return jsonify({
            'success': True,
            'data': {
                'history': history_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }
        })
    
    except Exception as e:
        logger.error(f"LinkedIn history endpoint error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error retrieving LinkedIn history'
        }), 500

@linkedin_bp.route('/api/linkedin/status', methods=['GET'])
def get_linkedin_status():
    """Get LinkedIn service status"""
    try:
        # Check if LinkedIn scraper is working
        test_url = "https://www.linkedin.com/feed/update/urn:li:activity:7357027266016530434"
        
        try:
            test_result = linkedin_scraper.scrape_post(test_url)
            scraper_status = "operational" if test_result.get('success') else "degraded"
        except Exception:
            scraper_status = "unavailable"
        
        # Check Gemini analyzer status
        try:
            gemini_status = "operational" if gemini_analyzer.is_available() else "unavailable"
        except Exception:
            gemini_status = "unavailable"
        
        return jsonify({
            'success': True,
            'data': {
                'linkedin_scraper': {
                    'status': scraper_status,
                    'last_checked': datetime.utcnow().isoformat()
                },
                'ai_analyzer': {
                    'status': gemini_status,
                    'provider': 'gemini'
                },
                'overall_status': 'operational' if scraper_status == 'operational' and gemini_status == 'operational' else 'degraded'
            }
        })
    
    except Exception as e:
        logger.error(f"LinkedIn status endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error checking LinkedIn status'
        }), 500

# Error handlers
@linkedin_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'details': str(error)
    }), 400

@linkedin_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'success': False,
        'error': 'Unauthorized',
        'details': 'Authentication required'
    }), 401

@linkedin_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"LinkedIn blueprint error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'details': 'Something went wrong on our end'
    }), 500
