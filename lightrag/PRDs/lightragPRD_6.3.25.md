## PRD: Rectify Relationship Extraction, Data Integrity, and Graph Visualization

**1. Introduction**

This document details the plan to resolve critical issues in LightRAG's knowledge graph pipeline. The primary problems are:
1.  **Relationship Extraction Failure:** Custom relationship types are not being extracted and stored; relationships default to a generic "RELATED" type. This is due to a misaligned parsing logic in `operate.py` with the LLM output format specified in `prompt.py`.
2.  **Graph Visualizer Edge Display Failure:** The graph visualizer fails to render edges and throws a `TypeError: '<' not supported between instances of 'NoneType' and 'NoneType'` when fetching graph data. This is likely caused by `None` or missing edge weights in the graph data, a downstream effect of the relationship parsing errors.

The goal is to ensure accurate processing and persistence of custom relationship types and their attributes, leading to a functional and informative graph visualization.

**2. Problem Statement (Refined)**

1.  **Relationship Data Mis-parsing:** The `_handle_single_relationship_extraction` function in `lightrag/operate.py` incorrectly maps indices from the LLM's output tuple for relationships. Specifically, the `relationship_type` field is misinterpreted as `keywords`, and `relationship_strength` parsing is fragile. This leads to the loss of intended custom relationship types and potentially incorrect or missing edge weights.
2.  **Defaulting to "RELATED" Type:** Due to the mis-parsing, the `advanced_operate.extract_entities_with_types` function defaults to "related" when it cannot find a `relationship_type` key in the initially parsed edge data.
3.  **Visualizer `TypeError` & Missing Edges:** The visualizer's call to `get_knowledge_graph` likely encounters `None` values for edge weights (or other critical edge properties used in comparisons/sorting by NetworkX or the visualizer itself) due to the upstream parsing and data integrity issues, causing the `TypeError`. This also prevents edges from being rendered.

**3. Goals**

*   **Goal 1 (Accurate Relationship Parsing - CRITICAL):** Correct the parsing logic in `lightrag/operate.py` (`_handle_single_relationship_extraction`) to accurately extract `relationship_type`, `relationship_keywords`, and `relationship_strength` according to the format specified in `PROMPTS["entity_extraction"]`.
*   **Goal 2 (Custom Relationship Type Persistence):** Ensure that correctly parsed and then standardized custom relationship types (via `RelationshipTypeRegistry`) are used for creating typed relationships in Neo4j.
*   **Goal 3 (Robust Edge Data & Weight Integrity):** Ensure edge weights are always valid numerical float values in Neo4j (e.g., defaulting to `0.5` or `1.0` if parsing fails or strength is missing), preventing `NoneType` errors.
*   **Goal 4 (Visualizer Edge Display):** Resolve the `TypeError` and enable the graph visualizer to correctly display edges with their respective (custom) relationship types and weights.
*   **Goal 5 (Enhanced Logging):** Improve logging to trace relationship data from raw LLM output through parsing, standardization, and persistence, explicitly showing extracted types, keywords, and strengths.

**4. Proposed Solutions & Technical Requirements**

**4.1. Correcting Relationship Data Parsing and Processing (Goal 1, 2, 3, 5)**

