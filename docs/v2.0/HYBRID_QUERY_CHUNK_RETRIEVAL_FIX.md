# Hybrid Query Chunk Retrieval Fix - Implementation Guide

**Date**: January 19, 2025  
**Version**: 2.0.1  
**Status**: ✅ FIXED  
**Issue**: Hybrid queries returned `retrieved_chunks_count: 0`  
**Solution**: Chunk-based relationship retrieval

## Problem Summary

### The Issue
Hybrid queries consistently returned `retrieved_chunks_count: 0` despite having:
- ✅ 35,111 relationships in Neo4j with proper `source_id` fields
- ✅ 5,260 chunks in PostgreSQL accessible by ID  
- ✅ 31,586 relationships in PostgreSQL vector storage with `chunk_ids`

### Root Cause
**Entity-pair-based vs Chunk-based mismatch**:
1. **PostgreSQL vector storage** returns specific relationships with specific `chunk_ids`
2. **Neo4j's `get_edges_batch()`** returns ALL relationships between entity pairs
3. **Mismatch**: Vector storage intended chunk X, but Neo4j returned relationship Y
4. **Result**: Wrong relationships → source_ids don't match → 0 chunks retrieved

## Solution Architecture

### Before (Broken Flow)
```
Vector Storage → Entity Pairs → get_edges_batch() → ALL relationships → Wrong source_ids → 0 chunks
```

### After (Fixed Flow)  
```
Vector Storage → chunk_ids → get_relationships_by_chunk_ids() → EXACT relationships → Correct source_ids → 39 chunks ✅
```

## Implementation Details

### Files Modified

#### 1. `lightrag/operate.py` 
**New Functions Added**:
- `get_relationships_by_chunk_ids()` - Neo4j chunk-based lookup
- `_get_edge_data_hybrid()` - Hybrid-specific edge data processing

#### 2. `lightrag/advanced_operate.py`
**Modified**:
- Import `_get_edge_data_hybrid`
- Added `_get_edge_data_with_details_hybrid()` function
- Updated hybrid mode to use new function

#### 3. `lightrag/kg/postgres_impl.py`
**Modified**:
- Updated relationships query to include `chunk_ids` in SELECT statement

### Key Changes

#### Neo4j Chunk Lookup Query
```cypher
UNWIND $chunk_ids AS chunk_id
MATCH ()-[r]->() 
WHERE r.source_id = chunk_id 
   OR r.source_id CONTAINS (chunk_id + $sep)
   OR r.source_id CONTAINS ($sep + chunk_id)
RETURN chunk_id, properties(r) AS properties, 
       type(r) AS neo4j_type, r.original_type AS original_type
```

#### PostgreSQL Vector Storage Fix
```sql
-- BEFORE: Missing chunk_ids
SELECT source_id as src_id, target_id as tgt_id, create_time

-- AFTER: Include chunk_ids  
SELECT source_id as src_id, target_id as tgt_id, chunk_ids, create_time
```

## Results

### Success Metrics
- **Before**: `retrieved_chunks_count: 0` ❌
- **After**: `retrieved_chunks_count: 39` ✅
- **Performance**: Similar response times
- **Compatibility**: Local/global modes unaffected

### Log Evidence
```
INFO: Hybrid query uses 25 entities, 19 relations, 39 chunks
INFO: Chunk lookup: Successfully fetched 39 valid chunks
```

## Technical Implementation

### Hybrid Mode Detection
The system uses `advanced_operate.py` as the main entry point, which calls specialized functions based on query mode.

### Error Handling
- Graceful fallback if chunk_ids not found
- Maintains data structure compatibility
- Comprehensive logging for troubleshooting

### Performance Optimization
- Batch processing of chunk_ids
- Direct chunk-to-relationship mapping
- Eliminates unnecessary relationship filtering

## Usage

No configuration changes required. The fix is automatically applied to all hybrid queries:

```bash
curl -X POST "http://localhost:9621/query" \
-H "Content-Type: application/json" \
-d '{"query": "Your query here", "mode": "hybrid"}'
```

## Monitoring

### Success Indicators
- `retrieved_chunks_count > 0` in hybrid queries
- Log: "Chunk lookup: Successfully fetched X valid chunks"
- Log: "Hybrid query uses X entities, Y relations, Z chunks" (Z > 0)

### Debug Logs
- `🔄 ADVANCED HYBRID MODE: Using chunk-based relationship retrieval`
- `🔍 Advanced hybrid mode detected`
- `Hybrid Query edges: [keywords]`

## Backward Compatibility

✅ **Local queries**: Unchanged  
✅ **Global queries**: Unchanged  
✅ **Mix queries**: Unchanged  
✅ **API compatibility**: Preserved  
✅ **Configuration**: No changes needed

## Troubleshooting

### If chunks still return 0:
1. Check vector storage has `chunk_ids`: `SELECT chunk_ids FROM tll_lightrag_vdb_relation LIMIT 5`
2. Verify Neo4j relationships have `source_id`: `MATCH ()-[r]->() RETURN r.source_id LIMIT 5`
3. Check logs for "ADVANCED HYBRID MODE" message
4. Restart server to ensure code changes are loaded

---

## Implementation Summary

**Root Issue**: Entity-pair lookup returned wrong relationships  
**Core Fix**: Chunk-based relationship retrieval  
**Result**: 0 → 39 chunks retrieved ✅  
**Impact**: Hybrid queries now provide full context for LLM responses

This fix restores the full functionality of hybrid queries, enabling users to benefit from both entity-based (local) and relationship-based (global) retrieval in a single query.