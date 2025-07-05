from __future__ import annotations
from typing import Any

GRAPH_FIELD_SEP = "<SEP>"

PROMPTS: dict[str, Any] = {}

PROMPTS["DEFAULT_LANGUAGE"] = "English"
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

# Updated entity types based on your training data
PROMPTS["DEFAULT_ENTITY_TYPES"] = [
    "tool",
    "technology",
    "concept",
    "workflow",
    "artifact",
    "person",
    "organization",
]

PROMPTS["DEFAULT_USER_PROMPT"] = "n/a"

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

**SPECIAL HANDLING FOR STRUCTURED SECTIONS**:
When encountering sections like "## Entities and Concepts", "## Tools and Technologies", or "## Relationships and Connections":
1. Recognize these contain PRE-EXTRACTED, well-documented entities and relationships
2. DO NOT re-extract entities that are already listed with descriptions in these sections
3. Focus on identifying any NEW entities or relationships mentioned in narrative text that aren't in these catalogs
4. If an entity is mentioned in both structured and narrative sections, prefer the structured documentation

**CRITICAL EXCLUSIONS - DO NOT EXTRACT THE FOLLOWING:**

❌ **Already Well-Documented Entities**:
- When processing structured catalog sections (## Entities and Concepts, ## Tools and Technologies, ## Relationships and Connections), be aware these are PRE-EXTRACTED entities
- Do NOT create duplicate entities for items already comprehensively documented in these sections
- Only extract NEW information or relationships not already captured in the structured format

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

PROMPTS["entity_extraction_examples"] = [
    """Example 1:

Entity_types: [tool, technology, workflow, concept, person]
Text:
```
During the session, Jason used n8n to create a Lead Enricher Workflow. This workflow integrated with the Brave Search API to gather company information. Claude AI was extensively used by Jason for debugging JavaScript code in the n8n Code Nodes. The developer implemented data transformation logic to parse JSON responses from the API.

The workflow encountered errors like "Code doesn't return items properly", which were resolved through iterative debugging with Claude AI. The AI assistant helped Jason refine the JavaScript code to ensure proper JSON formatting and data structure.
```

Output:
("entity"{tuple_delimiter}"Jason"{tuple_delimiter}"person"{tuple_delimiter}"The developer and user who creates workflows, debugs code, and works with various automation tools and APIs."){record_delimiter}
("entity"{tuple_delimiter}"n8n"{tuple_delimiter}"tool"{tuple_delimiter}"n8n is a workflow automation platform used for building data pipelines and integrating various services."){record_delimiter}
("entity"{tuple_delimiter}"Lead Enricher Workflow"{tuple_delimiter}"workflow"{tuple_delimiter}"A workflow designed to gather and enrich company and contact information from multiple sources."){record_delimiter}
("entity"{tuple_delimiter}"Brave Search API"{tuple_delimiter}"tool"{tuple_delimiter}"A web search API used for gathering company information and web data."){record_delimiter}
("entity"{tuple_delimiter}"Claude AI"{tuple_delimiter}"tool"{tuple_delimiter}"An AI assistant used extensively for debugging code and providing development assistance."){record_delimiter}
("entity"{tuple_delimiter}"JavaScript"{tuple_delimiter}"technology"{tuple_delimiter}"Programming language used in n8n Code Nodes for custom data manipulation."){record_delimiter}
("entity"{tuple_delimiter}"n8n Code Node"{tuple_delimiter}"tool"{tuple_delimiter}"A node within n8n that allows execution of custom JavaScript code."){record_delimiter}
("entity"{tuple_delimiter}"Data Transformation"{tuple_delimiter}"concept"{tuple_delimiter}"The process of converting data from one format to another for compatibility between systems."){record_delimiter}
("entity"{tuple_delimiter}"JSON"{tuple_delimiter}"technology"{tuple_delimiter}"A data format used for API responses and data interchange."){record_delimiter}
("relationship"{tuple_delimiter}"Jason"{tuple_delimiter}"n8n"{tuple_delimiter}"Jason uses n8n to create and manage automation workflows."{tuple_delimiter}"uses"{tuple_delimiter}"tool usage, workflow creation"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Jason"{tuple_delimiter}"Lead Enricher Workflow"{tuple_delimiter}"Jason created the Lead Enricher Workflow for data gathering."{tuple_delimiter}"creates"{tuple_delimiter}"workflow development, automation"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Jason"{tuple_delimiter}"Claude AI"{tuple_delimiter}"Jason extensively uses Claude AI for debugging JavaScript code and getting development assistance."{tuple_delimiter}"uses"{tuple_delimiter}"AI assistance, debugging"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Lead Enricher Workflow"{tuple_delimiter}"n8n"{tuple_delimiter}"The Lead Enricher Workflow is built and executed within the n8n platform."{tuple_delimiter}"runs_on"{tuple_delimiter}"workflow automation, platform usage"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Lead Enricher Workflow"{tuple_delimiter}"Brave Search API"{tuple_delimiter}"The workflow integrates with Brave Search API to gather company information."{tuple_delimiter}"calls_api"{tuple_delimiter}"api integration, data acquisition"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Claude AI"{tuple_delimiter}"JavaScript"{tuple_delimiter}"Claude AI assists in debugging and refining JavaScript code for the workflow."{tuple_delimiter}"debugs"{tuple_delimiter}"code assistance, debugging"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"n8n Code Node"{tuple_delimiter}"JavaScript"{tuple_delimiter}"The n8n Code Node executes custom JavaScript code for data processing."{tuple_delimiter}"executes"{tuple_delimiter}"code execution, custom logic"{tuple_delimiter}10){record_delimiter}
("relationship"{tuple_delimiter}"n8n Code Node"{tuple_delimiter}"Data Transformation"{tuple_delimiter}"Code Nodes perform data transformation operations on API responses."{tuple_delimiter}"processes"{tuple_delimiter}"data processing, transformation"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Brave Search API"{tuple_delimiter}"JSON"{tuple_delimiter}"The API returns responses in JSON format that need to be parsed."{tuple_delimiter}"returns"{tuple_delimiter}"api response, data format"{tuple_delimiter}7){completion_delimiter}
#############################
""",
    """Example 2:

Entity_types: [tool, technology, concept, artifact, workflow]
Text:
```
The automated backup system was implemented using Bash scripts and cron jobs. Initially, systemd was attempted but proved problematic. Claude AI provided a setup-backup-cron.sh script that creates a wrapper to handle the NVM environment for Node.js. The backup script exports all n8n workflows to timestamped JSON files for preservation.
```

Output:
("entity"{tuple_delimiter}"Automated Backup System"{tuple_delimiter}"workflow"{tuple_delimiter}"A system designed to automatically backup n8n workflows on a scheduled basis."){record_delimiter}
("entity"{tuple_delimiter}"Bash Script"{tuple_delimiter}"technology"{tuple_delimiter}"Shell scripting language used for automation tasks on Unix-like systems."){record_delimiter}
("entity"{tuple_delimiter}"cron"{tuple_delimiter}"tool"{tuple_delimiter}"A time-based job scheduler in Unix-like operating systems for automating tasks."){record_delimiter}
("entity"{tuple_delimiter}"systemd"{tuple_delimiter}"tool"{tuple_delimiter}"A system and service manager for Linux that was initially attempted for scheduling."){record_delimiter}
("entity"{tuple_delimiter}"Claude AI"{tuple_delimiter}"tool"{tuple_delimiter}"AI assistant that provided script generation and technical guidance."){record_delimiter}
("entity"{tuple_delimiter}"setup-backup-cron.sh"{tuple_delimiter}"artifact"{tuple_delimiter}"A Bash script that automates the setup of cron-based n8n workflow backup."){record_delimiter}
("entity"{tuple_delimiter}"NVM"{tuple_delimiter}"tool"{tuple_delimiter}"Node Version Manager used to manage Node.js environments."){record_delimiter}
("entity"{tuple_delimiter}"Node.js"{tuple_delimiter}"technology"{tuple_delimiter}"JavaScript runtime environment required for n8n operation."){record_delimiter}
("entity"{tuple_delimiter}"n8n workflows"{tuple_delimiter}"artifact"{tuple_delimiter}"Workflow definitions that need to be backed up for preservation."){record_delimiter}
("entity"{tuple_delimiter}"JSON files"{tuple_delimiter}"artifact"{tuple_delimiter}"Timestamped backup files containing exported workflow data."){record_delimiter}
("relationship"{tuple_delimiter}"Automated Backup System"{tuple_delimiter}"Bash Script"{tuple_delimiter}"The backup system is implemented using Bash scripts."{tuple_delimiter}"implements"{tuple_delimiter}"implementation, scripting"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Automated Backup System"{tuple_delimiter}"cron"{tuple_delimiter}"Cron is used to schedule the automated backup executions."{tuple_delimiter}"schedules"{tuple_delimiter}"scheduling, automation"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Claude AI"{tuple_delimiter}"setup-backup-cron.sh"{tuple_delimiter}"Claude AI generated the setup script for the backup system."{tuple_delimiter}"generates"{tuple_delimiter}"code generation, assistance"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"setup-backup-cron.sh"{tuple_delimiter}"NVM"{tuple_delimiter}"The setup script configures NVM environment for proper execution."{tuple_delimiter}"configures"{tuple_delimiter}"environment setup, configuration"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"NVM"{tuple_delimiter}"Node.js"{tuple_delimiter}"NVM manages the Node.js version required for n8n."{tuple_delimiter}"manages"{tuple_delimiter}"version management, runtime"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"n8n workflows"{tuple_delimiter}"JSON files"{tuple_delimiter}"Workflows are exported and saved as timestamped JSON files."{tuple_delimiter}"exports_to"{tuple_delimiter}"data export, backup"{tuple_delimiter}9){completion_delimiter}
#############################
""",
    """Example 3:

Entity_types: [tool, concept, technology, organization]
Text:
```
The team implemented semantic search using OpenAI embeddings in their RAG pipeline. The system vectorizes documents and stores them in a Neo4j knowledge graph for efficient retrieval.
```

Output:
("entity"{tuple_delimiter}"Semantic Search"{tuple_delimiter}"concept"{tuple_delimiter}"A search technique that understands the intent and contextual meaning of search queries."){record_delimiter}
("entity"{tuple_delimiter}"OpenAI"{tuple_delimiter}"organization"{tuple_delimiter}"AI company providing embedding models and APIs for natural language processing."){record_delimiter}
("entity"{tuple_delimiter}"Embeddings"{tuple_delimiter}"technology"{tuple_delimiter}"Vector representations of text that capture semantic meaning."){record_delimiter}
("entity"{tuple_delimiter}"RAG Pipeline"{tuple_delimiter}"workflow"{tuple_delimiter}"Retrieval-Augmented Generation pipeline for enhanced AI responses."){record_delimiter}
("entity"{tuple_delimiter}"Neo4j"{tuple_delimiter}"tool"{tuple_delimiter}"Graph database used for storing and querying knowledge graphs."){record_delimiter}
("entity"{tuple_delimiter}"Knowledge Graph"{tuple_delimiter}"concept"{tuple_delimiter}"A structured representation of entities and their relationships for efficient retrieval."){record_delimiter}
("relationship"{tuple_delimiter}"Semantic Search"{tuple_delimiter}"OpenAI"{tuple_delimiter}"Semantic search is implemented using OpenAI's embedding technology."{tuple_delimiter}"uses"{tuple_delimiter}"implementation, AI integration"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"OpenAI"{tuple_delimiter}"Embeddings"{tuple_delimiter}"OpenAI provides the embedding models for text vectorization."{tuple_delimiter}"provides"{tuple_delimiter}"model provision, technology"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"RAG Pipeline"{tuple_delimiter}"Semantic Search"{tuple_delimiter}"The RAG pipeline incorporates semantic search for document retrieval."{tuple_delimiter}"incorporates"{tuple_delimiter}"pipeline component, search integration"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Embeddings"{tuple_delimiter}"Neo4j"{tuple_delimiter}"Document embeddings are stored in Neo4j for retrieval."{tuple_delimiter}"stored_in"{tuple_delimiter}"data storage, vectorization"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Neo4j"{tuple_delimiter}"Knowledge Graph"{tuple_delimiter}"Neo4j serves as the database for the knowledge graph implementation."{tuple_delimiter}"hosts"{tuple_delimiter}"graph storage, database"{tuple_delimiter}10){completion_delimiter}
#############################
""",
]

PROMPTS[
    "summarize_entity_descriptions"
] = """You are a specialized technical documentation analyst responsible for consolidating entity information.
Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
Please create a single, comprehensive description that captures the entity's role in workflows and technical processes.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity names so we have the full context.

For technical entities (tools, technologies, workflows), ensure the summary includes:
- Primary purpose and functionality
- Key features or capabilities
- How it integrates with other tools/systems
- Common use cases in development/automation contexts

Use {language} as output language.

#######
---Data---
Entities: {entity_name}
Description List: {description_list}
#######
Output:
"""

PROMPTS["entity_continue_extraction"] = """You are a specialized technical documentation analyzer. Some additional entities and relationships may have been missed in the last extraction.

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

---Remember Steps---

1. Identify key entities that were missed. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify pairs of (source_entity, target_entity) that have **explicit, meaningful relationships** documented in the text.
**Apply the same strict criteria as before - only extract relationships that are clearly stated, not inferred**
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_type: Choose the most appropriate relationship type from the following list. If none fit exactly, choose "related":
  {relationship_types}

  **IMPORTANT: For multi-word relationship types, use underscores to separate words (e.g., 'created_by', 'integrates_with', 'calls_api'). Do not concatenate words without separators.**
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
- relationship_keywords: one or more high-level key words that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_type>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Return output in {language} as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. When finished, output {completion_delimiter}

**CRITICAL EXCLUSIONS - DO NOT EXTRACT:**
- Entities already documented in structured catalog sections (## Entities and Concepts, ## Tools and Technologies, ## Relationships and Connections)
- Fragment/incomplete items, generic placeholders, status metrics, or UI elements
- Anything that is merely listed without active usage context
- Duplicate entities when comprehensive documentation already exists in structured sections

---Output---

Add them below using the same format:
""".strip()

PROMPTS["entity_if_loop_extraction"] = """
---Goal---

It appears some entities may have still been missed. Check for:
- Additional tools or services not yet captured
- Technologies or frameworks mentioned in passing
- Implicit workflows or processes
- Concepts that were applied but not explicitly named

---Output---

Answer ONLY by `YES` OR `NO` if there are still entities that need to be added.
""".strip()

PROMPTS["fail_response"] = (
    "Sorry, I'm not able to provide an answer to that question.[no-context]"
)

PROMPTS["rag_response"] = """---Role---

You are a specialized technical documentation assistant with expertise in workflow automation, development processes, and technical troubleshooting, responding to queries using the Knowledge Graph and Document Chunks provided in JSON format below.

---Goal---

Generate a concise response based on Knowledge Base and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

When handling relationships with timestamps:
1. Each relationship has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting relationships, consider both the semantic content and the timestamp
3. Don't automatically prefer the most recently created relationships - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

For technical queries:
- Provide practical insights and patterns observed across sessions
- Highlight common workflows, tools, and integrations
- Include relevant error resolutions and debugging approaches when applicable

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- List up to 5 most important reference sources at the end under "References" section. Clearly indicating whether each source is from Knowledge Graph (KG) or Document Chunks (DC), and include the file path if available, in the following format: [KG/DC] file_path
- If you don't know the answer, just say so.
- Do not make anything up. Do not include information not provided by the Knowledge Base.
- Additional user prompt: {user_prompt}

Response:"""

PROMPTS["keywords_extraction"] = """---Role---

You are a specialized technical keyword analyst with expertise in workflow automation, development tools, and technical documentation, tasked with identifying both high-level and low-level keywords in queries and conversation history.

---Goal---

Given the query and conversation history, list both high-level and low-level keywords. High-level keywords focus on overarching concepts or themes, while low-level keywords focus on specific entities, details, or concrete terms.

For technical queries, ensure you capture:
- Tool and service names (both generic and specific versions)
- Programming languages and frameworks
- Technical concepts and patterns
- Workflow types and automation terms
- Error types and debugging approaches

---Instructions---

- Consider both the current query and relevant conversation history when extracting keywords
- Output the keywords in JSON format, it will be parsed by a JSON parser, do not add any extra content in output
- The JSON should have two keys:
  - "high_level_keywords" for overarching concepts or themes
  - "low_level_keywords" for specific entities or details

######################
---Examples---
######################
{examples}

#############################
---Real Data---
######################
Conversation History:
{history}

Current Query: {query}
######################
The `Output` should be human text, not unicode characters. Keep the same language as `Query`.
Output:

"""

PROMPTS["keywords_extraction_examples"] = [
    """Example 1:

Query: "How do I debug n8n workflow errors when integrating with external APIs?"
################
Output:
{
  "high_level_keywords": ["Workflow debugging", "API integration", "Error handling", "n8n automation"],
  "low_level_keywords": ["n8n", "workflow errors", "external APIs", "debugging", "integration issues", "API errors"]
}
#############################""",
    """Example 2:

Query: "What's the best way to implement automated backups for workflow configurations?"
################
Output:
{
  "high_level_keywords": ["Automated backups", "Workflow preservation", "Configuration management", "System automation"],
  "low_level_keywords": ["backup scripts", "cron jobs", "workflow export", "JSON files", "scheduling", "configuration files"]
}
#############################""",
    """Example 3:

Query: "How can I use Claude AI to help with JavaScript code in n8n Code Nodes?"
################
Output:
{
  "high_level_keywords": ["AI-assisted development", "Code generation", "Workflow automation", "LLM integration"],
  "low_level_keywords": ["Claude AI", "JavaScript", "n8n Code Nodes", "code debugging", "AI assistance", "custom functions"]
}
#############################""",
]

PROMPTS["naive_rag_response"] = """---Role---

You are a specialized technical documentation assistant responding to queries about workflows and development sessions using Document Chunks provided in JSON format below.

---Goal---

Generate a concise response based on Document Chunks and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Document Chunks, and incorporating general knowledge relevant to the Document Chunks. Do not include information not provided by Document Chunks.

When handling content with timestamps:
1. Each piece of content has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting information, consider both the content and the timestamp
3. Don't automatically prefer the most recent content - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

For technical content:
- Focus on actionable insights and patterns
- Highlight tool integrations and workflows
- Include relevant troubleshooting information when available

---Conversation History---
{history}

---Document Chunks(DC)---
{content_data}

---Response Rules---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- List up to 5 most important reference sources at the end under "References" section. Clearly indicating each source from Document Chunks(DC), and include the file path if available, in the following format: [DC] file_path
- If you don't know the answer, just say so.
- Do not include information not provided by the Document Chunks.
- Additional user prompt: {user_prompt}

Response:"""

# TODO: deprecated
PROMPTS[
    "similarity_check"
] = """Please analyze the similarity between these two questions:

Question 1: {original_prompt}
Question 2: {cached_prompt}

Please evaluate whether these two questions are semantically similar, and whether the answer to Question 2 can be used to answer Question 1, provide a similarity score between 0 and 1 directly.

Similarity score criteria:
0: Completely unrelated or answer cannot be reused, including but not limited to:
   - The questions have different topics
   - The tools or technologies mentioned are different
   - The workflows or processes are different
   - The error messages or issues are different
   - The specific integrations are different
   - The background context is different
   - The key technical requirements are different
1: Identical and answer can be directly reused
0.5: Partially related and answer needs modification to be used
Return only a number between 0-1, without any additional content.
"""

PROMPTS["relationship_post_processing"] = """---Role---
You are a specialized technical workflow analyst and knowledge graph quality assurance expert.

---Goal---
You are analyzing extracted entities and relationships from a technical document to improve accuracy and remove noise.

**IMPORTANT - Identity Resolution**:
Before processing, ensure these identity mappings are applied:
- ANY reference to "User", "user", "the user", or "a user" should be treated as "Jason"
- ANY reference to "Jaywalked" or "jaywalked" should be treated as "Jason" (this is Jason's username)
- ANY reference to "Jay" should be treated as "Jason" (this is Jason's nickname when talking to Claude)
- ANY reference to "Jason Cox" should be treated as "Jason" (use first name only)
- These are all the same person and should be consolidated into a single "Jason" entity

---Context---
DOCUMENT CONTENT:
{document_text}

EXTRACTED ENTITIES:
{entities_list}

EXTRACTED RELATIONSHIPS:
{relationships_list}

---Task---
Review and filter these relationships for accuracy and relevance. Your goal is to achieve 85-90% relationship accuracy by keeping only the most valuable and well-supported relationships.

**VALIDATION CRITERIA:**
1. **Document Evidence**: Relationship must be explicitly supported by document content
2. **Specificity**: Avoid abstract/generic relationships like "Users implements Parallel Technical Tasks"
3. **Practical Value**: Keep relationships that provide meaningful insights about the document
4. **Avoid Noise**: Remove relationships based on coincidental mentions or weak associations
5. **Preserve Relationship Types**: KEEP the original rel_type (e.g., "uses", "runs_on", "creates") unless it is factually incorrect. Do NOT change specific relationship types to generic "related"
6. **Entity Quality Check**: If an entity is a low-value fragment (error fragments, single symbols, generic file extensions), mark any relationships involving it for removal

**FILTERING GUIDELINES:**
✅ KEEP relationships that are:
- Explicitly stated tool usage ("Jason uses n8n to create workflows")
- Clear technical connections ("n8n runs Reddit Scrape To DB Workflow")
- Specific troubleshooting actions ("Jason debugs PostgreSQL connection error")
- Well-documented integrations ("Google Gemini Chat Model integrates with Gmail")
- Meaningful error resolution ("Jason resolves Git index.lock file error")

❌ REMOVE relationships that are:
- Too abstract ("Users implements Data Transformations")
- Based on weak associations ("Business Research investigates Hotworx")
- Involving low-value entities (error fragments, single symbols, placeholder files)
- Generic concepts without specific evidence
- Relationships with entities like: "$index", "#", "1.png", ".py files", "404", "97% storage"
- Redundant or duplicate meanings

**QUALITY SCORING** (1-10 scale):
- 9-10: Explicitly stated, high practical value
- 7-8: Well-supported, clear evidence
- 5-6: Moderately supported, some evidence
- 3-4: Weak evidence, questionable value
- 1-2: No clear evidence, likely noise

**CONFIDENCE THRESHOLD**: Keep relationships scoring 6 or higher.

---Output Format---
Respond with valid JSON only:

```json
{{
  "validated_relationships": [
    {{
      "src_id": "entity1",
      "tgt_id": "entity2",
      "rel_type": "uses",
      "description": "clear description of the relationship",
      "quality_score": 8,
      "evidence": "specific reference or quote from document supporting this relationship",
      "weight": 0.9,
      "source_id": "original_chunk_id"
    }}
  ],
  "removed_relationships": [
    {{
      "src_id": "entity1",
      "tgt_id": "entity2",
      "rel_type": "original_type",
      "reason": "specific reason for removal (e.g., 'too abstract', 'no document evidence', 'weak association')"
    }}
  ],
  "processing_summary": {{
    "total_input": 150,
    "validated": 85,
    "removed": 65,
    "accuracy_improvement": "Removed abstract relationships and unsupported associations",
    "average_quality_score": 7.2
  }}
}}
```

**CRITICAL INSTRUCTION**: You MUST preserve the exact original relationship type (rel_type) from the input relationships. Do NOT convert specific types like "uses", "runs_on", "processes", "implements", "stores", "creates", etc. to generic "related". The relationship types carry important semantic meaning that must be maintained.

Examples of what to preserve:
- "Gmail -[\"processes\"]-> Email Content" → Keep "processes"
- "n8n workflows -[\"runs_on\"]-> n8n" → Keep "runs_on"
- "SAIL POS -[\"stores\"]-> Customer Data" → Keep "stores"
- "Zoom -[\"implements\"]-> Screen Sharing" → Keep "implements"

Only change rel_type if it's factually incorrect (e.g., "eats" should be "uses" for software).

Focus on relationships that a domain expert reviewing this document would find genuinely useful and accurate.
"""
