# LightRAG Prompt Customization Guide

## Overview

LightRAG's knowledge extraction capabilities can be significantly enhanced by customizing the prompts in `lightrag/prompt.py` to match your specific domain and use case. This guide shows you how to create domain-specific entity types, relationship types, and examples.

## Default Enhanced Configuration

The default configuration has been optimized for technical workflows and includes:

### Entity Types
- `tool` - Software tools, APIs, platforms, services
- `technology` - Programming languages, frameworks, protocols
- `concept` - Abstract ideas, methodologies, patterns
- `workflow` - Processes, procedures, pipelines
- `artifact` - Files, scripts, configurations, outputs
- `person` - Individuals involved in processes
- `organization` - Companies, teams, departments

### Advanced Relationship Types
Instead of generic "related" relationships, the system extracts specific semantic relationships:

**Technical Relationships:**
- `calls_api`, `integrates_with`, `depends_on`
- `implements`, `configures`, `manages`
- `processes`, `transforms`, `exports_to`
- `debugs`, `optimizes`, `monitors`

**Operational Relationships:**
- `schedules`, `executes`, `automates`
- `generates`, `creates`, `modifies`
- `uses`, `provides`, `supports`

**Data Relationships:**
- `stored_in`, `reads_from`, `writes_to`
- `returns`, `contains`, `formats`

## Customizing for Your Domain

### 1. Define Domain-Specific Entity Types

```python
# Example for Healthcare Domain
PROMPTS["DEFAULT_ENTITY_TYPES"] = [
    "patient", "provider", "procedure", "medication", 
    "diagnosis", "symptom", "treatment", "facility"
]

# Example for Legal Domain  
PROMPTS["DEFAULT_ENTITY_TYPES"] = [
    "case", "statute", "precedent", "party", 
    "court", "judge", "evidence", "ruling"
]

# Example for Financial Domain
PROMPTS["DEFAULT_ENTITY_TYPES"] = [
    "asset", "transaction", "account", "institution",
    "regulation", "market", "instrument", "risk"
]
```

### 2. Create Domain-Specific Relationships

For each domain, define relationship types that capture the semantic connections:

```python
# Healthcare relationship examples
relationship_types = [
    "diagnoses", "treats", "prescribes", "administered_to",
    "indicates", "contraindicated_with", "monitors",
    "scheduled_at", "referred_to", "documented_in"
]

# Legal relationship examples  
relationship_types = [
    "cites", "overrules", "applies_to", "represents",
    "presides_over", "filed_in", "supports", "challenges",
    "governed_by", "establishes_precedent"
]

# Financial relationship examples
relationship_types = [
    "trades", "issues", "regulates", "invests_in",
    "correlates_with", "hedges", "settles_through",
    "rated_by", "backed_by", "denominated_in"
]
```

### 3. Update the Extraction Prompt

Modify the main entity extraction prompt to include your domain context:

```python
PROMPTS["entity_extraction"] = """---Goal---
Given a text document about [YOUR DOMAIN], and a list of entity types, 
identify all entities of those types from the text and all relationships 
among the identified entities.

When analyzing [YOUR DOMAIN] data, pay special attention to:
- [Domain-specific considerations]
- [Key entities to look for]
- [Important relationship patterns]
- [Domain terminology and conventions]

# ... rest of prompt structure remains the same
```

### 4. Create Domain-Specific Examples

Provide 2-3 comprehensive examples showing ideal extraction for your domain:

```python
PROMPTS["entity_extraction_examples"] = [
    """Example 1:
    
    Entity_types: [your_entity_types]
    Text:
    ```
    [Domain-specific text sample]
    ```
    
    Output:
    [Show ideal entity and relationship extraction]
    """,
    # Add 2-3 more examples
]
```

## Best Practices

### Relationship Type Design
1. **Be Specific**: Prefer "prescribes" over "related" for medical contexts
2. **Use Verbs**: Relationships should typically be actions or connections
3. **Standardize Format**: Use underscores for multi-word types (`filed_in`, `invested_by`)
4. **Include Direction**: Consider if relationships are directional (`A manages B` vs `B managed_by A`)

### Entity Type Design
1. **Cover Your Domain**: Include all major entity categories in your field
2. **Balance Granularity**: Not too broad (everything is "thing") or too narrow (hundreds of types)
3. **Use Domain Language**: Match terminology your users understand
4. **Consider Hierarchies**: You can have subtypes if needed

### Example Quality
1. **Show Complexity**: Examples should demonstrate challenging but realistic scenarios
2. **Cover Edge Cases**: Include examples of tricky relationship identification
3. **Demonstrate Consistency**: Show how similar patterns should be handled uniformly
4. **Use Real Language**: Examples should use natural language from your domain

## Testing Your Customizations

1. **Start Small**: Test with a few documents first
2. **Check Relationship Quality**: Verify the extracted relationships make sense
3. **Monitor Entity Coverage**: Ensure important entities aren't being missed
4. **Validate Consistency**: Same patterns should extract the same relationship types
5. **Measure Improvement**: Compare knowledge graph quality before/after customization

## Example Configurations

See `docs/examples/` for complete prompt configurations for:
- Healthcare/Medical
- Legal/Regulatory  
- Financial/Investment
- Academic/Research
- Manufacturing/Industrial

## Advanced Features

### Relationship Strength Tuning
You can customize how relationship strength is calculated based on:
- Co-occurrence frequency
- Semantic importance in your domain
- Explicit strength indicators in text

### Multi-Language Support
The prompt system supports extraction in multiple languages - customize the examples and instructions for your target language.

### Custom Validation
Add domain-specific validation rules to ensure extracted relationships meet your quality standards.

---

**Next Steps**: After customizing your prompts, rebuild any existing knowledge graphs to take advantage of the improved extraction quality.