# 第二部分 知识建模：Schema 设计（定稿 v6）

> 版本说明：本文件为定稿（v6），迭代过程见《03_Schema迭代记录》。
> 设计原则：每个决策均回溯至能力问题清单（Q1—Q7）——答不了题的节点/关系不设，用不到的属性不收。
> v6 变更（施工反馈驱动）：Country 扩展为"国家/地区/超国家组织"（新增欧盟 C_EU）；
> 出产/供应端点类型放宽；新增第 6 类节点 Source 与第 11 种关系"引用 CITES"；
> 回填 C 组施工的三个实际执行口径（见 2.5）。

## 2.1 实体类型（节点）

共 6 类节点，前 5 类与数据包 01—05 维表一一对应，Source 为 v6 新增。

### Country 国家/地区/超国家组织

| 属性                | 类型        | 说明                  |
| ----------------- | --------- | ------------------- |
| country_id        | string，主键 | C_+ISO3，如 C_CHL     |
| name_zh / name_en | string    | 中英文名                |
| iso_alpha3        | string    | ISO 3166-1，便于对外数据对齐 |
| region            | enum      | 六大洲，用于区域聚合与可视化着色    |
| role_in_chain     | enum      | 资源国/加工国/消费国/资源+加工国  |
| reserve_li_t 等    | float     | 各矿种储量（吨），NA=未公布     |

**v6 扩展**：本类涵盖"国家/地区/**超国家组织**"——欧盟（C_EU，iso_alpha3=NA）作为规制主体
入图，否则欧盟《新电池法规》《关键原材料法案》没有"发布于"的落点，Q4 链路断裂
（三方交叉点 3.1 决策，方案一）。

### Company 企业

| 属性                           | 类型        | 说明                        |
| ---------------------------- | --------- | ------------------------- |
| company_id                   | string，主键 | CO_ 前缀                    |
| name_zh / name_en            | string    | 中英文名                      |
| alias                        | list      | 别名/股票代码/旧名，实体对齐的依据        |
| company_type                 | enum      | 矿业/冶炼/材料/电池/整车/回收         |
| stage                        | enum      | 主营产业链环节：采矿→冶炼→材料→电芯→整车→回收（v2 数据新增"材料""贸易"取值，已在数据字典登记放行） |
| founded_year, listed, ticker | —         | 工商与上市信息                   |

**实体而非属性的取舍**：企业必须做节点——它是"供应/控股"关系的端点，且 Q5 的穿透查询以企业为跳板；而企业的"成立年份""是否上市"从不参与路径推演，故只做属性。

### Mineral 矿产/材料

| 属性                                    | 类型        | 说明                     |
| ------------------------------------- | --------- | ---------------------- |
| mineral_id                            | string，主键 | M_ 前缀                  |
| unit                                  | string    | 全表统一计量单位               |
| world_production_2025 / world_reserve | float     | 全球产量与储量                |
| hhi                                   | float     | 赫芬达尔指数，>2500 为高度集中（Q1） |
| top1_share                            | float     | 第一大生产国份额，单点依赖判断（Q7）    |
| battery_role                          | string    | 在电池中的作用（文本描述）          |

### Product 产品

| 属性               | 类型        | 说明                       |
| ---------------- | --------- | ------------------------ |
| product_id       | string，主键 | P_ 前缀                    |
| product_category | enum      | 材料/电芯/电池包/整车——决定所处产业层级   |
| chemistry        | string    | 技术路线：LFP/NCM/NCA/钠电等（Q3） |
| contains_cobalt  | Y/N       | 冗余展示属性：Q3 以 REQUIRES 边为唯一权威口径，本字段仅供可视化着色（v4 修订）            |

### PolicyEvent 政策/事件

| 属性                             | 类型        | 说明                       |
| ------------------------------ | --------- | ------------------------ |
| event_id                       | string，主键 | PE_+日期+国家+类型，自带排序键       |
| event_type                     | enum      | 出口管制/关税/罢工/断航/补贴/标准/产业政策 |
| trigger_word / arguments       | string    | 事件抽取的锚点与论元（支撑 LLM 抽取评估）  |
| announce_date / effective_date | date      | ISO 8601                 |
| impact_direction               | enum      | 收紧/放松/中性，供规则推理           |
| status                         | enum      | 已生效/已结束等                 |

**取舍说明**：政策事件做节点而非关系的属性——因为它本身被"受管制于"指向，且携带类型、日期、方向等一组属性，若压成边属性则无法被 Q4/Q6 检索。

### ★Source 来源（v6 新增，B4 决议）

