"""Broad, labelled ABC presentation over the unchanged canonical graph."""
import copy
from collections import Counter
from kg import ROOT,Graph,active,csv_read
from d_adapter import KGService,INTENTS
from d_app.service import DService,AS_OF
from d_app.catalog import catalog_entities

UX_VERSION='ux-v5b'

class PresentationService(DService):
    VIEW_VERSION='abc-display-v3'
    retrieval_max_hops=3
    retrieval_max_facts=80

    def __init__(self,backend='snapshot'):
        self.connection_warning=''
        try:super().__init__(backend)
        except ValueError as exc:
            if '内容与交付快照不一致' not in str(exc):raise
            self.core=KGService(backend);self.backend=backend;self.graph=self.core.graph;self.nodes=self.graph.nodes
            self.edge_index={e['id']:e for e in self.graph.edges}
            self.connection_warning='数据库与交付快照内容不同：当前展示数据库实际内容，尚未重新验收。'
        self.display_edges=[]
        # Keep original associations as annotated display records, never write
        # them back as verified natural-graphite dependencies.
        for row in csv_read(ROOT/'originals/A_full_v3/04_dim_product.csv'):
            if row['product_id'] not in ['P_GRA_ANODE','P_SIC_ANODE']:continue
            if row['product_id'] not in self.nodes or 'M_GRA' not in self.nodes:continue
            self.display_edges.append({'id':'DISPLAY_'+row['product_id']+'_M_GRA','source':row['product_id'],'target':'M_GRA','type':'RELATED_MATERIAL','record_ids':[], 'source_ids':row['source_id'].split('|'),'review_flag':True,'display_only':True,'origin_file':'originals/A_full_v3/04_dim_product.csv','note':'A原始材料关联；天然/人造及配方范围待确认，不断言必然依赖天然石墨。'})

    def catalog(self,text='',label=None):return catalog_entities(self,text,label)

    def browse_edges(self,include_review=True,include_future=True):
        result=[]
        for edge in self.graph.edges+self.display_edges:
            if edge['type']=='CITES':continue
            if edge.get('review_flag') and not include_review:continue
            if not include_future and not active(edge,AS_OF,True):continue
            e=copy.deepcopy(edge)
            future=bool(e.get('valid_from') and e['valid_from']>AS_OF)
            ended=bool(e.get('valid_to') and e['valid_to']<AS_OF)
            e['display_status']='未来安排' if future else '已结束/历史记录' if ended else '原始关联·范围待确认' if e.get('display_only') else '条件性依赖' if e.get('dependency_kind')=='conditional' else '待核实线索' if e.get('review_flag') else '普通记录'
            if e.get('display_only'):e['display_relation_label']='原始材料关联'
            if e['id']=='R0214':e['display_relation_label']='配方调整线索'
            result.append(e)
        return result

    def view(self,node_ids=None,edge_ids=None,include_review=True,citations=False,include_future=True):
        ids=set(node_ids or []);allowed=set(edge_ids) if edge_ids is not None else None
        edges=[e for e in self.browse_edges(include_review,include_future) if (allowed is None or e['id'] in allowed) and (allowed is not None or not ids or {e['source'],e['target']}<=ids)]
        ids.update(i for e in edges for i in [e['source'],e['target']])
        if citations:
            cited=[copy.deepcopy(e) for e in self.graph.edges if e['type']=='CITES' and e['source'] in ids]
            edges+=cited;ids.update(e['target'] for e in cited)
        return {'nodes':[copy.deepcopy(self.nodes[i]) for i in sorted(ids) if i in self.nodes and (citations or self.nodes[i]['label']!='Source')],'edges':edges}

    def entity(self,value,hops=1,include_review=True,citations=False,relation_types=None,include_future=True):
        if isinstance(hops,bool) or not isinstance(hops,int) or not 1<=hops<=6:raise ValueError('浏览深度须为1—6跳')
        eid=self.graph.resolve(value);ids={eid};chosen={}
        edges=self.browse_edges(include_review,include_future)
        for _ in range(hops):
            layer=[e for e in edges if (relation_types is None or e['type'] in relation_types) and (e['source'] in ids or e['target'] in ids)]
            for e in layer:chosen[e['id']]=e;ids.update([e['source'],e['target']])
        return {'entity':self.nodes[eid],'graph':self.view(ids,chosen,include_review,citations,include_future),'facts':list(chosen.values()),'sources':self.sources(s for e in chosen.values() for s in e['source_ids']),'backend':self.backend,'mode':'保留原记录并分级展示'}

    def alternatives(self,mineral,include_review=True):
        mid=self.graph.resolve(mineral,'Mineral');edges=self.browse_edges(include_review,False)
        impacted={e['source'] for e in edges if e['type'] in ['REQUIRES','RELATED_MATERIAL'] and e['target']==mid}
        rows=[]
        for e in edges:
            if e['type']!='SUBSTITUTES' or e['target'] not in impacted:continue
            alt=self.nodes[e['source']]
            deps=[r for r in edges if r['source']==alt['id'] and r['type'] in ['REQUIRES','RELATED_MATERIAL'] and r['target']==mid]
            note=e.get('substitution_condition') or e.get('note') or '原记录未说明'
            kind='一般技术替代（仍涉及目标矿种）' if deps else '可能绕开目标矿种（按现有依赖记录）' if alt.get('dependency_scope_complete') else '一般技术替代（依赖信息待补充）'
            if deps and any(word in note for word in ['降低','减少','减量']):kind='原记录含减量说明（未量化验证）'
            if deps and any(r.get('display_only') or r.get('dependency_kind')=='conditional' for r in deps):kind='一般技术替代（目标依赖范围待确认）'
            if e['id']=='R0214':kind='配方调整线索（非直接化学品替换）'
            rows.append({'alternative_id':e['source'],'alternative':alt['name'],'replaces_id':e['target'],'replaces':self.name(e['target']),'edge_id':e['id'],'candidate_kind':kind,'condition':note,'source_ids':e['source_ids'],'review_flag':e.get('review_flag',False),'display_status':e['display_status'],'scope':'保留原技术替代记录；类别是说明，不证明工艺、性能或产能已经满足。'})
        return rows

    def simulate(self,country,mineral,max_hops=4,include_review=True):
        if isinstance(max_hops,bool) or not isinstance(max_hops,int) or not 1<=max_hops<=6:raise ValueError('遍历深度须为1—6跳')
        cid=self.graph.resolve(country,'Country');mid=self.graph.resolve(mineral,'Mineral')
        known=[e for e in self.graph.production(mid) if e['source']==cid]
        linked=self.graph.bfs(mid,max_hops,as_of=AS_OF,include_review=include_review)
        companies=[r for r in linked if r['label']=='Company']
        for row in companies:
            row['path_status']='含待核实关系' if any(self.edge_index[i].get('review_flag') for i in row['path_edge_ids']) else '普通关系'
        deps=[e for e in self.browse_edges(include_review,False) if e['type'] in ['REQUIRES','RELATED_MATERIAL'] and e['target']==mid]
        products=[{'id':e['source'],'name':self.name(e['source']),'dependency_edge_id':e['id'],'review_flag':e.get('review_flag',False),'display_status':e['display_status']} for e in deps]
        nids={mid}|{i for r in linked for i in r['path_node_ids']}|{r['id'] for r in products}
        eids={e['id'] for e in deps}|{i for r in linked for i in r['path_edge_ids']}
        if known:nids.add(cid);eids.add(known[0]['id'])
        paths=[{'node_ids':([cid] if known else [])+r['path_node_ids'],'edge_ids':([known[0]['id']] if known else [])+r['path_edge_ids']} for r in companies]
        alternatives=self.alternatives(mid,include_review)
        for row in alternatives:
            nids.update([row['alternative_id'],row['replaces_id']]);eids.add(row['edge_id'])
        graph=self.view(nids,eids,include_review,include_future=False)
        result={'scenario':{'country_id':cid,'country':self.name(cid),'mineral_id':mid,'mineral':self.name(mid),'max_hops':max_hops,'as_of':AS_OF,'include_review':include_review},'status':'potential_association_only' if known else 'mineral_network_only','production':known,'observed_country_share_pct':known[0]['share_pct'] if known else None,'companies':companies,'company_count':len(companies),'products':products,'product_count':len(products),'alternatives':alternatives,'alternatives_scope':'展示一般技术替代、可能减量和可能绕开目标矿种的候选；不以完整依赖信息作为展示门槛。','other_recorded_producers':[{'country_id':e['source'],'country':self.name(e['source']),'observed_share_pct':e['share_pct'],'source_ids':e['source_ids'],'spare_capacity':None} for e in self.graph.production(mid) if e['source']!=cid],'levels':dict(Counter(r['level'] for r in companies)),'graph':graph,'highlight_paths':paths,'path_node_ids':sorted(nids),'path_edge_ids':sorted(eids),'sources':self.sources(s for e in graph['edges'] for s in e['source_ids']),'backend':self.backend,'scope':'国家为假设情景；企业为矿种关联，产品依赖独立列示；虚线和状态保留原始条件及待核实信息。'}
        if not known:result['reason']='未收录该国该矿种的正产量依据；继续展示矿种网络，不将该国接成已证实生产路径，也不计算该国份额。'
        return result

    def query(self,intent,parameters=None):
        p=dict(parameters or {})
        if intent not in ['substitution','potential_impact']:
            result=super().query(intent,p)
            if intent=='overview':result['answer']=result['answer'].replace('默认分析使用','原统计口径使用')+' 图谱浏览同时保留待核实、有条件及未来记录。'
            return result
        include=p.get('include_review',True)
        if intent=='potential_impact':
            scenario=self.simulate(p['country'],p['mineral'],p.get('max_hops',4),include)
            rows=scenario['companies'];graph=scenario['graph'];paths=scenario['highlight_paths'];sources=scenario['sources']
            answer=f"矿种网络关联{len(rows)}家企业、{len(scenario['products'])}种产品，展示{len(scenario['alternatives'])}条技术替代候选。"+scenario.get('reason','')
        else:
            rows=self.alternatives(p['mineral'],include);mid=self.graph.resolve(p['mineral'],'Mineral')
            ids={mid}|{r[k] for r in rows for k in ['alternative_id','replaces_id']}
            graph=self.view(ids,include_review=include,include_future=False);paths=[]
            sources=self.sources(s for r in rows for s in r['source_ids'])
            answer=f'展示{len(rows)}条技术替代候选，按是否仍涉及目标矿种、是否有减量说明及信息完整情况标注，不作一律剔除。'
        result={'intent':intent,'template':INTENTS[intent]['template'],'parameters':p,'backend':self.backend,'dataset':self.overview()['dataset'],'as_of':AS_OF,'status':'ok','answer':answer,'rows':rows,'graph':graph,'highlight_paths':paths,'sources':sources,'limitations':'展示关联与条件，不表示实际采购、剩余产能或技术适配已获验证。','execution':{'graph_read':self.backend,'algorithm':'展示层宽口径检索','cypher_executed':False,'note':'现有图谱内筛选，不冒充原C严格模板的当次执行。'}}
        if intent=='potential_impact':result['scenario_result']=scenario
        return result
