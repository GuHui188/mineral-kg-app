// Q01 数据规模
MATCH (n:KGEntity {dataset:$dataset}) OPTIONAL MATCH (n)-[r]->(:KGEntity {dataset:$dataset}) RETURN count(DISTINCT n) AS nodes,count(r) AS edges;

// Q02 正产量国家
MATCH (c:KGEntity:Country {dataset:$dataset})-[r:PRODUCES]->(m:KGEntity:Mineral {dataset:$dataset,id:$mineral_id}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND r.quantity>0 AND r.share_pct>0 RETURN c.id AS country_id,c.name AS country,r.quantity AS quantity,r.share_pct AS observed_share_pct,r.id AS edge_id,r.source_ids AS source_ids ORDER BY observed_share_pct DESC;

// Q03 部分覆盖HHI
MATCH (c:KGEntity:Country {dataset:$dataset})-[r:PRODUCES]->(m:KGEntity:Mineral {dataset:$dataset}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND r.quantity>0 AND r.share_pct>0 RETURN m.id AS mineral_id,sum(r.share_pct) AS coverage_pct,sum(r.share_pct*r.share_pct) AS partial_hhi,count(c) AS countries;

// Q04 已记录出口方向与份额口径
MATCH (a:KGEntity:Country {dataset:$dataset})-[r:EXPORTS_TO]->(b:KGEntity:Country {dataset:$dataset}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND r.mineral_id=$mineral_id RETURN a.id AS exporter,b.id AS importer,r.share_pct AS exporter_observed_share_pct,r.note AS scope,r.source_ids AS source_ids;

// Q05 矿种潜在多跳关联
MATCH p=(m:KGEntity:Mineral {dataset:$dataset,id:$mineral_id})-[:SUPPLIES*1..4]->(c:KGEntity:Company {dataset:$dataset}) WHERE all(r IN relationships(p) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of)) RETURN c.id AS company_id,[n IN nodes(p)|n.id] AS path_node_ids,[r IN relationships(p)|r.id] AS path_edge_ids LIMIT 200;

// Q06 涉目标国的政策
MATCH (e:KGEntity:PolicyEvent {dataset:$dataset})-[r:TARGETS]->(c:KGEntity:Country {dataset:$dataset,id:$country_id}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) OPTIONAL MATCH (e)-[:ISSUED_BY]->(issuer:KGEntity {dataset:$dataset}) RETURN e.id AS event_id,e.name AS event,issuer.id AS issuer_country_id,e.effective_date AS effective_date,e.status AS original_status,e.source_ids AS source_ids;

// Q07 供应及股权上游关联
MATCH p=(a:KGEntity {dataset:$dataset,id:$entity_id})<-[:SUPPLIES|HOLDS|INVESTS_IN*1..4]-(upstream:KGEntity {dataset:$dataset}) WHERE all(r IN relationships(p) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of)) RETURN upstream.id AS upstream_id,[n IN nodes(p)|n.id] AS path_node_ids,[r IN relationships(p)|r.id] AS path_edge_ids;

// Q08 避开目标矿种的有条件替代
MATCH (alt:KGEntity:Product {dataset:$dataset})-[r:SUBSTITUTES]->(p:KGEntity:Product {dataset:$dataset})-[dep:REQUIRES]->(m:KGEntity:Mineral {dataset:$dataset,id:$mineral_id}) WHERE coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND coalesce(dep.review_flag,false)=false AND alt.dependency_scope_complete=true AND NOT EXISTS {MATCH (alt)-[:REQUIRES]->(m)} RETURN alt.id AS alternative_id,p.id AS replaces_id,r.id AS edge_id,r.substitution_condition AS condition,r.source_ids AS source_ids;

// Q09 默认有向业务子图的入度加出度
MATCH (n:KGEntity {dataset:$dataset}) WHERE NOT n:Source OPTIONAL MATCH (n)-[r]-(m:KGEntity {dataset:$dataset}) WHERE type(r)<>"CITES" AND coalesce(r.review_flag,false)=false AND (r.valid_from IS NULL OR r.valid_from<=$as_of) AND (r.valid_to IS NULL OR r.valid_to>=$as_of) AND (type(r)<>"PRODUCES" OR NOT "Country" IN labels(startNode(r)) OR coalesce(r.quantity,0)>0) RETURN n.id AS id,count(DISTINCT CASE WHEN startNode(r)=n THEN "out:"+m.id ELSE "in:"+m.id END) AS degree ORDER BY degree DESC;

// Q10 事件锚点与当前数据范围
MATCH (e:KGEntity:PolicyEvent {dataset:$dataset,id:$event_id}) RETURN e.id AS event_id,e.effective_date AS effective_date,e.target_mineral AS target_mineral,e.valid_year AS data_year,"当前数据不支持政策前后因果或历史对比" AS scope;

// Q11 事实级来源回查
MATCH (a:KGEntity {dataset:$dataset})-[r]->(b:KGEntity {dataset:$dataset}) WHERE type(r)<>"CITES" AND $record_id IN r.record_ids UNWIND r.source_ids AS sid MATCH (s:KGEntity:Source {dataset:$dataset,id:sid}) RETURN a.id AS subject_id,type(r) AS predicate,b.id AS object_id,r.id AS edge_id,r.record_ids AS record_ids,r.note AS note,s.id AS source_id,s.title AS title,s.url AS url;

// Q12 来源对应业务事实数
MATCH (a:KGEntity {dataset:$dataset})-[r]->(:KGEntity {dataset:$dataset}) WHERE type(r)<>"CITES" UNWIND r.source_ids AS sid RETURN sid AS source_id,count(DISTINCT r.id) AS fact_count ORDER BY fact_count DESC;