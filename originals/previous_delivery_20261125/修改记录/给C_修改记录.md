# 给C：本次修改记录

基线ZIP：C_part.zip（此前交付；本轮未收到新版C）。原文件未覆盖，见originals。修改后的文件位于本项目C/；共享程序在根目录。

| 类别 | 修改文件（相对包根目录） | 修改内容 |
|---|---|---|
| 第一类 必须修改 | 02_import.py；02_setup_constraints.cypher；neo4j_client.py | 重建缺失导入；规范属性类型、命名空间与幂等；不覆盖旧库 |
| 第一类 必须修改 | queries.py；07_queries.cypher；apply_cypher.py；run_queries.py | 12模板统一参数/方向/时间/待核/正产量和来源口径 |
| 第一类 必须修改 | 08_simulate.py；根目录kg.py | 先筛边再BFS；只数Company；合法模块导入；替代依赖筛选；固定输出目录 |
| 第一类 必须修改 | verify_neo4j.py | 真实入库、重导、12查询和三场景对照脚本已完成；待本机安装Neo4j后执行 |
| 第二类 逻辑统一 | 03_导入校验报告.md；07_查询库与结果.md；08_推演结果.json/.md；README.md | 结果按当前快照重算；不沿用143节点/旧PageRank/旧截图；分清Python已测与Neo4j未测 |
| 第三类 非关键 | 旧dump；旧figure图片 | 仅归档，不要求按旧数字凑企业数，不自动恢复覆盖现有数据库；新dump尚无 |

详细字段改前/改后：reports/A_field_changes.csv（A）；全部文件修改与路径：reports/all_changes.csv。多数A日志行是统一新增时间或复核字段，不代表相同数量的事实错误。

Python重建/推演与22项回归已通过；Neo4j实际入库和Cypher执行仍待环境。不能把代码完成写成数据库验收完成。
