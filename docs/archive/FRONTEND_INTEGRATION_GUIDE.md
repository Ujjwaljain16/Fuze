# 🚀 Frontend Integration Guide - Enhanced Recommendation System

## Overview

Your recommendation engine now includes:
- ✅ **Gemini-powered explanations** in the main `/api/recommendations/unified-orchestrator` endpoint
- ✅ **User feedback tracking** for personalized learning
- ✅ **Skill gap analysis** for progressive learning paths
- ✅ **Detailed explainability** on-demand

---

## 📱 React Native Integration

### 1. Main Recommendations Endpoint (Enhanced with Gemini)

The main endpoint now automatically uses Gemini for intelligent explanations!

```typescript
// api/recommendations.ts
import { API_BASE_URL } from './config';

interface RecommendationRequest {
  title: string;
  description: string;
  technologies: string;
  project_id?: number;
  user_interests?: string;
  max_recommendations?: number;
  engine_preference?: 'fast' | 'context' | 'auto';
}

interface Recommendation {
  id: number;
  title: string;
  url: string;
  score: number;
  reason: string;  // 🤖 NOW GEMINI-POWERED!
  content_type: string;
  difficulty: string;
  technologies: string[];
  key_concepts: string[];
  quality_score: number;
  confidence: number;
  metadata: {
    score_components: {
      technology: number;
      semantic: number;
      content_type: number;
      difficulty: number;
      quality: number;
      intent_alignment: number;
    };
    ml_enhanced: boolean;
    ml_boost: number;
  };
}

export async function getRecommendations(
  request: RecommendationRequest,
  authToken: string
): Promise<Recommendation[]> {
  const response = await fetch(`${API_BASE_URL}/api/recommendations/unified-orchestrator`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Recommendations failed: ${response.status}`);
  }

  const data = await response.json();
  return data.recommendations;
}
```

**Usage in React Native Component:**

```typescript
// screens/RecommendationsScreen.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, ActivityIndicator } from 'react-native';
import { getRecommendations } from '../api/recommendations';

export function RecommendationsScreen({ project, authToken }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRecommendations();
  }, [project]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      const results = await getRecommendations({
        title: project.title,
        description: project.description,
        technologies: project.technologies.join(', '),
        project_id: project.id,
        max_recommendations: 10,
        engine_preference: 'auto',
      }, authToken);
      
      setRecommendations(results);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      {loading ? (
        <ActivityIndicator size="large" />
      ) : (
        <FlatList
          data={recommendations}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <RecommendationCard 
              recommendation={item}
              onPress={() => handleRecommendationPress(item)}
            />
          )}
        />
      )}
    </View>
  );
}
```

---

### 2. User Feedback Tracking (Learn from Interactions)

Track user interactions to personalize future recommendations:

```typescript
// api/feedback.ts
export type FeedbackType = 
  | 'clicked' 
  | 'saved' 
  | 'dismissed' 
  | 'not_relevant' 
  | 'helpful' 
  | 'completed';

interface FeedbackRequest {
  content_id: number;
  feedback_type: FeedbackType;
  context_data?: {
    query?: string;
    project_id?: number;
    user_notes?: string;
  };
}

export async function submitFeedback(
  feedback: FeedbackRequest,
  authToken: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/enhanced/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify(feedback),
  });

  if (!response.ok) {
    throw new Error(`Feedback submission failed: ${response.status}`);
  }
}
```

**Usage Example:**

```typescript
// components/RecommendationCard.tsx
import React from 'react';
import { View, Text, TouchableOpacity, Linking } from 'react-native';
import { submitFeedback } from '../api/feedback';

