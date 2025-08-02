import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Gemini AI-powered content analyzer for enhanced recommendation system
    """
    
    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        
        # Try different model names for compatibility
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("Successfully initialized Gemini with gemini-2.0-flash model")
        except Exception as e1:
            try:
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                logger.info("Successfully initialized Gemini with gemini-1.5-pro model")
            except Exception as e2:
                try:
                    self.model = genai.GenerativeModel('gemini-pro')
                    logger.info("Successfully initialized Gemini with gemini-pro model")
                except Exception as e3:
                    logger.error(f"Failed to initialize Gemini with all model names: {e1}, {e2}, {e3}")
                    raise ValueError(f"Failed to initialize Gemini AI: {e3}")
        
        # Configure generation parameters
        self.generation_config = {
            'temperature': 0.3,  # Lower temperature for more consistent results
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 2048,
        }
    
    def analyze_bookmark_content(self, title: str, description: str, content: str, url: str = "") -> Dict:
        """
        Analyze bookmark content using Gemini AI
        """
        try:
            # Prepare content for analysis (limit to avoid token limits)
            content_preview = content[:2000] if content else ""
            
            prompt = f"""
            Analyze this technical bookmark content and provide structured insights.
            
            Title: {title}
            Description: {description}
            URL: {url}
            Content Preview: {content_preview}
            
            Provide a JSON response with the following structure:
            {{
                "technologies": ["list", "of", "detected", "technologies"],
                "content_type": "tutorial|documentation|example|article|video|course|guide|reference",
                "difficulty": "beginner|intermediate|advanced",
                "intent": "learning|implementation|troubleshooting|optimization|reference|concept_explanation",
                "key_concepts": ["concept1", "concept2", "concept3"],
                "relevance_score": 85,
                "summary": "Brief summary of the content",
                "learning_objectives": ["objective1", "objective2"],
                "quality_indicators": {{
                    "completeness": 85,
                    "clarity": 90,
                    "practical_value": 80
                }},
                "target_audience": "beginner|intermediate|advanced|expert",
                "prerequisites": ["prerequisite1", "prerequisite2"]
            }}
            
            Important guidelines:
            - Be precise with technology detection (e.g., distinguish Java from JavaScript)
            - Assess content quality based on completeness, clarity, and practical value
            - Identify the target audience and learning objectives
            - Provide accurate difficulty assessment
            - Extract key concepts that would be valuable for learning
            - If content type is unclear, default to "article" or "guide"
            - If difficulty is unclear, default to "intermediate"
            - If target audience is unclear, default to "intermediate"
            - Always provide specific values, avoid "unknown" or "none"
            - For general content, classify as "article" or "guide"
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON response
            try:
                result = json.loads(response.text)
                logger.info(f"Successfully analyzed bookmark: {title}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response for {title}: {e}")
                return self._get_fallback_analysis(title, description, content)
                
        except Exception as e:
            logger.error(f"Gemini analysis failed for {title}: {e}")
            return self._get_fallback_analysis(title, description, content)
    
    def analyze_user_context(self, title: str, description: str, technologies: str, user_interests: str = "") -> Dict:
        """
        Analyze user context (project/task) using Gemini AI
        """
        try:
            prompt = f"""
            Analyze this user context and provide structured insights for recommendation matching.
            
            Title: {title}
            Description: {description}
            Technologies: {technologies}
            User Interests: {user_interests}
            
            Provide a JSON response with the following structure:
            {{
                "technologies": ["list", "of", "detected", "technologies"],
                "project_type": "web_app|mobile_app|desktop_app|api|library|tool|research|learning|general",
                "complexity_level": "simple|moderate|complex|advanced",
                "development_stage": "planning|development|testing|deployment|maintenance|learning",
                "learning_needs": ["need1", "need2", "need3"],
                "technical_requirements": ["req1", "req2"],
                "preferred_content_types": ["tutorial", "documentation", "example", "article", "guide"],
                "difficulty_preference": "beginner|intermediate|advanced",
                "focus_areas": ["area1", "area2"],
                "project_summary": "Brief summary of the project goals and scope"
            }}
            
            Guidelines:
            - Identify the type of project and its complexity
            - Determine what the user needs to learn or implement
            - Assess the development stage and technical requirements
            - Identify preferred content types and difficulty levels
            - For general learning requests, use "learning" as project_type and development_stage
            - If project type is unclear, default to "general" or "learning"
            - If complexity is unclear, default to "moderate"
            - Always provide specific values, avoid "unknown" or "none"
            - For general recommendations, focus on the user's technology interests
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            try:
                result = json.loads(response.text)
                logger.info(f"Successfully analyzed user context: {title}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response for context {title}: {e}")
                return self._get_fallback_context_analysis(title, description, technologies)
                
        except Exception as e:
            logger.error(f"Gemini context analysis failed for {title}: {e}")
            return self._get_fallback_context_analysis(title, description, technologies)
    
    def generate_recommendation_reasoning(self, bookmark: Dict, user_context: Dict) -> str:
        """
        Generate intelligent reasoning for why a bookmark is recommended
        """
        try:
            prompt = f"""
            Generate a clear, concise reason for why this bookmark is recommended for the user.
            
            Bookmark:
            - Title: {bookmark.get('title', '')}
            - Technologies: {bookmark.get('technologies', [])}
            - Content Type: {bookmark.get('content_type', '')}
            - Difficulty: {bookmark.get('difficulty', '')}
            - Key Concepts: {bookmark.get('key_concepts', [])}
            
            User Context:
            - Project: {user_context.get('title', '')}
            - Technologies: {user_context.get('technologies', [])}
            - Project Type: {user_context.get('project_type', '')}
            - Learning Needs: {user_context.get('learning_needs', [])}
            
            Provide a brief, human-readable reason (1-2 sentences) explaining why this bookmark is relevant.
            Focus on the most compelling match between the bookmark and user's needs.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate reasoning: {e}")
            return "Recommended based on content analysis"
    
    def rank_recommendations(self, recommendations: List[Dict], user_context: Dict) -> List[Dict]:
        """
        Use Gemini to intelligently rank and reorder recommendations
        """
        try:
            # Prepare recommendations for ranking
            recs_data = []
            for i, rec in enumerate(recommendations[:10]):  # Limit to top 10 for ranking
                recs_data.append({
                    'index': i,
                    'title': rec.get('title', ''),
                    'technologies': rec.get('technologies', []),
                    'content_type': rec.get('content_type', ''),
                    'difficulty': rec.get('difficulty', ''),
                    'relevance_score': rec.get('relevance_score', 0),
                    'key_concepts': rec.get('key_concepts', [])
                })
            
            prompt = f"""
            Rank these recommendations in order of relevance for the user's project.
            
            User Context:
            - Project: {user_context.get('title', '')}
            - Technologies: {user_context.get('technologies', [])}
            - Project Type: {user_context.get('project_type', '')}
            - Learning Needs: {user_context.get('learning_needs', [])}
            
            Recommendations:
            {json.dumps(recs_data, indent=2)}
            
            Return a JSON array with the indices in order of relevance (most relevant first):
            [0, 3, 1, 2, ...]
            
            Consider:
            - Technology match
            - Content type relevance
            - Difficulty alignment
            - Learning progression
            - Practical applicability
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            try:
                ranked_indices = json.loads(response.text)
                # Reorder recommendations based on Gemini ranking
                ranked_recommendations = [recommendations[i] for i in ranked_indices if i < len(recommendations)]
                logger.info("Successfully ranked recommendations using Gemini")
                return ranked_recommendations
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse ranking response: {e}")
                return recommendations
                
        except Exception as e:
            logger.error(f"Gemini ranking failed: {e}")
            return recommendations
    
    def _get_fallback_analysis(self, title: str, description: str, content: str) -> Dict:
        """Fallback analysis when Gemini fails"""
        # Try to extract basic information from title and description
        text = f"{title} {description}".lower()
        
        # Basic technology detection
        technologies = []
        if any(tech in text for tech in ['java', 'jvm', 'spring']):
            technologies.append('java')
        if any(tech in text for tech in ['javascript', 'js', 'react', 'node']):
            technologies.append('javascript')
        if any(tech in text for tech in ['python', 'django', 'flask']):
            technologies.append('python')
        if any(tech in text for tech in ['dsa', 'algorithm', 'data structure']):
            technologies.append('dsa')
        if any(tech in text for tech in ['instrumentation', 'bytecode', 'asm']):
            technologies.append('instrumentation')
        
        # Determine content type from title/description
        content_type = "article"
        if any(word in text for word in ['tutorial', 'guide', 'how to']):
            content_type = "tutorial"
        elif any(word in text for word in ['documentation', 'docs', 'api']):
            content_type = "documentation"
        elif any(word in text for word in ['example', 'sample', 'demo']):
            content_type = "example"
        
        return {
            "technologies": technologies,
            "content_type": content_type,
            "difficulty": "intermediate",
            "intent": "learning",
            "key_concepts": [],
            "relevance_score": 60,
            "summary": f"Content about {', '.join(technologies) if technologies else 'general topics'}",
            "learning_objectives": [],
            "quality_indicators": {
                "completeness": 60,
                "clarity": 60,
                "practical_value": 60
            },
            "target_audience": "intermediate",
            "prerequisites": []
        }
    
    def _get_fallback_context_analysis(self, title: str, description: str, technologies: str) -> Dict:
        """Fallback context analysis when Gemini fails"""
        # Try to extract basic information from title, description, and technologies
        text = f"{title} {description} {technologies}".lower()
        
        # Basic technology detection
        detected_techs = []
        if any(tech in text for tech in ['java', 'jvm', 'spring']):
            detected_techs.append('java')
        if any(tech in text for tech in ['javascript', 'js', 'react', 'node']):
            detected_techs.append('javascript')
        if any(tech in text for tech in ['python', 'django', 'flask']):
            detected_techs.append('python')
        if any(tech in text for tech in ['dsa', 'algorithm', 'data structure']):
            detected_techs.append('dsa')
        if any(tech in text for tech in ['instrumentation', 'bytecode', 'asm']):
            detected_techs.append('instrumentation')
        
        # Determine project type
        project_type = "general"
        if any(word in text for word in ['web', 'frontend', 'backend', 'api']):
            project_type = "web_app"
        elif any(word in text for word in ['mobile', 'app', 'ios', 'android']):
            project_type = "mobile_app"
        elif any(word in text for word in ['learning', 'study', 'tutorial']):
            project_type = "learning"
        
        return {
            "technologies": detected_techs,
            "project_type": project_type,
            "complexity_level": "moderate",
            "development_stage": "learning" if project_type == "learning" else "development",
            "learning_needs": detected_techs,
            "technical_requirements": detected_techs,
            "preferred_content_types": ["tutorial", "documentation", "article"],
            "difficulty_preference": "intermediate",
            "focus_areas": detected_techs,
            "project_summary": f"Project involving {', '.join(detected_techs) if detected_techs else 'general topics'}"
        } 