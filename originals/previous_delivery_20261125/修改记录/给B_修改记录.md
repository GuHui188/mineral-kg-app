# 给B：本次修改记录

基线ZIP：给A_替代核对.zip；给D_B补充材料.zip；给C_v6.1交付.zip。原文件未覆盖，见originals。修改后的文件位于本项目B/；共享程序在根目录。

| 类别 | 修改文件（相对包根目录） | 修改内容 |
|---|---|---|
| 第一类 必须修改 | extract_triples.py | 相对路径；补参股；完整实体清单；严格JSON/类型检查；保存结果可重放 |
| 第一类 必须修改 | audit_and_metrics.py | 新建审核表不得覆盖原件；R/F1无逐条gold时不记为已验证 |
| 第二类 逻辑统一 | 02_Schema设计.md；docs/02_Schema设计.md | 关系方向/派生/时间/来源统一；原两处重复文档同步 |
| 第二类 逻辑统一 | 04_实体对齐与融合.md；extend_alias.csv | 加入包钢稳定ID到新图；补已存在归一的锂精矿别名，E0015仍不导入 |
| 第二类 逻辑统一 | docs/01_需求分析.md；03_Schema迭代记录.md；05_知识抽取与评估.md | 修正政策路径、Q5采购来源措辞、历史比较和70%门槛；8类业务接口衔接 |
| 第三类 非关键 | audit_sheet.xlsx；new_triples.csv；new_triples_v2.csv；llm_outputs/；policy_texts/ | 原件保持不变；不要求重跑LLM、不凑到100条、不补造原会话或58条gold |

详细字段改前/改后：reports/A_field_changes.csv（A）；全部文件修改与路径：reports/all_changes.csv。多数A日志行是统一新增时间或复核字段，不代表相同数量的事实错误。

已保存的65条JSON重放匹配；人工审核原件保持不变。别名对齐不改变原事实判错。
