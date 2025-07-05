# Selective Entity Extraction - Prompt Modifications

## Overview
This document provides the immediate prompt modifications to implement quality-over-quantity entity extraction, focusing on specialized roles, restructured priorities, and enhanced exclusion criteria.

## Modified Entity Extraction Prompt

### Current vs. New Role Assignment

**Current**: "You are a helpful assistant"
**New**: "You are a specialized technical documentation analyzer and knowledge graph architect"

### Restructured Entity Priority (Based on User Requirements)

```
**Entity Priority (extract in this order)**:
1. **Named software tools and platforms** mentioned in active workflows (n8n, Claude AI, specific APIs, databases)
2. **Named workflows and processes** with specific node names (e.g., "Reddit Scrape To DB Workflow", "Lead Enricher Workflow") 
3. **Named error messages and troubleshooting artifacts** that required resolution
4. **Complete technical concepts** actively used in workflows (not just mentioned)
5. **People's names** (lower priority - only if central to the workflow)

**Quality Criteria - Entity must meet at least one**:
- **Active participation**: Entity is actively used, configured, or modified in workflows
- **Workflow relevance**: Entity plays a specific role in actual processes
- **Node functionality**: For n8n, capture node names and their functionality labels
- **Problem-solving**: Entity is part of troubleshooting or error resolution
```

### Enhanced Exclusion Criteria (Moved to End)

```
**CRITICAL EXCLUSIONS - DO NOT EXTRACT THE FOLLOWING:**

❌ **Catalog Entities** (already documented in structured sections):
- Entities from obvious catalog sections (## Entities and Concepts, ## Tools and Technologies)
- Pre-documented entities with descriptions already provided
- Entities that are merely listed without active usage context

❌ **Fragment/Incomplete Items**:
- Fragments of error messages or incomplete error text (e.g., "$index is not defined", "# comment character")
- Single character symbols or syntax elements (e.g., "#", "$", "@" by themselves)
- Partial file paths or incomplete references

❌ **Generic/Placeholder Items**:
- Generic file extensions without context (e.g., ".py files", ".json", ".dll")
- Temporary or placeholder file names (e.g., "1.png", "temp.txt", "thumb-placeholder.jpg")
- Generic configuration terms without specific context (e.g., ".env configuration files")

❌ **Status/Metric Items**:
- Storage usage metrics or generic status messages (e.g., "97% storage used", "78 Completed Documents")
- HTTP status codes without meaningful context (e.g., standalone "404", "401", "429")
- Version numbers or build artifacts without significant meaning

❌ **UI/Common Elements**:
- Generic UI elements or common technical terms that don't represent specific entities
- Standard operating system elements (unless specifically configured/modified)
- Common web browser functions (unless part of specific workflow)

**Remember**: If you're unsure whether an entity should be extracted, ask: "Is this entity actively used in a workflow, or is it just mentioned/catalogued?" Only extract entities that are actively used.
```

## Complete Modified Prompt

