# PRD: Selective Entity Extraction Improvements

## Overview
This PRD outlines improvements to LightRAG's entity extraction system to achieve quality over quantity, reducing over-extraction from 500+ entities to 40-60 high-quality entities while maintaining semantic accuracy.

## Problem Statement

### Current Issues
1. **Over-extraction**: Documents with structured entity sections (like `## Entities and Concepts`) generate 500+ entities and 200+ relationships
2. **Structured sections over-processed**: Pre-documented entities in structured sections are being re-extracted as hundreds of new entities
3. **Generic prompts**: "You are a helpful assistant" provides insufficient specialization
4. **Poor negative prompting**: Exclusion criteria positioned poorly in prompts, sometimes interpreted as inclusion instructions
5. **Limited entity cleanup**: No automated removal of orphaned entities after relationship filtering
6. **Insufficient logging**: No visibility into what entities/relationships are being removed during post-processing

### Target Metrics
- **Entities**: Reduce from 500+ to 40-60 high-quality entities
- **Relationships**: Maintain current post-processing reduction (~33% reduction is working well)
- **Accuracy**: Maintain or improve semantic accuracy
- **Processing time**: Should improve due to fewer entities to process

## Solution Components

### 1. Enhanced Entity Extraction Prompts

#### A. Specialized Role Assignment
**Current**: "You are a helpful assistant"
**New**: "You are a specialized technical documentation analyzer and knowledge graph architect"

#### B. Restructured Entity Priority (Revised)
1. **Named software tools and platforms** (n8n, Claude AI, specific APIs) - **CRITICAL PRIORITY**
2. **Named workflows and processes** with specific node names (e.g., "Reddit Scrape To DB Workflow", "Lead Enricher Workflow") - **HIGH PRIORITY** 
3. **Named error messages and troubleshooting artifacts** - **HIGH PRIORITY**
4. **Complete technical concepts** actively used in workflows - **MEDIUM PRIORITY**
5. **People's names** (de-prioritized per user request) - **LOW PRIORITY**

#### C. Enhanced Quality Criteria
- **Active participation requirement**: Entity must be actively used, not just mentioned
- **Workflow relevance**: Must play a role in actual processes, not just be catalogued
- **Node name importance**: Specifically capture n8n node names and their functionality labels
- **Cross-chunk relevance**: Entity should provide value across multiple contexts

#### D. Repositioned and Enhanced Exclusion Criteria
Move exclusion criteria to end of prompt with stronger negative language:

```
**CRITICAL EXCLUSIONS - DO NOT EXTRACT:**
- Entities from obvious catalog sections (## Entities and Concepts, ## Tools and Technologies)
- Fragments or partial error messages
- Generic file extensions without context
- Placeholder files or temporary artifacts
- Storage metrics or status messages
- HTTP codes without meaningful context
- Version numbers without significance
- Generic UI elements or common terms
```

### 2. Section-Specific Processing Strategy

#### A. Section Detection and Flagging
**Goal**: Identify structured entity sections during chunking and apply different processing rules.

**Implementation**:
1. **Chunk metadata tagging**: Add `chunk_type` field to identify:
   - `structured_entity_catalog` - for ## Entities and Concepts sections
   - `structured_relationship_catalog` - for ## Relationships and Connections sections  
   - `structured_tools_catalog` - for ## Tools and Technologies sections
   - `narrative_content` - for regular document content

2. **Section boundary detection**: When chunks are split due to size, preserve section context through metadata

#### B. Differential Processing Rules
**Structured Catalog Sections**:
- **Extraction rule**: Extract only entities NOT already well-documented in the structured format
- **Relationship rule**: Focus on cross-references between pre-documented entities
- **Filter rule**: Remove entities that are clearly already catalogued in the structured sections

**Narrative Content Sections**:
- **Standard processing**: Apply normal extraction rules
- **Cross-reference validation**: Check against structured sections to avoid duplicates

#### C. Post-Section Processing
After processing all chunks from structured sections:
1. **Cross-reference validation**: Compare extracted entities against pre-documented entities
2. **Merge and deduplicate**: Consolidate similar entities from different sections
3. **Quality scoring**: Rank entities by evidence strength and cross-section relevance

### 3. Enhanced Entity Cleanup with Logging

#### A. Orphaned Entity Removal
**Current**: `ENABLE_ENTITY_CLEANUP=false` by default
**New**: Enable by default with enhanced logic

