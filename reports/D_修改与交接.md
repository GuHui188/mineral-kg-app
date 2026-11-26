# D 本轮修改与队友交接

本轮基于上一轮最终持久交付包独立新增 D。原 A/B/C 业务文件和 kg.py、d_adapter.py、data/ 的 SHA256 全部保持一致。本轮未重跑抽取、未修改人工判定、未向 Neo4j 写入事实。

| 负责方 | 本轮修改 | 具体位置及交接 |
|---|---|---|
| A | 无 | A/ 全部保留；沿用既有待核实标记与来源，不补造采购和产能 |
| B | 无 | B/ 全部保留；D 的规则与模型路由新增于 d_app/rag.py |
| C | 无 | C/、kg.py、d_adapter.py、data/ 全部保留；D 的显示过滤与查询回执在 d_app/service.py |
| D | 新增 | app.py、api.py、d_app/、run_D.py、start_D.*、requirements_D*、README_D.md、tests/test_D.py、tools/verify_D_live.py、tools/check_deepseek.py、docs/、reports/D_* |
| 共享入口 | 修改 | README.md 增加 D 的最新入口，原 ABC 阶段说明继续保留 |

顺序：版本核对 → D适配 → 四页与可视化 → 只读API → 规则后备意图与GraphRAG → 测试/真实联调 → 汇报与交付。对应结果及所有可分发文件的哈希对照见 D_file_changes.csv。

本机私有 .env.local 不分发；队友使用 .env.D.example 在各自电脑配置。随包快照可独立运行主要功能，不需要原电脑密码或API密钥。
