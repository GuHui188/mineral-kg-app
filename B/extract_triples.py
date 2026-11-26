"""可重放已保存JSON；不默认重新调用LLM。新增抽取需另行配置API。"""
from pathlib import Path
import argparse,csv,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,Graph,PREDICATES,SCHEMA,build_graph,save_json

PREDICATE_NAMES=list(PREDICATES) # 10 business relations including INVESTS_IN/参股.
def build_entity_dict():
 g=Graph(build_graph());return {term:next(iter(ids)) for term,ids in g.aliases.items() if len(ids)==1},g.nodes
def make_prompt(text,source_id):
 aliases,nodes=build_entity_dict()
 entities=[{'id':n['id'],'name':n['name'],'type':n['label']} for n in nodes.values() if n['label']!='Source']
 return ('仅抽取原文明确陈述的事实，禁止补充常识。关系仅限：'+','.join(PREDICATE_NAMES)+
 '\n已知实体完整清单：'+json.dumps(entities,ensure_ascii=False)+
 '\n每项输出subject/predicate/object/evidence/source_id；subject和object优先使用实体ID；未知实体保留原名并标记待对齐；无事实输出[]。'+
 '\nsource_id='+source_id+'\n原文：\n'+text)
def parse_llm_json(raw):
 raw=raw.strip()
 if raw.startswith('```'):raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw,flags=re.I)
 obj=json.loads(raw)
 if not isinstance(obj,list):raise ValueError('LLM输出必须为JSON数组')
 for i,row in enumerate(obj):
  if not isinstance(row,dict) or not all(isinstance(row.get(k),str) for k in ['subject','predicate','object','evidence']):raise ValueError(f'第{i+1}项缺少字符串字段')
 return obj
def align(rows,source_id):
 aliases,nodes=build_entity_dict();result=[]
 for i,row in enumerate(rows,1):
  item=dict(row);reasons=[]
  for key in ['subject','object']:
   name=re.sub(r'[（(]新[）)]$','',row[key]).strip();eid=name if name in nodes else aliases.get(name.casefold())
   item[key+'_id']=eid
   if not eid:reasons.append('未知/歧义实体:'+name)
  typ=PREDICATES.get(row['predicate'])
  if not typ:reasons.append('非法关系:'+row['predicate'])
  elif item['subject_id'] and item['object_id']:
   if nodes[item['subject_id']]['label'] not in SCHEMA[typ][0] or nodes[item['object_id']]['label'] not in SCHEMA[typ][1]:reasons.append('端点类型不符合Schema')
  item.update(source_id=source_id,sequence_in_source=i,alignment_status='review' if reasons else 'aligned',alignment_notes=reasons)
  # Alignment is not manual factual acceptance. Never set import_flag from schema validity.
  result.append(item)
 return result
def replay_all():
 expected=[];actual=[]
 from kg import csv_read
 for source in ['S11','S12','S13','S20','S21','S23','S24']:
  rows=parse_llm_json((ROOT/'B'/'llm_outputs'/f'{source}.json').read_text(encoding='utf-8-sig'))
  actual.extend(align(rows,source))
  expected.extend([r for r in csv_read(ROOT/'B'/'new_triples.csv') if r['source_id']==source])
 if len(actual)!=len(expected):raise AssertionError('保存JSON与原始CSV行数不同')
 checks=[]
 def normalized(s):return re.sub(r'[（(]新[）)]$','',s).strip()
 for got,old in zip(actual,expected):
  good=(got['source_id']==old['source_id'] and got['predicate']==old['predicate'] and normalized(got['subject'])==normalized(old['subject_name']) and normalized(got['object'])==normalized(old['object_name']) and got['evidence'].strip()==old['evidence'].strip())
  got['original_triple_id']=old['triple_id'];checks.append({'triple_id':old['triple_id'],'matched_saved_record':good})
 save_json(ROOT/'reports'/'B_extraction_replay.json',{'count':len(actual),'all_records_matched':all(x['matched_saved_record'] for x in checks),'checks':checks,'aligned_records':actual,'scope':'仅重放已保存JSON及实体对齐；不是重新运行原模型，不恢复缺失的原始会话。'})
 return all(x['matched_saved_record'] for x in checks)
def main():
 p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');p.add_argument('--align',type=Path);p.add_argument('--source-id');p.add_argument('--prompt',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.replay:print('replay_match=',replay_all());return
 if not a.source_id:p.error('需要--source-id')
 if a.prompt:
  print(make_prompt(a.prompt.read_text(encoding='utf-8-sig'),a.source_id));return
 if not a.align or not a.output:p.error('需要--align及独立的--output')
 if a.output.exists():p.error('输出文件已存在，防止覆盖人工审核记录')
 save_json(a.output,align(parse_llm_json(a.align.read_text(encoding='utf-8-sig')),a.source_id))
if __name__=='__main__':main()