**Implementation**:
1. **Relationship-based cleanup**: Remove entities with no relationships after post-processing
2. **Quality threshold cleanup**: Remove entities below minimum quality score
3. **Cascade cleanup**: When relationships are removed, evaluate connected entities for removal

#### B. Comprehensive Logging
**Entity Removal Logging**:
```
INFO: Entity cleanup: Removing orphaned entity 'Generic Configuration' (no relationships)
INFO: Entity cleanup: Removing low-quality entity 'Storage Metrics' (quality score: 2/10)
INFO: Entity cleanup: Cascade removal of entity 'Temporary File' (connected relationship removed)
```

**Relationship Removal Logging**:
```
INFO: Relationship filtering: Removed 'User -> implements -> Data Transformation' (too abstract)
INFO: Relationship filtering: Removed 'Business Research -> investigates -> Hotworx' (weak association)
INFO: Relationship filtering: Kept 'Jason -> uses -> n8n' (explicit tool usage)
```

#### C. Statistics and Metrics
**Terminal Output Summary**:
```
=== Entity Extraction Summary ===
Initial entities extracted: 487
After quality filtering: 312
After relationship-based cleanup: 156
After merge/dedupe: 52
Final entities: 52

=== Relationship Summary ===
Initial relationships: 234
After chunk post-processing: 156 (33% reduction)
After entity cleanup cascade: 134
Final relationships: 134

=== Quality Metrics ===
Average entity quality score: 7.2/10
High-quality entities (8+): 34 (65%)
Low-quality entities removed: 156
```

### 4. Aggressive Entity Merging Enhancement

#### A. Stricter Merging Criteria
**Current**: Merge entities with identical names
**Enhanced**: 
- **Semantic similarity**: Merge entities with similar meanings (e.g., "n8n platform" + "n8n automation tool")
- **Functional similarity**: Merge entities serving the same role (e.g., "JavaScript Code" + "Custom JavaScript")
- **Identity resolution**: More aggressive name normalization

#### B. Relationship Consolidation
**Current**: Keep all relationships after merging
**Enhanced**:
- **Relationship deduplication**: Merge similar relationships between same entities
- **Relationship quality scoring**: Remove low-quality relationships during merge process
- **Semantic relationship merging**: Consolidate functionally identical relationships

### 5. Configuration Changes

#### A. Environment Variables
```bash
# Enhanced entity extraction controls
ENABLE_ENTITY_CLEANUP=true
ENTITY_QUALITY_THRESHOLD=6.0
ENABLE_AGGRESSIVE_ENTITY_MERGING=true
ENABLE_SECTION_AWARE_PROCESSING=true

# Logging controls
LOG_ENTITY_CLEANUP=true
LOG_RELATIONSHIP_FILTERING=true
LOG_ENTITY_MERGING=true

# Extraction limits
MAX_ENTITIES_PER_CHUNK=15
MAX_RELATIONSHIPS_PER_CHUNK=20
ENTITY_EXTRACT_MAX_GLEANING=1  # Reduced from default 2-3
```

#### B. New Configuration Options
```python
# In LightRAG initialization
rag = LightRAG(
    # Quality over quantity controls
    entity_quality_threshold=6.0,
    enable_aggressive_entity_merging=True,
    enable_section_aware_processing=True,
    
    # Logging controls
    log_entity_cleanup=True,
    log_relationship_filtering=True,
    
    # Extraction limits
    max_entities_per_chunk=15,
    max_relationships_per_chunk=20,
    entity_extract_max_gleaning=1,
)
```

## Implementation Plan

### Phase 1: Core Prompt Improvements (Week 1)
1. **Specialized role assignment** in all extraction prompts
2. **Restructured entity priority** with n8n node emphasis
3. **Enhanced exclusion criteria** positioned at prompt end
4. **Quality-focused instruction** consolidation

### Phase 2: Section-Aware Processing (Week 2)
1. **Chunk metadata tagging** for section identification
2. **Differential processing rules** for structured vs narrative content
3. **Cross-section validation** logic
4. **Post-section processing** pipeline

### Phase 3: Enhanced Cleanup and Logging (Week 3)
1. **Orphaned entity removal** with cascade logic
2. **Comprehensive logging** for all cleanup operations
3. **Statistics and metrics** dashboard
4. **Quality threshold enforcement**

### Phase 4: Aggressive Merging (Week 4)
1. **Semantic similarity** merging algorithms
2. **Relationship consolidation** logic
3. **Identity resolution** enhancements
4. **Final quality scoring** and ranking

## Success Metrics

