# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python Package Development
```bash
# Install for development (from repository root)
pip install -e .                    # Core library only
pip install -e ".[api]"            # With API server support
pip install -e ".[tools]"          # With visualization tools

# Code quality
pre-commit run --all-files         # Run all pre-commit hooks
ruff format .                      # Format code
ruff check . --fix                 # Lint and auto-fix issues
```

### WebUI Development
```bash
cd lightrag_webui
bun install                        # Install dependencies
bun run dev                        # Start development server
bun run build                      # Production build
bun run lint                       # Lint TypeScript/React code
```

### Running Services
```bash
# API Server
lightrag-server                    # Run FastAPI server (after pip install -e ".[api]")
lightrag-gunicorn                  # Run with Gunicorn for production

# Visualization
lightrag-viewer                    # Run graph visualizer tool

# Docker
docker compose up                  # Run complete stack (requires .env file)
```

## Architecture Overview

LightRAG is a modular RAG (Retrieval-Augmented Generation) system with pluggable storage backends and LLM providers. This enhanced fork includes production improvements and relationship type fixes.

### Core Modules

**lightrag/lightrag.py**
- Main `LightRAG` class orchestrating the entire RAG pipeline
- Handles document insertion, querying, and knowledge graph management
- Key methods: `insert()`, `query()`, `ainsert()`, `aquery()`

**lightrag/operate.py**
- Core operations for knowledge extraction and query processing
- Implements chunking, entity/relationship extraction, and retrieval strategies
- Uses prompts from `lightrag/prompt.py` for LLM interactions

**lightrag/kg/** (Knowledge Graph Storage)
- Abstract base classes in parent directory define storage interfaces
- Implementations for Neo4j, PostgreSQL+AGE, MongoDB, NetworkX, etc.
- Each implementation handles graph, vector, KV, and document storage
- Recent fixes: Neo4j relationship type standardization and visualization

**lightrag/llm/** (LLM Integrations)
- Modular LLM providers: OpenAI, Anthropic, Ollama, HuggingFace, etc.
- Each module implements async methods for chat completions and embeddings
- Uses `lightrag/llm_resilience.py` for retry logic and error handling

**lightrag/api/** (FastAPI Server)
- REST API with routes for documents, queries, and graph operations
- Includes WebUI served at root path
- Authentication support via API keys
- Health monitoring and status endpoints

### Storage Architecture

The system uses four types of storage, each with multiple backend options:
1. **Graph Storage**: Stores entities and relationships
2. **Vector Storage**: Stores embeddings for similarity search
3. **KV Storage**: Stores intermediate results and metadata
4. **Document Storage**: Tracks document processing status

### Key Design Patterns

- **Async-First**: All core operations use async/await
- **Storage Abstraction**: Clean interfaces allow swapping backends
- **Prompt Engineering**: Structured prompts in `prompt.py` for consistent LLM outputs
- **Error Resilience**: Retry logic and graceful degradation throughout

### Recent Enhancements (This Fork)

1. **Relationship Type Fix**: Standardizes multi-word relationships to underscore format
2. **Neo4j Improvements**: Fixed edge visualization and connection handling
3. **Production Features**: Health monitoring, better error messages, connection pooling
4. **WebUI Enhancements**: Improved graph visualization with Sigma.js

### Development Notes

- Python >= 3.9 required
- Uses pre-commit hooks with Ruff for code quality
- Environment variables configure LLM providers and storage backends
- WebUI uses React 19 + TypeScript + Vite + Tailwind CSS
- Limited test coverage - focus on integration tests when adding features