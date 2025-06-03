This is frustrating, but the logs are giving us clear pointers. The fact that you see:

1.  `INFO: Merged edge Automated Testing -> Continuous Integration: neo4j_type='None', rel_type='related', relationship_type='related', original_type='related', weight=0.9`
    *   This log comes from *your new logging* in `_merge_edges_then_upsert` (from the last PRD).
    *   It clearly shows that **at the point of completing the merge logic within `_merge_edges_then_upsert`**, the `merged_edge` dictionary *already* has `neo4j_type='None'` and all other type fields defaulted to `'related'`.

2.  `WARNING: neo4j_type missing in input properties for edge ... using rel_type='related'. Standardizing.`
    *   This warning from `Neo4JStorage.upsert_edge_detailed` confirms that the `properties` dictionary it received (which is a copy of `merged_edge`) indeed did not have a `neo4j_type` key, and the `rel_type` parameter passed to it was already 'related'.

**Conclusion from the Logs:**

The problem is **not** in `Neo4JStorage.upsert_edge_detailed`'s final decision to use "RELATED". That's a fallback because the correct type information isn't reaching it.
The problem **is** within `operate.py`'s `_merge_edges_then_upsert` function. The logic intended to preserve or correctly determine the `neo4j_type`, `original_type`, and `rel_type` for the `merged_edge` is failing.

Let's re-examine the proposed logic for `_merge_edges_then_upsert` from the previous PRD, focusing on how type fields are initialized and updated:

```python
# Previous PRD's suggestion for _merge_edges_then_upsert
# ...
        first_edge = edges[0]
        merged_edge = {
            "src_id": src_id,
            "tgt_id": tgt_id,
            "weight": 0.0,
            "description": "",
            "keywords": [], 
            "source_id": [], 
            "file_path": [], 
            "relationship_type": first_edge.get("relationship_type", "related"), # Human-readable std FROM FIRST EDGE
            "original_type": first_edge.get("original_type", first_edge.get("relationship_type", "related")), # LLM raw FROM FIRST EDGE
            "neo4j_type": first_edge.get("neo4j_type", "RELATED"), # Neo4j label FROM FIRST EDGE
            "created_at": int(time.time()) 
        }

        # Iterate through all edge instances to merge their properties
        for i, edge in enumerate(edges):
            # ... (weight, description, keywords, source_id, file_path merging) ...

            # Type Curation: Prioritize more specific types.
            current_neo4j_type = edge.get("neo4j_type", "RELATED") # Get neo4j_type from *current* edge in loop
            # THE BUG IS LIKELY HERE:
            if merged_edge.get("neo4j_type", "RELATED") == "RELATED" and current_neo4j_type != "RELATED":
                merged_edge["neo4j_type"] = current_neo4j_type
                merged_edge["relationship_type"] = edge.get("relationship_type", current_neo4j_type.lower().replace('_',' '))
                merged_edge["original_type"] = edge.get("original_type", current_neo4j_type.lower().replace('_',' '))
                # merged_edge["rel_type"] should also be updated here, this was missed in last PRD's snippet for merge logic
                merged_edge["rel_type"] = edge.get("relationship_type", current_neo4j_type.lower().replace('_',' ')) 
                logger.debug(f"Updated merged edge type for {src_id}->{tgt_id} to Neo4j Type: {merged_edge['neo4j_type']} (from instance with original: {edge.get('original_type')})")
            elif current_neo4j_type != "RELATED" and merged_edge.get("neo4j_type") != current_neo4j_type:
                logger.warning(f"Type conflict during merge for {src_id}->{tgt_id}: existing '{merged_edge.get('neo4j_type')}', new '{current_neo4j_type}'. Keeping existing.")
        # ...
        # Final logging of merged_edge:
        logger.info(f"Final merged edge data for {src_id}->{tgt_id}: "
                    f"neo4j_type='{merged_edge.get('neo4j_type', 'N/A')}', " # THIS SHOWS 'None' in your log
                    f"rel_type='{merged_edge.get('rel_type', 'N/A')}', " # THIS SHOWS 'related'
                    # ...
        )
```

**Potential Reasons Why `merged_edge` Ends Up with Default/None Types:**