### Quantitative Goals
- **Entity count reduction**: 500+ → 40-60 entities (88% reduction)
- **Maintain relationship quality**: Current 33% reduction rate maintained
- **Processing speed improvement**: 20-30% faster due to fewer entities
- **Entity quality score**: Average 7.5+ out of 10
- **Cache hit rate**: Maintain current 60-80% cache performance

### Qualitative Goals
- **Semantic accuracy**: No loss of meaningful relationships
- **Workflow completeness**: All critical n8n nodes and processes captured
- **Error coverage**: All important troubleshooting information preserved
- **Cross-section coherence**: Structured and narrative sections complement each other

## Risk Mitigation

### Technical Risks
1. **Over-aggressive filtering**: Implement gradual rollout with quality monitoring
2. **Section detection failures**: Fallback to standard processing for unrecognized sections
3. **Cache invalidation**: Ensure cache keys account for new processing rules
4. **Performance impact**: Monitor processing times and optimize if needed

### Quality Risks
1. **Loss of important entities**: Comprehensive testing with diverse document types
2. **Relationship accuracy**: Maintain existing post-processing validation
3. **Consistency issues**: Extensive logging and validation during implementation
4. **User workflow disruption**: Backward compatibility with existing configurations

## Testing Strategy

### Unit Tests
- **Prompt modifications**: Test with controlled entity extraction scenarios
- **Section detection**: Verify accurate identification of structured sections
- **Cleanup logic**: Test orphaned entity removal and cascade effects
- **Merging algorithms**: Validate semantic similarity and identity resolution

### Integration Tests
- **End-to-end processing**: Test complete pipeline with sample documents
- **Cache compatibility**: Verify cache performance with new processing rules
- **Cross-section validation**: Test structured + narrative content processing
- **Performance benchmarks**: Measure processing time and memory usage

### Production Validation
- **Gradual rollout**: Deploy with feature flags for controlled testing
- **Quality monitoring**: Track entity/relationship counts and quality scores
- **User feedback**: Monitor for any workflow disruptions or quality issues
- **Rollback plan**: Quick revert capability if issues arise

## Dependencies

### Technical Dependencies
- **Chunk post-processing system**: Already implemented and working
- **Entity cleanup infrastructure**: Needs enhancement for cascade removal
- **Logging framework**: Needs extension for cleanup and merging operations
- **Cache system**: Should work with new processing rules

### Configuration Dependencies
- **Environment variables**: New configuration options need documentation
- **Backward compatibility**: Existing configurations should continue working
- **Documentation updates**: Update user guides and configuration references

## Deliverables

### Code Changes
1. **Modified prompts**: Updated entity extraction prompts with specialized roles
2. **Section processing logic**: New chunk type detection and differential processing
3. **Enhanced cleanup**: Orphaned entity removal with cascade effects
4. **Logging infrastructure**: Comprehensive cleanup and merging logs
5. **Configuration options**: New environment variables and initialization parameters

### Documentation
1. **Updated configuration guide**: New environment variables and options
2. **Processing flow documentation**: How section-aware processing works
3. **Troubleshooting guide**: Understanding cleanup and merging logs
4. **Migration guide**: Upgrading from current entity extraction

### Testing
1. **Unit test suite**: Comprehensive tests for all new functionality
2. **Integration test scenarios**: End-to-end testing with diverse documents
3. **Performance benchmarks**: Before/after processing metrics
4. **Quality validation**: Entity and relationship accuracy verification

## Timeline

**Week 1-2**: Core implementation (prompts, section processing, cleanup)
**Week 3**: Testing and validation (unit tests, integration tests)
**Week 4**: Documentation and deployment preparation
**Week 5**: Gradual rollout and monitoring

## Success Criteria

### Must-Have
- [ ] Entity count reduced from 500+ to 40-60 per document
- [ ] No loss of critical workflow entities (n8n nodes, error messages)
- [ ] Comprehensive logging of all cleanup operations
- [ ] Backward compatibility with existing configurations

### Should-Have
- [ ] 20-30% processing speed improvement
- [ ] Average entity quality score 7.5+/10
- [ ] Automated section detection with 90%+ accuracy
- [ ] Enhanced merging reduces duplicate entities by 50%

### Could-Have
- [ ] Machine learning-based quality scoring
- [ ] Dynamic quality thresholds based on document type
- [ ] Advanced semantic similarity algorithms
- [ ] Real-time processing metrics dashboard

This PRD provides a comprehensive but practical approach to achieving quality over quantity in entity extraction without over-engineering the solution.