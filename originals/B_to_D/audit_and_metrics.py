# -*- coding: utf-8 -*-
"""
人工核对表生成 + 评估指标计算（B部分 · 知识抽取评估）

流程：
  1) 生成核对表：
     python audit_and_metrics.py build new_triples.csv
     → 产出 audit_sheet.xlsx（含"人工判定"列，组员填 正确/错误/部分正确）
  2) 回收后计算指标：
     python audit_and_metrics.py score audit_sheet.xlsx
     → 打印准确率；若核对表含 gold 列（标准答案），同时输出 P/R/F1
"""
import sys
import pandas as pd


def build(triples_csv: str, out="audit_sheet.xlsx"):
    df = pd.read_csv(triples_csv)
    df["人工判定"] = ""          # 填：正确 / 错误 / 部分正确
    df["判定理由"] = ""
    df["核对者"] = ""
    df.to_excel(out, index=False)
    print(f"已生成 {out}，共 {len(df)} 条待核对。"
          f"请按 evidence 列回查原文后填写【人工判定】列。")


def score(sheet="audit_sheet.xlsx"):
    df = pd.read_excel(sheet)
    judged = df[df["人工判定"].isin(["正确", "错误", "部分正确"])]
    if judged.empty:
        print("尚无已核对条目"); return
    n = len(judged)
    n_ok = (judged["人工判定"] == "正确").sum()
    n_part = (judged["人工判定"] == "部分正确").sum()
    acc_strict = n_ok / n
    acc_lenient = (n_ok + 0.5 * n_part) / n
    print(f"核对条数: {n}")
    print(f"严格准确率(正确/总数): {acc_strict:.3f}")
    print(f"宽松准确率(部分正确计0.5): {acc_lenient:.3f}")

    # 若存在 gold 列（标准答案三元组数），计算 P/R/F1
    if "gold_count" in df.columns and df["gold_count"].notna().any():
        gold_total = int(df["gold_count"].dropna().sum())
        extracted_ok = n_ok
        precision = extracted_ok / n if n else 0
        recall = extracted_ok / gold_total if gold_total else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        print(f"P={precision:.3f}  R={recall:.3f}  F1={f1:.3f}  (gold 标准三元组总数={gold_total})")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2])
    elif cmd == "score":
        score(sys.argv[2] if len(sys.argv) > 2 else "audit_sheet.xlsx")
    else:
        print(__doc__)
