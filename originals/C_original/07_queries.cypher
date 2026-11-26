// ============================================================
// 07_queries.cypher — C 组第④步：查询库（10 条）
// 环境：Neo4j 5.26.19 / APOC 5.26.19 / GDS 2.13.7
// 约定：数字一律以「跑出来的结果」为准；查询按 B 组 Q1–Q7 的能力问题组织
// ============================================================


// Q01 图的规模总览：每类节点的数量
MATCH (n)
RETURN labels(n)[0] AS 标签, count(*) AS 数量
ORDER BY 数量 DESC;


// Q02 矿种集中度：HHI + 第一生产国 + 份额（Q1「哪个矿最卡脖子」）
MATCH (m:Mineral)
RETURN m.name_zh AS 矿种,
       m.hhi AS HHI,
       m.top1_country AS 第一生产国,
       m.top1_share AS 第一国份额,
       CASE WHEN m.hhi > 2500 THEN '高度集中'
            WHEN m.hhi > 1500 THEN '中度集中'
            ELSE '低集中' END AS 集中度
ORDER BY m.hhi DESC;


// Q03 单点依赖预警：第一生产国份额 > 60% 的矿，且看它连了几家下游企业（Q7）
MATCH (m:Mineral)
WHERE m.top1_share > 60
OPTIONAL MATCH (m)-[:SUPPLIES]->(c:Company)
RETURN m.name_zh AS 矿种, m.top1_country AS 第一生产国,
       m.top1_share AS 份额, count(DISTINCT c) AS 下游企业数
ORDER BY 份额 DESC;


// Q04 中国的进口结构：谁在给中国供矿、占其出口多少（Q2，2 跳里的第 1 跳）
MATCH (src:Country)-[e:EXPORTS_TO]->(cn:Country {name_zh: '中国'})
RETURN src.name_zh AS 出口国, e.mineral_id AS 矿种,
       e.export_share_pct AS 占其出口比例
ORDER BY 占其出口比例 DESC;


// Q05 完整供应链路径：资源国 → 矿 → 上游企业 → 下游企业（Q2，多跳之一）
MATCH p=(c:Country)-[e:PRODUCES]->(m:Mineral)-[:SUPPLIES]->(a:Company)-[:SUPPLIES]->(b:Company)
WHERE toFloat(e.quantity) > 0
RETURN c.name_zh AS 资源国, m.name_zh AS 矿,
       a.name_zh AS 上游企业, a.stage AS 上游环节,
       b.name_zh AS 下游企业, b.stage AS 下游环节
LIMIT 15;


// Q06 管制事件的闭环：被管制对象 → 事件 → 发布国（Q4，多跳之二）
MATCH (x)-[:REGULATED_BY]->(pe:PolicyEvent)-[:ISSUED_BY]->(cn:Country)
WHERE cn.name_zh = '中国'
RETURN x.name_zh AS 被管制对象, labels(x)[0] AS 对象类型,
       pe.name_zh AS 事件, pe.effective_date AS 生效日期,
       pe.impact_direction AS 方向
ORDER BY 生效日期;


// Q07 股权穿透：控股/参股链，支持 1~3 跳（Q5）
MATCH p=(a)-[:HOLDS|INVESTS_IN*1..3]->(b:Company)
WHERE a:Company OR a:Country
RETURN a.name_zh AS 起点,
       [r IN relationships(p) | type(r)] AS 路径类型,
       [n IN nodes(p) | n.name_zh] AS 路径,
       length(p) AS 跳数
ORDER BY 跳数 DESC
LIMIT 10;


// Q08 可替代关系：谁替代谁、代价是什么（Q3）
MATCH (a:Product)-[r:SUBSTITUTES]->(b:Product)
RETURN a.name_zh AS 替代方, b.name_zh AS 被替代方, r.note AS 替代条件
ORDER BY 替代方;


// Q09 图算法：PageRank 找图上最关键的实体（只算业务边，排除 Source 与 CITES）
CALL gds.graph.project('kg_biz',
  ['Country','Company','Mineral','Product','PolicyEvent'],
  ['PRODUCES','EXPORTS_TO','SUPPLIES','HOLDS','INVESTS_IN','REGULATED_BY',
   'SUBSTITUTES','REQUIRES','ISSUED_BY','TARGETS'])
YIELD graphName, nodeCount, relationshipCount;

CALL gds.pageRank.stream('kg_biz', {maxIterations: 20, dampingFactor: 0.85})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, score
RETURN labels(n)[0] AS 类型, n.name_zh AS 名称, round(score, 4) AS PageRank
ORDER BY PageRank DESC
LIMIT 10;

CALL gds.graph.drop('kg_biz') YIELD graphName
RETURN graphName AS 已释放图;


// Q10 时序切片：按数据年份看各类关系的分布（Q6）
MATCH ()-[r]->()
WHERE r.data_year IS NOT NULL
RETURN r.data_year AS 年份, type(r) AS 关系, count(*) AS 数量
ORDER BY 年份, 数量 DESC;


// Q11 溯源闭环：某个来源支撑了图上哪些知识（Schema v6 的 CITES）
MATCH (s:Source)<-[c:CITES]-(n)
RETURN s.source_id AS 来源, s.source_level AS 等级,
       labels(n)[0] AS 节点类型, n.name_zh AS 知识,
       coalesce(c.rel_type, '节点级') AS 边级引用
ORDER BY s.source_id, 节点类型
LIMIT 20;


// Q12 溯源覆盖度：每条来源被多少条知识引用（找"最堪当证据"的来源）
MATCH (s:Source)
OPTIONAL MATCH (s)<-[c:CITES]-(n)
RETURN s.source_id AS 来源, s.source_level AS 等级,
       count(DISTINCT n) AS 支撑实体数, count(c) AS 引用次数
ORDER BY 引用次数 DESC
LIMIT 10;
