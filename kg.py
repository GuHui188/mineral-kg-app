"""Canonical graph, quality-aware queries and potential supply-chain analysis. Stdlib only."""
from pathlib import Path
from collections import Counter, defaultdict, deque
import csv, json, math, hashlib

ROOT=Path(__file__).resolve().parent
DATASET='mineral-20261125-v1'
DIMENSIONS=[('01_dim_country.csv','country_id','Country'),('02_dim_company.csv','company_id','Company'),('03_dim_mineral.csv','mineral_id','Mineral'),('04_dim_product.csv','product_id','Product'),('05_dim_policy_event.csv','event_id','PolicyEvent'),('07_来源登记表_source_registry.csv','source_id','Source')]
PREDICATES={'出产':'PRODUCES','出口至':'EXPORTS_TO','供应':'SUPPLIES','控股':'HOLDS','参股':'INVESTS_IN','受管制于':'REGULATED_BY','可替代':'SUBSTITUTES','需要':'REQUIRES','发布于':'ISSUED_BY','作用于':'TARGETS'}
SCHEMA={'PRODUCES':({'Country','Company'},{'Mineral'}),'EXPORTS_TO':({'Country'},{'Country'}),'SUPPLIES':({'Mineral','Company'},{'Company','Mineral','Product'}),'HOLDS':({'Country','Company'},{'Company'}),'INVESTS_IN':({'Country','Company'},{'Company'}),'REGULATED_BY':({'Mineral','Product'},{'PolicyEvent'}),'SUBSTITUTES':({'Product'},{'Product'}),'REQUIRES':({'Product'},{'Mineral'}),'ISSUED_BY':({'PolicyEvent'},{'Country'}),'TARGETS':({'PolicyEvent'},{'Country'}),'CITES':({'Country','Company','Mineral','Product','PolicyEvent'},{'Source'})}
NUMERIC={'quantity','share_pct','ratio_pct','hold_ratio_pct','confidence','valid_year','since_year','data_year','original_data_year','stat_year','collection_year','world_production_2025','world_reserve','top1_share','hhi','hhi_recomputed','hhi_coverage_pct','reserve_li_t','reserve_reo_t','reserve_ni_t','reserve_co_t','founded_year'}
def csv_read(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save_json(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def number(v):
 try:return float(v) if v not in [None,'','NA','—'] else None
 except (ValueError,TypeError):return None
def boolean(v):return str(v).strip().lower() in ['true','1','是']
def split(v):return [s.strip() for s in str(v or '').split('|') if s.strip() not in ['','NA','—','None']]
def cast(row):
 out={}
 for k,v in row.items():
  if k in NUMERIC:out[k]=number(v)
  elif k in ['review_flag','dependency_scope_complete']:out[k]=boolean(v)
  else:out[k]=None if v in ['','NA'] else v
 return out
def year(v):
 if not v:return None
 try:return int(str(v)[:4])
 except (ValueError,TypeError):return None
def active(e,as_of='2026-11-25',include_review=False):
 if e.get('review_flag') and not include_review:return False
 if e.get('valid_from') and str(e['valid_from'])[:10]>as_of:return False
 if e.get('valid_to') and str(e['valid_to'])[:10]<as_of:return False
 return True

def build_graph(root=ROOT):
 nodes={};edges=[];errors=[];decisions=[];a=root/'A'
 for fname,key,label in DIMENSIONS:
  for row in csv_read(a/fname):
   rid=row[key]
   if rid in nodes:errors.append('duplicate entity '+rid)
   n=cast(row);n.update(id=rid,label=label,dataset=DATASET,name=row.get('name_zh') or row.get('title'),source_ids=split(row.get('source_id')))
   if rid=='C_BRA':n['field_review_flags']=['reserve_reo_t']
   nodes[rid]=n
 by_name={n.get('name'):n['id'] for n in nodes.values() if n['label']=='Mineral'}
 def add(sid,typ,oid,rid,props,origin):
  if sid not in nodes or oid not in nodes:errors.append(f'{rid}: unknown endpoint {sid}/{oid}');return
  if typ not in SCHEMA or nodes[sid]['label'] not in SCHEMA[typ][0] or nodes[oid]['label'] not in SCHEMA[typ][1]:errors.append(f'{rid}: invalid schema {sid}/{typ}/{oid}');return
  e=dict(props);e.update(id=rid,source=sid,target=oid,type=typ,record_ids=[rid],origin=origin,dataset=DATASET)
  e['source_ids']=split(props.get('source_id'));e['review_flag']=boolean(props.get('review_flag'))
  edges.append(e)
 for row in csv_read(a/'06_fact_relation.csv'):
  props=cast(row)
  # Statistical years remain in data_year/stat_year; they do not assert a historical validity interval.
  add(row['subject_id'],PREDICATES[row['predicate']],row['object_id'],row['triple_id'],props,'A.fact')
 for row in csv_read(a/'04_dim_product.csv'):
  for mineral in split(row.get('key_minerals')):
   if mineral not in by_name:errors.append('unknown key_mineral '+mineral);continue
   mid=by_name[mineral]
   add(row['product_id'],'REQUIRES',mid,f"DREQ_{row['product_id']}_{mid}",{'source_id':row['source_id'],'confidence':number(row['confidence']),'review_flag':number(row['confidence'])<.8,'note':'由产品表确定依赖生成；本项目七矿种范围。'},'A.product.derived')
  for mineral in split(row.get('conditional_minerals')):
   mid=by_name[mineral]
   add(row['product_id'],'REQUIRES',mid,f"DOPT_{row['product_id']}_{mid}",{'source_id':row['source_id'],'confidence':number(row['confidence']),'review_flag':True,'dependency_kind':'conditional','note':'按车型/配方而定，不能作为全部产品确定依赖。'},'A.product.conditional')
 for row in csv_read(a/'05_dim_policy_event.csv'):
  base={'source_id':row['source_id'],'confidence':number(row['confidence']),'review_flag':number(row['confidence'])<.8,'note':row['note']}
  if row['event_type'] not in ['罢工','断航']:
   for cid in split(row['issuing_country']):add(row['event_id'],'ISSUED_BY',cid,'DISS_'+row['event_id']+'_'+cid,base,'A.policy.derived')
  for cid in split(row['target_country']):add(row['event_id'],'TARGETS',cid,'DTAR_'+row['event_id']+'_'+cid,base,'A.policy.derived')
 index={(e['source'],e['type'],e['target'],e.get('mineral_id')):e for e in edges}
 for row in csv_read(root/'B'/'new_triples_v2.csv'):
  rid=row['triple_id']
  if row['import_flag']!='是':
   decisions.append({'record_id':rid,'decision':'不从B抽取结果导入','reason':'保留B原人工判定及去重标志','judgement':row['人工判定']});continue
  typ=PREDICATES.get(row['predicate']);key=(row['subject_id'],typ,row['object_id'],None)
  if key in index:
   e=index[key];e['record_ids'].append(rid);e['source_ids']=sorted(set(e['source_ids']+split(row['source_id'])))
   e.setdefault('support_evidence',[]).append({'record_id':rid,'source_id':row['source_id'],'evidence':row['evidence']})
   decisions.append({'record_id':rid,'decision':'合并至 '+e['id'],'reason':'相同端点及关系去重，保留来源及抽取记录号'});continue
  props=cast(row);props['review_flag']=boolean(row['review_flag']);props['source_id']=row['source_id']
  props['original_value_status']=row['value_status']
  props['value_status']='待核' if props['review_flag'] else '已人工核对'
  props['valid_from']=row['valid_from']+'-01-01' if len(row.get('valid_from',''))==4 else row.get('valid_from') or None
  props['valid_to']=row['valid_to']+'-12-31' if len(row.get('valid_to',''))==4 else row.get('valid_to') or None
  props['confidence']=None # No invented model confidence.
  add(row['subject_id'],typ,row['object_id'],rid,props,'B.v6.1')
  decisions.append({'record_id':rid,'decision':'导入；待核单独标记' if props['review_flag'] else '导入','reason':'按B人工标记；没有新增人工抽检或LLM调用'})
 # Source nodes and entity-level CITES are navigational; fact-level sources stay on the business edge.
 citations=set()
 for n in nodes.values():
  if n['label']!='Source':citations.update((n['id'],sid) for sid in n['source_ids'])
 for e in edges:citations.update((e['source'],sid) for sid in e['source_ids'])
 for nid,sid in sorted(citations):add(nid,'CITES',sid,'CITE_'+nid+'_'+sid,{'source_id':sid,'review_flag':False},'derived.navigation')
 for e in edges:
  for sid in e['source_ids']:
   if sid not in nodes or nodes[sid]['label']!='Source':errors.append(e['id']+': unknown source '+sid)
 graph={'dataset':DATASET,'nodes':list(nodes.values()),'edges':edges,'integration_decisions':decisions,'build_errors':errors}
 payload=json.dumps({'nodes':graph['nodes'],'edges':edges},ensure_ascii=False,sort_keys=True).encode()
 graph['sha256']=hashlib.sha256(payload).hexdigest()
 return graph

class Graph:
 def __init__(self,data=None):
  self.data=data or json.loads((ROOT/'data'/'graph.json').read_text(encoding='utf-8'));self.nodes={n['id']:n for n in self.data['nodes']};self.edges=self.data['edges']
  self.aliases=defaultdict(set)
  for n in self.nodes.values():
   for term in [n['id'],n.get('name'),n.get('name_en')]+split(n.get('alias')):
    if term:self.aliases[term.casefold()].add(n['id'])
  p=ROOT/'B'/'extend_alias.csv'
  if p.exists():
   for r in csv_read(p):
    if r['status']=='确认' and r['entity_id'] in self.nodes:self.aliases[r['alias'].casefold()].add(r['entity_id'])
  self.out=defaultdict(list);self.inc=defaultdict(list)
  for e in self.edges:self.out[e['source']].append(e);self.inc[e['target']].append(e)
 def resolve(self,value,label=None):
  candidates=self.aliases.get(value.casefold(),set());candidates={i for i in candidates if label is None or self.nodes[i]['label']==label}
  if len(candidates)!=1:raise ValueError(f'实体无法唯一识别：{value}；候选={sorted(candidates)}')
  return next(iter(candidates))
 def selected(self,as_of='2026-11-25',include_review=False):return [e for e in self.edges if e['type']!='CITES' and active(e,as_of,include_review)]
 def overview(self,as_of='2026-11-25'):
  business=[e for e in self.edges if e['type']!='CITES'];current=self.selected(as_of)
  return {'dataset':DATASET,'sha256':self.data['sha256'],'as_of':as_of,'node_count':len(self.nodes),'business_nodes':sum(n['label']!='Source' for n in self.nodes.values()),'business_edges_stored':len(business),'business_edges_current_default':len(current),'citation_edges':len(self.edges)-len(business),'nodes_by_type':dict(Counter(n['label'] for n in self.nodes.values())),'business_edges_by_type':dict(Counter(e['type'] for e in business)),'default_edges_by_type':dict(Counter(e['type'] for e in current)),'review_edges':sum(bool(e.get('review_flag')) for e in business),'future_edges':sum(bool(e.get('valid_from') and e['valid_from']>as_of) for e in business),'scope':'现有数据关联分析；并非全球完整图或经确认的国家采购依赖。'}
 def production(self,mineral=None):
  mid=self.resolve(mineral,'Mineral') if mineral else None
  return sorted([e for e in self.selected() if e['type']=='PRODUCES' and self.nodes[e['source']]['label']=='Country' and (mid is None or e['target']==mid) and (number(e.get('quantity')) or 0)>0 and (number(e.get('share_pct')) or 0)>0],key=lambda e:e['share_pct'],reverse=True)
 def concentration(self):
  result=[]
  for n in self.nodes.values():
   if n['label']!='Mineral':continue
   rows=self.production(n['id']);result.append({'mineral_id':n['id'],'mineral':n['name'],'coverage_pct':round(sum(e['share_pct'] for e in rows),2),'partial_hhi':round(sum(e['share_pct']**2 for e in rows),2),'countries':len(rows),'scope':'收录份额平方和，非全球完整HHI，不套用全球集中等级','source_ids':sorted({s for e in rows for s in e['source_ids']})})
  return result
 def bfs(self,start,max_hops=4,reverse=False,types=('SUPPLIES',),as_of='2026-11-25',include_review=False):
  if isinstance(max_hops,bool) or not isinstance(max_hops,int) or not 1<=max_hops<=6:raise ValueError('max_hops必须为1—6的整数')
  adj=self.inc if reverse else self.out;visited={start};queue=deque([(start,[start],[])]);found=[]
  while queue:
   current,path,ids=queue.popleft()
   if len(ids)>=max_hops:continue
   for e in sorted(adj[current],key=lambda e:e['id']):
    if e['type'] not in types or not active(e,as_of,include_review):continue
    nxt=e['source'] if reverse else e['target']
    if nxt in visited:continue
    visited.add(nxt);pp=path+[nxt];ee=ids+[e['id']];found.append({'id':nxt,'name':self.nodes[nxt]['name'],'label':self.nodes[nxt]['label'],'level':len(ee),'path_node_ids':pp,'path_edge_ids':ee});queue.append((nxt,pp,ee))
  return found
 def substitutes(self,mineral,as_of='2026-11-25',include_review=False):
  mid=self.resolve(mineral,'Mineral');all_deps=defaultdict(set)
  # Any dependency, including conditional/review, prevents a false assertion of complete avoidance.
  for e in self.edges:
   if e['type']=='REQUIRES':all_deps[e['source']].add(e['target'])
  impacted={e['source'] for e in self.selected(as_of) if e['type']=='REQUIRES' and e['target']==mid};results=[]
  for e in self.edges:
   if e['type']!='SUBSTITUTES' or not active(e,as_of,include_review) or e['target'] not in impacted:continue
   alt=self.nodes[e['source']]
   if not alt.get('dependency_scope_complete',False) or mid in all_deps[alt['id']]:continue
   results.append({'alternative_id':alt['id'],'alternative':alt['name'],'replaces_id':e['target'],'replaces':self.nodes[e['target']]['name'],'edge_id':e['id'],'condition':e.get('substitution_condition') or e.get('note'),'source_ids':e['source_ids'],'review_flag':e['review_flag'],'scope':'技术路线候选；需要工艺/性能适配；未证明现有产能可以立即切换。'})
  return results
 def simulate(self,country,mineral,max_hops=4,as_of='2026-11-25',include_review=False):
  cid=self.resolve(country,'Country');mid=self.resolve(mineral,'Mineral')
  # Enforce validation even when no producer is found.
  if isinstance(max_hops,bool) or not isinstance(max_hops,int) or not 1<=max_hops<=6:raise ValueError('max_hops必须为1—6的整数')
  production=[e for e in self.production(mid) if e['source']==cid]
  if not production:return {'scenario':{'country_id':cid,'mineral_id':mid,'as_of':as_of},'status':'insufficient_production_evidence','reason':'当前表中无该国该矿种正产量记录；不按零产量、也不据此判断断供影响为零。','companies':[],'products':[],'alternatives':[]}
  linked=self.bfs(mid,max_hops,as_of=as_of,include_review=include_review)
  companies=[x for x in linked if x['label']=='Company'];deps=[e for e in self.selected(as_of,include_review) if e['type']=='REQUIRES' and e['target']==mid]
  products=[{'id':e['source'],'name':self.nodes[e['source']]['name'],'dependency_edge_id':e['id'],'review_flag':e['review_flag']} for e in deps]
  producers=[{'country_id':e['source'],'country':self.nodes[e['source']]['name'],'observed_share_pct':e['share_pct'],'production_edge_id':e['id'],'source_ids':e['source_ids'],'spare_capacity':None,'scope':'仅为其他已记录生产国，未验证剩余产能或对接贸易通道。'} for e in self.production(mid) if e['source']!=cid]
  return {'scenario':{'country_id':cid,'country':self.nodes[cid]['name'],'mineral_id':mid,'mineral':self.nodes[mid]['name'],'max_hops':max_hops,'as_of':as_of,'include_review':include_review},'status':'potential_association_only','scope':'国家产量仅作为情景锚点；矿产到企业为矿种关联，未确认这些企业从该国采购。不同产矿国的同矿种企业列表可能相同。无库存/流量数据，不计算损失量或断供概率。','production':production,'observed_country_share_pct':production[0]['share_pct'],'companies':companies,'products':products,'levels':dict(Counter(x['level'] for x in companies)),'company_count':len(companies),'product_count':len(products),'alternatives':self.substitutes(mid,as_of,include_review),'alternatives_scope':'仅列本包中通过筛选的技术候选；空列表不表示现实中不存在替代路线。','other_recorded_producers':producers,'path_node_ids':sorted({cid,mid}|{i for x in linked for i in x['path_node_ids']}),'path_edge_ids':sorted({production[0]['id']}|{i for x in linked for i in x['path_edge_ids']}|{e['id'] for e in deps}),'source_ids':sorted({s for e in production+deps for s in e['source_ids']})}
 def provenance(self,record_id):
  rows=[e for e in self.edges if record_id in e['record_ids'] and e['type']!='CITES']
  return [{'edge':e,'subject':self.nodes[e['source']],'object':self.nodes[e['target']],'sources':[self.nodes[s] for s in e['source_ids']]} for e in rows]
 def centrality(self,as_of='2026-11-25'):
  # Directed, unweighted business graph; no source navigation or review edges.
  ids=sorted(n['id'] for n in self.nodes.values() if n['label']!='Source');adj={i:set() for i in ids};incoming={i:set() for i in ids}
  for e in self.selected(as_of):
   # Missing/zero production is not a confirmed topological production connection.
   if e['type']=='PRODUCES' and self.nodes[e['source']]['label']=='Country' and (number(e.get('quantity')) or 0)<=0:continue
   adj[e['source']].add(e['target']);incoming[e['target']].add(e['source'])
  n=len(ids);rank={i:1/n for i in ids}
  for _ in range(200):
   dangling=sum(rank[i] for i in ids if not adj[i]);updated={i:(1-.85)/n+.85*dangling/n+.85*sum(rank[j]/len(adj[j]) for j in incoming[i]) for i in ids}
   if sum(abs(updated[i]-rank[i]) for i in ids)<1e-12:rank=updated;break
   rank=updated
  cb=dict.fromkeys(ids,0.0)
  for start in ids:
   stack=[];pred={i:[] for i in ids};sigma=dict.fromkeys(ids,0.0);sigma[start]=1.;dist=dict.fromkeys(ids,-1);dist[start]=0;q=deque([start])
   while q:
    v=q.popleft();stack.append(v)
    for w in adj[v]:
     if dist[w]<0:q.append(w);dist[w]=dist[v]+1
     if dist[w]==dist[v]+1:sigma[w]+=sigma[v];pred[w].append(v)
   delta=dict.fromkeys(ids,0.)
   while stack:
    w=stack.pop()
    for v in pred[w]:delta[v]+=sigma[v]/sigma[w]*(1+delta[w])
    if w!=start:cb[w]+=delta[w]
  scale=1/((n-1)*(n-2)) if n>2 else 0
  return sorted([{'id':i,'name':self.nodes[i]['name'],'pagerank':rank[i],'betweenness':cb[i]*scale,'degree':len(adj[i])+len(incoming[i])} for i in ids],key=lambda r:(-r['betweenness'],-r['pagerank'],r['id']))
 def subgraph(self,ids):
  ids=set(ids);return {'nodes':[n for n in self.nodes.values() if n['id'] in ids],'edges':[e for e in self.edges if e['source'] in ids and e['target'] in ids]}

def validate(graph):
 errors=list(graph['build_errors']);g=Graph(graph);business=[e for e in g.edges if e['type']!='CITES']
 if len({e['id'] for e in g.edges})!=len(g.edges):errors.append('duplicate edge IDs')
 logical=Counter((e['source'],e['type'],e['target'],e.get('mineral_id'),e.get('valid_from'),e.get('valid_to')) for e in business)
 if any(c>1 for c in logical.values()):errors.append('duplicate logical edges')
 for n in g.nodes.values():
  if n.get('confidence') is not None and not 0<=n['confidence']<=1:errors.append('invalid node confidence '+n['id'])
  if n['label']=='PolicyEvent' and not 1990<=n['valid_year']<=2100:errors.append('invalid event year '+n['id'])
 for e in business:
  if e.get('confidence') is not None and not 0<=e['confidence']<=1:errors.append('invalid edge confidence '+e['id'])
  if e.get('valid_from') and e.get('valid_to') and e['valid_from']>e['valid_to']:errors.append('inverted interval '+e['id'])
  for k in ['share_pct','hold_ratio_pct']:
   if e.get(k) is not None and not 0<=e[k]<=100:errors.append('invalid percentage '+e['id'])
  if e.get('mineral_id') and (e['mineral_id'] not in g.nodes or g.nodes[e['mineral_id']]['label']!='Mineral'):errors.append('invalid mineral reference '+e['id'])
  if e['type']=='EXPORTS_TO' and not e.get('mineral_id'):errors.append('missing trade mineral '+e['id'])
 attached={e['source'] for e in business}|{e['target'] for e in business}
 return {'passed':not errors,'errors':errors,'overview':g.overview(),'orphan_business_nodes':[n['id'] for n in g.nodes.values() if n['label']!='Source' and n['id'] not in attached],'unused_sources':[n['id'] for n in g.nodes.values() if n['label']=='Source' and not g.inc[n['id']]],'logical_duplicate_count':sum(max(0,c-1) for c in logical.values()),'validation_scope':'结构、类型、范围、来源编号与程序规则校验；不代表逐条外部事实复核。'}
