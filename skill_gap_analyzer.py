"""
Skill Gap Analysis System
==========================
Analyzes user's current skills and recommends what to learn next.
Progressive learning paths!

Features:
- Detect current skill level
- Identify missing prerequisites
- Suggest learning progression
- Adaptive difficulty recommendations
"""

import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SkillGapAnalyzer:
    """Analyzes skill gaps and creates learning paths"""
    
    def __init__(self):
        # Technology dependency graph (prerequisites)
        self.tech_dependencies = self._initialize_tech_dependencies()
        logger.info("Skill Gap Analyzer initialized")
    
    def _initialize_tech_dependencies(self) -> Dict[str, Dict]:
        """
        Define technology learning paths and prerequisites
        
        Format: {
            'technology': {
                'prerequisites': [...],
                'leads_to': [...],
                'difficulty': 'beginner'|'intermediate'|'advanced',
                'category': 'frontend'|'backend'|'devops'|'ml'|...
            }
        }
        """
        return {
            # Frontend
            'html': {
                'prerequisites': [],
                'leads_to': ['css', 'javascript'],
                'difficulty': 'beginner',
                'category': 'frontend'
            },
            'css': {
                'prerequisites': ['html'],
                'leads_to': ['sass', 'tailwind', 'javascript'],
                'difficulty': 'beginner',
                'category': 'frontend'
            },
            'javascript': {
                'prerequisites': ['html', 'css'],
                'leads_to': ['typescript', 'react', 'vue', 'angular', 'node'],
                'difficulty': 'intermediate',
                'category': 'frontend'
            },
            'typescript': {
                'prerequisites': ['javascript'],
                'leads_to': ['react', 'angular', 'node'],
                'difficulty': 'intermediate',
                'category': 'frontend'
            },
            'react': {
                'prerequisites': ['javascript'],
                'leads_to': ['next', 'react-native', 'redux'],
                'difficulty': 'intermediate',
                'category': 'frontend'
            },
            'vue': {
                'prerequisites': ['javascript'],
                'leads_to': ['nuxt', 'vuex'],
                'difficulty': 'intermediate',
                'category': 'frontend'
            },
            'angular': {
                'prerequisites': ['typescript'],
                'leads_to': ['rxjs', 'ngrx'],
                'difficulty': 'intermediate',
                'category': 'frontend'
            },
            
            # Backend
            'python': {
                'prerequisites': [],
                'leads_to': ['django', 'flask', 'fastapi', 'machine-learning'],
                'difficulty': 'beginner',
                'category': 'backend'
            },
            'flask': {
                'prerequisites': ['python'],
                'leads_to': ['rest-api', 'sqlalchemy'],
                'difficulty': 'intermediate',
                'category': 'backend'
            },
            'django': {
                'prerequisites': ['python'],
                'leads_to': ['rest-api', 'orm'],
                'difficulty': 'intermediate',
                'category': 'backend'
            },
            'node': {
                'prerequisites': ['javascript'],
                'leads_to': ['express', 'nest', 'rest-api'],
                'difficulty': 'intermediate',
                'category': 'backend'
            },
            'express': {
                'prerequisites': ['node', 'javascript'],
                'leads_to': ['rest-api', 'graphql'],
                'difficulty': 'intermediate',
                'category': 'backend'
            },
            
            # Database
            'sql': {
                'prerequisites': [],
                'leads_to': ['postgresql', 'mysql', 'database-design'],
                'difficulty': 'beginner',
                'category': 'database'
            },
            'postgresql': {
                'prerequisites': ['sql'],
                'leads_to': ['database-optimization', 'orm'],
                'difficulty': 'intermediate',
                'category': 'database'
            },
            'mongodb': {
                'prerequisites': [],
                'leads_to': ['nosql', 'aggregation'],
                'difficulty': 'beginner',
                'category': 'database'
            },
            
            # DevOps
            'git': {
                'prerequisites': [],
                'leads_to': ['github', 'ci-cd'],
                'difficulty': 'beginner',
                'category': 'devops'
            },
            'docker': {
                'prerequisites': [],
                'leads_to': ['kubernetes', 'containerization'],
                'difficulty': 'intermediate',
                'category': 'devops'
            },
            'kubernetes': {
                'prerequisites': ['docker'],
                'leads_to': ['cloud-native', 'orchestration'],
                'difficulty': 'advanced',
                'category': 'devops'
            },
            
            # Cloud
            'aws': {
                'prerequisites': [],
                'leads_to': ['ec2', 's3', 'lambda', 'cloud-architecture'],
                'difficulty': 'intermediate',
                'category': 'cloud'
            },
            
            # ML/AI
            'machine-learning': {
                'prerequisites': ['python'],
                'leads_to': ['tensorflow', 'pytorch', 'scikit-learn'],
                'difficulty': 'intermediate',
                'category': 'ml'
            },
            'tensorflow': {
                'prerequisites': ['python', 'machine-learning'],
                'leads_to': ['deep-learning', 'neural-networks'],
                'difficulty': 'advanced',
                'category': 'ml'
            },
            'pytorch': {
                'prerequisites': ['python', 'machine-learning'],
                'leads_to': ['deep-learning', 'neural-networks'],
                'difficulty': 'advanced',
                'category': 'ml'
            }
        }
    
    # ============================================================================
    # SKILL DETECTION
    # ============================================================================
    
    def analyze_user_skills(self, user_id: int) -> Dict:
        """
        Analyze user's current skills from their content history
        
        Returns:
            {
                'known_technologies': ['python', 'flask', 'javascript'],
                'skill_levels': {'python': 'intermediate', 'javascript': 'beginner'},
                'strong_categories': ['backend', 'frontend'],
                'learning_history': {...},
                'confidence_scores': {'python': 0.8, 'javascript': 0.5}
            }
        """
        try:
            from models import db, SavedContent, ContentAnalysis, UserFeedback
            
            # Get user's content history (last 180 days)
            cutoff_date = datetime.utcnow() - timedelta(days=180)
            
            content_query = db.session.query(
                SavedContent, ContentAnalysis
            ).outerjoin(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            ).filter(
                SavedContent.user_id == user_id,
                SavedContent.saved_at >= cutoff_date
            ).all()
            
            # Get user feedback for confidence scoring
            feedback_query = db.session.query(UserFeedback).filter(
                UserFeedback.user_id == user_id,
                UserFeedback.timestamp >= cutoff_date
            ).all()
            
            # Analyze technologies and skill levels
            tech_counts = defaultdict(int)
            tech_difficulties = defaultdict(list)
            tech_feedback = defaultdict(lambda: {'positive': 0, 'total': 0})
            categories = defaultdict(int)
            
            # From saved content
            for content, analysis in content_query:
                if analysis and analysis.technology_tags:
                    techs = [t.strip().lower() for t in analysis.technology_tags.split(',')]
                    difficulty = analysis.difficulty_level or 'intermediate'
                    
                    for tech in techs:
                        if tech:
                            tech_counts[tech] += 1
                            tech_difficulties[tech].append(difficulty)
                            
                            # Determine category
                            tech_info = self.tech_dependencies.get(tech, {})
                            category = tech_info.get('category', 'other')
                            categories[category] += 1
            
            # From feedback (indicates engagement level)
            for feedback in feedback_query:
                # Get tech from content
                content = db.session.query(SavedContent).get(feedback.content_id)
                if content:
                    analysis = db.session.query(ContentAnalysis).filter_by(
                        content_id=content.id
                    ).first()
                    
                    if analysis and analysis.technology_tags:
                        techs = [t.strip().lower() for t in analysis.technology_tags.split(',')]
                        is_positive = feedback.feedback_type in ['clicked', 'saved', 'helpful', 'completed']
                        
                        for tech in techs:
                            if tech:
                                tech_feedback[tech]['total'] += 1
                                if is_positive:
                                    tech_feedback[tech]['positive'] += 1
            
            # Determine skill levels
            known_technologies = list(tech_counts.keys())
            skill_levels = self._estimate_skill_levels(tech_counts, tech_difficulties)
            confidence_scores = self._calculate_confidence_scores(
                tech_counts, tech_feedback
            )
            
            # Identify strong categories
            strong_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            strong_categories = [cat for cat, _ in strong_categories[:3]]
            
            return {
                'known_technologies': known_technologies,
                'skill_levels': skill_levels,
                'strong_categories': strong_categories,
                'confidence_scores': confidence_scores,
                'total_content_items': len(content_query),
                'tech_exposure': dict(tech_counts)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user skills: {e}")
            return self._get_default_skills()
    
    def _estimate_skill_levels(self, tech_counts: Dict, 
                              tech_difficulties: Dict) -> Dict[str, str]:
        """Estimate skill level for each technology"""
        skill_levels = {}
        
        for tech, count in tech_counts.items():
            difficulties = tech_difficulties[tech]
            
            # Count exposure at each difficulty
            beginner_count = difficulties.count('beginner')
            intermediate_count = difficulties.count('intermediate')
            advanced_count = difficulties.count('advanced')
            
            # Estimate level based on exposure and difficulty distribution
            if advanced_count >= 3 or (intermediate_count >= 5 and advanced_count >= 1):
                skill_levels[tech] = 'advanced'
            elif intermediate_count >= 3 or count >= 10:
                skill_levels[tech] = 'intermediate'
            else:
                skill_levels[tech] = 'beginner'
        
        return skill_levels
    
    def _calculate_confidence_scores(self, tech_counts: Dict,
                                     tech_feedback: Dict) -> Dict[str, float]:
        """Calculate confidence in skill assessment (0-1)"""
        confidence_scores = {}
        
        for tech, count in tech_counts.items():
            # Base confidence from exposure count
            exposure_confidence = min(count / 10.0, 1.0)  # Max out at 10 items
            
            # Feedback confidence (engagement indicates real use)
            feedback_confidence = 0.5  # Default
            if tech in tech_feedback:
                fb = tech_feedback[tech]
                if fb['total'] > 0:
                    feedback_confidence = fb['positive'] / fb['total']
            
            # Combined confidence (weighted average)
            confidence = (exposure_confidence * 0.6 + feedback_confidence * 0.4)
            confidence_scores[tech] = round(confidence, 2)
        
        return confidence_scores
    
    def _get_default_skills(self) -> Dict:
        """Default skills for new users"""
        return {
            'known_technologies': [],
            'skill_levels': {},
            'strong_categories': [],
            'confidence_scores': {},
            'total_content_items': 0,
            'tech_exposure': {}
        }
    
    # ============================================================================
    # GAP ANALYSIS
    # ============================================================================
    
    def identify_skill_gaps(self, user_id: int, target_goal: str = None,
                           target_technologies: List[str] = None) -> Dict:
        """
        Identify skill gaps for a learning goal
        
        Args:
            user_id: User ID
            target_goal: Optional goal description
            target_technologies: Technologies user wants to learn
        
        Returns:
            {
                'missing_prerequisites': [...],
                'recommended_next_steps': [...],
                'advanced_topics': [...],
                'learning_path': [...]
            }
        """
        try:
            # Get current skills
            current_skills = self.analyze_user_skills(user_id)
            known_techs = set(t.lower() for t in current_skills['known_technologies'])
            
            # Determine target technologies
            if target_technologies:
                targets = [t.lower().strip() for t in target_technologies]
            else:
                # Infer from strong categories
                targets = self._infer_learning_targets(current_skills)
            
            gaps = {
                'missing_prerequisites': [],
                'recommended_next_steps': [],
                'advanced_topics': [],
                'learning_path': []
            }
            
            # Analyze each target
            for target in targets:
                target = target.lower()
                
                # Check prerequisites
                missing_prereqs = self._find_missing_prerequisites(target, known_techs)
                if missing_prereqs:
                    gaps['missing_prerequisites'].extend(missing_prereqs)
                
                # Check if user is ready for this tech
                if not missing_prereqs:
                    # User has prerequisites, this is a good next step
                    if target not in known_techs:
                        gaps['recommended_next_steps'].append({
                            'technology': target,
                            'reason': self._explain_recommendation(target, known_techs),
                            'difficulty': self.tech_dependencies.get(target, {}).get('difficulty', 'intermediate'),
                            'category': self.tech_dependencies.get(target, {}).get('category', 'general')
                        })
                else:
                    # User doesn't have prerequisites yet
                    gaps['advanced_topics'].append({
                        'technology': target,
                        'missing_prerequisites': missing_prereqs,
                        'reason': f"Complete {', '.join(missing_prereqs)} first"
                    })
            
            # Generate learning path
            gaps['learning_path'] = self._generate_learning_path(
                known_techs, targets, current_skills
            )
            
            # Remove duplicates
            gaps['missing_prerequisites'] = list(set(gaps['missing_prerequisites']))
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error identifying skill gaps: {e}")
            return {
                'missing_prerequisites': [],
                'recommended_next_steps': [],
                'advanced_topics': [],
                'learning_path': []
            }
    
    def _find_missing_prerequisites(self, target: str, 
                                   known_techs: Set[str]) -> List[str]:
        """Find prerequisites user is missing for a technology"""
        if target not in self.tech_dependencies:
            return []  # Unknown tech, assume no prerequisites
        
        prereqs = self.tech_dependencies[target]['prerequisites']
        missing = []
        
        for prereq in prereqs:
            if prereq.lower() not in known_techs:
                missing.append(prereq)
        
        return missing
    
    def _explain_recommendation(self, tech: str, known_techs: Set[str]) -> str:
        """Explain why this technology is recommended"""
        if tech not in self.tech_dependencies:
            return f"Next step in your learning journey"
        
        prereqs = self.tech_dependencies[tech]['prerequisites']
        
        if prereqs:
            # Find which prerequisites user has
            known_prereqs = [p for p in prereqs if p.lower() in known_techs]
            if known_prereqs:
                return f"Natural progression from {', '.join(known_prereqs)}"
        
        return "Foundational skill to learn"
    
    def _infer_learning_targets(self, current_skills: Dict) -> List[str]:
        """Infer what user might want to learn next based on current skills"""
        known_techs = set(t.lower() for t in current_skills['known_technologies'])
        targets = []
        
        # Find technologies that lead from current skills
        for tech in known_techs:
            if tech in self.tech_dependencies:
                next_techs = self.tech_dependencies[tech]['leads_to']
                for next_tech in next_techs:
                    if next_tech.lower() not in known_techs:
                        targets.append(next_tech)
        
        # Deduplicate and return top 5
        return list(set(targets))[:5]
    
    def _generate_learning_path(self, known_techs: Set[str], targets: List[str],
                               current_skills: Dict) -> List[Dict]:
        """Generate step-by-step learning path"""
        path = []
        skill_levels = current_skills.get('skill_levels', {})
        
        # Start with prerequisites user is missing
        all_missing_prereqs = set()
        for target in targets:
            missing = self._find_missing_prerequisites(target, known_techs)
            all_missing_prereqs.update(missing)
        
        # Order prerequisites by difficulty
        ordered_prereqs = sorted(
            all_missing_prereqs,
            key=lambda x: self._get_difficulty_level(x)
        )
        
        # Add to path
        for prereq in ordered_prereqs:
            path.append({
                'step': len(path) + 1,
                'technology': prereq,
                'type': 'prerequisite',
                'difficulty': self.tech_dependencies.get(prereq, {}).get('difficulty', 'beginner'),
                'estimated_time': self._estimate_learning_time(prereq, 'beginner')
            })
        
        # Add target technologies
        for target in targets:
            if target.lower() not in known_techs:
                path.append({
                    'step': len(path) + 1,
                    'technology': target,
                    'type': 'target',
                    'difficulty': self.tech_dependencies.get(target, {}).get('difficulty', 'intermediate'),
                    'estimated_time': self._estimate_learning_time(target, 'intermediate')
                })
        
        return path[:10]  # Limit to 10 steps
    
    def _get_difficulty_level(self, tech: str) -> int:
        """Get numeric difficulty level (1-3)"""
        if tech not in self.tech_dependencies:
            return 2  # Default intermediate
        
        difficulty = self.tech_dependencies[tech]['difficulty']
        return {'beginner': 1, 'intermediate': 2, 'advanced': 3}.get(difficulty, 2)
    
    def _estimate_learning_time(self, tech: str, skill_level: str) -> str:
        """Estimate learning time for a technology"""
        difficulty = self.tech_dependencies.get(tech, {}).get('difficulty', 'intermediate')
        
        time_estimates = {
            ('beginner', 'beginner'): '1-2 weeks',
            ('beginner', 'intermediate'): '2-4 weeks',
            ('intermediate', 'beginner'): '1 week',
            ('intermediate', 'intermediate'): '2-3 weeks',
            ('intermediate', 'advanced'): '4-6 weeks',
            ('advanced', 'intermediate'): '1-2 weeks',
            ('advanced', 'advanced'): '3-4 weeks'
        }
        
        return time_estimates.get((skill_level, difficulty), '2-3 weeks')
    
    # ============================================================================
    # RECOMMENDATION BOOSTING
    # ============================================================================
    
    def boost_recommendations_by_gaps(self, recommendations: List[Dict],
                                      skill_gaps: Dict) -> List[Dict]:
        """Boost recommendations that fill identified skill gaps"""
        
        # Extract gap technologies
        gap_techs = set()
        
        # Prerequisites are high priority
        for prereq in skill_gaps.get('missing_prerequisites', []):
            gap_techs.add(prereq.lower())
        
        # Next steps are medium priority
        for next_step in skill_gaps.get('recommended_next_steps', []):
            gap_techs.add(next_step['technology'].lower())
        
        if not gap_techs:
            return recommendations
        
        # Boost matching recommendations
        boosted_recs = []
        
        for rec in recommendations:
            rec_copy = rec.copy()
            rec_techs = set(t.lower() for t in rec.get('technologies', []))
            
            # Check overlap with gaps
            overlap = rec_techs.intersection(gap_techs)
            
            if overlap:
                # Boost score based on gap priority
                boost = 0
                
                if any(tech in skill_gaps.get('missing_prerequisites', []) for tech in overlap):
                    boost = 0.15  # +15% for prerequisites
                elif any(tech in [s['technology'] for s in skill_gaps.get('recommended_next_steps', [])] for tech in overlap):
                    boost = 0.10  # +10% for next steps
                
                rec_copy['score'] = min(1.0, rec.get('score', 0.5) + boost)
                rec_copy['gap_matched'] = list(overlap)
                rec_copy['reason'] = f"{rec.get('reason', '')} Fills skill gap: {', '.join(overlap)}."
            
            boosted_recs.append(rec_copy)
        
        # Re-sort
        boosted_recs.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return boosted_recs


# Global instance
_skill_analyzer = None

def get_skill_analyzer() -> SkillGapAnalyzer:
    """Get or create global skill analyzer instance"""
    global _skill_analyzer
    if _skill_analyzer is None:
        _skill_analyzer = SkillGapAnalyzer()
    return _skill_analyzer

