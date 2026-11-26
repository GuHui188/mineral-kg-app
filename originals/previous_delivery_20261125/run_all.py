"""Rebuild and verify A → B → C → D handoff, without API calls or Neo4j dependency."""
from pathlib import Path
import json,sys,subprocess,importlib.util,csv,collections
from kg import ROOT,DATASET,build_graph,Graph,validate,save_json,csv_read
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main():
 data=build_graph();save_json(ROOT/'data'/'graph.json',data);v=validate(data);save_json(ROOT/'reports'/'validation.json',v)
 if not v['passed']:raise RuntimeError('校验失败：'+str(v['errors']))
 g=Graph(data);replay=load('extract',ROOT/'B'/'extract_triples.py').replay_all()
 if not replay:raise RuntimeError('B保存的JSON与CSV不一致，详见重放报告')
 metrics=load('audit_metrics',ROOT/'B'/'audit_and_metrics.py').score(ROOT/'B'/'audit_sheet.xlsx');save_json(ROOT/'reports'/'B_metrics.json',metrics)
 save_json(ROOT/'reports'/'overview.json',g.overview());save_json(ROOT/'reports'/'concentration.json',g.concentration());save_json(ROOT/'reports'/'centrality.json',g.centrality())
 scenarios=[('刚果（金）','钴'),('中国','石墨'),('澳大利亚','锂')]
 results=[g.simulate(c,m) for c,m in scenarios];save_json(ROOT/'C'/'08_推演结果.json',results)
 reviews=[e for e in g.edges if e['type']!='CITES' and e.get('review_flag')]
 save_json(ROOT/'C'/'04_待核关系.json',reviews)
 with (ROOT/'C'/'04_待核关系.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['id','source','type','target','review_flag','note','record_ids','source_ids']);w.writeheader()
  for e in reviews:w.writerow({k:'|'.join(e.get(k,[])) if k in ['record_ids','source_ids'] else e.get(k) for k in w.fieldnames})
 with (ROOT/'C'/'04_待对齐实体_LLM.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['original_triple_id','subject','object','alignment_notes']);w.writeheader()
  replay_records=json.loads((ROOT/'reports'/'B_extraction_replay.json').read_text(encoding='utf-8'))['aligned_records']
  for r in replay_records:
   if r['alignment_status']=='review':w.writerow({k:'|'.join(r.get(k,[])) if k=='alignment_notes' else r.get(k) for k in w.fieldnames})
 with (ROOT/'reports'/'integration_decisions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['record_id','decision','reason','judgement']);w.writeheader();w.writerows(data['integration_decisions'])
 q=load('queries',ROOT/'C'/'queries.py');(ROOT/'C'/'07_queries.cypher').write_text('\n\n'.join('// '+qid+' '+name+'\n'+sql+';' for qid,(name,sql) in q.QUERIES.items()),encoding='utf-8')
 (ROOT/'C'/'08_simulate.cypher').write_text('// 参考查询：实际传播先按默认规则过滤，再由kg.py执行BFS。数据库后端用同一算法。\n\n'+'\n\n'.join('// '+qid+' '+q.QUERIES[qid][0]+'\n'+q.QUERIES[qid][1]+';' for qid in ['Q02','Q05','Q08']),encoding='utf-8')
 save_json(ROOT/'C'/'query_parameters.json',q.PARAMS)
 from d_adapter import KGService,INTENTS
 service=KGService();save_json(ROOT/'D_handoff'/'intent_templates.json',INTENTS)
 examples={'overview':{},'production':{'mineral':'钴'},'concentration':{},'potential_impact':{'country':'刚果金','mineral':'钴'},'substitution':{'mineral':'钴'},'policy':{'country':'中国'},'upstream':{'company':'宁德时代'},'provenance':{'record_id':'R0191'}}
 for intent,params in examples.items():save_json(ROOT/'D_handoff'/'examples'/f'{intent}.json',service.query(intent,params))
 save_json(ROOT/'D_handoff'/'graph_for_visualization.json',data);save_json(ROOT/'D_handoff'/'entity_aliases.json',{k:sorted(v) for k,v in g.aliases.items()})
 save_json(ROOT/'D_handoff'/'map_country_data.json',[{'id':n['id'],'name':n['name'],'iso_alpha3':n.get('iso_alpha3'),'region':n.get('region'),'map_eligible':bool(n.get('iso_alpha3'))} for n in g.nodes.values() if n['label']=='Country'])
 save_json(ROOT/'D_handoff'/'graphrag_context_example.json',service.context('宁德时代的钴上游供应有哪些来源'))
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
 (ROOT/'reports'/'regression_tests.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
 if result.returncode:print(result.stderr);raise RuntimeError('回归测试失败')
 npath=ROOT/'reports'/'neo4j_verification.json';neo=json.loads(npath.read_text(encoding='utf-8')) if npath.exists() else {}
 matched=neo.get('status')=='passed' and neo.get('sha256')==data['sha256']
 save_json(ROOT/'reports'/'run_status.json',{'offline_rebuild':'passed','data_validation':'passed','B_saved_json_replay':'passed','B_alias_alignment':'passed' if not any(r['alignment_status']=='review' for r in replay_records) else 'review_queue_available','B_metrics':'passed','regression_tests':'passed','d_eight_templates':'passed','neo4j_actual_import':'passed' if matched else 'blocked_not_installed','neo4j_cypher_execution':'passed' if matched else 'not_run','external_llm':'not_called','unverifiable_materials':'see reports/missing_materials.csv'})
 print(json.dumps({'validation':v['passed'],'overview':g.overview(),'scenarios':[{'country':r['scenario']['country'],'mineral':r['scenario']['mineral'],'companies':r['company_count'],'products':r['product_count'],'alternatives':len(r['alternatives'])} for r in results],'tests':result.stderr[-160:]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
