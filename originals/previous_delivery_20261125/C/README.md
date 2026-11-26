# C 新版执行入口

旧版完整材料位于originals/C_original。C/02_import.py、02_setup_constraints.cypher、apply_cypher.py、run_queries.py按README缺失项重建；并非声称找回队友原脚本。

根目录python run_all.py完成离线重建和验证。python C/verify_neo4j.py进行真实数据库验证（需要本机已启动Neo4j5）；环境变量配置见.env.example。

D导入合法Python模块：from d_adapter import KGService。KGService()使用可运行图快照；KGService('neo4j')从新版命名空间读取数据库后执行同一质量与推演规则，未导入时会报错而不会自动借用旧库。

不依赖APOC或GDS。中介中心性和PageRank由Python标准库实现。最大跳数1—6；默认4。敏感配置只在本机设置，不包含密码或API密钥。
