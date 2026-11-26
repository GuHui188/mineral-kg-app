#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
08_simulate.py — C 组第⑤步：断供推演接口

输入：断供国 + 矿种（+ 最大传播跳数）
输出：结构化 JSON（scenario / direct / levels / impact / alternatives / kpis）
      + 人读的报告（Markdown）

用法：
    python 08_simulate.py --password xxx                      # 跑 3 个预置场景
    python 08_simulate.py --password xxx --pair 刚果（金）:钴
    python 08_simulate.py --password xxx --pair 中国:石墨 --pair 澳大利亚:锂 --hops 4
给 D 组调用：
    from 08_simulate import simulate_supply_cut  （见文件末 __main__ 的返回结构）
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MD = os.path.join(HERE, "C_part", "08_推演结果.md")
PRESETS = [("刚果（金）", "钴"), ("中国", "石墨"), ("澳大利亚", "锂")]


# ---------------------------------------------------------------- Neo4j 客户端
class Neo4j:
    def __init__(self, host="127.0.0.1", port="7474", user="neo4j",
                 password="", database="neo4j"):
        self.url = f"http://{host}:{port}/db/{database}/tx/commit"
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.headers = {"Content-Type": "application/json",
                        "Authorization": "Basic " + token}

    def run(self, statement, params=None):
        payload = json.dumps({"statements": [
            {"statement": statement, "parameters": params or {}}]}).encode()
        req = urllib.request.Request(self.url, data=payload, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise SystemExit(f"连不上 Neo4j: {e.reason}")
        if data.get("errors"):
            raise SystemExit("Cypher 报错: " +
                             json.dumps(data["errors"][0], ensure_ascii=False)[:600])
        res = data["results"][0]
        return [dict(zip(res["columns"], r["row"])) for r in res.get("data", [])]


# ---------------------------------------------------------------- 解析 .cypher
def load_queries(path):
    blocks, title, buf = {}, None, []
    for line in open(path, encoding="utf-8").read().splitlines():
        s = line.strip()
        if s.startswith("// S") and "：" in s:
            if title and "\n".join(buf).strip():
                blocks[title] = "\n".join(buf).strip()
            title = s.lstrip("/ ").split("：")[0].strip()   # "S1 场景校验"
            buf = []
            continue
        if s.startswith("//"):
            continue
        if title:
            buf.append(line)
    if title and "\n".join(buf).strip():
        blocks[title] = "\n".join(buf).strip()
    return blocks


# ---------------------------------------------------------------- 推演主函数
def simulate_supply_cut(db, country, mineral, hops=3):
    """返回结构化推演结果；场景不存在时返回 {'error': ...}"""
    q = load_queries(os.path.join(HERE, "08_simulate.cypher"))
    params = {"country": country, "mineral": mineral, "maxHops": hops}

    def one(key):
        # $maxHops 出现在变长路径里必须是字面量，这里直接替换成数字
        stmt = q[key].rstrip().rstrip(";").replace("$maxHops", str(hops))
        return db.run(stmt, params)

    scenario = one("S1 场景校验")
    if not scenario:
        return {"error": f"{country} 没有 {mineral} 的有效产量（或该组合不存在），无法推演"}
    sc = scenario[0]

    direct = one("S2 直接受冲击")
    levels = one("S3 分层传播")
    impact_by_stage = one("S4 影响面")
    products = one("S5 受影响产品")
    alt_countries = one("S6 替代供应国")
    alt_products = one("S7 替代路线")
    terminals = one("S8 传导到终端")

    total_companies = db.run("MATCH (n:Company) RETURN count(n) AS c")[0]["c"]
    affected = sum(r["企业数"] for r in impact_by_stage)
    share = float(sc["占全球份额"] or 0)
    hhi = sc["HHI"] or 0

    if share >= 70:
        severity, why = "极高", "断供国占全球产量的七成以上，短期无法补位"
    elif share >= 50:
        severity, why = "高", "断供国是全球主供，替代国需要产能爬坡"
    elif share >= 30:
        severity, why = "中", "存在可替代供应国，但切换有成本"
    else:
        severity, why = "低", "供应格局分散，单一国家断供影响有限"

    src = sc["来源"]
    if isinstance(src, list):
        src = "、".join(str(x) for x in src)

    return {
        "scenario": {
            "country": sc["断供国"], "mineral": sc["矿种"],
            "production": sc["产量"], "unit": sc["单位"],
            "world_share_pct": share, "hhi": hhi,
            "top1_share": sc["全球第一国份额"],
            "data_review_flag": sc["数据待核实"], "source_id": src,
        },
        "direct": direct,
        "levels": levels,
        "impact": {
            "companies": affected,
            "share_of_all_companies": round(affected / total_companies, 3),
            "by_stage": impact_by_stage,
            "products": products,
            "terminals": terminals,
        },
        "alternatives": {"countries": alt_countries, "products": alt_products},
        "kpis": {"severity": severity, "reason": why,
                 "hops": hops, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")},
    }


# ---------------------------------------------------------------- 打印 / 报告
def render(result, out=None):
    w = out.write if out else sys.stdout.write
    if "error" in result:
        w(f"\n❌ {result['error']}\n")
        return
    sc, im = result["scenario"], result["impact"]
    k = result["kpis"]
    w(f"\n{'=' * 62}\n断供推演：{sc['country']} × {sc['mineral']}\n{'=' * 62}\n")
    w(f"  全球份额 {sc['world_share_pct']}%   该矿 HHI {sc['hhi']}   "
      f"严重度【{k['severity']}】\n  判断依据：{k['reason']}\n")
    w(f"\n[分层传播] 最多 {k['hops']} 跳\n")
    for r in result["levels"]:
        w(f"  第 {r['跳数']} 跳：{r['节点数']} 个节点  例：{'、'.join(r['示例企业'] or [])}\n")
    w(f"\n[影响面] 受影响企业 {im['companies']} 家"
      f"（占全部企业 {int(im['share_of_all_companies'] * 100)}%）\n")
    for r in im["by_stage"]:
        w(f"  {r['环节']:<6}{r['企业数']:>3} 家：{'、'.join(r['企业'])}\n")
    if im["products"]:
        w(f"\n[受影响产品] {'、'.join(p['产品'] for p in im['products'])}\n")
    if im["terminals"]:
        w("[传导到终端] " + "、".join(f"{t['终端客户']}({t['最短跳数']}跳)"
                                 for t in im["terminals"]) + "\n")
    if result["alternatives"]["countries"]:
        w("\n[替代供应国] " + "、".join(
            f"{c['替代国']}({c['全球份额']}%)" for c in result["alternatives"]["countries"][:5]) + "\n")
    else:
        w("\n[替代供应国] 无（该矿仅有此一国规模产量）\n")


def write_md(results):
    lines = ["# 第五部分 断供推演结果", "",
             f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}",
             "> 执行：`08_simulate.py`（APOC 广度优先 + 影响面聚合 + 替代路径）",
             "> 口径：只走 `quantity > 0` 的真实产量，只走 `review_flag=false` 的供应边；"
             "跳数上限 3 跳", ""]
    for res in results:
        if "error" in res:
            lines += [f"## ❌ {res['error']}", ""]
            continue
        sc, im, k = res["scenario"], res["impact"], res["kpis"]
        lines += [f"## {sc['country']} × {sc['mineral']}（严重度：{k['severity']}）", "",
                  "| 指标 | 数值 |", "|---|---|",
                  f"| 断供国全球份额 | **{sc['world_share_pct']}%** |",
                  f"| 该矿 HHI | {sc['hhi']} |",
                  f"| 受影响企业 | **{im['companies']} 家**（占全部 {int(im['share_of_all_companies'] * 100)}%）|",
                  f"| 传播跳数上限 | {k['hops']} |",
                  f"| 数据来源 | {sc['source_id']} |", "",
                  "### 分层传播", "", "| 跳数 | 节点数 | 示例 |", "|---|---|---|"]
        for r in res["levels"]:
            lines.append(f"| 第 {r['跳数']} 跳 | {r['节点数']} | "
                         f"{'、'.join(r['示例企业'] or [])} |")
        lines += ["", "### 影响面（按环节）", "", "| 环节 | 企业数 | 企业 |", "|---|---|---|"]
        for r in im["by_stage"]:
            lines.append(f"| {r['环节']} | {r['企业数']} | {'、'.join(r['企业'])} |")
        if im["products"]:
            lines += ["", "### 受影响产品", "", "| 产品 | 类别 | 技术路线 |", "|---|---|---|"]
            for p in im["products"]:
                lines.append(f"| {p['产品']} | {p['类别']} | {p['技术路线']} |")
        if im["terminals"]:
            lines += ["", "### 传导到终端", "",
                      "| 终端客户 | 环节 | 最短跳数 |", "|---|---|---|"]
            for t in im["terminals"]:
                lines.append(f"| {t['终端客户']} | {t['环节']} | {t['最短跳数']} |")
        if res["alternatives"]["countries"]:
            lines += ["", "### 替代供应国", "", "| 替代国 | 产量 | 全球份额 |", "|---|---|---|"]
            for c in res["alternatives"]["countries"]:
                lines.append(f"| {c['替代国']} | {c['产量']} | {c['全球份额']} |")
        if res["alternatives"]["products"]:
            lines += ["", "### 替代产品路线", "",
                      "| 受影响产品 | 替代产品 | 替代代价 |", "|---|---|---|"]
            for a in res["alternatives"]["products"]:
                lines.append(f"| {a['受影响产品']} | {a['替代产品']} | {a['替代代价']} |")
        lines.append("")
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines))
    return OUT_MD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default="7474")
    ap.add_argument("--user", default="neo4j")
    ap.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD"))
    ap.add_argument("--pair", action="append", default=[],
                    help="国家:矿种，可重复；不给则跑预置场景")
    ap.add_argument("--hops", type=int, default=3)
    args = ap.parse_args()

    if not args.password:
        import getpass
        args.password = getpass.getpass("Neo4j 密码: ")
    db = Neo4j(args.host, args.port, args.user, args.password, "neo4j")

    pairs = []
    for p in args.pair:
        c, m = p.split(":", 1)
        pairs.append((c.strip(), m.strip()))
    if not pairs:
        pairs = PRESETS

    results = []
    for c, m in pairs:
        res = simulate_supply_cut(db, c, m, args.hops)
        results.append(res)
        render(res)
    path = write_md(results)
    print(f"\n→ 推演报告已写出: {path}")
    json.dump(results, open(os.path.join(HERE, "C_part", "08_推演结果.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
