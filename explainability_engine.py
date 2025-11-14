"""
Explainability Engine - POWERED BY GEMINI AI
=============================================
Provides intelligent, dynamic explanations for why content was recommended.
NO hardcoded explanations - uses Gemini for natural language reasoning!

Features:
- 🤖 Gemini-powered explanations (intelligent & contextual)
- 📊 Detailed scoring breakdown
- 💡 Natural language reasoning
- ✨ Key strengths identification
- 🎯 Personalized insights
- 📈 Visual score distribution

Fallback: If Gemini unavailable, uses structured rule-based explanations
"""

import logging
from typing import Dict, List
from recommendation_config import RecommendationConfig as Config

logger = logging.getLogger(__name__)


class RecommendationExplainer:
    """Explains why recommendations were made"""
    
    def __init__(self):
        logger.info("Recommendation Explainer initialized")
    
    def explain_recommendation(self, recommendation: Dict, query_context: Dict, 
                              score_components: Dict = None) -> Dict:
        """
        Generate detailed explanation for a recommendation
        
        Args:
            recommendation: The recommendation dict
            query_context: User's query/project context
            score_components: Individual score components
        
        Returns:
            {
                'overall_score': 0.85,
                'confidence': 'high',
                'breakdown': {...},
                'why_recommended': "...",
                'key_strengths': [...],
                'considerations': [...],
                'alternatives': [...]
            }
        """
        try:
            # Overall assessment
            overall_score = recommendation.get('score', 0)
            confidence = self._assess_confidence(overall_score, score_components)
            
            # Detailed breakdown
            breakdown = self._create_breakdown(recommendation, score_components)
            
            # Human-readable explanation
            why_recommended = self._generate_why_recommended(
                recommendation, query_context, breakdown
            )
            
            # Key strengths
            key_strengths = self._identify_key_strengths(breakdown)
            
            # Considerations (potential limitations)
            considerations = self._identify_considerations(
                recommendation, query_context, breakdown
            )
            
            explanation = {
                'overall_score': round(overall_score, 2),
                'confidence': confidence,
                'breakdown': breakdown,
                'why_recommended': why_recommended,
                'key_strengths': key_strengths,
                'considerations': considerations,
                'score_distribution': self._create_score_distribution(breakdown)
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error explaining recommendation: {e}")
            return self._get_default_explanation(recommendation)
    
    def _create_breakdown(self, recommendation: Dict, 
                         score_components: Dict = None) -> Dict:
        """Create detailed scoring breakdown"""
        breakdown = {}
        
        # Technology match
        technologies = recommendation.get('technologies', [])
        rec_techs = set(t.lower() for t in technologies)
        
        tech_score = score_components.get('technology', 0) if score_components else 0.5
        breakdown['technology_match'] = {
            'score': round(tech_score, 2),
            'weight': Config.CONTEXT_ENGINE_WEIGHTS['technology'],
            'contribution': round(tech_score * Config.CONTEXT_ENGINE_WEIGHTS['technology'], 3),
            'details': {
                'matched_technologies': list(rec_techs),
                'total_technologies': len(technologies)
            },
            'explanation': self._explain_tech_match(tech_score, technologies)
        }
        
        # Semantic relevance
        semantic_score = score_components.get('semantic', 0) if score_components else 0.5
        breakdown['semantic_relevance'] = {
            'score': round(semantic_score, 2),
            'weight': Config.CONTEXT_ENGINE_WEIGHTS['semantic'],
            'contribution': round(semantic_score * Config.CONTEXT_ENGINE_WEIGHTS['semantic'], 3),
            'explanation': self._explain_semantic(semantic_score)
        }
        
        # Content type match
        content_type = recommendation.get('content_type', 'article')
        content_score = score_components.get('content_type', 0) if score_components else 0.5
        breakdown['content_type'] = {
            'score': round(content_score, 2),
            'weight': Config.CONTEXT_ENGINE_WEIGHTS['content_type'],
            'contribution': round(content_score * Config.CONTEXT_ENGINE_WEIGHTS['content_type'], 3),
            'type': content_type,
            'explanation': self._explain_content_type(content_type, content_score)
        }
        
        # Difficulty alignment
        difficulty = recommendation.get('difficulty', 'intermediate')
        difficulty_score = score_components.get('difficulty', 0) if score_components else 0.5
        breakdown['difficulty_alignment'] = {
            'score': round(difficulty_score, 2),
            'weight': Config.CONTEXT_ENGINE_WEIGHTS['difficulty'],
            'contribution': round(difficulty_score * Config.CONTEXT_ENGINE_WEIGHTS['difficulty'], 3),
            'level': difficulty,
            'explanation': self._explain_difficulty(difficulty, difficulty_score)
        }
        
        # Quality
        quality = recommendation.get('quality_score', 6) / 10.0
        breakdown['quality'] = {
            'score': round(quality, 2),
            'weight': Config.CONTEXT_ENGINE_WEIGHTS['quality'],
            'contribution': round(quality * Config.CONTEXT_ENGINE_WEIGHTS['quality'], 3),
            'quality_rating': f"{recommendation.get('quality_score', 6)}/10",
            'explanation': self._explain_quality(recommendation.get('quality_score', 6))
        }
        
        # Intent alignment (if available)
        if score_components and 'intent_alignment' in score_components:
            intent_score = score_components['intent_alignment']
            breakdown['intent_alignment'] = {
                'score': round(intent_score, 2),
                'weight': Config.CONTEXT_ENGINE_WEIGHTS['intent_alignment'],
                'contribution': round(intent_score * Config.CONTEXT_ENGINE_WEIGHTS['intent_alignment'], 3),
                'explanation': self._explain_intent(intent_score)
            }
        
        return breakdown
    
    def _explain_tech_match(self, score: float, technologies: List[str]) -> str:
        """Explain technology matching"""
        if score >= 0.8:
            return f"Excellent match! Covers {', '.join(technologies[:3])}{'...' if len(technologies) > 3 else ''}"
        elif score >= 0.6:
            return f"Good match with your tech stack: {', '.join(technologies[:2])}"
        elif score >= 0.4:
            return f"Partial match with some technologies: {', '.join(technologies[:2]) if technologies else 'general content'}"
        else:
            return "Limited technology overlap, but may provide foundational knowledge"
    
    def _explain_semantic(self, score: float) -> str:
        """Explain semantic relevance"""
        if score >= 0.8:
            return "Highly relevant to your query - discusses very similar concepts"
        elif score >= 0.6:
            return "Good conceptual match with your needs"
        elif score >= 0.4:
            return "Moderately related to your query"
        else:
            return "Tangentially related - may provide background context"
    
    def _explain_content_type(self, content_type: str, score: float) -> str:
        """Explain content type match"""
        type_benefits = {
            'tutorial': "Step-by-step guide perfect for hands-on learning",
            'documentation': "Comprehensive reference material for building",
            'article': "In-depth explanation of concepts",
            'video': "Visual learning resource",
            'code': "Real code examples to learn from"
        }
        
        benefit = type_benefits.get(content_type, "Helpful learning resource")
        
        if score >= 0.7:
            return f"{benefit} - excellent fit for your needs"
        else:
            return benefit
    
    def _explain_difficulty(self, difficulty: str, score: float) -> str:
        """Explain difficulty alignment"""
        if score >= 0.8:
            return f"Perfect difficulty level ({difficulty}) for your current skill level"
        elif score >= 0.6:
            return f"{difficulty.capitalize()} level - appropriate challenge"
        else:
            return f"{difficulty.capitalize()} level - may be {'easier' if score < 0.5 else 'harder'} than optimal"
    
    def _explain_quality(self, quality_score: int) -> str:
        """Explain quality rating"""
        if quality_score >= 8:
            return "Excellent quality content - highly curated"
        elif quality_score >= 6:
            return "Good quality resource"
        else:
            return "Decent quality, may need supplementing"
    
    def _explain_intent(self, score: float) -> str:
        """Explain intent alignment"""
        if score >= 0.8:
            return "Strongly aligns with your learning goals"
        elif score >= 0.6:
            return "Matches your stated objectives well"
        else:
            return "Provides related knowledge for your goals"
    
    def _assess_confidence(self, overall_score: float, 
                          score_components: Dict = None) -> str:
        """Assess confidence level in recommendation"""
        if overall_score >= 0.8:
            return "high"
        elif overall_score >= 0.6:
            return "medium"
        elif overall_score >= 0.4:
            return "moderate"
        else:
            return "low"
    
    def _generate_why_recommended(self, recommendation: Dict, 
                                  query_context: Dict, breakdown: Dict) -> str:
        """Generate human-readable explanation using Gemini AI"""
        
        # Try Gemini first for intelligent explanations
        try:
            gemini_explanation = self._generate_gemini_explanation(
                recommendation, query_context, breakdown
            )
            if gemini_explanation:
                return gemini_explanation
        except Exception as e:
            logger.warning(f"Gemini explanation failed, using fallback: {e}")
        
        # Fallback to structured explanation
        return self._generate_fallback_explanation(recommendation, query_context, breakdown)
    
    def _generate_gemini_explanation(self, recommendation: Dict,
                                    query_context: Dict, breakdown: Dict) -> str:
        """Generate intelligent explanation using Gemini"""
        try:
            from gemini_utils import get_gemini_response
            
            # Build context for Gemini
            prompt = f"""You are an expert learning advisor. Explain why this content was recommended to the user in 1-2 natural, conversational sentences.

User's Query:
- Title: {query_context.get('title', 'Not specified')}
- Technologies: {query_context.get('technologies', 'Not specified')}
- Description: {query_context.get('description', 'Learning resource')}

Recommended Content:
- Title: {recommendation.get('title', 'Untitled')}
- Type: {recommendation.get('content_type', 'article')}
- Difficulty: {recommendation.get('difficulty', 'intermediate')}
- Technologies: {', '.join(recommendation.get('technologies', [])[:5])}
- Quality Score: {recommendation.get('quality_score', 6)}/10

Scoring Breakdown:
- Technology Match: {breakdown.get('technology_match', {}).get('score', 0):.0%}
- Semantic Relevance: {breakdown.get('semantic_relevance', {}).get('score', 0):.0%}
- Content Type Fit: {breakdown.get('content_type', {}).get('score', 0):.0%}
- Difficulty Alignment: {breakdown.get('difficulty_alignment', {}).get('score', 0):.0%}
- Quality: {breakdown.get('quality', {}).get('score', 0):.0%}

Write a clear, helpful explanation focusing on the TOP 2-3 reasons this content is valuable for the user. Be conversational and encouraging. Start directly with the explanation (no preamble like "This was recommended because...").

Example good explanations:
- "This tutorial perfectly matches your Python and Flask stack, walking you through REST API design at an intermediate level that's ideal for your current skills."
- "Great semantic match for your React learning goals! This high-quality video breaks down component architecture in a beginner-friendly way."
- "Excellent fit for building your full-stack app - covers Node.js backend patterns you need, with practical code examples at the right difficulty level."

Your explanation:"""
            
            explanation = get_gemini_response(prompt)
            
            if explanation and len(explanation) > 20:
                # Clean up the response
                explanation = explanation.strip()
                # Remove common prefixes if Gemini added them
                for prefix in ["This content was recommended because ", "This was recommended because ", "Recommended because "]:
                    if explanation.startswith(prefix):
                        explanation = explanation[len(prefix):]
                        explanation = explanation[0].upper() + explanation[1:]  # Capitalize
                
                return explanation
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating Gemini explanation: {e}")
            return None
    
    def _generate_fallback_explanation(self, recommendation: Dict,
                                      query_context: Dict, breakdown: Dict) -> str:
        """Fallback structured explanation if Gemini unavailable"""
        reasons = []
        
        # Top contributing factors
        contributions = {k: v.get('contribution', 0) 
                        for k, v in breakdown.items()}
        top_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Technology match
        if 'technology_match' in [f[0] for f in top_factors]:
            tech_details = breakdown['technology_match']['details']
            techs = tech_details['matched_technologies'][:3]
            if techs:
                reasons.append(f"matches your tech stack ({', '.join(techs)})")
        
        # Content type
        content_type = recommendation.get('content_type', 'article')
        if breakdown['content_type']['score'] >= 0.7:
            reasons.append(f"is a {content_type} format that suits your learning style")
        
        # Difficulty
        difficulty = recommendation.get('difficulty', 'intermediate')
        if breakdown['difficulty_alignment']['score'] >= 0.7:
            reasons.append(f"is at the right {difficulty} difficulty level")
        
        # Quality
        quality = recommendation.get('quality_score', 6)
        if quality >= 8:
            reasons.append("is high-quality, well-curated content")
        
        # Semantic
        if breakdown['semantic_relevance']['score'] >= 0.7:
            reasons.append("closely matches what you're looking for")
        
        if not reasons:
            reasons.append("covers relevant topics for your learning journey")
        
        # Construct explanation
        if len(reasons) == 1:
            explanation = f"This {content_type} was recommended because it {reasons[0]}."
        elif len(reasons) == 2:
            explanation = f"This {content_type} was recommended because it {reasons[0]} and {reasons[1]}."
        else:
            explanation = f"This {content_type} was recommended because it {', '.join(reasons[:-1])}, and {reasons[-1]}."
        
        return explanation
    
    def _identify_key_strengths(self, breakdown: Dict) -> List[str]:
        """Identify key strengths using Gemini for intelligent insights"""
        
        # Try Gemini for intelligent strength identification
        try:
            gemini_strengths = self._generate_gemini_strengths(breakdown)
            if gemini_strengths and len(gemini_strengths) >= 2:
                return gemini_strengths[:3]
        except Exception as e:
            logger.debug(f"Gemini strengths failed, using fallback: {e}")
        
        # Fallback to rule-based strengths
        strengths = []
        
        for component, details in breakdown.items():
            score = details.get('score', 0)
            
            if score >= 0.8:
                if component == 'technology_match':
                    strengths.append("🎯 Excellent technology match")
                elif component == 'semantic_relevance':
                    strengths.append("💡 Highly relevant content")
                elif component == 'quality':
                    strengths.append("⭐ High-quality resource")
                elif component == 'difficulty_alignment':
                    strengths.append("📊 Perfect difficulty level")
                elif component == 'content_type':
                    strengths.append("📚 Ideal content format")
        
        # Ensure at least one strength
        if not strengths:
            # Find highest scoring component
            best = max(breakdown.items(), key=lambda x: x[1].get('score', 0))
            strengths.append(f"✓ Good {best[0].replace('_', ' ')}")
        
        return strengths[:3]  # Top 3 strengths
    
    def _generate_gemini_strengths(self, breakdown: Dict) -> List[str]:
        """Generate key strengths using Gemini"""
        try:
            from gemini_utils import get_gemini_response
            
            # Build scoring summary
            scores_text = "\n".join([
                f"- {k.replace('_', ' ').title()}: {v.get('score', 0):.0%}"
                for k, v in breakdown.items()
            ])
            
            prompt = f"""Based on these recommendation scores, identify the TOP 3 key strengths in a bullet-point format. Be specific and encouraging.

Scores:
{scores_text}

Format each strength as:
- [Emoji] [Brief strength description]

Examples:
- 🎯 Perfect match for your tech stack
- ⭐ Excellent quality (9/10 rating)
- 📊 Ideal intermediate difficulty level

Provide exactly 3 strengths (or 2 if only 2 scores are high). Focus on scores above 70%.

Your response (3 bullet points):"""
            
            response = get_gemini_response(prompt)
            
            if response:
                # Parse bullet points
                strengths = []
                for line in response.strip().split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                        strength = line.lstrip('-•* ').strip()
                        if strength and len(strength) > 5:
                            strengths.append(strength)
                
                return strengths[:3]
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating Gemini strengths: {e}")
            return []
    
    def _identify_considerations(self, recommendation: Dict, query_context: Dict,
                                breakdown: Dict) -> List[str]:
        """Identify potential limitations or considerations"""
        considerations = []
        
        # Check for weak points
        for component, details in breakdown.items():
            score = details.get('score', 0)
            
            if score < 0.4:
                if component == 'technology_match':
                    considerations.append("⚠️ Limited technology overlap - may be more general")
                elif component == 'difficulty_alignment':
                    difficulty = details.get('level', 'intermediate')
                    considerations.append(f"⚠️ {difficulty.capitalize()} level may not perfectly match your current skill")
                elif component == 'semantic_relevance':
                    considerations.append("⚠️ Not directly focused on your specific query")
        
        # Check quality
        quality = recommendation.get('quality_score', 6)
        if quality < 5:
            considerations.append("ℹ️ Quality rating suggests this may need supplementing with other resources")
        
        # If no considerations, add a neutral one
        if not considerations:
            considerations.append("✓ No major limitations identified")
        
        return considerations[:2]  # Top 2 considerations
    
    def _create_score_distribution(self, breakdown: Dict) -> Dict[str, float]:
        """Create a visual-ready score distribution"""
        distribution = {}
        
        for component, details in breakdown.items():
            contribution = details.get('contribution', 0)
            distribution[component] = round(contribution, 3)
        
        return distribution
    
    def _get_default_explanation(self, recommendation: Dict) -> Dict:
        """Fallback explanation if detailed analysis fails"""
        return {
            'overall_score': recommendation.get('score', 0.5),
            'confidence': 'medium',
            'breakdown': {},
            'why_recommended': "This content matches your query and may be helpful for your learning journey.",
            'key_strengths': ["✓ Relevant to your search"],
            'considerations': ["ℹ️ Detailed analysis unavailable"],
            'score_distribution': {}
        }
    
    def create_comparison(self, recommendations: List[Dict]) -> Dict:
        """Compare multiple recommendations"""
        if not recommendations:
            return {}
        
        comparison = {
            'total_analyzed': len(recommendations),
            'score_range': {
                'highest': max(r.get('score', 0) for r in recommendations),
                'lowest': min(r.get('score', 0) for r in recommendations),
                'average': sum(r.get('score', 0) for r in recommendations) / len(recommendations)
            },
            'diversity': {
                'content_types': list(set(r.get('content_type', 'article') for r in recommendations)),
                'difficulty_levels': list(set(r.get('difficulty', 'intermediate') for r in recommendations)),
                'tech_coverage': len(set(tech for r in recommendations for tech in r.get('technologies', [])))
            },
            'quality_distribution': {
                'high_quality': len([r for r in recommendations if r.get('quality_score', 6) >= 8]),
                'good_quality': len([r for r in recommendations if 6 <= r.get('quality_score', 6) < 8]),
                'moderate_quality': len([r for r in recommendations if r.get('quality_score', 6) < 6])
            }
        }
        
        return comparison


# Global instance
_explainer = None

def get_explainer() -> RecommendationExplainer:
    """Get or create global explainer instance"""
    global _explainer
    if _explainer is None:
        _explainer = RecommendationExplainer()
    return _explainer

