# 🚀 Recommendation Engine Architecture Guide

## 📊 **Current Engine Status**

Based on your system, here are the **6 main engines** available:

### ✅ **Currently Active (Default)**
1. **Unified Orchestrator** - **PRIMARY** (Currently Used)
   - **Composition**: Contains 2 sub-engines
   - **Sub-engines**: 
     - `FastSemanticEngine` (Fast, lightweight)
     - `ContextAwareEngine` (Detailed, comprehensive)
   - **Selection**: Auto-selects based on request complexity

### 🔧 **Standalone Engines Available**
2. **Unified Engine** - Standalone version
3. **Smart Engine** - AI-powered recommendations
4. **Enhanced Engine** - Advanced features
5. **Phase 3 Engine** - Latest experimental features
6. **Fast Gemini Engine** - Gemini AI integration

---

## 🎯 **Default Engine: Unified Orchestrator**

### **What it contains:**
```
Unified Orchestrator
├── FastSemanticEngine (Primary for simple requests)
│   ├── Fast semantic similarity
│   ├── Technology overlap scoring
│   └── Project context boosting
└── ContextAwareEngine (Primary for complex requests)
    ├── Multi-component scoring
    ├── Difficulty matching
    ├── Content type analysis
    └── Detailed reasoning
```

### **Auto-Selection Logic:**
- **Simple Requests** → `FastSemanticEngine`
- **Complex Requests** → `ContextAwareEngine`

### **Complexity Assessment:**
- Title length > 50 chars
- Description length > 100 chars  
- Technologies > 3 items
- User interests > 50 chars

---

## 🔄 **How to Switch Engines**

### **Method 1: API Request Parameter**
```json
{
  "title": "React Project",
  "description": "Building a web app",
  "technologies": "React, JavaScript",
  "engine_preference": "fast",  // or "context", "auto"
  "project_id": 1
}
```

### **Method 2: Use Different Endpoints**
```bash
# Unified Orchestrator (Default)
POST /api/recommendations/unified-orchestrator

# Standalone Unified Engine
POST /api/recommendations/unified

# Smart Engine
POST /api/recommendations/smart-recommendations

# Enhanced Engine
POST /api/recommendations/enhanced

# Phase 3 Engine
POST /api/recommendations/phase3/recommendations

# Gemini Enhanced
POST /api/recommendations/gemini-enhanced
```

### **Method 3: Frontend Configuration**
In your frontend requests, add:
```javascript
const requestData = {
  // ... other data
  engine_preference: 'fast',  // 'fast', 'context', 'auto'
  // or use different endpoints
};
```

---

## 🎛️ **Engine Comparison**

| Engine | Speed | Accuracy | Features | Best For |
|--------|-------|----------|----------|----------|
| **FastSemantic** | ⚡⚡⚡ | ⭐⭐ | Basic similarity | Quick results |
| **ContextAware** | ⚡⚡ | ⭐⭐⭐⭐ | Multi-factor scoring | Complex projects |
| **Unified** | ⚡⚡ | ⭐⭐⭐ | Standard features | General use |
| **Smart** | ⚡ | ⭐⭐⭐⭐ | AI-powered | High accuracy |
| **Enhanced** | ⚡ | ⭐⭐⭐⭐⭐ | Advanced features | Best quality |
| **Phase 3** | ⚡ | ⭐⭐⭐⭐⭐ | Experimental | Latest features |
| **Fast Gemini** | ⚡ | ⭐⭐⭐⭐ | Gemini AI | AI-enhanced |

---

## 🚀 **Engine Selection Guide**

### **For Speed:**
```json
{
  "engine_preference": "fast"
}
```
- Uses `FastSemanticEngine`
- Best for simple queries
- Response time: ~100-300ms

### **For Accuracy:**
```json
{
  "engine_preference": "context"
}
```
- Uses `ContextAwareEngine`
- Best for complex projects
- Response time: ~300-800ms

### **For Auto-Selection:**
```json
{
  "engine_preference": "auto"
}
```
- Automatically chooses based on request complexity
- Best for general use
- Response time: Variable

### **For AI Enhancement:**
```json
{
  "enhance_with_gemini": true
}
```
- Adds Gemini AI analysis to any engine
- Enhanced reasoning and explanations
- Response time: +500-1000ms

---

## 🔧 **Advanced Configuration**

### **Engine-Specific Parameters:**
```json
{
  "engine_preference": "context",
  "diversity_weight": 0.3,
  "quality_threshold": 6,
  "max_recommendations": 10,
  "include_global_content": true
}
```

### **Performance Tuning:**
```json
{
  "engine_preference": "fast",
  "quality_threshold": 8,  // Higher quality filter
  "max_recommendations": 5  // Fewer but better results
}
```

---

## 📈 **Performance Monitoring**

### **Check Engine Status:**
```bash
GET /api/recommendations/status
```

### **Get Performance Metrics:**
```bash
GET /api/recommendations/performance-metrics
```

### **Monitor Cache Performance:**
- Cache hit rate
- Response times
- Engine usage statistics

---

## 🎯 **Recommended Usage**

### **For Project Pages:**
```json
{
  "engine_preference": "context",
  "enhance_with_gemini": true,
  "project_id": 1
}
```

### **For Dashboard:**
```json
{
  "engine_preference": "fast",
  "max_recommendations": 5
}
```

### **For Learning Paths:**
```json
{
  "engine_preference": "context",
  "diversity_weight": 0.5
}
```

---

## 🔄 **Switching Engines in Frontend**

### **In Recommendations.jsx:**
```javascript
const fetchRecommendations = async () => {
  const response = await api.post('/api/recommendations/unified-orchestrator', {
    // ... other data
    engine_preference: 'context',  // Change this to switch engines
    enhance_with_gemini: true
  });
};
```

### **In ProjectDetail.jsx:**
```javascript
const fetchProjectData = async () => {
  const recommendationsRes = await api.post('/api/recommendations/unified-orchestrator', {
    // ... project data
    engine_preference: 'context',  // Best for project-specific recommendations
    enhance_with_gemini: true
  });
};
```

---

## 🎉 **Current Default Configuration**

Your system is currently using the **Unified Orchestrator** which:
- ✅ **Auto-selects** between Fast and Context engines
- ✅ **Boosts project-relevant** content
- ✅ **Provides caching** for performance
- ✅ **Supports Gemini enhancement**
- ✅ **Tracks performance metrics**

This is the **optimal configuration** for most use cases! 🚀 