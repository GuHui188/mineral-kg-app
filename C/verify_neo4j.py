"""Actual Neo4j import, rerun idempotence, 12 queries and D backend parity."""
from pathlib import Path
import importlib.util,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,Graph,save_json,DATASET
from neo4j_client import Neo4j
from queries import QUERIES,PARAMS
def main():
 status={'status':'not_run'}
 try:
  db=Neo4j();db.run('RETURN 1 AS ready');spec=importlib.util.spec_from_file_location('kg_import',ROOT/'C'/'02_import.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  data=json.loads((ROOT/'data'/'graph.json').read_text(encoding='utf-8'));first=mod.import_graph(db,data);second=mod.import_graph(db,data)
  if first!=second:raise AssertionError('重复导入不幂等')
  queries={qid:{'name':name,'rows':db.run(sql,PARAMS)} for qid,(name,sql) in QUERIES.items()}
  save_json(ROOT/'reports'/'neo4j_queries.json',queries)
  from d_adapter import KGService
  local=KGService();remote=KGService('neo4j');parity=[]
  graph=local.graph;semantic=[]
  def check(name,condition):
   semantic.append({'check':name,'passed':bool(condition)})
   if not condition:raise AssertionError('Cypher/Python语义不一致：'+name)
  check('Q01_count',queries['Q01']['rows']==[{'nodes':len(data['nodes']),'edges':len(data['edges'])}])
  check('Q02_positive_producers',{r['country_id'] for r in queries['Q02']['rows']}=={e['source'] for e in graph.production(PARAMS['mineral_id'])})
  concentrations={r['mineral_id']:r for r in graph.concentration()}
  check('Q03_partial_hhi',len(queries['Q03']['rows'])==len(concentrations) and all(abs(r['coverage_pct']-concentrations[r['mineral_id']]['coverage_pct'])<.011 and abs(r['partial_hhi']-concentrations[r['mineral_id']]['partial_hhi'])<.011 for r in queries['Q03']['rows']))
  check('Q04_review_filtered_trade',{(r['exporter'],r['importer']) for r in queries['Q04']['rows']}=={(e['source'],e['target']) for e in graph.selected() if e['type']=='EXPORTS_TO' and e.get('mineral_id')==PARAMS['mineral_id']})
  check('Q05_downstream_companies',{r['company_id'] for r in queries['Q05']['rows']}=={r['id'] for r in graph.bfs(PARAMS['mineral_id']) if r['label']=='Company'})
  check('Q06_target_country_policies',{r['event_id'] for r in queries['Q06']['rows']}=={r['event_id'] for r in local.query('policy',{'country':PARAMS['country_id']})['rows']})
  check('Q07_upstream_entities',{r['upstream_id'] for r in queries['Q07']['rows']}=={r['id'] for r in local.query('upstream',{'company':PARAMS['entity_id']})['rows']})
  check('Q08_qualified_substitutes',{r['edge_id'] for r in queries['Q08']['rows']}=={r['edge_id'] for r in graph.substitutes(PARAMS['mineral_id'])})
  check('Q09_directed_degree',{r['id']:r['degree'] for r in queries['Q09']['rows']}=={r['id']:r['degree'] for r in graph.centrality()})
  check('Q10_event_anchor',len(queries['Q10']['rows'])==1 and queries['Q10']['rows'][0]['event_id']==PARAMS['event_id'])
  expected_sources={s['id'] for row in graph.provenance(PARAMS['record_id']) for s in row['sources']}
  check('Q11_fact_sources',{r['source_id'] for r in queries['Q11']['rows']}==expected_sources)
  from collections import Counter
  expected=Counter(s for e in graph.edges if e['type']!='CITES' for s in e['source_ids'])
  check('Q12_source_fact_counts',{r['source_id']:r['fact_count'] for r in queries['Q12']['rows']}==dict(expected))
  for country,mineral in [('刚果金','钴'),('中国','石墨'),('澳大利亚','锂')]:
   a=local.simulate(country,mineral);b=remote.simulate(country,mineral)
   # Stored list order is immaterial; compare key result sets.
   good=({x['id'] for x in a['companies']}=={x['id'] for x in b['companies']} and {x['id'] for x in a['products']}=={x['id'] for x in b['products']} and {x['edge_id'] for x in a['alternatives']}=={x['edge_id'] for x in b['alternatives']})
   if not good:raise AssertionError('数据库与快照推演不一致：'+country+mineral)
   parity.append({'country':country,'mineral':mineral,'passed':good})
  d_examples={'overview':{},'production':{'mineral':'钴'},'concentration':{},'potential_impact':{'country':'刚果金','mineral':'钴'},'substitution':{'mineral':'钴'},'policy':{'country':'中国'},'upstream':{'company':'宁德时代'},'provenance':{'record_id':'R0191'}}
  for intent,parameters in d_examples.items():save_json(ROOT/'D_handoff'/'examples_neo4j'/f'{intent}.json',remote.query(intent,parameters))
  save_json(ROOT/'reports'/'neo4j_semantic_checks.json',semantic)
  save_json(ROOT/'C'/'08_推演结果_数据库实测.json',[remote.simulate(c,m) for c,m in [('刚果金','钴'),('中国','石墨'),('澳大利亚','锂')]])
  from datetime import datetime,timezone
  status={'status':'passed','tested_at_utc':datetime.now(timezone.utc).isoformat(),'dataset':DATASET,'database':db.database,'actual_import':first,'second_import':second,'idempotence':first==second,'cypher_templates_executed':len(queries),'semantic_checks_passed':len(semantic),'d_intents_executed':len(d_examples),'simulation_parity':parity,'sha256':data['sha256']}
 except Exception as e:status={'status':'blocked','actual_import_verified':False,'error':str(e),'note':'快照重建和Python推演通过，不等同Neo4j入库及Cypher执行已通过。'}
 save_json(ROOT/'reports'/'neo4j_verification.json',status)
 print(json.dumps(status,ensure_ascii=False,indent=2));return 0 if status['status']=='passed' else 2
if __name__=='__main__':sys.exit(main())