1.  **Initialization Problem:** If `edges[0]` (the first edge instance being merged) *itself* has missing or defaulted type fields (`relationship_type`, `original_type`, `neo4j_type`), then `merged_edge` will be initialized with these incorrect/default values. If subsequent `edge` instances in the loop also have defaulted types or their `neo4j_type` is "RELATED", the "Type Curation" logic won't update it to something more specific.
2.  **`advanced_operate.extract_entities_with_types` Not Setting Types Correctly:** This is less likely given the successful "Parsed relationship" logs, but it's a possibility that the `edge` dictionaries *entering* `_merge_edges_then_upsert` are already faulty.
    *   The `extract_entities_with_types` function (diff from previous session) was modified to use `simple_neo4j_standardize` instead of the full registry for `neo4j_type`.
        ```python
        # advanced_operate.py
        original_rel_type = edge.get("relationship_type", "related")
        neo4j_type = simple_neo4j_standardize(original_rel_type) # This is the key line
        edge["relationship_type"] = neo4j_type.lower().replace('_', ' ')
        edge["original_type"] = original_rel_type
        edge["neo4j_type"] = neo4j_type # neo4j_type is set here
        ```
        This looks like it *should* be setting `neo4j_type` correctly on each individual `edge` dictionary *before* they are passed to `_merge_edges_then_upsert`.

3.  **Logic Error in Type Curation during Merge:**
    *   The condition `merged_edge.get("neo4j_type", "RELATED") == "RELATED"` means that if `merged_edge` was initialized with a specific type from `edges[0]`, but `edges[0]["neo4j_type"]` was *already* "RELATED" (perhaps because the LLM outputted "related" or the registry defaulted it), then subsequent specific types from other `edge` instances in the loop *would not* overwrite it. This is not the desired behavior; we want the *most specific type found across all instances* being merged.
    *   The `rel_type` field (human-readable standardized) for `merged_edge` might not be getting updated consistently with `neo4j_type` and `original_type` inside the type curation block.

**Troubleshooting & PRD Revision:**

The PRD needs to focus intensely on the `_merge_edges_then_upsert` logic.

---
## PRD: Correct Relationship Type Propagation in Merge & Upsert Pipeline (Revision 2)

**1. Introduction**

This document addresses the persistent issue of custom relationship types defaulting to "RELATED" during Neo4j ingestion, despite successful initial parsing from LLM output. Log analysis indicates the type information is lost or incorrectly defaulted within the `operate.py/_merge_edges_then_upsert` function. This revision focuses on rectifying this specific data propagation problem.

**2. Problem Statement (Further Refined)**

Log output `INFO: Merged edge ...: neo4j_type='None', rel_type='related', ...` clearly shows that by the end of the `_merge_edges_then_upsert` function in `operate.py`, the `merged_edge` dictionary has lost specific type information (its `neo4j_type` is 'None' and `rel_type` is 'related'). This occurs even though individual edge instances fed into the merge process (from `advanced_operate.extract_entities_with_types`) have correctly populated `neo4j_type`, `original_type`, and `relationship_type` fields. The current merge logic for type fields is flawed.

**3. Goals**

*   **Goal 1 (Correct Type Merging):** Revise `operate.py/_merge_edges_then_upsert` to accurately aggregate and select the most specific/appropriate `neo4j_type`, `original_type`, and `rel_type` from all edge instances being merged for a single conceptual relationship.
*   **Goal 2 (Consistent Neo4j Labels):** Ensure the `Neo4JStorage.upsert_edge_detailed` method receives and uses the correctly merged and prioritized `neo4j_type` for Cypher relationship labels.
*   **Goal 3 (Visualizer Edge Types):** Enable the graph visualizer to display edges with their true custom types.
*   **Goal 4 (Clearer Logging):** Add specific logging to track the type selection process during the merge.

**4. Proposed Solutions & Technical Requirements**

**4.1. Revise Type Handling in `_merge_edges_then_upsert` (in `lightrag/operate.py`) - Goal 1, 2, 4**

