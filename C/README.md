# C 已验收执行入口

实际环境：Neo4j Community 5.26.34；数据库neo4j；验收时间2026-11-25 13:44:46 UTC+8。首次与重复导入均149个图谱节点、618条关系，幂等检查通过。12条Cypher均执行，并逐项与Python口径对照通过；三个场景数据库/快照一致，D八类数据库接口样例均已运行。

代码入口：02_import.py入库；02_setup_constraints.cypher约束；queries.py/07_queries.cypher查询；verify_neo4j.py完整验收；kg.py为共享构图与分析；08_simulate.py兼容命令行。Q07上游方向和Q09入/出度口径已在本轮统一。

根目录python run_all.py重建规范图与样例并运行22项回归；python C/verify_neo4j.py连接真实数据库再验收。前者不实时证明数据库仍在线；后者需要本机服务及环境变量。可运行C/验证数据库.ps1安全地在本机输入密码，交付文件不保存密码。

给D：from d_adapter import KGService；KGService('neo4j')已实测可用；KGService()为备用快照。数据库端读取图后使用同一Python规则，不把原始用户问题拼接成Cypher。八类数据库样例见D_handoff/examples_neo4j。

图谱节点149个（业务实体113、Source 36），关系618条（业务318、来源导航300）。库内另有1个KGDataset快照管理节点；MATCH (n)统计为150，二者统计对象不同。

旧C原包在originals/C_original；前一轮未安装阶段的交付保存在originals/previous_delivery_20261125。没有恢复旧库、停服务或生成新dump；可用本包完整数据与导入脚本重建。
