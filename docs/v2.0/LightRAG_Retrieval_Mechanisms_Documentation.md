# LightRAG v2.0 Retrieval Mechanisms Documentation

## Overview

LightRAG v2.0 implements a sophisticated multi-database retrieval system that combines **Neo4j** for knowledge graph storage and **PostgreSQL** for vector embeddings, text chunks, and metadata storage. This document details the complete retrieval flow from initial query to streaming response.

## Architecture Components

### Database Roles

1. **Neo4j Graph Database**
   - Stores entities and relationships in a graph structure
   - Handles graph traversal queries and relationship discovery
   - Provides degree calculations for ranking nodes and edges

2. **PostgreSQL Database**
   - Stores vector embeddings for semantic similarity search
   - Manages text chunks and document metadata
   - Handles full-text storage and LLM response caching

### Key Storage Classes

- `Neo4JStorage`: Graph database operations (lightrag/kg/neo4j_impl.py)
- `PGVectorStorage`: Vector similarity search (lightrag/kg/postgres_impl.py)
- `PGKVStorage`: Key-value document storage (lightrag/kg/postgres_impl.py)

## Query Processing Flow

### 1. Initial Query Processing (lightrag/api/routers/query_routes.py)

```python
# Entry points
@router.post("/query")                    # Non-streaming endpoint
@router.post("/query/stream")             # Streaming endpoint

# Request processing
async def query_text_stream(request: QueryRequest):
    param = request.to_query_params(True)  # Convert to QueryParam
    response = await rag.aquery(request.query, param=param)
```

**Query Parameters:**
- `mode`: "local", "global", "hybrid", "naive", "mix", "bypass"
- `top_k`: Number of top results to retrieve
- `max_token_for_text_unit`: Token limit for text chunks
- `max_token_for_global_context`: Token limit for relationships
- `max_token_for_local_context`: Token limit for entities

### 2. Core Query Routing (lightrag/lightrag.py:aquery)

The main `aquery` method routes queries based on mode:

```python
async def aquery(self, query: str, param: QueryParam = QueryParam()) -> Any:
    if param.mode == "naive":
        return await naive_query(query, self.chunks_vdb, param)
    elif param.mode == "local":
        return await kg_query(query, self.knowledge_graph_inst, self.entities_vdb, 
                             self.text_chunks, param)
    elif param.mode == "global":
        return await kg_query(query, self.knowledge_graph_inst, self.relationships_vdb,
                             self.text_chunks, param)
    elif param.mode == "hybrid":
        return await kg_query(query, self.knowledge_graph_inst, 
                             [self.entities_vdb, self.relationships_vdb],
                             self.text_chunks, param)
```

### 3. Knowledge Graph Query Processing (lightrag/operate.py)

#### Main Query Function: `kg_query`

```python
async def kg_query(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage | list[BaseVectorStorage],
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
) -> str | AsyncIterator[str]:
```

**Query Flow:**
1. **Keyword Extraction**: Extract high-level and low-level keywords from query
2. **Parallel Retrieval**: Execute entity and relationship queries concurrently
3. **Data Aggregation**: Combine results from multiple sources
4. **Context Generation**: Format results for LLM processing

#### Keyword Extraction Process

```python
# Extract keywords using LLM
keywords_extraction_func = partial(
    use_llm_func_with_cache,
    llm_response_cache=llm_response_cache,
    global_config=entities_vdb.global_config,
)

# Get high-level and low-level keywords
kw_prompt = PROMPTS["keywords_extraction"].format(
    query=query, 
    examples=PROMPTS["keywords_extraction_examples"]
)
```

## Database Query Operations

### Neo4j Graph Queries (lightrag/kg/neo4j_impl.py)

#### 1. Entity Retrieval
```cypher
-- Get node by entity ID
MATCH (n:base {entity_id: $entity_id}) RETURN n

-- Get multiple nodes (batch operation)
MATCH (n:base) WHERE n.entity_id IN $entity_ids RETURN n
```

#### 2. Relationship Retrieval
```cypher
-- Get edge between two entities
MATCH (a:base {entity_id: $src_id})-[r]->(b:base {entity_id: $tgt_id}) 
RETURN r

-- Get relationships for multiple entity pairs
MATCH (a:base)-[r]->(b:base) 
WHERE (a.entity_id, b.entity_id) IN $edge_pairs 
RETURN a.entity_id, b.entity_id, r
```