*   **Requirement - CRITICAL:** The logic for initializing and updating type-related fields in `merged_edge` needs to be more robust. It should prioritize non-generic types.
    ```python
    # In lightrag/operate.py -> _merge_edges_then_upsert
    async def _merge_edges_then_upsert(
        src_id: str,
        tgt_id: str,
        edges: list[dict], # List of edge dicts from extract_entities_with_types
        knowledge_graph_inst: BaseGraphStorage,
        global_config: dict[str, Any],
        # ... other params ...
    ) -> dict | None:
        if not edges:
            logger.warning(f"No edges provided to merge for {src_id} -> {tgt_id}")
            return None
            
        logger.debug(f"Merging {len(edges)} edge instances for {src_id} -> {tgt_id}")

        # Initialize merged_edge with defaults that clearly indicate no specific type yet.
        # We will iterate through all edges to find the best type.
        merged_edge = {
            "src_id": src_id,
            "tgt_id": tgt_id,
            "weight": 0.0,
            "description": "",
            "keywords": [], 
            "source_id": [], 
            "file_path": [], 
            "relationship_type": "related", # Default human-readable std
            "original_type": "related",     # Default LLM raw
            "neo4j_type": "RELATED",      # Default Neo4j label
            "created_at": int(time.time())
        }
        
        # Iterate through all edge instances to merge their properties
        all_original_types = []
        all_neo4j_types = []

        for i, edge_instance in enumerate(edges):
            logger.debug(f"Processing instance {i+1}/{len(edges)} for merge {src_id}->{tgt_id}: "
                         f"original_type='{edge_instance.get('original_type')}', "
                         f"rel_type='{edge_instance.get('relationship_type')}', " # This is human-readable-std from advanced_operate
                         f"neo4j_type='{edge_instance.get('neo4j_type')}'")

            merged_edge["weight"] += float(edge_instance.get("weight", 0.5))

            if edge_instance.get("description"):
                if merged_edge["description"]:
                    merged_edge["description"] += f"{GRAPH_FIELD_SEP}{edge_instance['description']}"
                else:
                    merged_edge["description"] = edge_instance["description"]
            
            # Keywords merging (from previous PRD, ensure this is robust)
            new_keywords = edge_instance.get("keywords", [])
            # ... (robust keyword merging logic as discussed previously, ensuring it's a list of strings)
            current_keywords_list = merged_edge.get("keywords", [])
            if not isinstance(current_keywords_list, list): current_keywords_list = [str(current_keywords_list)] if current_keywords_list else []
            
            if isinstance(new_keywords, str): new_keywords = [kw.strip() for kw in new_keywords.split(',') if kw.strip()]
            elif not isinstance(new_keywords, list): new_keywords = [str(new_keywords).strip()] if new_keywords else []
            
            temp_new_keywords_list = []
            for item_kw in new_keywords:
                if isinstance(item_kw, str): temp_new_keywords_list.append(item_kw.strip())
                elif isinstance(item_kw, list): # Should not happen if advanced_operate is correct
                    for sub_item_kw in item_kw: temp_new_keywords_list.append(str(sub_item_kw).strip())
                else: temp_new_keywords_list.append(str(item_kw).strip())
            current_keywords_list.extend(filter(None, temp_new_keywords_list))
            merged_edge["keywords"] = current_keywords_list

            # source_id and file_path merging (as discussed previously)
            # ... (robust source_id merging logic) ...
            new_source_ids = edge_instance.get("source_id", [])
            current_source_ids_list = merged_edge.get("source_id", [])
            if not isinstance(current_source_ids_list, list): current_source_ids_list = [str(current_source_ids_list)] if current_source_ids_list else []
            if isinstance(new_source_ids, str): new_source_ids = [sid.strip() for sid in new_source_ids.split(GRAPH_FIELD_SEP) if sid.strip()]
            elif not isinstance(new_source_ids, list): new_source_ids = [str(new_source_ids).strip()] if new_source_ids else []
            current_source_ids_list.extend(filter(None, new_source_ids))
            merged_edge["source_id"] = current_source_ids_list

            # ... (robust file_path merging logic) ...
            new_file_paths = edge_instance.get("file_path", [])
            current_file_paths_list = merged_edge.get("file_path", [])
            if not isinstance(current_file_paths_list, list): current_file_paths_list = [str(current_file_paths_list)] if current_file_paths_list else []
            if isinstance(new_file_paths, str): new_file_paths = [fp.strip() for fp in new_file_paths.split(GRAPH_FIELD_SEP) if fp.strip()]
            elif not isinstance(new_file_paths, list): new_file_paths = [str(new_file_paths).strip()] if new_file_paths else []
            current_file_paths_list.extend(filter(None, new_file_paths))
            merged_edge["file_path"] = current_file_paths_list

            # Collect all types encountered for this merge group
            if edge_instance.get("original_type"):
                all_original_types.append(edge_instance["original_type"])
            if edge_instance.get("neo4j_type"):
                all_neo4j_types.append(edge_instance["neo4j_type"])
        
        # Finalize list fields
        merged_edge["keywords"] = list(set(merged_edge["keywords"])) # Deduplicate
        merged_edge["source_id"] = GRAPH_FIELD_SEP.join(list(set(merged_edge["source_id"])))
        merged_edge["file_path"] = GRAPH_FIELD_SEP.join(list(set(merged_edge["file_path"])))

        # Determine the best type information after iterating all instances
        # Prioritize non-generic, non-None types.
        # If multiple specific types exist, this logic might need further refinement (e.g., most frequent, or manual resolution flag)
        final_original_type = "related"
        final_neo4j_type = "RELATED"
        
        # Find a specific original_type if one exists
        specific_original_types = [ot for ot in all_original_types if ot and ot.lower() != "related"]
        if specific_original_types:
            final_original_type = specific_original_types[0] # Take the first specific one encountered
            logger.debug(f"For {src_id}->{tgt_id}, selected specific original_type: '{final_original_type}' from {specific_original_types}")
        
        # Find a specific neo4j_type if one exists
        specific_neo4j_types = [nt for nt in all_neo4j_types if nt and nt != "RELATED"]
        if specific_neo4j_types:
            final_neo4j_type = specific_neo4j_types[0] # Take the first specific one
            logger.debug(f"For {src_id}->{tgt_id}, selected specific neo4j_type: '{final_neo4j_type}' from {specific_neo4j_types}")
        elif final_original_type != "related": # If no specific neo4j_type, but specific original_type, standardize original
            # This assumes advanced_operate's simple_neo4j_standardize is available or similar logic
            final_neo4j_type = final_original_type.upper().replace(' ', '_').replace('-', '_')
            final_neo4j_type = re.sub(r'[^A-Z0-9_]', '_', final_neo4j_type) # Basic sanitization
            if not final_neo4j_type: final_neo4j_type = "RELATED"
            logger.debug(f"For {src_id}->{tgt_id}, derived neo4j_type '{final_neo4j_type}' from original_type '{final_original_type}'")


        merged_edge["original_type"] = final_original_type
        merged_edge["neo4j_type"] = final_neo4j_type
        merged_edge["relationship_type"] = final_neo4j_type.lower().replace('_', ' ') # Human-readable from final Neo4j type
        merged_edge["rel_type"] = merged_edge["relationship_type"] # Ensure consistency

        # ... (description summarization logic) ...
        force_llm_summary_on_merge = global_config.get("force_llm_summary_on_merge", 6) 
        num_fragment = merged_edge["description"].count(GRAPH_FIELD_SEP) + 1
        if num_fragment > 1 and num_fragment >= force_llm_summary_on_merge:
            merged_edge["description"] = await _handle_entity_relation_summary(
                 f"({src_id}, {tgt_id})", merged_edge["description"], global_config, 
                 pipeline_status, pipeline_status_lock, llm_response_cache
            )
        
        # Final log before passing to upsert_edge
        logger.info(f"Final merged_edge for {src_id}->{tgt_id}: "
                    f"neo4j_type='{merged_edge['neo4j_type']}', "
                    f"rel_type='{merged_edge['rel_type']}', "
                    f"original_type='{merged_edge['original_type']}', "
                    f"weight={merged_edge['weight']:.2f}")

        # Pass the fully populated merged_edge dictionary to upsert_edge
        await knowledge_graph_inst.upsert_edge(src_id, tgt_id, merged_edge)
        return merged_edge 
    ```
    *   **Logging:** The `logger.debug` and `logger.info` statements above are crucial to trace how types are selected and merged.
    *   **Rationale:** This revised logic explicitly initializes `merged_edge` with default "related" types and then iterates through all `edge_instance`s, prioritizing the first encountered non-generic type for `original_type` and `neo4j_type`. It also ensures that all three type fields (`relationship_type`, `original_type`, `neo4j_type`) plus `rel_type` are consistently populated in `merged_edge` before it's passed to `upsert_edge`. The keyword, source_id, and file_path merging is also made more robust.

