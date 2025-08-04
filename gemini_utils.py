import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import time
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Gemini AI-powered content analyzer for enhanced recommendation system
    """
    
    def __init__(self, api_key: str = None):
        api_key = api_key or os.environ.get('GEMINI_API_KEY')
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
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    def _make_gemini_request(self, prompt: str, retry_count: int = 0) -> Optional[str]:
        """
        Make a request to Gemini with retry logic and better error handling
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Validate response
            if not response:
                logger.warning(f"Empty response object from Gemini (attempt {retry_count + 1})")
                return None
                
            if not hasattr(response, 'text'):
                logger.warning(f"Response object has no text attribute (attempt {retry_count + 1})")
                return None
                
            response_text = response.text
            if not response_text or response_text.strip() == "":
                logger.warning(f"Empty response text from Gemini (attempt {retry_count + 1})")
                return None
                
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"Gemini request failed (attempt {retry_count + 1}): {e}")
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_gemini_request(prompt, retry_count + 1)
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """
        Extract JSON from Gemini response, handling various response formats
        """
        if not response_text:
            return None
            
        # Try to find JSON in the response
        # Look for JSON blocks marked with ```json or ```
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the match
                    cleaned = match.strip()
                    if cleaned.startswith('{') and cleaned.endswith('}'):
                        return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
        
        # If no JSON found in code blocks, try to parse the entire response
        try:
            # Remove any markdown formatting
            cleaned_response = re.sub(r'^```.*?\n', '', response_text, flags=re.MULTILINE)
            cleaned_response = re.sub(r'\n```$', '', cleaned_response, flags=re.MULTILINE)
            cleaned_response = cleaned_response.strip()
            
            if cleaned_response.startswith('{') and cleaned_response.endswith('}'):
                return json.loads(cleaned_response)
        except json.JSONDecodeError:
            pass
            
        return None
    
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
                "prerequisites": ["prerequisite1", "prerequisite2"],
                "learning_path": {{
                    "is_foundational": true,
                    "builds_on": ["concept1", "concept2"],
                    "leads_to": ["concept3", "concept4"],
                    "estimated_time": "2-3 hours",
                    "hands_on_practice": true
                }},
                "project_applicability": {{
                    "suitable_for": ["web_app", "mobile_app", "api", "data_analysis", "desktop_app", "library", "tool"],
                    "implementation_ready": true,
                    "code_examples": true,
                    "real_world_examples": true
                }},
                "skill_development": {{
                    "primary_skills": ["skill1", "skill2"],
                    "secondary_skills": ["skill3", "skill4"],
                    "skill_level_after": "intermediate",
                    "certification_relevant": false
                }}
            }}
            
            Important guidelines:
            - Be precise with technology detection (e.g., distinguish Java from JavaScript)
            - Assess content quality based on completeness, clarity, and practical value
            - Identify the target audience and learning objectives
            - Provide accurate difficulty assessment
            - Extract key concepts that would be valuable for learning
            - For learning_path: Identify if content is foundational, what it builds on, and what it leads to
            - For project_applicability: Determine which project types this content is suitable for
            - For skill_development: Identify primary and secondary skills that will be developed
            - If content type is unclear, default to "article" or "guide"
            - If difficulty is unclear, default to "intermediate"
            - If target audience is unclear, default to "intermediate"
            - Always provide specific values, avoid "unknown" or "none"
            - For general content, classify as "article" or "guide"
            - Respond ONLY with valid JSON, no additional text
            """
            
            response_text = self._make_gemini_request(prompt)
            
            if not response_text:
                logger.warning(f"Empty response from Gemini for {title}, using fallback")
                return self._get_fallback_analysis(title, description, content)
            
            # Try to extract JSON from response
            result = self._extract_json_from_response(response_text)
            
            if result:
                logger.info(f"Successfully analyzed bookmark: {title}")
                return result
            else:
                logger.warning(f"Could not extract JSON from Gemini response for {title}, using fallback")
                logger.debug(f"Raw response: {response_text[:500]}...")
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
            - Respond ONLY with valid JSON, no additional text
            """
            
            response_text = self._make_gemini_request(prompt)
            
            if not response_text:
                logger.warning(f"Empty response from Gemini for context {title}, using fallback")
                return self._get_fallback_context_analysis(title, description, technologies)
            
            # Try to extract JSON from response
            result = self._extract_json_from_response(response_text)
            
            if result:
                logger.info(f"Successfully analyzed user context: {title}")
                return result
            else:
                logger.warning(f"Could not extract JSON from Gemini response for context {title}, using fallback")
                logger.debug(f"Raw response: {response_text[:500]}...")
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
            
            response_text = self._make_gemini_request(prompt)
            
            if not response_text:
                logger.warning("Empty response from Gemini for reasoning, using fallback")
                return self._get_fallback_reasoning(bookmark, user_context)
            
            # Clean up the response (remove markdown formatting if present)
            cleaned_response = re.sub(r'^```.*?\n', '', response_text, flags=re.MULTILINE)
            cleaned_response = re.sub(r'\n```$', '', cleaned_response, flags=re.MULTILINE)
            cleaned_response = cleaned_response.strip()
            
            if cleaned_response:
                logger.info("Successfully generated recommendation reasoning")
                return cleaned_response
            else:
                logger.warning("Empty cleaned response from Gemini for reasoning, using fallback")
                return self._get_fallback_reasoning(bookmark, user_context)
                
        except Exception as e:
            logger.error(f"Gemini reasoning generation failed: {e}")
            return self._get_fallback_reasoning(bookmark, user_context)
    
    def _get_fallback_reasoning(self, bookmark: Dict, user_context: Dict) -> str:
        """
        Generate fallback reasoning when Gemini fails
        """
        bookmark_techs = bookmark.get('technologies', [])
        user_techs = user_context.get('technologies', [])
        
        # Find common technologies
        common_techs = set(bookmark_techs) & set(user_techs)
        
        if common_techs:
            tech_list = ', '.join(list(common_techs)[:3])
            return f"Relevant for your {user_context.get('project_type', 'project')} using {tech_list}."
        
        content_type = bookmark.get('content_type', 'content')
        difficulty = bookmark.get('difficulty', 'intermediate')
        
        return f"Helpful {content_type} at {difficulty} level for your learning goals."
    
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
            "prerequisites": [],
            "learning_path": {
                "is_foundational": False,
                "builds_on": [],
                "leads_to": [],
                "estimated_time": "1-2 hours",
                "hands_on_practice": False
            },
            "project_applicability": {
                "suitable_for": ["general"],
                "implementation_ready": False,
                "code_examples": False,
                "real_world_examples": False
            },
            "skill_development": {
                "primary_skills": technologies,
                "secondary_skills": [],
                "skill_level_after": "intermediate",
                "certification_relevant": False
            }
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
    
    def analyze_batch_content(self, batch_prompt: str) -> Dict:
        """
        Analyze multiple content items in a single API call for batch processing
        """
        try:
            # Create a structured prompt that explicitly requests JSON output
            structured_prompt = f"""
            Analyze the following content items and provide insights in valid JSON format ONLY:

            {batch_prompt}

            Please respond with ONLY a valid JSON object containing analysis for each item. 
                            The JSON should have this structure:
                {{
                    "items": [
                        {{
                            "title": "item title",
                            "technologies": ["tech1", "tech2"],
                            "content_type": "tutorial|article|documentation",
                            "difficulty": "beginner|intermediate|advanced",
                            "key_concepts": ["concept1", "concept2"],
                            "relevance_score": 85,
                            "summary": "brief summary",
                            "learning_objectives": ["objective1", "objective2"],
                            "learning_path": {{
                                "is_foundational": true,
                                "builds_on": ["concept1"],
                                "leads_to": ["concept2"],
                                "estimated_time": "2-3 hours",
                                "hands_on_practice": true
                            }},
                            "project_applicability": {{
                                "suitable_for": ["web_app", "api"],
                                "implementation_ready": true,
                                "code_examples": true,
                                "real_world_examples": true
                            }},
                            "skill_development": {{
                                "primary_skills": ["skill1"],
                                "secondary_skills": ["skill2"],
                                "skill_level_after": "intermediate",
                                "certification_relevant": false
                            }}
                        }}
                    ],
                    "overall_insights": {{
                        "common_technologies": ["tech1", "tech2"],
                        "difficulty_distribution": {{"beginner": 1, "intermediate": 2}},
                        "content_types": ["tutorial", "article"],
                        "recommended_order": ["item1", "item2", "item3"],
                        "learning_paths": {{
                            "foundational_topics": ["topic1", "topic2"],
                            "advanced_topics": ["topic3", "topic4"],
                            "estimated_total_time": "8-12 hours"
                        }},
                        "project_coverage": {{
                            "web_apps": 3,
                            "apis": 2,
                            "mobile_apps": 1
                        }},
                        "skill_progression": {{
                            "beginner_skills": ["skill1", "skill2"],
                            "intermediate_skills": ["skill3", "skill4"],
                            "advanced_skills": ["skill5"]
                        }}
                    }}
                }}

            Respond with ONLY the JSON, no additional text.
            """
            
            response_text = self._make_gemini_request(structured_prompt)
            
            if not response_text:
                logger.warning("Empty response from Gemini for batch analysis, using fallback")
                return self._get_batch_fallback_analysis("")
            
            # Try to extract JSON from response
            result = self._extract_json_from_response(response_text)
            
            if result:
                logger.info("Successfully analyzed batch content")
                return result
            else:
                logger.warning("Could not extract JSON from Gemini batch response, using fallback")
                logger.debug(f"Raw batch response: {response_text[:500]}...")
                return self._get_batch_fallback_analysis(batch_prompt)
                
        except Exception as e:
            logger.error(f"Error in batch content analysis: {e}")
            return self._get_batch_fallback_analysis(batch_prompt)
    
    def _get_batch_fallback_analysis(self, batch_prompt: str) -> Dict:
        """
        Fallback analysis for batch processing when JSON parsing fails
        """
        try:
            # Parse the batch prompt to extract content items
            lines = batch_prompt.split('\n')
            items = []
            
            for line in lines:
                line = line.strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    # Extract title and description from the line
                    parts = line.split(' - ', 1)
                    if len(parts) >= 2:
                        title = parts[0].split('.', 1)[1].strip().strip('"')
                        description = parts[1].strip()
                        
                        # Basic technology detection
                        technologies = []
                        text_lower = f"{title} {description}".lower()
                        if any(tech in text_lower for tech in ['javascript', 'js', 'react', 'node']):
                            technologies.append('JavaScript')
                        if any(tech in text_lower for tech in ['python', 'django', 'flask']):
                            technologies.append('Python')
                        if any(tech in text_lower for tech in ['java', 'jvm', 'spring']):
                            technologies.append('Java')
                        if any(tech in text_lower for tech in ['promise', 'async', 'await']):
                            technologies.append('JavaScript')
                        if any(tech in text_lower for tech in ['data structure', 'algorithm']):
                            technologies.append('DSA')
                        
                        # Determine content type and difficulty
                        content_type = "article"
                        if any(word in text_lower for word in ['tutorial', 'guide', 'how to']):
                            content_type = "tutorial"
                        elif any(word in text_lower for word in ['documentation', 'docs', 'api']):
                            content_type = "documentation"
                        
                        difficulty = "intermediate"
                        if any(word in text_lower for word in ['beginner', 'basic', 'intro']):
                            difficulty = "beginner"
                        elif any(word in text_lower for word in ['advanced', 'expert', 'complex']):
                            difficulty = "advanced"
                        
                        items.append({
                            "title": title,
                            "technologies": technologies,
                            "content_type": content_type,
                            "difficulty": difficulty,
                            "key_concepts": [],
                            "relevance_score": 75,
                            "summary": description,
                            "learning_objectives": [],
                            "learning_path": {
                                "is_foundational": difficulty == "beginner",
                                "builds_on": [],
                                "leads_to": [],
                                "estimated_time": "1-2 hours",
                                "hands_on_practice": content_type == "tutorial"
                            },
                            "project_applicability": {
                                "suitable_for": ["general"],
                                "implementation_ready": content_type in ["tutorial", "example"],
                                "code_examples": content_type in ["tutorial", "example"],
                                "real_world_examples": content_type in ["tutorial", "example"]
                            },
                            "skill_development": {
                                "primary_skills": technologies,
                                "secondary_skills": [],
                                "skill_level_after": difficulty,
                                "certification_relevant": False
                            }
                        })
            
            # Create overall insights
            all_technologies = []
            difficulty_counts = {"beginner": 0, "intermediate": 0, "advanced": 0}
            content_types = []
            
            for item in items:
                all_technologies.extend(item["technologies"])
                difficulty_counts[item["difficulty"]] += 1
                if item["content_type"] not in content_types:
                    content_types.append(item["content_type"])
            
            # Remove duplicates and get common technologies
            common_technologies = list(set(all_technologies))
            
            return {
                "items": items,
                "overall_insights": {
                    "common_technologies": common_technologies,
                    "difficulty_distribution": difficulty_counts,
                    "content_types": content_types,
                    "recommended_order": [item["title"] for item in items],
                    "learning_paths": {
                        "foundational_topics": [item["title"] for item in items if item["difficulty"] == "beginner"],
                        "advanced_topics": [item["title"] for item in items if item["difficulty"] == "advanced"],
                        "estimated_total_time": f"{len(items) * 2}-{len(items) * 3} hours"
                    },
                    "project_coverage": {
                        "web_apps": len([item for item in items if "JavaScript" in item["technologies"] or "React" in item["technologies"]]),
                        "apis": len([item for item in items if "Node.js" in item["technologies"] or "Python" in item["technologies"]]),
                        "mobile_apps": len([item for item in items if "React Native" in item["technologies"]])
                    },
                    "skill_progression": {
                        "beginner_skills": list(set([skill for item in items if item["difficulty"] == "beginner" for skill in item["technologies"]])),
                        "intermediate_skills": list(set([skill for item in items if item["difficulty"] == "intermediate" for skill in item["technologies"]])),
                        "advanced_skills": list(set([skill for item in items if item["difficulty"] == "advanced" for skill in item["technologies"]]))
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in batch fallback analysis: {e}")
            return {
                "items": [],
                "overall_insights": {
                    "common_technologies": [],
                    "difficulty_distribution": {"beginner": 0, "intermediate": 0, "advanced": 0},
                    "content_types": [],
                    "recommended_order": [],
                    "learning_paths": {
                        "foundational_topics": [],
                        "advanced_topics": [],
                        "estimated_total_time": "0 hours"
                    },
                    "project_coverage": {
                        "web_apps": 0,
                        "apis": 0,
                        "mobile_apps": 0
                    },
                    "skill_progression": {
                        "beginner_skills": [],
                        "intermediate_skills": [],
                        "advanced_skills": []
                    }
                }
            } 