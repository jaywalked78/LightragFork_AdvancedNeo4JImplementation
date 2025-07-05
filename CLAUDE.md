# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is LightRAG v2.0.0 Production Ready - an advanced knowledge graph-based Retrieval-Augmented Generation system with sophisticated semantic relationship extraction, multi-database support, and comprehensive document management capabilities.

## Core Development Commands

### Python Environment Setup
```bash
# Install with basic functionality
pip install -e .

# Install with API server support
pip install -e ".[api]"

# Install with visualization tools
pip install -e ".[tools]"
```

### Running the Application

#### LightRAG Server (API + Web UI)
```bash
# Standard run
python lightrag/api/lightrag_server.py

# With Gunicorn (production)
python lightrag/api/run_with_gunicorn.py

# Docker Compose
docker compose up

# Entry points (if installed)
lightrag-server
lightrag-gunicorn
```

#### Web UI Development
```bash
cd lightrag_webui

# Development (with Bun - preferred)
bun run dev

# Development (with Node)
npm run dev-no-bun

# Build
bun run build
# or
npm run build-no-bun

# Lint
npm run lint
```

### Testing
```bash
# Run basic tests
python tests/test_graph_storage.py

# Test specific storage implementations
python tests/test_lightrag_ollama_chat.py

# General Python testing (if pytest is available)
pytest tests/
```

### Linting and Code Quality
```bash
# Web UI linting
cd lightrag_webui
npm run lint

# Python code formatting (if available)
black lightrag/
ruff lightrag/
```

## Architecture Overview

### Core Components

#### 1. LightRAG Engine (`lightrag/`)
- **`lightrag.py`** - Main LightRAG class and core functionality
- **`operate.py`** - Core document processing and relationship extraction (contains critical v2.0 fixes)
- **`advanced_lightrag.py`** - Production-ready wrapper with enhanced logging and metrics
- **`advanced_operate.py`** - Enhanced query operations with detailed tracking

#### 2. Knowledge Graph Storage (`lightrag/kg/`)
- **Multi-storage support**: NetworkX, Neo4j, PostgreSQL, Redis, MongoDB, Qdrant, etc.
- **`neo4j_impl.py`** - Neo4j graph storage with cascade delete support
- **`postgres_impl.py`** - PostgreSQL storage with multi-table management
- **`shared_storage.py`** - Shared storage utilities and pipeline status management

#### 3. Large Language Model Integration (`lightrag/llm/`)
- **Support for**: OpenAI, Anthropic, Ollama, HuggingFace, Azure, Bedrock, etc.
- **`anthropic.py`** - Enhanced with VoyageAI embedding integration
- **`llama_index_impl.py`** - LlamaIndex integration for broader LLM support

#### 4. API Server (`lightrag/api/`)
- **`lightrag_server.py`** - FastAPI-based server with comprehensive endpoints
- **`routers/document_routes.py`** - Document management with multi-database cascade delete
- **`routers/graph_routes.py`** - Graph visualization and export endpoints
- **`routers/query_routes.py`** - Query processing and retrieval endpoints

#### 5. Web UI (`lightrag_webui/`)
- **React + TypeScript** application with modern UI components
- **Real-time graph visualization** with Sigma.js
- **Document management** with batch operations and progress tracking
- **Multi-language support** (English, Chinese, Arabic, French)

### Version 2.0 Key Features

#### Semantic Relationship Preservation System
- **Fixed critical bug** that converted all relationships to generic "related"
- **96.8% relationship retention** with 100% semantic type preservation
- **35+ specific relationship types** maintained throughout processing pipeline
- **File**: `lightrag/operate.py:309` - Critical field assignment fix

#### Post-Processing Cache System
- **60-80% cost reduction** in LLM calls during reprocessing
- **Content-based caching** for chunk-level validation
- **Intelligent cache invalidation** based on content changes
- **Configuration**: `ENABLE_LLM_CACHE_FOR_POST_PROCESS=true`

#### Multi-Database Cascade Delete
- **PostgreSQL support** with custom stored functions
- **Neo4j support** with Cypher-based cleanup
- **Multi-document entity management** - preserves shared entities
- **API endpoints**: `DELETE /documents/{doc_id}` and `DELETE /documents/batch`

#### Enhanced Prompt Engineering
- **Domain-specific prompts** in `lightrag/prompt.py`
- **Generic template** in `lightrag/genericPrompt.py` for customization
- **Claude-assisted customization** workflow for different domains

## Configuration Management