*   **4.1.2. Confirm `Neo4JStorage.upsert_edge` (Simple Wrapper) and `upsert_edge_detailed`:**
    *   **Requirement:** The changes from the previous PRD (item 4.1.2) for `Neo4JStorage.upsert_edge` (simple 3-arg version) are still vital: it *must* pass the *entire* `edge_data` (which is the `merged_edge` from above) as the `properties` argument to `upsert_edge_detailed`.
    *   **Requirement:** The changes from the previous PRD (item 4.1.1) for `Neo4JStorage.upsert_edge_detailed` (detailed version) are still vital: it must prioritize `neo4j_type` from the incoming `properties` dictionary for the Cypher label.
    *   **Rationale:** These ensure that the meticulously prepared `merged_edge` data is correctly used.

**4.2. Other Fixes (Reiteration from Previous PRD)**

*   **Filter "content_keywords" (Goal 3):** The solution in PRD#3 (section 4.2) for `operate.py` to filter `content_keywords` before relationship parsing remains essential.
*   **Graph Visualizer Data Integrity (Goal 4, 5):** The solution in PRD#3 (section 4.3.1) for robust float weight handling in `kg/neo4j_impl.py -> get_knowledge_graph` is critical to prevent the visualizer's `TypeError`. Also, ensure GraphML export (PRD#3 section 4.3.2) includes the correct edge type (from `r.neo4j_type` or `type(r)`) as the `label`.