| 属性            | 类型        | 说明                          |
| ------------- | --------- | --------------------------- |
| source_id     | string，主键 | S 前缀，对应 07 来源登记表（v2 共 31 条） |
| title / url   | string    | 来源标题与链接                     |
| publisher     | string    | 发布机构（商务部/IEA/路透社等）           |
| source_level  | enum      | 官方原文/权威转引/行业媒体（来源等级）        |

**为什么加**：v1—v5 中 source_id 只是边上的属性，能"从知识查来源"，不能"从来源反查影响了哪些知识"。
加 Source 节点 + 引用边后形成**溯源闭环**，答辩可演示"某条新闻支撑了图上哪些知识"。

## 2.2 关系类型（边）

共 11 种关系 = 数据包原有 6 种 + 建模新增 5 种（★标记）。

| 关系                | 方向（主→客）                       | 方向语义                     | 边属性                                         | 支撑问题   |
| ----------------- | ----------------------------- | ------------------------ | ------------------------------------------- | ------ |
| 出产 PRODUCES       | Country/Company → Mineral     | 资源国/矿企流向矿产，"谁有矿"（v6 放宽：企业可作主体，如洛阳钼业产钴） | quantity, unit, world_share_pct（占全球产量）, data_year        | Q1, Q2 |
| 出口至 EXPORTS_TO    | Country → Country             | 出口国流向进口国                 | **mineral_id（v2 数据已实列）**, export_share_pct（占出口国出口额，与 world_share_pct 严格区分）, data_year | Q2     |
| 供应 SUPPLIES       | Company/Mineral → Company/Mineral/Product | 上游流向下游（v6 放宽客体：企业可供应矿产品/材料，如 SQM 供应锂、华友供应硫酸锂） | quantity, since_year, data_year             | Q2, Q5 |
| 控股 HOLDS          | Company/Country → Company     | 控制性持股（>50% 或第一大股东且实际控制）指向被控股方 | hold_ratio_pct（v2 规范列名，ratio_pct 已弃用）, since_year（data_year 一律填采集年份，不填入股年份）                       | Q5     |
| ★参股 INVESTS_IN    | Company/Country → Company     | **财务性持股，不构成控制（v5 新增）**——参股方指向被持股方 | hold_ratio_pct, since_year                       | Q5     |
| 受管制于 REGULATED_BY | Mineral/Product → PolicyEvent | 被管制对象指向管制事件              | 挂全套溯源属性（source_id/confidence/evidence_type/data_year，同总约定）                                 | Q4     |
| 可替代 SUBSTITUTES   | Product → Product             | 替代方指向被替代方（单向记录，允许双向成对存在） | note（替代条件与代价）                               | Q3     |
| ★需要 REQUIRES      | Product → Mineral             | 产品指向其 BOM 所需矿产           | —                                           | Q2, Q3 |
| ★发布于 ISSUED_BY    | PolicyEvent → Country         | 事件指向发布方（仅对 event_type ∈ 出口管制/关税/补贴/产业政策/标准 生成；罢工/断航类无发布主体） | —                                           | Q4     |
| ★作用于 TARGETS      | PolicyEvent → Country | 事件指向作用国家（仅到国家；对矿产的管制统一由"受管制于"表达，避免双向双写）                 | —                                           | Q4, Q6 |
| ★引用 CITES         | 任意节点/事实边 → Source             | 知识指向其来源（v6 新增，溯源闭环）      | —                                           | 答辩溯源演示 |

**控股/参股的判定口径**：以"是否构成控制"为准——持股 >50%、或虽不足 50% 但为第一大股东且形成实际控制（如董事会主导）记为**控股**；其余财务性持股记为**参股**。
落地情况：天齐锂业持 SQM 约 22%（第二大股东）→ 参股；大众持国轩高科 24.9%（第一大股东，组内判定未形成实际控制）→ 参股。
R0188/R0189 已在 A 组 v2 数据包中改记"参股"，10 种业务关系全部有实例落地。

### 方向语义的三条约定

1. **物流/价值流方向**：出产、出口至、供应均沿"资源 → 加工 → 制造"正向流动，与冲击传导方向一致——BFS 顺边推进即为断供传导路径（Q2）。
2. **控制权方向**：控股/参股由持股方指向被持股方，与国家持股（C→CO）和企业持股（CO→CO）两种情形兼容。
3. **管制方向**："受管制于"由被管制对象指向事件（M/P→PE），使"某国发布了哪些管制、管了什么"可经 发布于+受管制于 两跳闭合回答。

### 边属性总约定（所有事实边共有）

