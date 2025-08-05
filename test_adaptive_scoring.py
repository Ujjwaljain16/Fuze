#!/usr/bin/env python3
"""
Test script for Adaptive Scoring Engine
Tests dynamic weights and context-aware penalties
"""

from adaptive_scoring_engine import adaptive_scoring_engine, ContextType, UserIntent

def test_adaptive_scoring_engine():
    """Test the adaptive scoring engine with various scenarios"""
    
    print("Testing Adaptive Scoring Engine")
    print("=" * 50)
    
    # Test case 1: Learning context with beginner user
    print("\nTest 1: Learning Context (Beginner User)")
    print("-" * 30)
    
    bookmark_learning = {
        'title': 'Python Basics Tutorial',
        'notes': 'Introduction to Python programming for beginners',
        'technology_tags': ['python', 'programming'],
        'content_type': 'tutorial',
        'difficulty_level': 'beginner',
        'quality_score': 0.8
    }
    
    context_learning = {
        'technologies': ['python', 'javascript'],
        'skill_level': 'beginner',
        'learning_goals': 'Learn Python programming basics',
        'content_type': 'tutorial',
        'context_type': 'learning'
    }
    
    result = adaptive_scoring_engine.calculate_adaptive_score(bookmark_learning, context_learning)
    print(f"Final Score: {result['final_score']:.3f}")
    print(f"Context Type: {result['context_type']}")
    print(f"User Intent: {result['user_intent']}")
    print(f"Component Scores: {result['component_scores']}")
    print(f"Dynamic Weights: {result['dynamic_weights']}")
    print(f"Penalties: {result['penalties']}")
    print(f"Reasoning: {result['reasoning']}")
    
    # Test case 2: Project context with advanced user
    print("\nTest 2: Project Context (Advanced User)")
    print("-" * 30)
    
    bookmark_project = {
        'title': 'Advanced React Patterns',
        'notes': 'Complex React patterns and optimization techniques',
        'technology_tags': ['react', 'javascript', 'frontend'],
        'content_type': 'project',
        'difficulty_level': 'advanced',
        'quality_score': 0.9
    }
    
    context_project = {
        'technologies': ['react', 'typescript', 'node.js'],
        'skill_level': 'advanced',
        'project_description': 'Building a complex React application',
        'content_type': 'project',
        'context_type': 'project',
        'project_id': 123
    }
    
    result = adaptive_scoring_engine.calculate_adaptive_score(bookmark_project, context_project)
    print(f"Final Score: {result['final_score']:.3f}")
    print(f"Context Type: {result['context_type']}")
    print(f"User Intent: {result['user_intent']}")
    print(f"Component Scores: {result['component_scores']}")
    print(f"Dynamic Weights: {result['dynamic_weights']}")
    print(f"Penalties: {result['penalties']}")
    print(f"Reasoning: {result['reasoning']}")
    
    # Test case 3: Research context
    print("\nTest 3: Research Context")
    print("-" * 30)
    
    bookmark_research = {
        'title': 'Machine Learning Research Paper',
        'notes': 'Latest research on neural network architectures',
        'technology_tags': ['machine learning', 'ai', 'neural networks'],
        'content_type': 'research',
        'difficulty_level': 'advanced',
        'quality_score': 0.95
    }
    
    context_research = {
        'technologies': ['python', 'tensorflow'],
        'skill_level': 'intermediate',
        'learning_goals': 'Research machine learning techniques',
        'content_type': 'research',
        'context_type': 'research'
    }
    
    result = adaptive_scoring_engine.calculate_adaptive_score(bookmark_research, context_research)
    print(f"Final Score: {result['final_score']:.3f}")
    print(f"Context Type: {result['context_type']}")
    print(f"User Intent: {result['user_intent']}")
    print(f"Component Scores: {result['component_scores']}")
    print(f"Dynamic Weights: {result['dynamic_weights']}")
    print(f"Penalties: {result['penalties']}")
    print(f"Reasoning: {result['reasoning']}")
    
    # Test case 4: Irrelevant content (should get penalties)
    print("\nTest 4: Irrelevant Content (Should Get Penalties)")
    print("-" * 30)
    
    bookmark_irrelevant = {
        'title': 'Cooking Recipes',
        'notes': 'Delicious recipes for home cooking',
        'technology_tags': ['cooking', 'food'],
        'content_type': 'article',
        'difficulty_level': 'beginner',
        'quality_score': 0.7
    }
    
    context_tech = {
        'technologies': ['python', 'javascript', 'react'],
        'skill_level': 'intermediate',
        'learning_goals': 'Learn web development',
        'content_type': 'tutorial',
        'context_type': 'learning'
    }
    
    result = adaptive_scoring_engine.calculate_adaptive_score(bookmark_irrelevant, context_tech)
    print(f"Final Score: {result['final_score']:.3f}")
    print(f"Context Type: {result['context_type']}")
    print(f"User Intent: {result['user_intent']}")
    print(f"Component Scores: {result['component_scores']}")
    print(f"Dynamic Weights: {result['dynamic_weights']}")
    print(f"Penalties: {result['penalties']}")
    print(f"Reasoning: {result['reasoning']}")
    
    # Test case 5: Skill mismatch (beginner content for advanced user)
    print("\nTest 5: Skill Mismatch (Beginner Content for Advanced User)")
    print("-" * 30)
    
    bookmark_beginner = {
        'title': 'Hello World in Python',
        'notes': 'Your first Python program',
        'technology_tags': ['python'],
        'content_type': 'tutorial',
        'difficulty_level': 'beginner',
        'quality_score': 0.8
    }
    
    context_advanced = {
        'technologies': ['python', 'django', 'flask'],
        'skill_level': 'advanced',
        'learning_goals': 'Advanced Python development',
        'content_type': 'tutorial',
        'context_type': 'learning'
    }
    
    result = adaptive_scoring_engine.calculate_adaptive_score(bookmark_beginner, context_advanced)
    print(f"Final Score: {result['final_score']:.3f}")
    print(f"Context Type: {result['context_type']}")
    print(f"User Intent: {result['user_intent']}")
    print(f"Component Scores: {result['component_scores']}")
    print(f"Dynamic Weights: {result['dynamic_weights']}")
    print(f"Penalties: {result['penalties']}")
    print(f"Reasoning: {result['reasoning']}")

