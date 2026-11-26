// 参考查询：实际传播先按默认规则过滤，再由kg.py执行BFS。数据库后端用同一算法。

// Q02 正产量国家
MATCH (c:KGEntity:Country {dataset:$dataset})-[r:PRODUCES]->(m:KGEntity:Mineral {dataset:$dataset,id:$mineral_id}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND r.quantity>0 AND r.share_pct>0 RETURN c.id AS country_id,c.name AS country,r.quantity AS quantity,r.share_pct AS observed_share_pct,r.id AS edge_id,r.source_ids AS source_ids ORDER BY observed_share_pct DESC;

// Q05 矿种潜在多跳关联
MATCH p=(m:KGEntity:Mineral {dataset:$dataset,id:$mineral_id})-[:SUPPLIES*1..4]->(c:KGEntity:Company {dataset:$dataset}) WHERE all(r IN relationships(p) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of)) RETURN c.id AS company_id,[n IN nodes(p)|n.id] AS path_node_ids,[r IN relationships(p)|r.id] AS path_edge_ids LIMIT 200;

// Q08 避开目标矿种的有条件替代
MATCH (alt:KGEntity:Product {dataset:$dataset})-[r:SUBSTITUTES]->(p:KGEntity:Product {dataset:$dataset})-[dep:REQUIRES]->(m:KGEntity:Mineral {dataset:$dataset,id:$mineral_id}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND coalesce(dep.review_flag,false)=false AND alt.dependency_scope_complete=true AND NOT EXISTS {MATCH (alt)-[:REQUIRES]->(m)} RETURN alt.id AS alternative_id,p.id AS replaces_id,r.id AS edge_id,r.substitution_condition AS condition,r.source_ids AS source_ids;