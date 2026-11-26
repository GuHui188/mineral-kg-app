# 关键矿产知识图谱：ABC修正与D前置交付

日期2026-11-25。原始交付完整保留，修正在独立A/B/C目录完成。先阅读“ABC_修改记录与D前置验收.docx”，再按各自修改记录反馈队友。

## 当前状态
已完成数据修正、65条保存抽取结果重放、人工准确率复算、规范图快照、12条参数Cypher准备、三场景Python推演、D八类接口与22项回归检查。当前快照149节点、318业务边、300来源导航边。

用户确认本机未安装Neo4j。实际Neo4j入库、12条Cypher执行、新库dump尚未完成；不得表述为全部数据库验收通过。D可先基于同一图快照开展前端/问答联调，数据库环境具备后执行单独验收脚本。GraphRAG模型调用属于D后续配置。

## 目录
originals/zips/：五个最新原ZIP及原C_part.zip；originals/各目录：逐文件保留（74个交付文件有SHA核验）；legacy保留更早A/B工作副本。
A/：修正后数据、字典与质量报告；B/：整合Schema、抽取与评估脚本，原始65条数据/人工审核不改。
C/：重建导入、约束、查询与推演；D_handoff/：可视化、地图、8意图、路径/来源、上下文与样例。
修改记录/：给A/B/C分别的修改清单；reports/：字段级与文件级日志、验证、缺失材料、结果。

## 推荐执行顺序
1. 备份已完成：只读参照originals，来源ZIP与SHA见reports/original_zip_manifest.csv。
2. A规则修正已完成。要从归档复现这些变换：python tools/prepare_data.py（仅重建项目A副本；不改originals）。
3. B对齐/原保存结果重放、C规范图重建及D样例生成：python run_all.py。
4. 安装并启动Neo4j5（兼容Java17/21），在本机设置.env.example所示环境变量。环境文件不会被Python自动加载；PowerShell使用$env:NEO4J_PASSWORD设置本机值，切勿发群。
5. python C/verify_neo4j.py：入库→重复导入幂等→12条Cypher→三场景与快照对照。仅status=passed才可写“Neo4j验收通过”。
6. D：from d_adapter import KGService；已测快照用KGService()，验收后数据库用KGService('neo4j')。接口见D_handoff/接口说明.md。

依赖：Python3.10+；pip install -r requirements.txt。核心图查询/推演只用标准库，B读取Excel需要openpyxl；Word报告重建另需python-docx。没有APOC/GDS强制依赖，没有密码/API密钥。

## 重要范围
默认排除129条待核业务边和1条未来生效边；数据总量不等于默认分析量。保留原始不确定项，未补造合同、历史面板、gold清单或原模型会话。
国家断供结果为矿种潜在关联，不证明企业实际采购来源；其他生产国不等于剩余产能；替代需要适配，HHI为不完整覆盖。业务孤立节点和未使用来源允许存在，不为指标凑边。
