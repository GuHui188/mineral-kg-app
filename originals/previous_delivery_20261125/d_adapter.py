"""D可直接调用的数据接口；参数模板、结构化答案、路径高亮与子图上下文。"""
from pathlib import Path
from datetime import date
import sys,json,re
from kg import ROOT,Graph,DATASET,active

INTENTS={
 'overview':{'name':'图谱概览','template':'Q01','keywords':['概览','规模','多少节点']},
 'production':{'name':'产量与分布','template':'Q02','keywords':['产量','产矿','生产国']},
 'concentration':{'name':'覆盖范围与集中度','template':'Q03','keywords':['集中','HHI','hhi']},
 'potential_impact':{'name':'矿种潜在关联推演','template':'Q05','keywords':['断供','影响','冲击']},
 'substitution':{'name':'有条件的技术替代','template':'Q08','keywords':['替代','绕开','避开']},
 'policy':{'name':'涉目标国政策','template':'Q06','keywords':['政策','管制','关税','禁令']},
 'upstream':{'name':'供应与股权上游关联','template':'Q07+SUPPLIES逆向','keywords':['上游','控股','股权','参股']},
 'provenance':{'name':'事实来源','template':'Q11','keywords':['来源','溯源','依据','证据']},
}
class KGService:
 def __init__(self,backend='snapshot'):
  if backend not in ['snapshot','neo4j']:raise ValueError('backend仅支持snapshot/neo4j')
  self.backend=backend
  if backend=='neo4j':
   sys.path.insert(0,str(ROOT/'C'));from neo4j_client import Neo4j
   rows=Neo4j().run('MATCH (n:KGEntity {dataset:$dataset}) RETURN properties(n) AS properties',{'dataset':DATASET})
   erows=Neo4j().run('MATCH (a:KGEntity {dataset:$dataset})-[r]->(b:KGEntity {dataset:$dataset}) RETURN properties(r) AS properties,a.id AS source,b.id AS target,type(r) AS relation_type',{'dataset':DATASET})
   if not rows:raise ValueError('指定dataset未导入，不能自动切换成旧库结果')
   nodes=[r['properties'] for r in rows];edges=[]
   for r in erows:
    e=r['properties'];e.update(source=r['source'],target=r['target'],type=r['relation_type']);edges.append(e)
   stored=Neo4j().run('MATCH (s:KGDataset {id:$dataset}) RETURN s.sha256 AS sha256',{'dataset':DATASET})
   self.graph=Graph({'nodes':nodes,'edges':edges,'sha256':stored[0]['sha256']})
  else:self.graph=Graph()
 def search(self,text,limit=20):
  if not isinstance(limit,int) or not 1<=limit<=100:raise ValueError('limit范围1—100')
  term=text.casefold();ids=set()
  for alias,items in self.graph.aliases.items():
   if term in alias:ids.update(items)
  return [self.graph.nodes[i] for i in sorted(ids)[:limit]]
 def simulate(self,country,mineral,max_hops=4,as_of='2026-11-25',include_review=False):
  date.fromisoformat(as_of);return self.graph.simulate(country,mineral,max_hops,as_of,include_review)
 def overview(self):return self.graph.overview()
 def subgraph(self,node_ids):return self.graph.subgraph(node_ids)
 def query(self,intent,parameters=None):
  p=parameters or {};g=self.graph;as_of=p.get('as_of','2026-11-25');date.fromisoformat(as_of);rows=[];paths=[];note=''
  if intent not in INTENTS:raise ValueError('未知意图，请使用8类模板之一')
  if intent=='overview':rows=[g.overview(as_of)]
  elif intent=='production':rows=g.production(p.get('mineral'))
  elif intent=='concentration':rows=g.concentration();note='只展示已收录国家覆盖率与份额平方和；不评全球HHI等级。'
  elif intent=='potential_impact':
   result=self.simulate(p['country'],p['mineral'],p.get('max_hops',4),as_of,p.get('include_review',False));rows=result.get('companies',[])
   anchor=result.get('production',[{}])[0];cid=result['scenario']['country_id']
   paths=[{'node_ids':[cid]+x['path_node_ids'],'edge_ids':[anchor['id']]+x['path_edge_ids']} for x in rows];note=result.get('scope',result.get('reason',''))
  elif intent=='substitution':
   rows=g.substitutes(p['mineral'],as_of);note='均为需适配的技术路线候选；当前供给量及切换成本未知。';mid=g.resolve(p['mineral'],'Mineral')
   for row in rows:
    dep=next(e for e in g.edges if e['type']=='REQUIRES' and e['source']==row['replaces_id'] and e['target']==mid)
    paths.append({'node_ids':[row['alternative_id'],row['replaces_id'],mid],'edge_ids':[row['edge_id'],dep['id']]})
  elif intent=='policy':
   cid=g.resolve(p['country'],'Country')
   for e in g.selected(as_of):
    if e['type']=='TARGETS' and e['target']==cid:
     event=g.nodes[e['source']];issuers=[r['target'] for r in g.selected(as_of) if r['type']=='ISSUED_BY' and r['source']==event['id']]
     rows.append({'event_id':event['id'],'name':event['name'],'effective_date':event.get('effective_date'),'original_status':event.get('status'),'issuing_countries':issuers,'source_ids':event['source_ids']})
   note='这是原数据登记的政策与目标国关联，不表示所有政策在查询日仍有效；缺少逐条政策失效更新记录。'
  elif intent=='upstream':
   eid=g.resolve(p['company'],'Company');rows=g.bfs(eid,p.get('max_hops',4),reverse=True,types=('SUPPLIES','HOLDS','INVESTS_IN'),as_of=as_of)
   for row in rows:row['registered_country_id']=g.nodes[row['id']].get('country_id')
   paths=[{'node_ids':x['path_node_ids'],'edge_ids':x['path_edge_ids']} for x in rows];note='企业注册地、股东所属国和供应关联不能直接当作实际采购来源国。'
  elif intent=='provenance':rows=g.provenance(p['record_id'])
  ids={i for path in paths for i in path['node_ids']};edge_ids={i for path in paths for i in path['edge_ids']}
  for row in rows:
   for k in ['source','target','country_id','mineral_id','alternative_id','replaces_id','event_id','id']:
    v=row.get(k)
    if isinstance(v,str) and v in g.nodes:ids.add(v)
   if 'edge' in row:ids.update([row['edge']['source'],row['edge']['target']]);edge_ids.add(row['edge']['id'])
  sources=sorted({s for e in g.edges if e['id'] in edge_ids for s in e['source_ids']}|{s for r in rows for s in r.get('source_ids',[])})
  ids.update(sources)
  return {'intent':intent,'template':INTENTS[intent]['template'],'parameters':p,'backend':self.backend,'dataset':DATASET,'as_of':as_of,'answer':f"{INTENTS[intent]['name']}：返回{len(rows)}条记录。"+note,'rows':rows,'graph':g.subgraph(ids),'highlight_paths':paths,'sources':[g.nodes[s] for s in sources],'limitations':note}
 def classify(self,question):
  for name in ['provenance','substitution','potential_impact','policy','upstream','concentration','production','overview']:
   if any(k in question for k in INTENTS[name]['keywords']):return name
  return None
 def answer(self,question):
  intent=self.classify(question)
  if not intent:return {'status':'context_only','context':self.context(question),'answer':'当前规则模板未覆盖该问题。可将以下子图上下文交给另行配置的LLM；本接口没有调用模型。'}
  params={};matches=[]
  for alias,ids in self.graph.aliases.items():
   if alias in question.casefold() and len(ids)==1:matches.append((len(alias),next(iter(ids))))
  for _,eid in sorted(matches,reverse=True):
   label=self.graph.nodes[eid]['label'];key={'Country':'country','Mineral':'mineral','Company':'company'}.get(label)
   if key:params.setdefault(key,eid)
  rid=re.search(r'\b[RE]\d{4}\b',question,re.I)
  if rid:params['record_id']=rid.group().upper()
  required={'potential_impact':['country','mineral'],'substitution':['mineral'],'policy':['country'],'upstream':['company'],'provenance':['record_id']}.get(intent,[])
  missing=[k for k in required if k not in params]
  if missing:return {'status':'needs_parameters','intent':intent,'parameters':params,'missing_parameters':missing,'answer':'请补充：'+','.join(missing)}
  return self.query(intent,params)
 def context(self,question,max_facts=30):
  ids={eid for alias,candidates in self.graph.aliases.items() if len(alias)>=2 and alias in question.casefold() for eid in candidates};facts=[]
  for e in self.graph.selected():
   if e['source'] in ids or e['target'] in ids:facts.append({'subject_id':e['source'],'predicate':e['type'],'object_id':e['target'],'record_ids':e['record_ids'],'source_ids':e['source_ids'],'note':e.get('note')})
  return {'question':question,'facts':facts[:max_facts],'truncated':len(facts)>max_facts,'llm_called':False,'instructions':'仅使用给定事实，保留记录号和来源；缺少信息应说明；不得从矿种关联推断实际国家采购关系。'}
