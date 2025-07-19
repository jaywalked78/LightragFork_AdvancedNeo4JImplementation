# PRD: Hybrid Query Chunk-Based Relationship Retrieval

**Date:** January 19, 2025  
**Version:** 1.0  
**Status:** Draft  
**Priority:** High  

## Executive Summary

Fix the critical "chunks missing from storage" issue in hybrid queries by implementing chunk-based relationship retrieval instead of entity-pair-based retrieval. This addresses the fundamental mismatch between PostgreSQL vector storage and Neo4j graph storage that causes zero chunks to be returned in hybrid mode queries.

## Problem Statement

### Current Issue
Hybrid queries consistently return `retrieved_chunks_count: 0` despite having:
- ✅ 35,111 relationships in Neo4j with proper `source_id` fields
- ✅ 5,260 chunks in PostgreSQL accessible by ID
- ✅ 31,586 relationships in PostgreSQL vector storage with chunk_ids

### Root Cause Analysis
1. **PostgreSQL vector storage** stores one canonical relationship per entity pair with specific `chunk_ids`
2. **Neo4j graph storage** stores multiple relationships between the same entity pairs (different types, source_ids)
3. **Current code** uses `get_edges_batch(entity_pairs)` which returns ALL relationships between entities
4. **Mismatch occurs** when trying to map vector storage's specific chunk_ids to Neo4j's multiple relationships
5. **Result**: Wrong relationships retrieved, source_ids don't match intended chunks

### Evidence
```
PostgreSQL: Airtable -> n8n with chunk_ids: ['chunk-feb9c55ac0e8d1c68fdca8ac3c8593c0']
Neo4j: 21 different relationships between Airtable and n8n with various source_ids
Current code: Picks wrong relationship, chunks not found
```

## Solution Overview

Replace entity-pair-based relationship retrieval with **chunk-based relationship retrieval** for hybrid queries.

### Core Concept
Instead of: `"Find relationships between entity A and B"`  
Use: `"Find relationships that contain chunk X"`

This ensures we get the **exact relationship** that the vector storage intended, with the correct `source_id` values.

## Technical Requirements

### Functional Requirements

#### FR1: Chunk-Based Relationship Lookup
- **Input**: List of chunk_ids from PostgreSQL vector storage
- **Process**: Query Neo4j relationships where `source_id` contains those chunk_ids
- **Output**: Specific relationships with matching source_ids

#### FR2: Source ID Cleanup
- **Input**: PostgreSQL array format `{chunk-id}`
- **Process**: Remove curly braces to get plain `chunk-id`
- **Output**: Clean chunk_ids for Neo4j queries

#### FR3: Hybrid Mode Isolation
- **Scope**: Changes apply only to hybrid/mix query mode
- **Preservation**: Local and global modes remain unchanged
- **Compatibility**: Existing query interfaces maintained

#### FR4: Performance Optimization
- **Efficiency**: Direct chunk_id → relationship mapping
- **Scalability**: Batch processing for multiple chunk_ids
- **Caching**: Leverage existing LLM caching mechanisms

### Non-Functional Requirements

#### NFR1: Backward Compatibility
- No breaking changes to existing API endpoints
- Local and global query modes unaffected
- Configuration compatibility maintained

#### NFR2: Performance
- Response time improvement through precise relationship matching
- Reduced memory usage by eliminating unnecessary relationship filtering
- Maintained query throughput

#### NFR3: Reliability
- 100% chunk retrieval success rate for valid chunk_ids
- Graceful handling of missing or invalid chunk_ids
- Comprehensive error logging and monitoring

## Implementation Plan

### Phase 1: Core Infrastructure (Day 1)

#### 1.1 Create New Function: `get_relationships_by_chunk_ids()`
```python
async def get_relationships_by_chunk_ids(
    chunk_ids: List[str],
    knowledge_graph_inst: BaseGraphStorage
) -> Dict[str, Dict]:
    """
    Retrieve relationships from Neo4j based on chunk_ids instead of entity pairs.
    
    Args:
        chunk_ids: List of chunk identifiers from vector storage
        knowledge_graph_inst: Neo4j storage instance
        
    Returns:
        Dictionary mapping chunk_id to relationship properties
    """
```

#### 1.2 Neo4j Query Implementation
```cypher
UNWIND $chunk_ids AS chunk_id
MATCH ()-[r]->() 
WHERE r.source_id = chunk_id 
   OR r.source_id CONTAINS ($chunk_id + '<SEP>')
   OR r.source_id CONTAINS ('<SEP>' + $chunk_id)
RETURN chunk_id, properties(r) AS properties, 
       type(r) AS neo4j_type, r.original_type AS original_type, r.rel_type AS rel_type
```

#### 1.3 Source ID Cleanup Function
```python
def clean_source_id(source_id: str) -> str:
    """Clean PostgreSQL array format from source_id: {chunk-id} -> chunk-id"""
    if source_id is None:
        return None
    return str(source_id).strip('{}')
```

