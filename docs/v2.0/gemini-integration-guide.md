# Gemini Integration Guide for LightRAG v2.0

## Overview

This document provides comprehensive documentation for the complete Google Gemini integration implemented in LightRAG v2.0. While the integration is fully functional, it is **not recommended for production use** due to output consistency issues with structured format adherence and tool usage that are critical for knowledge graph applications.

## ⚠️ Production Recommendation

**Status: Implemented but Not Recommended for Production**

The Gemini integration was completed and tested but revealed significant issues:
- **Inconsistent output parsing** with structured formats
- **Poor adherence to prompt formatting** requirements
- **Unreliable tool usage** behavior
- **Variable quality** in entity/relationship extraction

For production use, **OpenAI GPT-4.1-mini remains the recommended LLM** for maintaining the 52% entity reduction and 29% unique entity discovery achievements with gamified prompts.

## Technical Implementation

### Architecture Overview

The integration uses Google's new unified Gen AI SDK (`google-genai`) which replaces the deprecated `google-generativeai` package and supports both:
- **Gemini Developer API** (for development/testing)
- **Vertex AI** (for enterprise deployment)

### Files Modified/Created

#### 1. Core Gemini Implementation
**File**: `lightrag/llm/gemini.py`
- Complete LLM and embedding functions using new unified SDK
- Support for both Developer API and Vertex AI
- Async implementation with retry logic
- Streaming support for real-time applications

#### 2. Configuration System Updates
**File**: `lightrag/api/config.py`
- Added "gemini" to supported LLM bindings
- Added "gemini" to supported embedding bindings  
- Default host configuration for Gemini API
- Environment variable integration

#### 3. API Server Integration
**File**: `lightrag/api/lightrag_server.py`
- Gemini binding validation
- Dynamic import system for Gemini modules
- RAG initialization with Gemini model function
- Enhanced logging for Gemini usage
- Embedding function integration

#### 4. Enhanced Logging
**File**: `lightrag/api/utils_api.py`
- Visual indicators for Gemini configuration in splash screen
- Color-coded display for Gemini binding
- Enhanced startup logging

## Configuration

### Environment Variables

#### Basic Gemini Configuration
```bash
# Primary LLM Configuration
LLM_BINDING=gemini
LLM_MODEL=gemini-2.5-flash
LLM_BINDING_HOST=https://generativelanguage.googleapis.com
LLM_BINDING_API_KEY=your-gemini-api-key-here

# Optional: Embedding with Gemini
EMBEDDING_BINDING=gemini
EMBEDDING_MODEL=text-embedding-004
```

#### Advanced Configuration
```bash
# Use Vertex AI instead of Developer API
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Performance tuning
MAX_TOKENS=32768
MAX_ASYNC=4
TEMPERATURE=0.1
```

### Supported Models
- **LLM Models**: `gemini-2.5-flash`, `gemini-pro`, `gemini-pro-vision`
- **Embedding Models**: `text-embedding-004`, `textembedding-gecko`

## API Usage

### Developer API Setup
```python
# Automatic configuration via environment
rag = LightRAG(
    working_dir="./knowledge_graph",
    llm_model_func=gemini_model_complete,
    embedding_func=gemini_embedding_func
)
```

### Vertex AI Setup
```python
# Set environment variables for Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "your-project"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# Initialize with same code
rag = LightRAG(...)
```

## Integration Features

### 1. Unified SDK Architecture
- Single codebase for both Developer API and Vertex AI
- Automatic failover and retry logic
- Native async/await support
- Built-in rate limiting

### 2. Gamified Prompt Preservation
- Full compatibility with existing gamified prompt system
- Maintains cognitive framing optimizations
- Preserves "Master Scout" tactical intelligence approach
- No modifications required to prompt templates

### 3. Enhanced Logging System
```bash
# Example startup logs with Gemini
🚀 Loading Gemini integration with new unified Google Gen AI SDK...
✅ Gemini integration loaded successfully
🤖 Initializing LightRAG with Gemini gemini-2.5-flash (preserving gamified prompts)
🤖 Using Gemini Developer API with model: gemini-2.5-flash
```

### 4. Streaming Support
```python
# Real-time response streaming
async for chunk in gemini_complete_stream(
    model="gemini-2.5-flash",
    prompt="Your query here",
    system_prompt="System instructions"
):
    print(chunk, end="", flush=True)
```

## Performance Characteristics

### Theoretical Benefits
- **Speed**: Gemini 2.5 Flash optimized for low latency
- **Context**: Larger context windows (up to 32k tokens)
- **Cost**: Potentially lower costs than OpenAI
- **Scale**: Google's infrastructure for high-volume processing

