# Schema 整合执行版（2026-11-25）

基线：给C_v6.1交付.zip/02_Schema设计.md；结合A完整v3及A补充材料整合。原稿保存在originals/B_to_C。

## 六类节点与十一类关系
Country（含地区/超国家组织）、Company、Mineral、Product、PolicyEvent、Source。矿产M_GRA仅为天然石墨，不自动覆盖人造石墨。

| 关系 | 方向和范围 |
|---|---|
| PRODUCES | Country/Company → Mineral；替代供给国须为国家正产量记录 |
| EXPORTS_TO | Country → Country；mineral_id描述贸易矿种，原份额的分母须看note，不能直接当进口依赖度 |
| SUPPLIES | Mineral/Company → Company/Mineral/Product；现有数据多为矿种或集团关联 |
| HOLDS | Country/Company → Company；国家控股仅适用现有国家层简化，R0191必须是包钢集团→北方稀土 |
| INVESTS_IN | Country/Company → Company；参股不自动等同实际控制 |
| REGULATED_BY | Mineral/Product → PolicyEvent |
| SUBSTITUTES | Product → Product，替代方指向被替代方；不是对称关系，须保留适配条件 |
| REQUIRES | Product → Mineral；由确定依赖生成；conditional依赖存为待核，不作全部产品通用断言 |
| ISSUED_BY | PolicyEvent → Country；罢工、断航不生成发布主体 |
| TARGETS | PolicyEvent → Country；含涉目标国/境外影响范围，不误写成指向Mineral |
| CITES | 业务实体节点 → Source，只作导航；业务事实的来源保存在业务边source_ids与record_ids |

## 执行规则
1. 身份：原有稳定ID不重编；kg_id=dataset:id用于Neo4j隔离，避免覆盖旧C库。
2. 时间：data_year/original_data_year保留A原口径，collection_year取访问年；stat_year只保留已有出产统计年。未知关系有效期不由数据年推断；E0060明确2031-01-01至2060-12-31，2026默认排除。
3. 待核：A confidence<0.80及A1明确待核/来源未列项标True；B使用其人工审核与review_flag，不补造模型置信度。129条待核业务边保存在图中，默认分析排除。
4. 替代：从被替代产品反向找SUBSTITUTES入边；候选必须已登记本项目范围依赖，且所有确定/条件依赖均不含目标矿种。配方未知时不能用缺边证明避矿。硫酸镍/硫酸钴不是直接互换品。
5. 推演：国家出产只作情景锚点；矿种→企业为潜在关联，不证明某企业从该国采购。BFS先过滤后访问；计数只含Company，不强求固定8家。B源CSV的“待核对”保留在original_value_status；融合图按已有人工判定及review_flag生成当前value_status，避免状态自相矛盾，不改人工原表。
6. 数据质量：未列不等于零；HHI只展示现有份额平方和及覆盖率。政策原状态保留但不证明查询日仍有效；目前没有完整历史面板。
7. 事实级来源：A与B同端点关系去重时保留所有记录号/来源；如E0006、E0007合入对应REQUIRES，不通过重复边增加规模。
8. 课程范围：老师建议人工抽样50—100条；65条符合建议，不存在准确率70%的明文硬性门槛。未取得逐条gold时只报告可核算准确率，不将汇总R/F1写为已完整复现。
