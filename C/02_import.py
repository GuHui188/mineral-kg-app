"""Import immutable, namespaced canonical graph; refuses replacing a different snapshot."""
from pathlib import Path
import json,sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,DATASET,SCHEMA,save_json,Graph
from neo4j_client import Neo4j
def props(item,prefix):
 result={k:v for k,v in item.items() if v is not None and k not in ['source','target','type','support_evidence']}
 for k,v in list(result.items()):
  if isinstance(v,dict) or isinstance(v,list) and any(isinstance(x,(dict,list)) for x in v):result[k]=json.dumps(v,ensure_ascii=False)
 result[prefix]=DATASET+':'+item['id'];return result
def import_graph(db,data):
 db.run('CREATE CONSTRAINT kg_entity_unique IF NOT EXISTS FOR (n:KGEntity) REQUIRE n.kg_id IS UNIQUE')
 db.run('CREATE CONSTRAINT kg_snapshot_unique IF NOT EXISTS FOR (n:KGDataset) REQUIRE n.id IS UNIQUE')
 existing=db.run('MATCH (s:KGDataset {id:$dataset}) RETURN s.sha256 AS sha256',{'dataset':DATASET})
 if existing and existing[0]['sha256']!=data['sha256']:raise ValueError('同名dataset已有不同快照。请使用新的DATASET版本，不覆盖既有图。')
 statements=[]
 for label in sorted({n['label'] for n in data['nodes']}):
  rows=[props(n,'kg_id') for n in data['nodes'] if n['label']==label]
  statements.append((f'UNWIND $rows AS row MERGE (n:KGEntity:{label} {{kg_id:row.kg_id}}) SET n += row',{'rows':rows}))
 for typ in sorted({e['type'] for e in data['edges']}):
  if typ not in SCHEMA:raise ValueError('非法关系类型')
  rows=[{'source':DATASET+':'+e['source'],'target':DATASET+':'+e['target'],'properties':props(e,'kg_edge_id')} for e in data['edges'] if e['type']==typ]
  statements.append((f'UNWIND $rows AS row MATCH (a:KGEntity {{kg_id:row.source}}),(b:KGEntity {{kg_id:row.target}}) MERGE (a)-[r:{typ} {{kg_edge_id:row.properties.kg_edge_id}}]->(b) SET r += row.properties',{'rows':rows}))
 statements.append(('MERGE (s:KGDataset {id:$dataset}) SET s.sha256=$sha256',{'dataset':DATASET,'sha256':data['sha256']}))
 db.batch(statements)
 stats=db.run('MATCH (n:KGEntity {dataset:$dataset}) OPTIONAL MATCH (n)-[r]->(:KGEntity {dataset:$dataset}) RETURN count(DISTINCT n) AS nodes,count(r) AS edges',{'dataset':DATASET})[0]
 expected={'nodes':len(data['nodes']),'edges':len(data['edges'])}
 if stats!=expected:raise AssertionError(f'导入统计不符：{stats}，预期{expected}')
 return stats
if __name__=='__main__':
 data=json.loads((ROOT/'data'/'graph.json').read_text(encoding='utf-8'));db=Neo4j();s1=import_graph(db,data);s2=import_graph(db,data)
 report={'status':'passed','first_import':s1,'second_import':s2,'idempotence_passed':s1==s2,'dataset':DATASET,'sha256':data['sha256']};save_json(ROOT/'reports'/'neo4j_import.json',report);print(json.dumps(report,ensure_ascii=False))