### Phase 2: Integration (Day 1-2)

#### 2.1 Update Hybrid Query Logic
- Modify `_find_most_related_text_unit_from_relationships()`
- Replace `get_edges_batch()` calls with `get_relationships_by_chunk_ids()`
- Apply source_id cleanup to PostgreSQL chunk_ids

#### 2.2 Data Flow Updates
```
Old Flow:
Vector Storage → Entity Pairs → get_edges_batch() → Wrong Relationships → No Chunks

New Flow:
Vector Storage → chunk_ids → get_relationships_by_chunk_ids() → Correct Relationships → Chunks Retrieved
```

#### 2.3 Error Handling
- Handle missing chunk_ids gracefully
- Log relationship retrieval statistics
- Fallback mechanisms for edge cases

### Phase 3: Testing & Validation (Day 2)

#### 3.1 Unit Tests
- Test `clean_source_id()` function with various inputs
- Test `get_relationships_by_chunk_ids()` with sample data
- Test hybrid query end-to-end flow

#### 3.2 Integration Tests
- Validate chunk retrieval success rate
- Compare hybrid query results before/after changes
- Performance benchmarking

#### 3.3 Regression Tests
- Ensure local/global modes unaffected
- Verify API compatibility
- Configuration validation

## Success Metrics

### Primary Metrics
- **Chunk Retrieval Rate**: 0% → 95%+ for hybrid queries
- **Query Success Rate**: Maintained at 100%
- **Response Quality**: Improved due to correct chunk retrieval

### Secondary Metrics
- **Response Time**: 5-10% improvement through precise matching
- **Memory Usage**: 10-15% reduction by eliminating wrong relationships
- **Error Rate**: Maintained near 0%

### Validation Criteria
- Hybrid queries return `retrieved_chunks_count > 0`
- Retrieved chunks contain relevant content for the query
- Source traceability maintained through proper chunk_ids

## Rollout Plan

### Development Environment
1. Implement changes in feature branch
2. Test with existing knowledge base
3. Validate against known good queries

### Staging Environment
1. Deploy to staging for comprehensive testing
2. Run performance benchmarks
3. User acceptance testing

### Production Environment
1. Feature flag controlled rollout
2. Monitor key metrics
3. Gradual traffic increase to 100%

## Risk Assessment

### High Risk
- **Data Inconsistency**: If PostgreSQL chunk_ids don't match Neo4j source_ids
  - **Mitigation**: Comprehensive validation scripts
  - **Rollback**: Feature flag disabled

### Medium Risk
- **Performance Impact**: New query patterns may affect performance
  - **Mitigation**: Thorough performance testing
  - **Monitoring**: Real-time performance metrics

### Low Risk
- **Compatibility Issues**: Changes isolated to hybrid mode
  - **Mitigation**: Comprehensive regression testing

## Dependencies

### Internal Dependencies
- Neo4j graph storage availability
- PostgreSQL vector storage accessibility
- LightRAG query processing pipeline

### External Dependencies
- Neo4j driver compatibility
- PostgreSQL driver functionality
- No external API dependencies

## Monitoring & Observability

### Key Metrics to Track
```python
# Query Performance
- hybrid_query_response_time_ms
- chunk_retrieval_success_rate
- relationship_match_accuracy

# Error Tracking
- chunk_id_not_found_errors
- neo4j_query_failures
- source_id_cleanup_errors

# Usage Analytics
- hybrid_vs_local_vs_global_query_distribution
- chunk_retrieval_volume
- query_satisfaction_scores
```

### Alerting
- Alert if chunk retrieval rate drops below 90%
- Alert on Neo4j query failures
- Alert on response time degradation > 20%

## Documentation Updates

### Developer Documentation
- Update hybrid query flow diagrams
- Document new functions and their usage
- Add troubleshooting guides

### API Documentation
- No API changes required
- Update internal implementation notes
- Add performance characteristics

## Future Enhancements

### Phase 4: Optimization (Future)
- Implement relationship caching based on chunk_ids
- Optimize Neo4j queries with indexes on source_id fields
- Batch optimization for large chunk_id sets

### Phase 5: Advanced Features (Future)
- Chunk-based relationship ranking
- Multi-hop relationship traversal using chunk_ids
- Advanced chunk similarity scoring

## Conclusion

This PRD addresses a critical architectural issue in LightRAG's hybrid query system. By implementing chunk-based relationship retrieval, we solve the fundamental mismatch between vector storage and graph storage that has been causing zero chunk retrieval in hybrid queries.

The solution is surgical, affecting only the problematic hybrid mode while preserving all existing functionality. Expected outcomes include restored chunk retrieval functionality, improved query accuracy, and better performance through precise relationship matching.

**Success Definition**: Hybrid queries consistently return relevant chunks with proper source traceability, restoring the full value of the hybrid query mode for users.