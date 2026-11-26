// Run each block separately in Neo4j Browser after connecting locally.
// Graph node count excludes the single KGDataset management node.
MATCH (n:KGEntity {dataset:'mineral-20261125-v1'})
RETURN n.label AS entity_type,count(n) AS nodes;

MATCH (a:KGEntity {dataset:'mineral-20261125-v1'})-[r]->(:KGEntity {dataset:'mineral-20261125-v1'})
RETURN type(r) AS relation_type,count(r) AS edges;

MATCH p=(m:KGEntity:Mineral {dataset:'mineral-20261125-v1',id:'M_CO'})-[:SUPPLIES*1..4]->(c:KGEntity:Company)
WHERE all(r IN relationships(p) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<='2026-11-25') AND (r.valid_to IS NULL OR r.valid_to>='2026-11-25'))
RETURN p LIMIT 30;

// R0191: Baogang Group controls Northern Rare Earth; preserve A v3 correction.
MATCH p=(a:KGEntity {dataset:'mineral-20261125-v1'})-[r:HOLDS]->(b:KGEntity)
WHERE 'R0191' IN r.record_ids
RETURN p;