def test_context_detection():
    """Test context type and user intent detection"""
    print("\nTesting Context Detection")
    print("=" * 30)
    
    test_contexts = [
        {
            'name': 'Learning Context',
            'context': {
                'learning_goals': 'Learn React basics',
                'user_input': 'I want to learn React'
            }
        },
        {
            'name': 'Project Context',
            'context': {
                'project_id': 123,
                'project_description': 'Building a web app'
            }
        },
        {
            'name': 'Task Context',
            'context': {
                'task_id': 456,
                'user_input': 'I need to fix a bug'
            }
        },
        {
            'name': 'Research Context',
            'context': {
                'learning_goals': 'Research machine learning',
                'user_input': 'I want to research AI'
            }
        },
        {
            'name': 'Practice Context',
            'context': {
                'user_input': 'I want to practice algorithms'
            }
        }
    ]
    
    for test_case in test_contexts:
        print(f"\n{test_case['name']}:")
        context_type = adaptive_scoring_engine._determine_context_type(test_case['context'])
        user_intent = adaptive_scoring_engine._determine_user_intent(test_case['context'])
        print(f"  Context Type: {context_type.value}")
        print(f"  User Intent: {user_intent.value}")

def test_weight_adjustments():
    """Test dynamic weight adjustments"""
    print("\nTesting Weight Adjustments")
    print("=" * 30)
    
    # Test different skill levels
    skill_levels = ['beginner', 'intermediate', 'advanced']
    context_type = ContextType.LEARNING
    
    for skill_level in skill_levels:
        print(f"\nSkill Level: {skill_level}")
        weights = adaptive_scoring_engine._get_dynamic_weights(
            context_type, 
            UserIntent.LEARN_NEW, 
            skill_level
        )
        print(f"  Weights: {weights}")
        print(f"  Total Weight: {sum(weights.values()):.3f}")

def test_penalty_calculation():
    """Test penalty calculation for low-scoring components"""
    print("\nTesting Penalty Calculation")
    print("=" * 30)
    
    # Test case with very low scores
    component_scores = {
        'tech_match': 0.05,  # Very low
        'semantic_similarity': 0.1,  # Very low
        'content_relevance': 0.1,  # Very low
        'difficulty_alignment': 0.1,  # Very low
        'intent_alignment': 0.1  # Very low
    }
    
    context = {'skill_level': 'intermediate'}
    
    penalties = adaptive_scoring_engine._calculate_penalties(component_scores, context)
    print(f"Component Scores: {component_scores}")
    print(f"Penalties Applied: {penalties}")
    
    # Calculate final score with penalties
    total_score = sum(component_scores.values()) / len(component_scores)
    final_score = adaptive_scoring_engine._apply_penalties(total_score, penalties)
    print(f"Original Score: {total_score:.3f}")
    print(f"Final Score (with penalties): {final_score:.3f}")

if __name__ == "__main__":
    try:
        test_adaptive_scoring_engine()
        test_context_detection()
        test_weight_adjustments()
        test_penalty_calculation()
        print("\n✅ All adaptive scoring tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 