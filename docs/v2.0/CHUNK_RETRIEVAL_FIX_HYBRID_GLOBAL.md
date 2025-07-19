# Hybrid & Global Query Chunk Retrieval Fix - Implementation Guide

**Date**: January 19, 2025  
**Version**: 2.0.2  
**Status**: ✅ FIXED  
**Issue**: Hybrid and Global queries returned `retrieved_chunks_count: 0`  
**Solution**: Chunk-based relationship retrieval for both modes

## Problem Summary

### The Issue
Both Hybrid and Global queries consistently returned `retrieved_chunks_count: 0` despite having:
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

---

# Global Query Chunk Retrieval Fix - Extension

**Date**: January 19, 2025  
**Version**: 2.0.2  
**Status**: ✅ FIXED  
**Issue**: Global queries also returned `retrieved_chunks_count: 0`  
**Solution**: Applied the same chunk-based relationship retrieval strategy to global mode

## Global Mode Problem Analysis

### The Same Issue Affecting Global Mode
After successfully fixing hybrid mode, analysis revealed that **global mode had the identical problem**:

**Symptoms from logs:**
```
GLOBAL mode:
INFO: ⚠️  STANDARD _get_edge_data called (not hybrid version)
INFO: Chunk lookup: 12 source_ids are None, 0 are empty strings
INFO: Chunk lookup: Successfully fetched 0 valid chunks
INFO: Global query uses 13 entities, 12 relations, 0 chunks ❌
```

**vs**

```
HYBRID mode:
INFO: 🔄 ADVANCED HYBRID MODE: Using chunk-based relationship retrieval
INFO: Chunk lookup: Successfully fetched 29 valid chunks  
INFO: Hybrid query uses 30 entities, 20 relations, 29 chunks ✅
```

### Root Cause Identical to Hybrid
Global mode suffered from the exact same **entity-pair-based vs chunk-based mismatch**:
1. **PostgreSQL vector storage** returns specific relationships with specific `chunk_ids`
2. **Standard `_get_edge_data()` uses `get_edges_batch()`** which returns ALL relationships between entity pairs
3. **Mismatch**: Vector storage intended chunk X, but `get_edges_batch()` returned relationship Y without proper `source_id`
4. **Result**: Wrong relationships → `source_ids = None` → 0 chunks retrieved

## Global Mode Solution Implementation

### Files Modified for Global Fix

#### 1. `lightrag/operate.py` 
**New Functions Added**:
- `_get_edge_data_global()` - Global-specific chunk-based edge data processing (line 3891)

**Modified Functions**:
- Global mode routing (line 2884): Changed from `_get_edge_data()` to `_get_edge_data_global()`

#### 2. `lightrag/advanced_operate.py`
**New Functions Added**:
- `_get_edge_data_with_details_global()` - Enhanced global version with retrieval details (line 1638)

**Modified Functions**:
- Import `_get_edge_data_global` (line 56)
- Global mode routing (line 1274): Changed from `_get_edge_data_with_details()` to `_get_edge_data_with_details_global()`

### Technical Implementation Details

#### `_get_edge_data_global()` Function
```python
async def _get_edge_data_global(
    keywords,
    knowledge_graph_inst: BaseGraphStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
):
    """
    Global-specific version that uses chunk-based relationship retrieval.
    
    Applies the same fix as hybrid mode: instead of using get_edges_batch() which
    returns relationships without proper source_ids, we use chunk_ids from vector 
    storage to get the exact relationships that have chunk content.
    """
    logger.info("🔄 GLOBAL MODE: Using chunk-based relationship retrieval")
    
    # Step 1: Query vector storage for relationships  
    results = await relationships_vdb.query(keywords, top_k=query_param.top_k, ids=query_param.ids)
    
    # Step 2: Extract chunk_ids from vector storage results
    all_chunk_ids = []
    for r in results:
        chunk_ids = r.get("chunk_ids", [])
        # Handle various chunk_id formats
        if isinstance(chunk_ids, str):
            chunk_ids = [chunk_ids]
        for chunk_id in chunk_ids:
            clean_chunk_id = str(chunk_id).strip('{}')
            all_chunk_ids.append(clean_chunk_id)
    
    # Step 3: Get relationships from Neo4j using chunk_ids (the key fix!)
    chunk_relationships = await get_relationships_by_chunk_ids(all_chunk_ids, knowledge_graph_inst)
    
    # Step 4-8: Same processing as hybrid mode...
```

#### Entity Context Bug Fix
Fixed a critical bug discovered during testing:
```python
# BEFORE (KeyError):
"entity": n["entity"]

# AFTER (Correct field name):
"entity": n["entity_name"],
"type": n.get("entity_type", "UNKNOWN"),
"rank": n["rank"],
```