| 属性            | 说明                     |
| ------------- | ---------------------- |
| source_id     | 指向来源登记表（v6 起同时生成 CITES 边） |
| confidence    | 0—1 置信度                |
| evidence_type | 原表数值/公告原文/年报披露/媒体报道/推算 |
| data_year     | 数据所属年份，支撑 Q6 时序切片      |

## 2.3 质量门槛策略（入图规则）

数据包自带证据分级，入图时执行：

1. **evidence_type=实测/原表数值/公告原文/年报披露** → 直接入图；
2. **evidence_type=推算 或 confidence<0.80** → 入图但标记 `review_flag=true`，在可视化与问答中显式标注"待核实"（如 R0192 宁德时代控股湖南裕能，confidence=0.60）；
3. **LLM 抽取边**一律 `origin='LLM'` 并携带人工核对结论：判"部分正确"的 6 条入图边带 `review_flag=true`；判"错误"的 11 条不入图（见 05 文档与 `new_triples_v2.csv`）；
4. 缺失值一律显式标注（NA/未公布/无规模产量），**禁止留空**——缺失本身即信息。

## 2.4 Schema 图（文字版）

```
                发布于                 作用于
  PolicyEvent ────────→ Country   PolicyEvent ────────→ Country
       ↑                                                   （含超国家组织 C_EU）
       │ 受管制于
  Mineral / Product
       ↑
  Country ──出产──→ Mineral ──供应──→ Company ──供应──→ Company(下游)
     │         ↑                      ↑    │
     │   Company ──出产──（矿企产矿）      │ 控股/参股(Company/Country→Company)
     └──────出口至(Country→Country, 带 mineral_id)─┘
                                             ↓
  Product ──需要──→ Mineral    Product ──可替代──→ Product

  任意节点/事实边 ──引用 CITES──→ Source（v6 溯源闭环）
```

## 2.5 与数据包的字段映射（交接 C 部分的接口，v6 回填实际执行口径）

- 01—05 维表 → 前 5 类节点，字段名即属性名，原样映射；07 来源登记表 → Source 节点（v6）；
- 06 关系表 → 关系边，`subject_id/predicate/object_id` 直接映射；
  - 06 表 v2 已新增 `mineral_id` 实列（17 条出口至已回填），**优先读列**，无值才回退 note 关键词判定（C 组脚本已兼容）；
  - 持股比例统一读 `hold_ratio_pct`（控股/参股共用）；`ratio_pct` 为 v1 兼容列，已弃用；
  - share_pct 列按谓词拆分为 world_share_pct（出产）/ export_share_pct（出口至）；
- ★需要 REQUIRES：由 04 表 `key_minerals` 字段拆分生成（"锂|石墨|铜" → 3 条边）；
  矿产中文名 → mineral_id 的对照依赖与 03 表 name_zh 精确匹配，导入前须全量校验（v2 已验证全部命中）；
- ★发布于/作用于：由 05 表 `issuing_country/target_country` 字段转化为边，
  **转化前校验**（v4 新增）：发布于仅对 event_type ∈ {出口管制/关税/补贴/产业政策/标准} 生成；
  作用于仅生成 PE→Country；v2 数据已修复四处脏值（苏伊士/罢工发布国置 NA，欧盟两条改 C_EU）；
- 05 表 `target_mineral` 字段：**辅助属性，不入图**（对矿产的管制统一由"受管制于"边表达，避免双写）；
- B 组 LLM 三元组以 `scripts/new_triples_v2.csv` 交付：`import_flag=是` 的 28 条入图
  （`origin='LLM'`，部分正确者带 `review_flag=true`）；`support_of` 列标注重复 27 条
  （16 条与 06 表同向同端点、11 条与 05 表自动生成边重合，作补充证据不重复造边；
  其中 E0035 同时判"错误"，归入不入图）；判"错误"共 11 条不入图。28+26+11=65。

## 2.6 当前规模口径（A 组 v2 数据包 + B 组入图三元组）

| 项 | 数量 | 说明 |
|---|---|---|
| 节点（维表口径） | 112 + 31 | 国家 22 / 企业 47 / 矿产 7 / 产品 21 / 事件 15，另 Source 31（v6） |
| 06 表关系边 | 231 | 含 v2 新增 17 条（矿→企业供应边 16 + 比亚迪→特斯拉 1） |
| B 组 LLM 入图边 | 28 | new_triples_v2.csv 中 import_flag=是 |
| 谓词 | 7 种（06 表）/ 11 种（Schema 全量） | 06 表：出产/出口至/供应/控股/参股/受管制于/可替代 |

> 图上最终节点/边数以 C 组导入校验报告为准。