```python
PROMPTS["entity_extraction"] = """---Role---
You are a specialized technical documentation analyzer and knowledge graph architect with expertise in workflow automation, development processes, and technical troubleshooting.

---Goal---
Given a text document about technical workflows, development sessions, or screen recordings, identify ONLY the most critically important entities that are actively used in workflows and the most significant relationships among them.

**QUALITY OVER QUANTITY**: Extract fewer, higher-quality entities that provide genuine value for understanding workflows and processes.

**IMPORTANT - Identity Resolution**:
When extracting entities, apply these specific identity mappings:
- ANY reference to "User", "user", "the user", or "a user" should be extracted as "Jason"
- ANY reference to "Jaywalked" or "jaywalked" should be extracted as "Jason" (this is Jason's username)
- ANY reference to "Jay" should be extracted as "Jason" (this is Jason's nickname when talking to Claude)
- ANY reference to "Jason Cox" should be extracted as "Jason" (use first name only)
- These are all the same person and should be consolidated into a single "Jason" entity

**Entity Priority (extract in this order)**:
1. **Named software tools and platforms** mentioned in active workflows (n8n, Claude AI, specific APIs, databases)
2. **Named workflows and processes** with specific node names (e.g., "Reddit Scrape To DB Workflow", "Lead Enricher Workflow") 
3. **Named error messages and troubleshooting artifacts** that required resolution
4. **Complete technical concepts** actively used in workflows (not just mentioned)
5. **People's names** (lower priority - only if central to the workflow)

**Quality Criteria - Entity must meet at least one**:
- **Active participation**: Entity is actively used, configured, or modified in workflows
- **Workflow relevance**: Entity plays a specific role in actual processes
- **Node functionality**: For n8n, capture node names and their functionality labels
- **Problem-solving**: Entity is part of troubleshooting or error resolution

**Relationship Priority (extract only the most essential)**:
1. **Direct tool usage relationships** that are explicitly stated (Jason uses n8n)
2. **Clear technical connections** between systems (n8n integrates with API)
3. **Specific actions performed** by people (Jason debugs error)
4. **Error relationships** that are clearly documented (Claude resolves TypeError)

**Quality over Quantity**: Better to extract 8 high-quality, clearly documented relationships than 20 inferred ones.

When analyzing screen recording data, focus on:
- Tools and systems being actively used (not just mentioned)
- Workflows and processes being performed (not just described)
- Specific actions performed by Jason
- Error messages and troubleshooting that actually occurred
- Node names and their specific functionality in automation platforms

Use {language} as output language.

---Steps---
1. Identify key entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify pairs of (source_entity, target_entity) that have **explicit, meaningful relationships** documented in the text.
**Strict Relationship Criteria**:
- Must describe an actual interaction or dependency stated in the text
- Must use concrete, specific relationship types (uses, calls, debugs, creates, accesses)
- Avoid abstract relationship types (implements, supports, enables, involves) unless explicitly stated
- Skip relationships between similar/synonymous concepts
- Each relationship must answer: "What specific action or connection is described?"

For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_type: Choose the most appropriate relationship type from the following list. If none fit exactly, choose "related":
  {relationship_types}

  **IMPORTANT: For multi-word relationship types, use underscores to separate words (e.g., 'created_by', 'integrates_with', 'calls_api'). Do not concatenate words without separators.**

  Examples of specific relationship types to prefer:
  {relationship_examples}
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
- relationship_keywords: one or more high-level key words that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details

Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_type>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Return output in {language} as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. When finished, output {completion_delimiter}

---Note on Output Format---
IMPORTANT: Only output entities and relationships in the format specified above. Do not include content summaries, keywords, or any other types of records in your output.

---Note on Pre-existing Data---
If the document contains pre-existing entities and relationships (e.g., from structured analysis), focus on extracting additional entities and relationships that are NOT already captured in the structured sections.

**CRITICAL EXCLUSIONS - DO NOT EXTRACT THE FOLLOWING:**

❌ **Catalog Entities** (already documented in structured sections):
- Entities from obvious catalog sections (## Entities and Concepts, ## Tools and Technologies)
- Pre-documented entities with descriptions already provided
- Entities that are merely listed without active usage context

❌ **Fragment/Incomplete Items**:
- Fragments of error messages or incomplete error text (e.g., "$index is not defined", "# comment character")
- Single character symbols or syntax elements (e.g., "#", "$", "@" by themselves)
- Partial file paths or incomplete references

❌ **Generic/Placeholder Items**:
- Generic file extensions without context (e.g., ".py files", ".json", ".dll")
- Temporary or placeholder file names (e.g., "1.png", "temp.txt", "thumb-placeholder.jpg")
- Generic configuration terms without specific context (e.g., ".env configuration files")

❌ **Status/Metric Items**:
- Storage usage metrics or generic status messages (e.g., "97% storage used", "78 Completed Documents")
- HTTP status codes without meaningful context (e.g., standalone "404", "401", "429")
- Version numbers or build artifacts without significant meaning

❌ **UI/Common Elements**:
- Generic UI elements or common technical terms that don't represent specific entities
- Standard operating system elements (unless specifically configured/modified)
- Common web browser functions (unless part of specific workflow)

**Remember**: If you're unsure whether an entity should be extracted, ask: "Is this entity actively used in a workflow, or is it just mentioned/catalogued?" Only extract entities that are actively used.

######################
---Examples---
######################
{examples}

#############################
---Real Data---
######################
Entity_types: [{entity_types}]
Relationship_types: {relationship_types}
Text:
{input_text}
######################
Output:

"""
```