*   **4.1.1. Fix Parsing Logic in `_handle_single_relationship_extraction` (in `lightrag/operate.py`):**
    *   **Requirement - CRITICAL:** Modify the function to correctly map `record_attributes` indices based on the 7-item tuple format (0=indicator, 1=src, 2=tgt, 3=desc, 4=rel_type, 5=keywords, 6=strength).
        ```python
        # In lightrag/operate.py -> _handle_single_relationship_extraction
        async def _handle_single_relationship_extraction(
            record_attributes: list[str],
            chunk_key: str,
            file_path: str = "unknown_source", # Ensure file_path is passed down
        ):
            logger.debug(f"Attempting to parse relationship record: {record_attributes} from chunk {chunk_key}")
            if len(record_attributes) != 7 or '"relationship"' not in record_attributes[0]: # Strict check for 7 elements
                logger.error(f"Malformed relationship record (expected 7 attributes, got {len(record_attributes)}): {record_attributes} from chunk {chunk_key}")
                return None

            source = normalize_extracted_info(clean_str(record_attributes[1]), is_entity=True)
            target = normalize_extracted_info(clean_str(record_attributes[2]), is_entity=True)

            if not source or not target:
                logger.warning(f"Missing source or target for relationship in chunk {chunk_key}: src='{source}', tgt='{target}'")
                return None
            if source == target:
                logger.debug(f"Self-loop relationship skipped for {source} in chunk {chunk_key}")
                return None

            edge_description = normalize_extracted_info(clean_str(record_attributes[3]))
            raw_rel_type = clean_str(record_attributes[4]) # Actual relationship type from LLM
            edge_keywords = normalize_extracted_info(clean_str(record_attributes[5]), is_entity=False) # Actual keywords
            edge_keywords = edge_keywords.replace("，", ",") # Normalize Chinese comma

            raw_strength_str = record_attributes[6].strip('"').strip("'")
            weight = 0.5  # Default weight
            try:
                extracted_weight = float(raw_strength_str)
                if 0.0 <= extracted_weight <= 1.0: # LLM asked for 0-1
                    weight = extracted_weight
                elif 0.0 <= extracted_weight <= 10.0: # LLM might give 0-10
                    weight = extracted_weight / 10.0
                    logger.debug(f"Normalized relationship strength {raw_strength_str} to {weight} for {source}-{target}")
                else:
                    logger.warning(f"Relationship strength '{raw_strength_str}' for {source}-{target} is out of 0.0-10.0 range. Defaulting to {weight}.")
            except ValueError:
                logger.warning(f"Invalid relationship strength '{raw_strength_str}' for {source}-{target}. Defaulting to {weight}.")
            
            logger.info(f"Parsed relationship from chunk {chunk_key}: {source} -[{raw_rel_type}({weight})]-> {target}, Keywords: '{edge_keywords}'")

            return dict(
                src_id=source,
                tgt_id=target,
                weight=weight,
                description=edge_description,
                relationship_type=raw_rel_type, # This is the raw type from LLM
                keywords=edge_keywords,
                source_id=chunk_key,
                file_path=file_path,
            )
        ```
    *   **Logging:** The `logger.info` in the snippet above provides crucial insight into what's parsed. Also log the `record_attributes` at `DEBUG` level.

*   **4.1.2. Ensure `file_path` Propagation:**
    *   **Requirement:** Verify that `file_path` is correctly passed down from `extract_entities` through `_process_single_content` to `_handle_single_entity_extraction` and `_handle_single_relationship_extraction`. The `file_path` is already present in `_process_single_content`'s `chunk_dp`.
    *   **Rationale:** `file_path` is important for provenance and is used in `upsert_edge_detailed`.

*   **4.1.3. Verify `RelationshipTypeRegistry` Usage in `advanced_operate.extract_entities_with_types`:**
    *   **Requirement:** This part of the code seems logically sound, *assuming it now receives the correctly parsed `original_rel_type`*.
        ```python
        # In advanced_operate.py -> extract_entities_with_types, inside the loop for edges:
        original_rel_type = edge.get("relationship_type", "related") # This should now be the LLM's raw type
        # ... rest of the existing logic for standardization ...
        logger.info(f"Relationship type processing for {edge.get('src_id')}-{edge.get('tgt_id')}: LLM raw='{original_rel_type}', Standardized human='{edge['relationship_type']}', Neo4j Label='{edge['neo4j_type']}'")
        ```
    *   **Logging:** The added `logger.info` above and the existing logging suggestions for `RelationshipTypeRegistry.get_neo4j_type` remain critical.