## Global Mode Results

### Success Metrics - Before vs After
| Metric | Before Fix | After Fix | Status |
|--------|------------|-----------|---------|
| **Chunks Retrieved** | 0 | **27** | ✅ Fixed |
| **Relationships** | 12 | 12 | ✅ Same |
| **Entities** | 13 | 17 | ✅ Improved |
| **source_ids = None** | 12 | **0** | ✅ Fixed |

### Log Evidence - Success
```
INFO: 🔄 ADVANCED GLOBAL MODE: Using chunk-based relationship retrieval
INFO: 🔄 GLOBAL MODE: Using chunk-based relationship retrieval
INFO: Global edge query: Extracted 12 chunk_ids from 12 vector results
INFO: Chunk-based lookup: Found 12 relationships for 12 chunk_ids
INFO: Chunk lookup: 0 source_ids are None, 0 are empty strings ✅
INFO: Chunk lookup: Successfully fetched 27 valid chunks ✅
INFO: Global query uses 17 entities, 12 relations, 27 chunks ✅
```

## Updated Solution Architecture

### Universal Flow (Both Hybrid & Global)
```
Vector Storage → chunk_ids → get_relationships_by_chunk_ids() → EXACT relationships → Correct source_ids → ✅ Chunks Retrieved
```

### Mode Comparison - After Fixes
| Mode | Strategy | Chunks Retrieved | Function Used |
|------|----------|------------------|---------------|
| **Local** | Entity-based | ✅ Working | `_get_node_data()` |
| **Global** | Chunk-based relationships | ✅ **27 chunks** | `_get_edge_data_global()` |
| **Hybrid** | Chunk-based relationships + entities | ✅ **29 chunks** | `_get_edge_data_hybrid()` |

## Updated Usage

### Global Mode Queries
No configuration changes required. The fix is automatically applied to all global queries:

```bash
curl -X POST "http://localhost:9621/query" \
-H "Content-Type: application/json" \
-d '{"query": "Your query here", "mode": "global"}'
```

### Updated Monitoring

#### Success Indicators - Global Mode
- `retrieved_chunks_count > 0` in global queries ✅
- Log: "🔄 GLOBAL MODE: Using chunk-based relationship retrieval" ✅
- Log: "Global query uses X entities, Y relations, Z chunks" (Z > 0) ✅
- Log: "0 source_ids are None" ✅

#### Debug Logs - Global Mode
- `🔄 ADVANCED GLOBAL MODE: Using chunk-based relationship retrieval`
- `Global edge query: Extracted X chunk_ids from Y vector results`
- `Chunk-based lookup: Found X relationships for Y chunk_ids`

## Updated Backward Compatibility

✅ **Local queries**: Unchanged  
✅ **Global queries**: ✅ **Now fixed with chunk retrieval**  
✅ **Hybrid queries**: ✅ **Already fixed**  
✅ **Mix queries**: Unchanged  
✅ **API compatibility**: Preserved  
✅ **Configuration**: No changes needed

## Updated Troubleshooting

### If Global mode chunks still return 0:
1. Check vector storage has `chunk_ids`: `SELECT chunk_ids FROM tll_lightrag_vdb_relation LIMIT 5`
2. Verify Neo4j relationships have `source_id`: `MATCH ()-[r]->() RETURN r.source_id LIMIT 5`
3. Check logs for "🔄 GLOBAL MODE: Using chunk-based relationship retrieval" message
4. Ensure no "source_ids are None" in logs
5. Restart server to ensure code changes are loaded

---

## Final Implementation Summary

**Root Issue**: Both hybrid and global modes suffered from entity-pair lookup returning wrong relationships  
**Universal Fix**: Chunk-based relationship retrieval applied to both modes  
**Results**: 
- **Hybrid**: 0 → 29 chunks retrieved ✅  
- **Global**: 0 → 27 chunks retrieved ✅  

**Impact**: Both hybrid and global queries now provide full chunk context for LLM responses, ensuring comprehensive retrieval across all relationship-based query modes.

### Architecture Achievement
```
✅ Local Mode:   Entity-based retrieval working
✅ Global Mode:  Chunk-based relationship retrieval working  
✅ Hybrid Mode:  Chunk-based relationship + entity retrieval working
✅ Universal:    All modes now retrieve chunks properly
```

This comprehensive fix ensures that LightRAG v2.0.2 provides reliable chunk retrieval across all query modes, maximizing the context available to LLMs for generating accurate and comprehensive responses.