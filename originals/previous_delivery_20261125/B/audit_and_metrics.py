"""Preserve original audit; strict precision is verifiable, recall requires an itemized gold set."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,save_json,csv_read
def score(sheet):
 from openpyxl import load_workbook
 wb=load_workbook(sheet,data_only=True,read_only=True);rows=list(wb.active.values);headers=rows[0];records=[dict(zip(headers,r)) for r in rows[1:]];wb.close()
 judged=[r for r in records if r.get('人工判定') in ['正确','错误','部分正确']]
 total=len(judged);ok=sum(r['人工判定']=='正确' for r in judged);part=sum(r['人工判定']=='部分正确' for r in judged)
 reported_gold=sum(float(r.get('gold_count') or 0) for r in records)
 return {'audited_count':total,'correct':ok,'partial':part,'wrong':total-ok-part,'strict_accuracy':ok/total if total else None,'lenient_accuracy':(ok+.5*part)/total if total else None,'gold_itemized_available':False,'reported_gold_count':reported_gold,'verified_recall':None,'verified_f1':None,'reported_count_based_recall':ok/reported_gold if reported_gold else None,'reported_count_based_f1':2*ok/(total+reported_gold) if reported_gold else None,'scope':'严格准确率及加权准确率可以从原核对表重算；R/F1仅为58条人工总数口径的算术复算，没有逐条金标准，不能声称完整复现。65条符合课程建议50—100条；不伪造至100条。'}
def build(source,output):
 from openpyxl import Workbook
 output=Path(output)
 if output.exists():raise FileExistsError('拒绝覆盖已有核对表，请使用新输出路径')
 records=csv_read(source);headers=list(dict.fromkeys(list(records[0])+['人工判定','判定理由','核对者','gold_count']));wb=Workbook();ws=wb.active;ws.append(headers)
 for row in records:ws.append([row.get(k,'') for k in headers])
 output.parent.mkdir(parents=True,exist_ok=True);wb.save(output)
if __name__=='__main__':
 p=argparse.ArgumentParser();sp=p.add_subparsers(dest='action',required=True);s=sp.add_parser('score');s.add_argument('sheet',nargs='?',type=Path,default=ROOT/'B'/'audit_sheet.xlsx');b=sp.add_parser('build');b.add_argument('source',type=Path);b.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.action=='score':
  r=score(a.sheet);save_json(ROOT/'reports'/'B_metrics.json',r);print(json.dumps(r,ensure_ascii=False,indent=2))
 else:build(a.source,a.output)