*   **4.1.4. Correct Relationship Type and Robust Weight in `Neo4JStorage.upsert_edge_detailed`:**
    *   **Requirement (Type):**
        ```python
        # In lightrag/kg/neo4j_impl.py -> upsert_edge_detailed
        # The 'rel_type' parameter here should ideally be the human-readable standardized type (e.g., "calls api")
        # if processed by advanced_operate, or the raw LLM type if coming directly.
        # The 'properties' dict should contain 'original_type' (LLM raw) and 'neo4j_type' (for the Cypher label).

        neo4j_label_to_use = properties.get("neo4j_type") # This should be the standardized Neo4j label
        if not neo4j_label_to_use:
            # Fallback if neo4j_type is not in properties: standardize the input `rel_type`
            logger.warning(f"neo4j_type missing in properties for edge {source_id}->{target_id} with input rel_type='{rel_type}'. Standardizing input rel_type.")
            neo4j_label_to_use = self.rel_registry.get_neo4j_type(rel_type)
            properties["neo4j_type"] = neo4j_label_to_use # Store it back
            if "original_type" not in properties:
                 properties["original_type"] = rel_type # Store original if not already there

        logger.info(f"Upserting edge in Neo4j: {source_id}-[{neo4j_label_to_use}]->{target_id}. Input rel_type='{rel_type}', Properties: {properties.get('original_type', 'N/A')}, {properties.get('rel_type', 'N/A')}")

        # Validate neo4j_label_to_use (as before)
        # ...

        query = f"""
        MATCH (src:base {{entity_id: $source_id}}), (tgt:base {{entity_id: $target_id}})
        MERGE (src)-[r:{neo4j_label_to_use}]->(tgt)
        ON CREATE SET r = $properties
        ON MATCH SET r += $properties 
        RETURN r
        """
        ```
    *   **Requirement (Weight):** Before setting `edge_properties["weight"]` ensure `weight` (the parameter to `upsert_edge_detailed`) is a float. If `process_relationship_weight` is called here, ensure its input `weight` is numeric or `None`.
        ```python
        # Ensure 'weight' in edge_properties is a float before upserting.
        # The previous parsing fix (4.1.1) should ensure 'weight' in 'edges_data' (input to this) is float.
        # process_relationship_weight further ensures this.
        current_weight = properties.get("weight")
        if not isinstance(current_weight, float):
            logger.error(f"Edge {source_id}->{target_id} has non-float weight '{current_weight}' before upsert. Defaulting to 0.2.")
            properties["weight"] = 0.2 
        ```
    *   **Rationale:** Final checkpoint for correct Neo4j type usage and robust numeric weights.

**4.2. Fixing Graph Visualizer (Goal 4 & addressing the `TypeError`)**

*   **4.2.1. Ensure Numeric Edge Weights in Neo4j:**
    *   The fixes in 4.1.1 (parsing `relationship_strength`) and 4.1.4 (robust weight handling in `upsert_edge_detailed` calling `process_relationship_weight`) are designed to ensure that the `weight` property stored in Neo4j is always a float. This is the most direct way to prevent the `TypeError` if it's caused by `None` weights.
*   **4.2.2. Verify Data Flow to Visualizer:**
    *   **Requirement:** In `lightrag/kg/neo4j_impl.py -> get_knowledge_graph`, when constructing `KnowledgeGraphEdge` objects, ensure the `weight` property is explicitly cast to `float` and has a default if missing from the database record.
        ```python
        # Inside get_knowledge_graph, when creating KnowledgeGraphEdge
        edge_props_from_db = dict(rel) if rel else {}
        edge_weight = 1.0 # Default if not found or invalid
        try:
            raw_weight = edge_props_from_db.get("weight")
            if raw_weight is not None:
                edge_weight = float(raw_weight)
        except (ValueError, TypeError):
            logger.warning(f"Edge {rel_source}->{rel_target} has invalid DB weight '{raw_weight}'. Defaulting to 1.0.")
        
        # ...
        properties={
            "relationship_type": rel_type, # This is type(r) from Neo4j
            "weight": edge_weight,        # Ensures float
            # ... other properties
        }
        ```
    *   **Requirement:** In `lightrag/tools/lightrag_visualizer/graph_visualizer.py -> load_file`:
        After `self.graph = nx.read_graphml(filepath)`, log a sample of edge attributes, specifically checking for `weight` and its type.
        ```python
        if self.graph and self.graph.edges:
            print("Visualizer: Sample edge data from loaded GraphML:")
            for u, v, data in list(self.graph.edges(data=True))[:5]:
                edge_label = data.get('label', data.get('type', 'N/A')) # Check common attributes for type
                edge_weight = data.get('weight', 'N/A (missing)')
                print(f"Edge ({u})-({edge_label} / w:{edge_weight})->({v}): Data: {data}")
        ```
    *   **Requirement (Visualizer Layout):** In `GraphViewer.calculate_layout`, if `nx.spring_layout` (or any other layout) is ever called with `weight="some_key"`, ensure that `some_key` exists for all edges and is numeric. Currently, it's `weight=None`, which is safer. The `TypeError` might be from Python-side sorting of edges if `max_nodes` is hit in `get_knowledge_graph`.
    *   **Rationale:** Directly addresses the `TypeError` by ensuring weights are numeric throughout the data pipeline leading to the visualizer. Correctly assigns edge types for display.