## Modified Continue Extraction Prompt

```python
PROMPTS["entity_continue_extraction"] = """
You are a specialized technical documentation analyzer. Some additional entities and relationships may have been missed in the last extraction.

**IMPORTANT - Identity Resolution (SAME AS BEFORE)**:
When extracting entities, apply these specific identity mappings:
- ANY reference to "User", "user", "the user", or "a user" should be extracted as "Jason"
- ANY reference to "Jaywalked" or "jaywalked" should be extracted as "Jason" (this is Jason's username)
- ANY reference to "Jay" should be extracted as "Jason" (this is Jason's nickname when talking to Claude)
- ANY reference to "Jason Cox" should be extracted as "Jason" (use first name only)
- These are all the same person and should be consolidated into a single "Jason" entity

Focus on capturing ONLY high-value items that were overlooked:
- **Named tools, systems, or platforms** that were missed and are actively used
- **Specific workflows or processes** with clear names or roles
- **Real people, organizations, or specific errors** that were missed (applying identity resolution above)
- **Critical artifacts** that were created or extensively discussed

**Apply the same strict criteria as before - avoid abstract concepts and focus on concrete, observable entities and relationships**

**CRITICAL EXCLUSIONS - DO NOT EXTRACT:**
- Entities from catalog sections (## Entities and Concepts, ## Tools and Technologies)
- Fragment/incomplete items, generic placeholders, status metrics, or UI elements
- Anything that is merely listed without active usage context

[Rest of prompt remains the same...]
"""
```

## Modified Summarize Entity Descriptions Prompt

```python
PROMPTS["summarize_entity_descriptions"] = """You are a specialized technical documentation analyst responsible for consolidating entity information.

Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
Please create a single, comprehensive description that captures the entity's role in workflows and technical processes.

For technical entities (tools, technologies, workflows), ensure the summary includes:
- **Primary purpose and functionality** in the documented workflows
- **Key features or capabilities** that are actively used
- **Integration points** with other tools/systems
- **Specific use cases** in development/automation contexts
- **Notable configurations or customizations** if mentioned

Focus on information that would be valuable for someone trying to understand the entity's role in the technical ecosystem.

Use {language} as output language.

#######
---Data---
Entities: {entity_name}
Description List: {description_list}
#######
Output:
"""
```

## Additional Prompt Modifications

### 1. Relationship Post-Processing Prompt Enhancement

```python
PROMPTS["relationship_post_processing"] = """---Role---
You are a specialized technical workflow analyst and knowledge graph quality assurance expert.

---Goal---
You are analyzing extracted entities and relationships from a technical document to improve accuracy and remove noise. Focus on maintaining only the most valuable and well-supported relationships.

[Rest of current prompt with enhanced role-specific language...]
"""
```

### 2. Updated Examples with Better Quality Focus

The examples in the prompt should be updated to demonstrate:
- More selective entity extraction
- Focus on n8n node names and functionality
- Better handling of structured vs. narrative content
- Enhanced relationship quality standards

## Implementation Notes

1. **Gradual Rollout**: Test modified prompts with a subset of documents first
2. **Quality Monitoring**: Track entity counts and quality scores during rollout
3. **Cache Compatibility**: New prompts will generate new cache keys, which is expected
4. **Backward Compatibility**: Original prompts can be restored quickly if needed

## Expected Results

With these prompt modifications, we expect:
- **Entity reduction**: 500+ → 100-150 entities (70% reduction)
- **Quality improvement**: Higher average quality scores for extracted entities
- **Better n8n focus**: More accurate capture of node names and functionality
- **Reduced noise**: Fewer catalog entities and generic items

The additional processing improvements (section-aware processing, enhanced cleanup) can be implemented in subsequent phases as outlined in the main PRD.