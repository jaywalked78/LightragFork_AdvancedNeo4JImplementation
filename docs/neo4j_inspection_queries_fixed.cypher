// Neo4j Inspection Queries for LightRAG - FIXED VERSION

// 1. Find Jason node and all its properties
MATCH (n:person {entity_id: 'Jason'})
RETURN n;

// 2. Find n8n node and its properties  
MATCH (n {entity_id: 'n8n'})
RETURN n;

// 3. Count total entities and show top 10 by description length
MATCH (n)
WHERE n.entity_id IS NOT NULL AND n.description IS NOT NULL
WITH n, length(n.description) as desc_length
ORDER BY desc_length DESC
LIMIT 10
RETURN n.entity_id, labels(n) as labels, desc_length, left(n.description, 200) as description_preview;

// 4. Show all relationships for Jason (outgoing and incoming)
MATCH (jason:person {entity_id: 'Jason'})-[r]->(target)
RETURN 'Jason -[' + type(r) + ']-> ' + target.entity_id as relationship, r.weight, r.description
UNION ALL
MATCH (source)-[r]->(jason:person {entity_id: 'Jason'})
RETURN source.entity_id + ' -[' + type(r) + ']-> Jason' as relationship, r.weight, r.description
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
RETURN n.entity_id, labels(n) as labels, degree, left(n.description, 100) as description_preview;

// 8. Check all unique node labels in the graph
CALL db.labels() YIELD label
RETURN label
ORDER BY label;

// 9. Find relationships with highest weights
MATCH (s)-[r]->(t)
WHERE r.weight IS NOT NULL AND s.entity_id IS NOT NULL AND t.entity_id IS NOT NULL
RETURN s.entity_id as source, type(r) as rel_type, t.entity_id as target, r.weight
ORDER BY r.weight DESC
LIMIT 20;

// 10. Analyze chunk references for Jason
MATCH (jason:person {entity_id: 'Jason'})
RETURN jason.entity_id, size(split(jason.chunk_ids, '<SEP>')) as num_chunks, left(jason.chunk_ids, 200) as chunk_sample;

// 11. Find entities that co-occur in files with Jason
MATCH (jason:person {entity_id: 'Jason'}), (other)
WHERE jason <> other AND other.entity_id IS NOT NULL 
  AND any(file IN split(jason.file_path, '<SEP>') WHERE file IN split(other.file_path, '<SEP>'))
WITH other, size([file IN split(jason.file_path, '<SEP>') WHERE file IN split(other.file_path, '<SEP>')]) as shared_files
WHERE shared_files > 0
RETURN other.entity_id, labels(other) as labels, shared_files
ORDER BY shared_files DESC
LIMIT 20;

// 12. Get relationship statistics between specific nodes
MATCH (jason:person {entity_id: 'Jason'})-[r]-(n8n {entity_id: 'n8n'})
RETURN type(r) as relationship_type, r.weight, r.description, r.keywords;

// 13. Analyze entity types by label
MATCH (n)
WHERE n.entity_id IS NOT NULL
RETURN labels(n) as entity_labels, count(n) as count
ORDER BY count DESC;

// 14. Find all entities with type 'tool' or 'software'
MATCH (n:tool)
RETURN n.entity_id, n.entity_type, left(n.description, 150) as description
UNION
MATCH (n:software) 
RETURN n.entity_id, n.entity_type, left(n.description, 150) as description
ORDER BY n.entity_id;

// 15. Analyze Jason's tools by relationship
MATCH (jason:person {entity_id: 'Jason'})-[r:USES|UTILIZES|OPERATES|MANAGES]->(tool)
WHERE tool.entity_id IS NOT NULL
RETURN tool.entity_id, labels(tool) as labels, type(r) as relationship, r.weight
ORDER BY r.weight DESC;

// 16. Count chunks per entity
MATCH (n)
WHERE n.entity_id IS NOT NULL AND n.chunk_ids IS NOT NULL
WITH n, size(split(n.chunk_ids, '<SEP>')) as chunk_count
ORDER BY chunk_count DESC
LIMIT 20
RETURN n.entity_id, labels(n) as labels, chunk_count;

// 17. Find files with most entities
WITH split('screen_recording_2025_03_26_at_7_19_51_pm-development_troubleshooting_automation.md', '<SEP>') as sample_files
MATCH (n)
WHERE n.file_path IS NOT NULL
WITH n, [file IN split(n.file_path, '<SEP>') | file] as files
UNWIND files as file
WITH file, count(distinct n) as entity_count
ORDER BY entity_count DESC
LIMIT 20
RETURN file, entity_count;

// 18. Get schema information
CALL db.schema.visualization() YIELD nodes, relationships
RETURN nodes, relationships;

// 19. Check relationship properties schema
MATCH ()-[r]->()
WITH r LIMIT 1
RETURN type(r) as relationship_type, keys(r) as properties;

// 20. Find all Jason's direct connections with their relationship types
MATCH (jason:person {entity_id: 'Jason'})-[r]-(connected)
WHERE connected.entity_id IS NOT NULL
RETURN DISTINCT connected.entity_id, labels(connected) as labels, collect(DISTINCT type(r)) as relationship_types
ORDER BY size(collect(DISTINCT type(r))) DESC
LIMIT 30;