### Observed Issues
- **Consistency**: Variable adherence to structured output formats
- **Parsing**: Difficulty with complex JSON/structured responses
- **Entity Extraction**: Inconsistent entity/relationship identification
- **Tool Usage**: Poor performance with function calling

## Testing Results

### Integration Test
```bash
# Test Gemini API connection
python test_gemini_integration.py

# Expected output:
🔗 Testing Gemini API Connection...
✅ API Response: Gemini API working correctly!
✅ Embedding Shape: (1, 768)
```

### Performance Comparison Framework
```python
# A/B testing against OpenAI baseline
async def performance_comparison():
    results = {
        "gemini": {"entities": 0, "relationships": 0, "query_times": []},
        "openai": {"entities": 165, "relationships": 123, "query_times": []}
    }
    # Implementation in test files
```

## Installation Requirements

### Dependencies
```bash
# Core requirement
pip install google-genai

# Optional for faster async performance
pip install google-genai[aiohttp]

# For Vertex AI authentication
pip install google-auth google-auth-oauthlib
```

### Authentication Setup

#### Developer API
```bash
# Get API key from https://aistudio.google.com/app/apikey
export GEMINI_API_KEY="your-api-key-here"
```

#### Vertex AI
```bash
# Install Google Cloud SDK
gcloud auth application-default login

# Or use service account
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

## Migration Guide

### From OpenAI to Gemini
```bash
# 1. Comment out OpenAI configuration
#LLM_BINDING=openai
#LLM_MODEL=gpt-4.1-mini

# 2. Enable Gemini configuration
LLM_BINDING=gemini
LLM_MODEL=gemini-2.5-flash
LLM_BINDING_API_KEY=your-gemini-key

# 3. Restart server
python lightrag/api/lightrag_server.py
```

### Rollback Strategy
```bash
# Keep OpenAI as fallback
LLM_BINDING=openai  # Change back to openai
# Restart server - no code changes needed
```

## Troubleshooting

### Common Issues

#### 1. SDK Installation Problems
```bash
# Force reinstall
pip uninstall google-genai
pip install google-genai --force-reinstall
```

#### 2. Authentication Errors
```bash
# Verify API key
export GEMINI_API_KEY="your-key"
python -c "import os; print('Key:', os.getenv('GEMINI_API_KEY')[:10] + '...')"
```

#### 3. Output Format Issues
```bash
# Increase temperature for more consistent outputs
TEMPERATURE=0.0  # More deterministic
TEMPERATURE=0.3  # More creative but less consistent
```

### Performance Monitoring
```python
# Monitor response quality
def validate_response_format(response):
    try:
        # Check for proper JSON structure
        parsed = json.loads(response)
        return "entities" in parsed and "relationships" in parsed
    except:
        return False
```

## Code Examples

### Basic Usage
```python
from lightrag.llm.gemini import gemini_complete_if_cache

response = await gemini_complete_if_cache(
    model="gemini-2.5-flash",
    prompt="Extract entities from: Jason used n8n for automation",
    system_prompt="You are a knowledge graph expert.",
    temperature=0.1
)
```

### Advanced Configuration
```python
# Custom client configuration
client = genai.Client(
    api_key="your-key",
    http_options=types.HttpOptions(
        api_version="v1",
        timeout=30.0
    )
)
```

## Future Considerations

### When to Revisit Gemini
1. **Improved structured output**: When Google enhances format adherence
2. **Better tool usage**: When function calling becomes more reliable
3. **Cost advantages**: If pricing becomes significantly more attractive
4. **Performance improvements**: When speed/quality trade-offs improve

### Monitoring Improvements
- Track Google's Gemini API updates
- Monitor community feedback on structured outputs
- Test new model versions (Gemini 3.0+)
- Evaluate enterprise Vertex AI features

## Summary

The Gemini integration is **complete and functional** but **not recommended for production** due to output consistency issues critical for knowledge graph applications. The implementation provides:

✅ **Complete integration** with new unified Google Gen AI SDK
✅ **Full compatibility** with existing gamified prompt optimizations  
✅ **Enterprise-ready** Vertex AI support
✅ **Comprehensive logging** and monitoring
✅ **Easy migration** path when ready

❌ **Output inconsistency** makes it unsuitable for production
❌ **Structured format adherence** issues
❌ **Tool usage reliability** problems

**Recommendation**: Keep OpenAI GPT-4.1-mini for production while monitoring Gemini improvements for future migration.