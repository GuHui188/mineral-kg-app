# -*- coding: utf-8 -*-
"""
LLM 三元组抽取脚本（B部分 · 知识抽取）
用法：
  1) 有 API：配置环境变量 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL 后直接运行
     python extract_triples.py input_texts.txt
  2) 无 API（人工/外部大模型代抽）：先用 --print-prompt 生成提示词，
     把大模型的 JSON 输出存为 llm_output.json，再运行
     python extract_triples.py --align llm_output.json
输入文本格式（input_texts.txt）：每段以 "## <source_id>" 开头，后接原文段落。
输出：new_triples.csv（与 06_fact_relation.csv 同构，可直接并入图谱）
"""
import json, os, re, sys, csv
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "关键矿产供应链数据包--李天语" / "关键矿产供应链数据包--李天语"

PREDICATES = ["出产", "出口至", "供应", "控股", "受管制于", "可替代", "需要", "发布于", "作用于"]
ENTITY_TYPES = ["国家/地区", "企业", "矿产/材料", "产品", "政策/事件"]


def build_entity_dict():
    """从维表构建 别名->(主键, 类型) 字典，用于抽取结果的实体对齐。"""
    alias_map = {}
    files = {
        "01_dim_country.csv": ("country_id", "国家/地区"),
        "02_dim_company.csv": ("company_id", "企业"),
        "03_dim_mineral.csv": ("mineral_id", "矿产/材料"),
        "04_dim_product.csv": ("product_id", "产品"),
        "05_dim_policy_event.csv": ("event_id", "政策/事件"),
    }
    for fname, (key, etype) in files.items():
        df = pd.read_csv(DATA_DIR / fname)
        for _, row in df.iterrows():
            names = [row.get("name_zh"), row.get("name_en")]
            if isinstance(row.get("alias"), str):
                names += row["alias"].split("|")
            for n in names:
                if isinstance(n, str) and n.strip():
                    alias_map[n.strip()] = (row[key], etype)

    # 叠加 B 方扩展别名字典（不动 A 的维表；setdefault 保证不覆盖维表已有映射）
    ext = Path(__file__).resolve().parent / "extend_alias.csv"
    if ext.exists():
        ea = pd.read_csv(ext)
        for _, row in ea.iterrows():
            if row.get("status") == "确认" and isinstance(row.get("alias"), str):
                alias_map.setdefault(row["alias"].strip(), (row["entity_id"], None))
    return alias_map


PROMPT_TEMPLATE = """你是知识图谱信息抽取助手。从下面的文本中抽取供应链知识三元组。

【实体类型】仅限：{entity_types}
【关系类型】仅限：{predicates}
【已知实体】（优先复用，括号内为标准名）：{known_entities}

【输出要求】
- 输出 JSON 数组，每条为 {{"subject": "...", "predicate": "...", "object": "...", "evidence": "原文中支撑该三元组的句子"}}
- subject/object 尽量使用【已知实体】中的标准名；若为新实体，在名称后加 "(新)"
- 仅抽取文本明确陈述的事实，禁止推测；无则输出 []
- predicate 必须严格取自【关系类型】

【文本】
{text}
"""


def make_prompt(text: str, alias_map) -> str:
    known = "、".join(list(alias_map.keys())[:80])  # 控制 prompt 长度
    return PROMPT_TEMPLATE.format(
        entity_types="/".join(ENTITY_TYPES),
        predicates="/".join(PREDICATES),
        known_entities=known,
        text=text,
    )


def call_llm(prompt: str) -> str:
    """调用 OpenAI 兼容接口。无 API 时请用 --print-prompt / --align 流程。"""
    import urllib.request
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    key = os.environ["LLM_API_KEY"]
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def parse_llm_json(raw: str):
    m = re.search(r"\[.*\]", raw, re.S)
    return json.loads(m.group(0)) if m else []


def align(triples, alias_map, source_id):
    """实体对齐 + 谓词校验，输出与 06 表同构的记录。"""
    rows = []
    for t in triples:
        if t.get("predicate") not in PREDICATES:
            t["predicate"] = "【非法谓词】" + str(t.get("predicate"))
        s_name = re.sub(r"\(新\)$", "", t.get("subject", "")).strip()
        o_name = re.sub(r"\(新\)$", "", t.get("object", "")).strip()
        s_id, _ = alias_map.get(s_name, ("NEW:" + s_name, None))
        o_id, _ = alias_map.get(o_name, ("NEW:" + o_name, None))
        rows.append({
            "subject_id": s_id, "subject_name": s_name,
            "predicate": t["predicate"],
            "object_id": o_id, "object_name": o_name,
            "evidence": t.get("evidence", ""), "source_id": source_id,
            "value_status": "待核对",
        })
    return rows


def main():
    args = sys.argv[1:]
    alias_map = build_entity_dict()

    if args and args[0] == "--print-prompt":
        text = Path(args[1]).read_text(encoding="utf-8")
        print(make_prompt(text, alias_map))
        return

    if args and args[0] == "--align":
        llm_out = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        source_id = sys.argv[sys.argv.index("--source") + 1] if "--source" in sys.argv else "SXX"
        rows = align(llm_out, alias_map, source_id)
        out = Path("new_triples.csv")
        pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
        print(f"已写出 {out}，共 {len(rows)} 条；含 NEW 标记的需人工复核")
        return

    # 默认：对输入文件逐段抽取
    text = Path(args[0]).read_text(encoding="utf-8")
    all_rows = []
    for block in re.split(r"^## ", text, flags=re.M):
        if not block.strip():
            continue
        source_id, _, body = block.partition("\n")
        raw = call_llm(make_prompt(body.strip(), alias_map))
        all_rows += align(parse_llm_json(raw), alias_map, source_id.strip())
    pd.DataFrame(all_rows).to_csv("new_triples.csv", index=False, encoding="utf-8-sig")
    print(f"已写出 new_triples.csv，共 {len(all_rows)} 条")


if __name__ == "__main__":
    main()