export function RecommendationCard({ recommendation, authToken, projectId }) {
  const handlePress = async () => {
    // Track click
    await submitFeedback({
      content_id: recommendation.id,
      feedback_type: 'clicked',
      context_data: {
        project_id: projectId,
      }
    }, authToken);

    // Open link
    Linking.openURL(recommendation.url);
  };

  const handleSave = async () => {
    // Track save
    await submitFeedback({
      content_id: recommendation.id,
      feedback_type: 'saved',
      context_data: {
        project_id: projectId,
      }
    }, authToken);

    // Add to saved items
    // ... your save logic
  };

  const handleDismiss = async () => {
    // Track dismiss
    await submitFeedback({
      content_id: recommendation.id,
      feedback_type: 'dismissed',
      context_data: {
        project_id: projectId,
      }
    }, authToken);
  };

  return (
    <View style={styles.card}>
      <TouchableOpacity onPress={handlePress}>
        <Text style={styles.title}>{recommendation.title}</Text>
        
        {/* 🤖 GEMINI-POWERED EXPLANATION */}
        <Text style={styles.reason}>{recommendation.reason}</Text>
        
        <View style={styles.metadata}>
          <Text>Score: {Math.round(recommendation.score)}</Text>
          <Text>Difficulty: {recommendation.difficulty}</Text>
          <Text>Quality: {recommendation.quality_score}/10</Text>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity onPress={handleSave}>
            <Text>💾 Save</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleDismiss}>
            <Text>🚫 Not Relevant</Text>
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    </View>
  );
}
```

---

### 3. Skill Gap Analysis

Analyze user's current skills vs. target technologies and get learning paths:

```typescript
// api/skillGap.ts
interface SkillGapRequest {
  current_skills: string[];
  target_technologies: string[];
  learning_style?: 'visual' | 'hands-on' | 'theoretical' | 'mixed';
  time_available?: 'limited' | 'moderate' | 'extensive';
}

interface SkillGapAnalysis {
  gaps: {
    technology: string;
    importance: string;  // 'critical' | 'important' | 'nice-to-have'
    estimated_learning_time: string;
    prerequisites: string[];
    learning_path: {
      stage: string;
      content_types: string[];
      estimated_time: string;
    }[];
  }[];
  recommendations: Recommendation[];
  learning_roadmap: {
    phase: number;
    technologies: string[];
    duration: string;
    goals: string[];
  }[];
}

export async function analyzeSkillGaps(
  request: SkillGapRequest,
  authToken: string
): Promise<SkillGapAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/enhanced/skill-gaps`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Skill gap analysis failed: ${response.status}`);
  }

  return await response.json();
}
```

**Usage Example:**

```typescript
// screens/LearningPathScreen.tsx
import React, { useState } from 'react';
import { View, Text, Button } from 'react-native';
import { analyzeSkillGaps } from '../api/skillGap';