#### 3. Graph Traversal for Related Entities
```cypher
-- Find entities related to a list of entity IDs
MATCH (n:base)-[r]-(m:base) 
WHERE n.entity_id IN $entity_ids 
RETURN DISTINCT m.entity_id, m.entity_name, m.entity_type, m.description
```

#### 4. Degree Calculations
```cypher
-- Calculate node degrees (for ranking)
MATCH (n:base {entity_id: $entity_id}) 
OPTIONAL MATCH (n)-[r]-() 
RETURN count(r) as degree

-- Calculate edge degrees (relationship strength)
MATCH (a:base {entity_id: $src_id})-[r]-(n)-[r2]-(b:base {entity_id: $tgt_id}) 
RETURN count(r) + count(r2) as edge_degree
```

### PostgreSQL Vector Queries (lightrag/kg/postgres_impl.py)

#### 1. Vector Similarity Search
```sql
-- Entity vector similarity search
SELECT *, content_vector <=> $1::vector as distance 
FROM lightrag_vdb_entity 
WHERE workspace = $2 
ORDER BY content_vector <=> $1::vector 
LIMIT $3

-- Relationship vector similarity search  
SELECT *, content_vector <=> $1::vector as distance
FROM lightrag_vdb_relationships 
WHERE workspace = $2
ORDER BY content_vector <=> $1::vector
LIMIT $3
```

#### 2. Text Chunk Retrieval
```sql
-- Get text chunks by IDs
SELECT *, EXTRACT(EPOCH FROM create_time)::BIGINT as created_at 
FROM lightrag_kv_text_chunks 
WHERE workspace = $1 AND id IN ($2, $3, ...)

-- Get document content
SELECT * FROM lightrag_kv_doc_full 
WHERE workspace = $1 AND id = $2
```

#### 3. Cache Operations
```sql
-- LLM response cache lookup
SELECT * FROM lightrag_kv_llm_response_cache 
WHERE workspace = $1 AND mode = $2 AND id = $3

-- Document status tracking
SELECT * FROM TLL_LIGHTRAG_DOC_STATUS 
WHERE workspace = $1 AND id = ANY($2)
```

## Multi-Database Data Aggregation

### 1. Local Query (_get_node_data)

**Process:**
1. **Vector Search**: Query PostgreSQL for similar entities
```python
results = await entities_vdb.query(query, top_k=query_param.top_k)
```

2. **Graph Enrichment**: Get detailed entity data from Neo4j
```python
nodes_dict, degrees_dict = await asyncio.gather(
    knowledge_graph_inst.get_nodes_batch(node_ids),
    knowledge_graph_inst.node_degrees_batch(node_ids)
)
```

3. **Related Data Discovery**: Find connected relationships and text chunks
```python
use_relations = await _find_most_related_edges_from_entities(node_datas, query_param, knowledge_graph_inst)
use_text_units = await _find_most_related_text_unit_from_entities(node_datas, query_param, text_chunks_db)
```

### 2. Global Query (_get_edge_data)

**Process:**
1. **Relationship Vector Search**: Find similar relationships in PostgreSQL
```python
results = await relationships_vdb.query(keywords, top_k=query_param.top_k)
```

2. **Graph Data Enrichment**: Get relationship details from Neo4j
```python
edge_data_dict, edge_degrees_dict = await asyncio.gather(
    knowledge_graph_inst.get_edges_batch(edge_pairs_dicts),
    knowledge_graph_inst.edge_degrees_batch(edge_pairs_tuples)
)
```

3. **Entity Discovery**: Find entities connected to relationships
```python
use_entities = await _find_most_related_entities_from_relationships(edge_datas, query_param, knowledge_graph_inst)
```

### 3. Data Combination and Ranking

**Ranking Strategy:**
- **Entities**: Ranked by degree (number of connections) and vector similarity
- **Relationships**: Ranked by edge degree and relationship weight
- **Text Chunks**: Ranked by relevance to entities/relationships

**Token Management:**
```python
# Truncate results based on token limits
node_datas = truncate_list_by_token_size(
    node_datas,
    key=lambda x: x["description"],
    max_token_size=query_param.max_token_for_local_context,
    tokenizer=tokenizer
)
```

## Context Formation

### JSON Structure Generation

The system formats retrieved data into structured JSON for LLM processing:

