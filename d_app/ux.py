"""Display and export helpers; no graph data or selection rules are changed."""
import csv,io,json
from collections import Counter
from d_app.public_view import public_value,business_text

def catalog_rows(api,nodes,label,include_review=True,include_future=True):
    edges=api.browse_edges(include_review,include_future)
    stored_ids={e['id'] for e in api.graph.edges if e['type']!='CITES'}
    result=[]
    for n in nodes:
        row={'名称':n['name']}
        if label=='Company':row.update({'产业环节':n.get('stage'),'企业类型':n.get('company_type'),'所属国家':api.name(n['country_id']) if n.get('country_id') else '未登记','主要产品':n.get('main_products')})
        elif label=='Product':row.update({'类别':n.get('product_category'),'化学体系':n.get('chemistry'),'关键矿产':n.get('key_minerals') or '依赖范围待确认','条件性依赖':n.get('conditional_minerals') or '无登记'})
        elif label=='Country':row.update({'地区':n.get('region'),'产业链角色':n.get('role_in_chain')})
        elif label=='Mineral':row.update({'主要用途':n.get('battery_role'),'全球产量':n.get('world_production_2025'),'单位':n.get('unit'),'统计年份':n.get('valid_year')})
        elif label=='PolicyEvent':row.update({'事件类型':n.get('event_type'),'生效日期':n.get('effective_date'),'登记状态':n.get('status')})
        elif label=='Source':row.update({'机构':n.get('publisher'),'资料类型':n.get('source_type'),'资料等级':n.get('authority_level')})
        if label=='Source':row['图谱关系引用数']=sum(e['id'] in stored_ids and n['id'] in e.get('source_ids',[]) for e in edges)
        else:row['显示关系数']=sum(n['id'] in [e['source'],e['target']] for e in edges)
        result.append(row)
    return result

COLUMNS={'id':'对象编号','name':'名称','country_id':'国家编号','country':'国家/地区','mineral_id':'矿产编号','mineral':'矿产',
 'source':'起点','target':'终点','type':'关系','subject':'主体','object':'客体','predicate':'关系','quantity':'产量','unit':'单位',
 'share_pct':'产量份额（%）','observed_share_pct':'产量份额（%）','source_ids':'来源','record_ids':'记录号','edge_id':'关系编号',
 'alternative_id':'候选编号','replaces_id':'适用对象编号','alternative':'替代路线','replaces':'适用对象','candidate_kind':'候选类别',
 'condition':'适用条件','review_flag':'待核实','display_status':'记录状态','path_status':'路径状态','path':'关联路径',
 'level':'矿产下游层级','scope':'范围说明','note':'说明','stat_year':'统计年份','data_year':'登记年份','valid_year':'登记年份',
 'coverage_pct':'产量份额覆盖率（%）','partial_hhi':'产量集中度（已收录国家）','countries':'收录产国数',
 'pagerank':'连接重要性（PageRank）','betweenness':'路径桥梁作用（中介中心性）','degree':'直接连接数（度）',
 'event_id':'事件编号','effective_date':'登记生效日期','original_status':'登记状态','spare_capacity':'可调用剩余产能',
 'dependency_edge_id':'关联记录编号','dependency_scope_complete':'依赖范围登记完整','key_minerals':'关键矿产',
 'display_only':'材料范围说明','as_of':'分析时点','max_hops':'矿产下游最大层数','include_review':'包含待核实关系',
 'entity_id':'对象编号','alias':'别名','basis':'匹配依据','status':'状态','hold_ratio_pct':'持股比例（%）',
 'url':'资料链接','title':'资料标题','source_id':'来源编号','publisher':'发布机构'}

def cell(value):
    if value is None:return '未登记'
    if isinstance(value,bool):return '是' if value else '否'
    if isinstance(value,list):return '、'.join(str(cell(v)) for v in value) if value else '无'
    if isinstance(value,dict):return json.dumps(public_value(value),ensure_ascii=False)
    from d_app.service import RELATIONS
    return RELATIONS.get(value,business_text(value)) if isinstance(value,str) else value

def display_rows(rows):
    return [{COLUMNS.get(k,k):cell(v) for k,v in r.items()} for r in public_value(rows)]

def csv_bytes(rows):
    rows=display_rows(rows)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')

def export_tables(result):
    if isinstance(result,list):return {'结果':result}
    if not isinstance(result,dict):return {}
    tables={}
    if result.get('cases'):
        for i,r in enumerate(result['cases']):
            tables.setdefault('情景汇总',[]).append({'国家':r['scenario']['country'],'矿产':r['scenario']['mineral'],
              '关联企业数':len(r['companies']),'产品与材料数':len(r['products']),'技术替代候选数':len(r['alternatives'])})
        return tables
    for key,name in [('rows','查询结果'),('companies','关联企业'),('products','产品与材料'),('other_recorded_producers','其他产国'),('entities','目录'),('events','政策事件'),('edges','关系记录')]:
        if isinstance(result.get(key),list) and result[key]:tables[name]=result[key]
    if result.get('alternatives'):tables['技术替代候选']=result['alternatives']
    if not tables and result.get('graph'):tables['节点']=result['graph'].get('nodes',[])
    return tables

def hierarchy_levels(graph,paths=None):
    levels={}
    for path in paths or []:
        for level,eid in enumerate(path['node_ids']):levels[eid]=min(levels.get(eid,level),level)
    last=max(levels.values(),default=4)
    stages={'采矿':2,'冶炼':3,'材料':4,'正极材料':4,'电芯':5,'整车':6,'贸易':3,'回收':3}
    for n in graph['nodes']:
        if n['id'] not in levels:
            levels[n['id']]={'Country':0,'Mineral':1,'Product':last+1,'PolicyEvent':0,'Source':last+2}.get(n['label'],stages.get(n.get('stage'),3))
    return levels

RELATION_SCOPE_LABEL='包含数值缺失、附条件及待确认关系'
RELATION_SCOPE_HELP='包括来源未提供具体数值、仅适用于特定车型或配方，以及依据仍待确认的关系。勾选后，将上述关系一并纳入展示和关联分析，并保留各自的状态说明。'
