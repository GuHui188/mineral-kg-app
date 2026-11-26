// ============================================================
// 08_simulate.cypher — C 组第⑤步：断供推演（参数化，供 08_simulate.py 调用）
// 参数：$country 断供国、$mineral 矿种、$maxHops 最大传播跳数
// 逻辑：国家 -出产(产量>0)-> 矿 -供应-> 企业 -供应-> 下游企业…
// ============================================================


// S1 场景校验：这个国家真的产这个矿吗？份额多少？
MATCH (c:Country {name_zh: $country})-[p:PRODUCES]->(m:Mineral {name_zh: $mineral})
RETURN c.name_zh AS 断供国, m.name_zh AS 矿种,
       toFloat(p.quantity) AS 产量, p.unit AS 单位,
       toFloat(p.world_share_pct) AS 占全球份额,
       m.top1_share AS 全球第一国份额, m.hhi AS HHI,
       p.review_flag AS 数据待核实, p.source_id AS 来源
LIMIT 1;


// S2 直接受冲击：这个矿直接供给了哪些企业（第 1 跳）
MATCH (:Mineral {name_zh: $mineral})-[r:SUPPLIES]->(co:Company)
RETURN co.name_zh AS 企业, co.stage AS 环节, co.company_type AS 类型,
       r.review_flag AS 待核实
ORDER BY 环节, 企业;


// S3 分层传播：用 APOC 广度优先，按跳数给出受影响节点数
MATCH (m:Mineral {name_zh: $mineral})
CALL apoc.path.expandConfig(m, {
  relationshipFilter: 'SUPPLIES>',
  minLevel: 1, maxLevel: $maxHops,
  bfs: true, uniqueness: 'NODE_GLOBAL'
}) YIELD path
WITH path, length(path) AS hop
WHERE all(r IN relationships(path) WHERE NOT coalesce(r.review_flag, false))
WITH hop, last(nodes(path)) AS node
WITH hop, collect(DISTINCT node) AS ns
RETURN hop AS 跳数, size(ns) AS 节点数,
       [n IN ns | n.name_zh][0..8] AS 示例企业,
       [n IN ns | n.stage][0..8] AS 示例环节
ORDER BY 跳数;


// S4 影响面：按产业链环节汇总受影响企业
MATCH (m:Mineral {name_zh: $mineral})
CALL apoc.path.expandConfig(m, {
  relationshipFilter: 'SUPPLIES>',
  minLevel: 1, maxLevel: $maxHops,
  bfs: true, uniqueness: 'NODE_GLOBAL'
}) YIELD path
WITH path WHERE all(r IN relationships(path) WHERE NOT coalesce(r.review_flag, false))
WITH last(nodes(path)) AS co
WITH DISTINCT co
RETURN co.stage AS 环节, count(*) AS 企业数,
       collect(co.name_zh) AS 企业
ORDER BY 企业数 DESC;


// S5 受影响产品：哪些产品需要这个矿（BOM 层面）
MATCH (prod:Product)-[:REQUIRES]->(:Mineral {name_zh: $mineral})
RETURN prod.name_zh AS 产品, prod.product_category AS 类别,
       prod.chemistry AS 技术路线
ORDER BY 产品;


// S6 替代供应国：除断供国之外，还有谁能供（按全球份额降序）
MATCH (c:Country)-[p:PRODUCES]->(:Mineral {name_zh: $mineral})
WHERE c.name_zh <> $country AND toFloat(p.quantity) > 0
RETURN c.name_zh AS 替代国, toFloat(p.quantity) AS 产量,
       toFloat(p.world_share_pct) AS 全球份额
ORDER BY 全球份额 DESC;


// S7 替代路线：受影响产品有没有可替代的产品/技术路线
MATCH (alt:Product)-[s:SUBSTITUTES]->(prod:Product)-[:REQUIRES]->(:Mineral {name_zh: $mineral})
RETURN prod.name_zh AS 受影响产品, alt.name_zh AS 替代产品,
       s.note AS 替代代价
ORDER BY 受影响产品;


// S8 传导到终端：从矿出发能走到哪些整车/电池客户（最远一跳）
MATCH p=(:Mineral {name_zh: $mineral})-[:SUPPLIES*1..$maxHops]->(buyer:Company)
WHERE buyer.stage IN ['整车', '电芯']
  AND all(r IN relationships(p) WHERE NOT coalesce(r.review_flag, false))
WITH buyer, min(length(p)) AS 最短跳数
RETURN buyer.name_zh AS 终端客户, buyer.stage AS 环节, 最短跳数
ORDER BY 最短跳数, 终端客户;