```json
{
  "entities": [
    {
      "id": 1,
      "entity": "n8n",
      "type": "tool", 
      "description": "Workflow automation platform",
      "rank": 15,
      "created_at": "2024-01-15 10:30:00",
      "file_path": "workflow_docs.pdf"
    }
  ],
  "relationships": [
    {
      "id": 1,
      "entity1": "n8n",
      "entity2": "API",
      "description": "n8n integrates with external APIs",
      "keywords": ["integration", "automation"],
      "weight": 0.9,
      "rank": 8,
      "created_at": "2024-01-15 10:30:00"
    }
  ],
  "text_units": [
    {
      "id": 1,
      "content": "The workflow automation...",
      "tokens": 150,
      "full_doc_id": "doc-123",
      "chunk_order_index": 0
    }
  ]
}
```

## Response Generation and Streaming

### 1. LLM Response Generation

The formatted context is sent to the LLM with specialized prompts:

```python
# For hybrid/local/global queries
prompt = PROMPTS["rag_response"].format(
    context_data=formatted_context,
    query=query,
    response_type=query_param.response_type,
    history=conversation_history
)

# Generate response (streaming or non-streaming)
if query_param.stream:
    return llm_model_func(prompt, stream=True)
else:
    return await llm_model_func(prompt, stream=False)
```

### 2. Streaming Response Mechanism

**FastAPI Streaming Implementation:**
```python
async def stream_generator():
    if isinstance(response, str):
        # Cache hit - send immediately
        yield f"{json.dumps({'response': response})}\n"
    else:
        # Stream from LLM
        async for chunk in response:
            if chunk:
                yield f"{json.dumps({'response': chunk})}\n"

return StreamingResponse(
    stream_generator(),
    media_type="application/x-ndjson",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
)
```

### 3. Response Caching

**Cache Strategy:**
- **LLM Response Cache**: Stores complete responses for repeated queries
- **Processing Cache**: Caches intermediate processing results
- **Vector Cache**: Caches embedding computations

```python
# Cache lookup
cache_key = compute_args_hash(query, query_param)
cached_response = await llm_response_cache.get_by_id(cache_key)

if cached_response:
    return cached_response["return"]

# Cache storage after generation
await save_to_cache(
    cache_key, 
    response, 
    llm_response_cache, 
    global_config
)
```

## Query Mode Comparison

| Mode | Description | Neo4j Usage | PostgreSQL Usage | Best For |
|------|-------------|-------------|------------------|----------|
| **naive** | Simple text search | None | Vector search only | Basic similarity search |
| **local** | Entity-focused | Entity retrieval, relationship discovery | Entity vectors, text chunks | Entity-specific queries |
| **global** | Relationship-focused | Relationship retrieval, entity discovery | Relationship vectors, text chunks | Pattern and connection queries |
| **hybrid** | Combined approach | Both entity and relationship queries | All vector stores | Complex analytical queries |
| **mix** | Includes vector context | Graph operations | Full vector search + graph results | Comprehensive retrieval |

## Performance Optimizations

### 1. Batch Operations
- **Node Batch Retrieval**: `get_nodes_batch()` for multiple entities
- **Edge Batch Retrieval**: `get_edges_batch()` for multiple relationships  
- **Degree Batch Calculation**: Concurrent degree calculations

### 2. Concurrent Processing
```python
# Parallel data retrieval
ll_data, hl_data = await asyncio.gather(
    _get_node_data(...),    # Local entity data
    _get_edge_data(...)     # Global relationship data
)
```

### 3. Token Management
- Dynamic truncation based on token limits
- Prioritized ranking before truncation
- Context optimization for LLM efficiency

### 4. Connection Pooling
- PostgreSQL connection pooling with asyncpg
- Neo4j connection management with retry logic
- Health monitoring and circuit breaker patterns

## Error Handling and Resilience

### 1. Database Connection Management
- Automatic reconnection for transient failures
- Circuit breaker pattern for prolonged outages
- Graceful degradation when databases are unavailable

### 2. Query Resilience
- Retry logic for failed operations
- Fallback to alternative query strategies
- Partial result handling when some operations fail

### 3. Data Validation
- Entity and relationship validation during processing
- Consistency checks between Neo4j and PostgreSQL
- Error logging and monitoring integration

This comprehensive retrieval system enables LightRAG v2.0 to provide sophisticated knowledge graph-based question answering with high performance and reliability across multiple database backends.