export function LearningPathScreen({ project, user, authToken }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzePath = async () => {
    setLoading(true);
    try {
      const result = await analyzeSkillGaps({
        current_skills: user.skills,
        target_technologies: project.technologies,
        learning_style: user.learningStyle || 'mixed',
        time_available: 'moderate',
      }, authToken);
      
      setAnalysis(result);
    } catch (error) {
      console.error('Skill gap analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <Button title="Analyze My Learning Path" onPress={analyzePath} />
      
      {analysis && (
        <View>
          <Text style={styles.heading}>Your Learning Roadmap</Text>
          
          {/* Show skill gaps */}
          {analysis.gaps.map((gap, index) => (
            <View key={index} style={styles.gapCard}>
              <Text style={styles.techName}>{gap.technology}</Text>
              <Text>Importance: {gap.importance}</Text>
              <Text>Time: {gap.estimated_learning_time}</Text>
              
              {gap.learning_path.map((stage, idx) => (
                <View key={idx} style={styles.stage}>
                  <Text>{stage.stage}</Text>
                  <Text>{stage.estimated_time}</Text>
                </View>
              ))}
            </View>
          ))}

          {/* Show personalized recommendations for each gap */}
          <Text style={styles.heading}>Recommended Learning Resources</Text>
          {analysis.recommendations.map((rec) => (
            <RecommendationCard 
              key={rec.id}
              recommendation={rec}
              authToken={authToken}
            />
          ))}
        </View>
      )}
    </View>
  );
}
```

---

### 4. Detailed Explanation (On-Demand)

Get in-depth Gemini-powered explanation for a specific recommendation:

```typescript
// api/explanation.ts
interface DetailedExplanation {
  overall_score: number;
  confidence: string;  // 'high' | 'medium' | 'moderate' | 'low'
  breakdown: {
    technology_match: {
      score: number;
      weight: number;
      contribution: number;
      explanation: string;
    };
    semantic_relevance: {
      score: number;
      weight: number;
      contribution: number;
      explanation: string;
    };
    // ... other components
  };
  why_recommended: string;  // 🤖 Gemini-generated natural language
  key_strengths: string[];
  considerations: string[];
  score_distribution: Record<string, number>;
}

export async function getDetailedExplanation(
  recommendationId: number,
  context: {
    query?: string;
    project_id?: number;
  },
  authToken: string
): Promise<DetailedExplanation> {
  const response = await fetch(
    `${API_BASE_URL}/api/enhanced/explain-recommendation/${recommendationId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify(context),
    }
  );

  if (!response.ok) {
    throw new Error(`Explanation failed: ${response.status}`);
  }

  return await response.json();
}
```

**Usage Example:**

```typescript
// components/ExplanationModal.tsx
import React, { useState, useEffect } from 'react';
import { Modal, View, Text, ScrollView, Button } from 'react-native';
import { getDetailedExplanation } from '../api/explanation';

export function ExplanationModal({ recommendation, visible, onClose, authToken, projectId }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (visible) {
      loadExplanation();
    }
  }, [visible, recommendation.id]);

  const loadExplanation = async () => {
    setLoading(true);
    try {
      const result = await getDetailedExplanation(
        recommendation.id,
        { project_id: projectId },
        authToken
      );
      setExplanation(result);
    } catch (error) {
      console.error('Failed to load explanation:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} onRequestClose={onClose}>
      <ScrollView style={styles.modal}>
        <Text style={styles.title}>Why This Was Recommended</Text>

        {loading ? (
          <ActivityIndicator />
        ) : explanation ? (
          <>
            {/* Main Gemini explanation */}
            <View style={styles.section}>
              <Text style={styles.heading}>📖 Explanation</Text>
              <Text style={styles.explanation}>
                {explanation.why_recommended}
              </Text>
            </View>

            {/* Key strengths */}
            <View style={styles.section}>
              <Text style={styles.heading}>✨ Key Strengths</Text>
              {explanation.key_strengths.map((strength, idx) => (
                <Text key={idx}>• {strength}</Text>
              ))}
            </View>

            {/* Score breakdown */}
            <View style={styles.section}>
              <Text style={styles.heading}>📊 Score Breakdown</Text>
              <Text>Overall: {Math.round(explanation.overall_score * 100)}%</Text>
              <Text>Confidence: {explanation.confidence}</Text>
              
              {Object.entries(explanation.breakdown).map(([key, value]) => (
                <View key={key} style={styles.breakdownItem}>
                  <Text>{key}: {Math.round(value.score * 100)}%</Text>
                  <Text style={styles.small}>{value.explanation}</Text>
                </View>
              ))}
            </View>

            {/* Considerations */}
            {explanation.considerations.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.heading}>⚠️ Keep in Mind</Text>
                {explanation.considerations.map((consideration, idx) => (
                  <Text key={idx}>• {consideration}</Text>
                ))}
              </View>
            )}
          </>
        ) : (
          <Text>Failed to load explanation</Text>
        )}

        <Button title="Close" onPress={onClose} />
      </ScrollView>
    </Modal>
  );
}
```

---

### 5. User Insights & Preferences

Get insights about user's learning patterns:

```typescript
// api/insights.ts
interface UserInsights {
  total_interactions: number;
  learning_patterns: {
    preferred_content_types: { type: string; count: number }[];
    preferred_difficulties: { level: string; count: number }[];
    most_engaged_technologies: { tech: string; count: number }[];
  };
  completion_rate: number;
  average_quality_preference: number;
  recommendations: string[];
}

export async function getUserInsights(authToken: string): Promise<UserInsights> {
  const response = await fetch(`${API_BASE_URL}/api/enhanced/user-insights`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${authToken}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch insights: ${response.status}`);
  }

  return await response.json();
}
```

---

## 🎯 Best Practices

### 1. **Track All Interactions**

```typescript
// Every time user interacts, track it:
const trackInteraction = async (contentId, feedbackType, context) => {
  try {
    await submitFeedback({
      content_id: contentId,
      feedback_type: feedbackType,
      context_data: context,
    }, authToken);
  } catch (error) {
    // Fail silently - don't disrupt user experience
    console.error('Feedback tracking failed:', error);
  }
};
```

### 2. **Show Progressive Disclosure**

```typescript
// Start with main explanation, allow drill-down
<RecommendationCard recommendation={rec}>
  <Text>{rec.reason}</Text> {/* Main Gemini explanation */}
  
  <TouchableOpacity onPress={() => showDetailedExplanation(rec.id)}>
    <Text>🔍 Why was this recommended?</Text>
  </TouchableOpacity>
</RecommendationCard>
```

### 3. **Cache Aggressively**

```typescript
// Cache recommendations locally
import AsyncStorage from '@react-native-async-storage/async-storage';

const getCachedRecommendations = async (projectId) => {
  const cached = await AsyncStorage.getItem(`recs_${projectId}`);
  if (cached) {
    const { recommendations, timestamp } = JSON.parse(cached);
    // Cache valid for 5 minutes
    if (Date.now() - timestamp < 5 * 60 * 1000) {
      return recommendations;
    }
  }
  return null;
};

const cacheRecommendations = async (projectId, recommendations) => {
  await AsyncStorage.setItem(`recs_${projectId}`, JSON.stringify({
    recommendations,
    timestamp: Date.now(),
  }));
};
```

### 4. **Handle Loading States**

```typescript
const [loadingStates, setLoadingStates] = useState({
  recommendations: false,
  skillGap: false,
  explanation: false,
});

// Show specific loading indicators for different operations
```

### 5. **Error Handling**

```typescript
const handleError = (error, context) => {
  if (error.message.includes('401')) {
    // Re-authenticate
    navigation.navigate('Login');
  } else if (error.message.includes('429')) {
    // Rate limited
    showToast('Too many requests. Please wait a moment.');
  } else {
    // Generic error
    showToast(`Failed to ${context}. Please try again.`);
  }
};
```

---

## 🚀 Quick Start Checklist

- [ ] Integrate main recommendation endpoint with Gemini explanations
- [ ] Add feedback tracking on clicks, saves, dismissals
- [ ] Implement "Why this?" detailed explanation modal
- [ ] Add skill gap analysis to project setup flow
- [ ] Track completion of learning resources
- [ ] Show user insights in profile/settings
- [ ] Cache recommendations locally
- [ ] Handle loading and error states gracefully

---

## 📊 API Response Times

- **Main Recommendations**: 2-5s (fresh), <100ms (cached)
- **Feedback Submission**: <200ms
- **Skill Gap Analysis**: 3-7s (involves complex analysis)
- **Detailed Explanation**: 1-3s (Gemini generation)
- **User Insights**: <500ms

---

## 🔗 Available Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/recommendations/unified-orchestrator` | POST | Get recommendations (Gemini-powered) |
| `/api/enhanced/feedback` | POST | Track user interactions |
| `/api/enhanced/skill-gaps` | POST | Analyze skill gaps & learning paths |
| `/api/enhanced/explain-recommendation/<id>` | POST | Get detailed explanation |
| `/api/enhanced/user-insights` | GET | Get user learning patterns |
| `/api/enhanced/personalized-recommendations` | POST | Get personalized recs based on history |

---

## 💡 Example: Complete Flow

```typescript
// 1. User opens project
const recommendations = await getRecommendations({...});

// 2. User clicks a recommendation
await submitFeedback({ content_id: rec.id, feedback_type: 'clicked' });
Linking.openURL(rec.url);

// 3. User wants more details
const explanation = await getDetailedExplanation(rec.id, { project_id });

// 4. User saves for later
await submitFeedback({ content_id: rec.id, feedback_type: 'saved' });

// 5. After learning, user marks complete
await submitFeedback({ content_id: rec.id, feedback_type: 'completed' });

// 6. System learns from this interaction for future recommendations!
```

---

## 🎉 You're All Set!

Your recommendation system is now:
- ✅ Powered by Gemini AI for intelligent explanations
- ✅ Learning from user interactions
- ✅ Providing progressive learning paths
- ✅ Offering detailed transparency

Start integrating and watch your users engage more with personalized, AI-powered learning recommendations! 🚀
