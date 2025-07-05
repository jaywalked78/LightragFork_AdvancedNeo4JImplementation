// Neo4j Inspection Queries for LightRAG

// 1. Find Jason node and all its properties
MATCH (n {entity_id: 'Jason'})
RETURN n;

// 2. Find n8n node and its properties
MATCH (n {entity_id: 'n8n'})
RETURN n;

// 3. Count total entities and show top 10 by description length
MATCH (n)
WHERE n.entity_id IS NOT NULL
WITH n, length(n.description) as desc_length
ORDER BY desc_length DESC
LIMIT 10
RETURN n.entity_id, desc_length, left(n.description, 200) as description_preview;

// 4. Show all relationships for Jason (outgoing and incoming)
MATCH (jason {entity_id: 'Jason'})-[r]->(target)
RETURN 'Jason -[' + type(r) + ']-> ' + target.entity_id as outgoing_relationships, r.weight
UNION ALL
MATCH (source)-[r]->(jason {entity_id: 'Jason'})
RETURN source.entity_id + ' -[' + type(r) + ']-> Jason' as incoming_relationships, r.weight
ORDER BY r.weight DESC;

// 5. Show all relationships for n8n
MATCH (n8n {entity_id: 'n8n'})-[r]-(connected)
RETURN n8n.entity_id, type(r) as relationship_type, connected.entity_id as connected_to, r.weight
ORDER BY r.weight DESC
LIMIT 20;

// 6. Count relationships by type
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC;

// 7. Find nodes with most connections (potential hub nodes)
MATCH (n)
WHERE n.entity_id IS NOT NULL
WITH n, count{(n)-[]->()} + count{()-[]->(n)} as degree
ORDER BY degree DESC
LIMIT 10
RETURN n.entity_id, degree, left(n.description, 100) as description_preview;

// 8. Check if there are any COMMUNITY nodes (which there likely aren't in LightRAG)
MATCH (c:COMMUNITY)
RETURN count(c) as community_count;

// 9. Find all unique node labels in the graph
CALL db.labels() YIELD label
RETURN label
ORDER BY label;

// 10. Find relationships with highest weights
MATCH (s)-[r]->(t)
WHERE r.weight IS NOT NULL AND s.entity_id IS NOT NULL AND t.entity_id IS NOT NULL
RETURN s.entity_id as source, type(r) as rel_type, t.entity_id as target, r.weight
ORDER BY r.weight DESC
LIMIT 20;

// 11. Analyze chunk references for Jason
MATCH (jason {entity_id: 'Jason'})
RETURN jason.entity_id, jason.chunk_ids, size(jason.chunk_ids) as num_chunks;

// 12. Find entities that share chunks with Jason
MATCH (jason {entity_id: 'Jason'}), (other)
WHERE jason <> other AND other.entity_id IS NOT NULL 
  AND any(chunk IN jason.chunk_ids WHERE chunk IN other.chunk_ids)
RETURN other.entity_id, size([chunk IN jason.chunk_ids WHERE chunk IN other.chunk_ids]) as shared_chunks
ORDER BY shared_chunks DESC
LIMIT 10;

// 13. Get relationship statistics between specific nodes
MATCH (jason {entity_id: 'Jason'})-[r]-(n8n {entity_id: 'n8n'})
RETURN type(r) as relationship_type, r.weight, r.description, r.keywords;

// 14. Find all TEXT_CHUNK references (if stored in Neo4j)
MATCH (tc:TEXT_CHUNK)
RETURN count(tc) as text_chunk_count;

// 15. Analyze entity types by looking at descriptions
MATCH (n)
WHERE n.description IS NOT NULL AND n.entity_id IS NOT NULL
WITH n, 
     CASE 
       WHEN n.description CONTAINS 'tool' OR n.description CONTAINS 'software' THEN 'Tool/Software'
       WHEN n.description CONTAINS 'person' OR n.description CONTAINS 'user' THEN 'Person'
       WHEN n.description CONTAINS 'concept' OR n.description CONTAINS 'method' THEN 'Concept'
       ELSE 'Other'
     END as entity_type
RETURN entity_type, count(n) as count
ORDER BY count DESC;

// 16. Check what properties nodes have (to verify correct property names)
MATCH (n)
WHERE n.entity_id = 'Jason' OR n.entity_id = 'n8n'
RETURN n.entity_id, keys(n) as properties
LIMIT 5;