**5. Implementation Steps**

1.  **Branch:** `fix/relationship-merge-final`
2.  **CRITICAL: Refactor `_merge_edges_then_upsert`:** Implement changes from **4.1.1** of this PRD.
3.  **Verify `Neo4JStorage.upsert_edge` and `upsert_edge_detailed`:** Double-check the implementations against **4.1.2** of this PRD (and relevant items from PRD#3).
4.  **Implement/Verify `content_keywords` Filtering:** Ensure PRD#3 section **4.2** is correctly implemented.
5.  **Test End-to-End:**
    *   Process test document(s).
    *   **Log Check 1 (Merge):** Verify logs from `_merge_edges_then_upsert` show `merged_edge` has the correct, specific `neo4j_type`, `original_type`, and `rel_type`.
    *   **Log Check 2 (Upsert Detailed):** Verify `Neo4JStorage.upsert_edge_detailed` logs show it's using the correct `neo4j_label_to_use` from the `properties` and that all stored properties are Neo4j-compatible.
    *   **Neo4j Query:** `MATCH (n)-[r]->(m) RETURN type(r), r.original_type, r.rel_type, r.neo4j_type, r.weight, r.keywords LIMIT 25`.
        *   `type(r)` must be the custom standardized Neo4j label (e.g., "INTEGRATES_WITH").
        *   `r.keywords` must be a string.
        *   All type properties must reflect the journey correctly.
6.  **Visualizer Test:** Confirm visualizer works and displays typed edges.
7.  **Clean Up & PR.**

**6. Expected Outcome**

*   The `_merge_edges_then_upsert` function will correctly preserve and prioritize specific type information (`neo4j_type`, `original_type`, `rel_type`) from the list of input edges.
*   `Neo4JStorage.upsert_edge_detailed` will consistently use the correct `neo4j_type` (e.g., "INTEGRATES_WITH") as the relationship label in Cypher queries.
*   The `WARNING: neo4j_type missing in properties...` will be eliminated.
*   Neo4j will store relationships with their intended custom types.
*   The graph visualizer will display these custom typed edges correctly.
