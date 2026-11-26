"""Application adapter; leaves ABC data and algorithms untouched."""
from __future__ import annotations
import copy
import json
import os
import re
import sys
from pathlib import Path
from kg import ROOT, DATASET, active
from d_adapter import KGService, INTENTS

AS_OF = '2026-11-25'
LABELS = {'Country':'国家/地区','Company':'企业','Mineral':'矿产','Product':'产品','PolicyEvent':'政策/事件','Source':'来源'}
RELATIONS = {'PRODUCES':'出产','EXPORTS_TO':'出口至','SUPPLIES':'供应','HOLDS':'控股','INVESTS_IN':'参股','REGULATED_BY':'受规制','SUBSTITUTES':'可替代','REQUIRES':'需要','ISSUED_BY':'发布方','TARGETS':'针对','RELATED_MATERIAL':'原始材料关联','CITES':'来源'}
EXAMPLES = ['图谱规模概览','钴产量分布','锂集中度 HHI','刚果金钴断供会影响哪些企业','有哪些钴替代路线','针对中国的政策有哪些','宁德时代上游供应与股权关联','R0191 的来源是什么']

def load_config():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env.local', override=False)

def preferred_backend():
    return os.getenv('KG_BACKEND', 'snapshot')

class DService:
    def __init__(self, backend='snapshot'):
        self.core = KGService(backend)
        self.backend = backend
        self.graph = self.core.graph
        self.nodes = self.graph.nodes
        self.edge_index = {e['id']:e for e in self.graph.edges}
        # A stored hash alone cannot establish parity: compare actual DB content too.
        if backend == 'neo4j':
            expected = json.loads((ROOT/'data/graph.json').read_text(encoding='utf-8'))
            def clean(v):
                if isinstance(v, dict):
                    return {k:clean(x) for k,x in v.items() if x is not None and k not in ('kg_id','kg_edge_id','support_evidence')}
                if isinstance(v,list): return [clean(x) for x in v]
                if isinstance(v,str) and v.startswith(('{','[')):
                    try:return clean(json.loads(v))
                    except ValueError:pass
                return v
            if {n['id']:clean(n) for n in expected['nodes']} != {i:clean(n) for i,n in self.nodes.items()}:
                raise ValueError('Neo4j 节点内容与交付快照不一致，请先运行 C 验收。')
            if {e['id']:clean(e) for e in expected['edges']} != {e['id']:clean(e) for e in self.graph.edges}:
                raise ValueError('Neo4j 关系内容与交付快照不一致，请先运行 C 验收。')

    def name(self, entity_id):
        return self.nodes.get(entity_id, {}).get('name', entity_id)

    def choices(self, label):
        return sorted([n['id'] for n in self.nodes.values() if n['label']==label], key=self.name)

    def catalog(self, text='', label=None):
        """Filter the complete entity collection before pagination/display."""
        if label and label not in LABELS:raise ValueError('未知实体类型')
        term=text.strip().casefold()
        matched={i for alias,ids in self.graph.aliases.items() if term in alias for i in ids}
        return [copy.deepcopy(self.nodes[i]) for i in sorted(matched) if not label or self.nodes[i]['label']==label]

    def overview(self):
        result=self.core.overview()
        result['backend']=self.backend
        return result

    def sources(self, ids):
        return [copy.deepcopy(self.nodes[i]) for i in sorted(set(ids)) if i in self.nodes and self.nodes[i]['label']=='Source']

    def view(self, node_ids=None, edge_ids=None, include_review=False, citations=False):
        """Return only edges explicitly allowed by the current view and date."""
        ids=set(node_ids or [])
        allowed=set(edge_ids) if edge_ids is not None else None
        edges=[]
        for edge in self.graph.edges:
            if edge['type']=='CITES':
                if not citations or edge['source'] not in ids:continue
            else:
                if not active(edge,AS_OF,include_review):continue
                if allowed is not None and edge['id'] not in allowed:continue
                if allowed is None and ids and not {edge['source'],edge['target']} <= ids:continue
            edges.append(copy.deepcopy(edge))
        ids.update(i for e in edges for i in (e['source'],e['target']))
        return {'nodes':[copy.deepcopy(self.nodes[i]) for i in sorted(ids) if i in self.nodes and (citations or self.nodes[i]['label']!='Source')], 'edges':edges}

    def entity(self, value, hops=1, include_review=False, citations=False, relation_types=None):
        if not 1<=hops<=3:raise ValueError('浏览深度须为 1—3 跳')
        eid=self.graph.resolve(value)
        ids={eid}; edges={}
        for _ in range(hops):
            new=[]
            for e in self.graph.selected(AS_OF,include_review):
                if relation_types is not None and e['type'] not in relation_types:continue
                if e['source'] in ids or e['target'] in ids:new.append(e)
            for e in new:edges[e['id']]=e;ids.update((e['source'],e['target']))
        return {'entity':self.nodes[eid], 'graph':self.view(ids,edges,include_review,citations), 'facts':list(edges.values()), 'sources':self.sources(s for e in edges.values() for s in e['source_ids']), 'backend':self.backend}

    def query(self, intent, parameters=None):
        p=dict(parameters or {})
        if p.get('as_of',AS_OF)!=AS_OF:raise ValueError('本交付以 2026-11-25 为分析基准，暂不支持历史重建')
        if 'max_hops' in p and not 1<=p['max_hops']<=4:raise ValueError('模板分析深度须为 1—4 跳')
        result=self.core.query(intent,p)
        # The underlying subgraph() returns induced edges, including review/future edges.
        # Filter at the presentation boundary to preserve the algorithm's selection scope.
        ids=[n['id'] for n in result['graph']['nodes']]
        result['graph']=self.view(ids,include_review=p.get('include_review',False))
        if intent=='potential_impact':result['scenario_result']=self.core.simulate(p['country'],p['mineral'],p.get('max_hops',4),include_review=p.get('include_review',False))
        result['status']='ok'
        result['execution']={'graph_read':self.backend,'algorithm':'C/Python 参数化模板','cypher_executed':False}
        if self.backend=='neo4j':
            # Execute the original allowlisted C template, never generated user Cypher.
            sys.path.insert(0,str(ROOT/'C'))
            from neo4j_client import Neo4j
            from queries import QUERIES, PARAMS
            args=dict(PARAMS)
            for key,label,dest in [('country','Country','country_id'),('mineral','Mineral','mineral_id'),('company','Company','entity_id')]:
                if p.get(key):args[dest]=self.graph.resolve(p[key],label)
            if p.get('record_id'):args['record_id']=p['record_id']
            raw=Neo4j().run(QUERIES[result['template']][1],args)
            result['execution'].update(cypher_executed=True, template=result['template'], cypher_rows=len(raw), note='Cypher 查询回执；最终展示采用 C 的一致性已验收 Python 算法，应用用户选择的遍历深度。')
        result['answer']=self.explain(result)
        return result

    def explain(self, result):
        intent=result['intent']; rows=result['rows']; names=lambda xs:'、'.join(xs)
        if intent=='overview':
            r=rows[0];return f"当前图谱收录 {r['business_nodes']} 个业务实体、{r['nodes_by_type']['Source']} 个来源和 {r['business_edges_stored']} 条业务关系；默认分析使用 {r['business_edges_current_default']} 条关系。"
        if intent=='production':
            if not rows:return '当前数据没有符合条件的正产量记录；缺少记录不能解释为没有生产。'
            return '已收录产量份额前列：'+names(f"{self.name(r['source'])}—{self.name(r['target'])} {r['share_pct']:.2f}%" for r in rows[:5])+'。份额及统计年份沿用原始来源。'
        if intent=='concentration':return '已计算 '+str(len(rows))+' 种矿产的收录覆盖率和份额平方和；该指标是部分 HHI，不能据此划分完整全球集中度等级。'
        if intent=='potential_impact':
            r=result['scenario_result']
            if r['status']=='insufficient_production_evidence':return r['reason']
            return f"{r['scenario']['country']}—{r['scenario']['mineral']}情景关联 {len(r['companies'])} 家企业，另列 {len(r['products'])} 种产品依赖及 {len(r['alternatives'])} 条有条件技术替代。企业名单来自矿种关联，不证明这些企业从该国采购；产品列表独立计算。"
        if intent=='substitution':return (f'找到 {len(rows)} 条通过依赖检查的有条件技术替代路线。' if rows else '当前没有通过筛选的技术替代记录；这不能证明现实中不存在替代。')+'技术适配、商业产能与切换成本需另行评估。'
        if intent=='policy':return f'找到 {len(rows)} 条以该国为原登记目标的政策/事件。列示原始生效日期和状态，未持续核查是否仍有效。'
        if intent=='upstream':return f'找到 {len(rows)} 个供应、控股或参股上游关联节点。关联方向和类型见路径；注册地或股东所在地不能解释为实际采购来源。'
        return f'找到 {len(rows)} 条匹配事实；请查看原记录号、关系属性和来源链接。' if rows else '未找到该记录号；请检查 R/E 编号或改用实体检索。'

    def answer(self, question, use_llm=False):
        if not question.strip():raise ValueError('请输入问题')
        base=self.core.answer(question.strip())
        if base.get('status')=='needs_parameters':
            zh={'country':'国家','mineral':'矿种','company':'企业','record_id':'记录号（如 R0191）'}
            base['answer']='请补充'+ '、'.join(zh[x] for x in base['missing_parameters'])+'，也可使用下方模板查询。'
            base['llm_called']=False;return base
        if 'intent' in base and base.get('status')!='context_only':
            result=self.query(base['intent'],base['parameters']);result['llm_called']=False;result['answer_mode']='规则模板';return result
        from d_app.rag import answer_open_question
        return answer_open_question(self,question,use_llm)

    def simulate(self, country, mineral, max_hops=4, include_review=False):
        result=self.core.simulate(country,mineral,max_hops,include_review=include_review)
        eids=result.get('path_edge_ids',[])
        result['graph']=self.view(result.get('path_node_ids',[]),eids,include_review)
        paths=[]
        for row in result['companies']:
            paths.append({'node_ids':[result['scenario']['country_id']]+row['path_node_ids'],'edge_ids':[result['production'][0]['id']]+row['path_edge_ids']})
        result['highlight_paths']=paths
        result['sources']=self.sources(s for e in result['graph']['edges'] for s in e['source_ids'])
        result['backend']=self.backend
        return result

    def map_rows(self, mineral):
        mid=self.graph.resolve(mineral,'Mineral'); production={e['source']:e for e in self.graph.production(mid)}
        countries=json.loads((ROOT/'D_handoff/map_country_data.json').read_text(encoding='utf-8'))
        return [{'country_id':c['id'],'country':c['name'],'iso_alpha3':c['iso_alpha3'], 'map_eligible':c['map_eligible'], 'share_pct':production.get(c['id'],{}).get('share_pct'), 'quantity':production.get(c['id'],{}).get('quantity'), 'stat_year':production.get(c['id'],{}).get('stat_year'), 'unit':production.get(c['id'],{}).get('unit'), 'source_ids':production.get(c['id'],{}).get('source_ids',[])} for c in countries]
