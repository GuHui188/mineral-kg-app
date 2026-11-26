"""Actual Neo4j import, rerun idempotence, 12 queries and D backend parity."""
from pathlib import Path
import importlib.util,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,Graph,save_json
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
  for country,mineral in [('刚果金','钴'),('中国','石墨'),('澳大利亚','锂')]:
   a=local.simulate(country,mineral);b=remote.simulate(country,mineral)
   # Stored list order is immaterial; compare key result sets.
   good=({x['id'] for x in a['companies']}=={x['id'] for x in b['companies']} and {x['id'] for x in a['products']}=={x['id'] for x in b['products']} and {x['edge_id'] for x in a['alternatives']}=={x['edge_id'] for x in b['alternatives']})
   if not good:raise AssertionError('数据库与快照推演不一致：'+country+mineral)
   parity.append({'country':country,'mineral':mineral,'passed':good})
  status={'status':'passed','actual_import':first,'second_import':second,'idempotence':first==second,'cypher_templates_executed':len(queries),'simulation_parity':parity,'sha256':data['sha256']}
 except Exception as e:status={'status':'blocked','actual_import_verified':False,'error':str(e),'note':'快照重建和Python推演通过，不等同Neo4j入库及Cypher执行已通过。'}
 save_json(ROOT/'reports'/'neo4j_verification.json',status)
 print(json.dumps(status,ensure_ascii=False,indent=2));return 0 if status['status']=='passed' else 2
if __name__=='__main__':sys.exit(main())