### Environment Variables (`.env`)
```bash
# LLM Configuration
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=your_database

NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# V2.0 Feature Toggles
ENABLE_LLM_POST_PROCESSING=false          # Full document LLM post-processing
ENABLE_CHUNK_POST_PROCESSING=true         # Chunk-level post-processing (recommended)
ENABLE_LLM_CACHE_FOR_POST_PROCESS=true    # Cost optimization caching
ENABLE_ENTITY_CLEANUP=true                # Orphaned entity cleanup

# Performance Tuning
MAX_TOKENS=32768
MAX_ASYNC=4
TOP_K=60
COSINE_THRESHOLD=0.2
```

### Storage Configuration Patterns
```python
# Multi-database setup
rag = LightRAG(
    working_dir="./knowledge_graph",
    llm_model_func=your_llm_function,
    embedding_func=your_embedding_function,
    
    # Storage backends
    graph_storage="Neo4JStorage",
    vector_storage="PGVectorStorage", 
    kv_storage="PGKVStorage",
    doc_status_storage="PGDocStatusStorage",
    
    # V2.0 semantic preservation
    enable_llm_post_processing=True,
    enable_llm_cache_for_post_process=True,
    enable_chunk_post_processing=True
)
```

## Development Workflows

### Domain-Specific Customization
```bash
# 1. Switch to generic prompts
cp lightrag/genericPrompt.py lightrag/prompt.py

# 2. Use Claude to customize for your domain:
# "Here is the genericPrompt.py file and information about my domain: [details].
#  Please rewrite this to be hyper-focused on [use case], keeping the exact 
#  same structure but changing examples and terminology to match my data."
```

### Adding New Storage Backends
1. Implement in `lightrag/kg/` following existing patterns
2. Add to `STORAGE_IMPLEMENTATIONS` mapping
3. Define environment requirements in `STORAGE_ENV_REQUIREMENTS`
4. Test with `tests/test_graph_storage.py`

### API Endpoint Development
1. Add routes in appropriate `lightrag/api/routers/` file
2. Update response models if needed
3. Test with the Web UI or API clients
4. Document in API schema

### Web UI Feature Development
```bash
cd lightrag_webui

# Start development server
bun run dev

# Key directories:
# src/features/ - Main application features
# src/components/ - Reusable UI components  
# src/api/ - API client functions
# src/locales/ - Internationalization files
```

## Common Integration Patterns

### Basic Document Processing
```python
# Initialize with v2.0 features
rag = await initialize_rag()

# Process documents with semantic preservation
await rag.ainsert("Your document content")

# Query with maintained relationships
result = await rag.aquery("How does X integrate with Y?")
```

### Multi-Database Document Deletion
```python
# Individual deletion with cascade cleanup
response = await delete_document(doc_id="doc-123", file_name="document.pdf")

# Batch deletion with progress tracking
response = await delete_documents_batch([
    {"doc_id": "doc-1", "file_name": "file1.pdf"},
    {"doc_id": "doc-2", "file_name": "file2.pdf"}
])
```

### Custom Knowledge Graph Integration
```python
# Insert custom entities and relationships
custom_kg = {
    "entities": [...],
    "relationships": [...],
    "chunks": [...]
}
rag.insert_custom_kg(custom_kg)
```

## Troubleshooting

### Version 2.0 Specific Issues
- **Relationship types becoming "related"**: Ensure `enable_chunk_post_processing=True`
- **High LLM costs**: Enable `enable_llm_cache_for_post_process=True`
- **Document deletion failures**: Check database connections and cascade delete functions
- **Graph visualization issues**: Verify multiple documents are loaded and Neo4j connection

### Performance Optimization
- Use chunk-level post-processing over full document processing
- Enable LLM caching for cost reduction
- Tune `MAX_ASYNC` and batch sizes based on your LLM provider limits
- Use PostgreSQL indexes for large datasets (see docs/v2.0/ guides)

### Database Setup
- **PostgreSQL**: Install custom cascade delete functions from docs/v2.0/
- **Neo4j**: Create appropriate indexes for performance
- **Multi-database**: Ensure both systems are properly configured

## Key Files for Understanding

1. **`PR_SUMMARY.md`** - Complete changelog and technical details for v2.0
2. **`lightrag/operate.py:309`** - Critical relationship type preservation fix
3. **`lightrag/prompt.py`** vs **`lightrag/genericPrompt.py`** - Domain customization approach
4. **`lightrag/api/routers/document_routes.py`** - Multi-database deletion implementation
5. **`docs/v2.0/`** - Implementation guides for all major v2.0 features

This is a production-ready system with sophisticated relationship extraction, comprehensive database management, and enterprise-grade features for knowledge graph applications.