**5. Implementation Steps (Revised)**

1.  **Branch:** `fix/relationship-visualizer-v2`
2.  **Core Parsing Fix & Logging:** Implement **4.1.1** (fix `_handle_single_relationship_extraction` indexing, add length check, log parsed values) and **4.1.2** (ensure `file_path` propagation).
3.  **Test Parsing Locally:** Create a small test script that calls `_handle_single_relationship_extraction` with sample LLM-like output strings (correctly formatted and malformed) to verify parsing.
4.  **Verify Registry Flow & Logging:** Implement/confirm logging for `extract_entities_with_types` (4.1.2) and `RelationshipTypeRegistry` (4.1.3). Process a test document and trace a relationship type from raw LLM output to standardized type via logs.
5.  **Implement Neo4j Storage Fixes:** Implement changes in `Neo4JStorage.upsert_edge_detailed` (**4.1.4** - use registry for Cypher type, robust weight) and in `get_knowledge_graph` (**4.2.2** - ensure float weight for `KnowledgeGraphEdge`).
6.  **End-to-End Test (Data Integrity):**
    *   Reprocess a test document.
    *   Verify all new logs for correct data flow.
    *   Query Neo4j: `MATCH ()-[r]-() RETURN type(r), r.original_type, r.rel_type, r.neo4j_type, r.weight LIMIT 25`. Confirm custom types for `type(r)` and that `r.weight` is always a float.
7.  **Visualizer Testing:**
    *   Export GraphML from the corrected Neo4j data. Inspect it for edge labels and numeric weights (4.2.1).
    *   Load into the visualizer. Add logging as per 4.2.2 (Visualizer Edge Data Parsing). The `TypeError` should be resolved. Edges should render.
8.  **Refine & Cleanup:** Adjust log levels. Remove temporary print statements.
9.  **Documentation:** Update developer notes on expected relationship tuple format from LLM and debugging tips for this pipeline stage.
10. **PR and Code Review.**

**6. Testing & Validation (Updated Focus)**

*   **Unit Tests:**
    *   **CRITICAL:** Test `_handle_single_relationship_extraction` with various `record_attributes` inputs (correct length, incorrect length, various `relationship_type` strings, valid/invalid/missing `relationship_strength` strings).
    *   Test `Neo4JStorage.upsert_edge_detailed` for correct Cypher query generation with standardized types.
*   **Integration Tests:**
    *   Process documents yielding diverse relationship types and strengths.
    *   Verify Neo4j data: `type(r)` shows custom types, `r.weight` is float.
    *   Verify GraphML output for correct edge labels and numeric weights.
    *   Verify visualizer loads graph without `TypeError` and displays edges.

**7. Expected Outcome**

*   `_handle_single_relationship_extraction` correctly parses all 6 fields (description, type, keywords, strength) from the 7-item relationship tuple from the LLM.
*   Custom relationship types are accurately stored in Neo4j (e.g., `CALLS_API`).
*   Edge `weight` properties in Neo4j are always valid floats.
*   The `TypeError` in the graph visualizer is resolved.
*   The graph visualizer displays edges. (Displaying *labels* on edges in the visualizer itself might be a separate UI enhancement if not already present, but the lines should draw).
*   Logging clearly shows the journey of relationship data.

This refined PRD tackles the root parsing issue head-on, which should cascade fixes to the downstream problems.
