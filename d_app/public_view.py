"""Public wording for the application; stored records remain unchanged."""
from collections import Counter

STAGES=('采矿','冶炼','正极材料','材料','电芯','整车','贸易','回收')

def business_text(value):
    if not isinstance(value,str):return value
    if '本次修正：' in value:
        return value.split('本次修正：',1)[1]
    if value.startswith('v3 修正：'):
        return '包钢（集团）持有北方稀土38.03%股份；控制链在当前收录范围内止于包钢集团。'
    if 'v3 复核未取得原表逐行核对' in value:
        return '中国锰产量登记为空，原表是否单列仍待核实；缺失值不作为零产量，不填入估计数。'
    if value=='原始材料关联':return '材料关联（范围待确认）'
    if value=='现有图谱内筛选，不冒充原C严格模板的当次执行。':return '读取图谱后计算结果。'
    if value.startswith('A原始材料关联'):return '材料登记关联；天然、人造及配方范围待确认。'
    if '05表本轮恢复年份' in value:return '维表数据所属年份；政策有效区间以事件日期为准。'
    return value

def public_value(value):
    if isinstance(value,dict):return {k:public_value(v) for k,v in value.items() if k not in {'origin_file','dataset'}}
    if isinstance(value,list):return [public_value(v) for v in value]
    return business_text(value)

def industry_rows(api,companies=None):
    nodes=companies if companies is not None else api.catalog('','Company')
    groups={stage:[] for stage in STAGES}
    for node in nodes:groups.setdefault(node.get('stage') or node.get('company_type') or '未分类',[]).append(node['name'])
    return [{'产业环节':stage,'企业数':len(names),'企业':'、'.join(names)} for stage,names in groups.items() if names]

def source_rows(api):
    counts=Counter(sid for e in api.graph.edges if e['type']!='CITES' for sid in e.get('source_ids',[]))
    return [{'来源ID':n['id'],'资料标题':n.get('title') or n['name'],'发布机构':n.get('publisher'),
             '资料类型':n.get('source_type'),'资料等级':n.get('authority_level'),'发布日期':n.get('publish_date'),
             '链接类型':n.get('url_status'),'支撑范围':n.get('used_for'),'图谱关系引用数':counts[n['id']],
             '链接':n.get('url')} for n in api.catalog('','Source')]

def basis_rows(api):
    """Show the sources of relationships used by the app, using its actual direction."""
    import csv
    from kg import ROOT
    path=ROOT/'originals/A_supp/A3_替代关系与产品依赖依据.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:materials=list(csv.DictReader(f))
    records={i:e for e in api.browse_edges() for i in e.get('record_ids',[])}
    result=[]
    for material in materials:
        rid=material['关系ID'];edge=records.get(rid)
        if not edge:continue
        result.append({'记录号':rid,'候选路线':api.name(edge['source']),'关联产品':api.name(edge['target']),
          '关系说明':edge.get('display_relation_label') or '技术替代候选','适用条件':edge.get('substitution_condition') or edge.get('note'),
          '依据资料':material['依据标题/机构'],'资料等级':material['证据等级'],'来源ID':material['07 表编号'],'链接':material['链接']})
    return result

def scenario_cases(api,hops=4,include_review=True):
    return [api.simulate(country,mineral,hops,include_review) for country,mineral in
            [('C_COD','M_CO'),('C_CHN','M_GRA'),('C_AUS','M_LI')]]

def scenario_case_rows(api,cases):
    return [{'案例':api.name(r['scenario']['country_id'])+' × '+api.name(r['scenario']['mineral_id']),
             '登记产量份额（%）':r.get('observed_country_share_pct'),'关联企业数':len(r['companies']),
             '产品与材料关联数':len(r['products']),'技术替代候选数':len(r['alternatives'])} for r in cases]

def audit_record_rows(api):
    """Current graph and linked disclosure material, without revision narratives."""
    import csv
    from kg import ROOT
    with (ROOT/'originals/A_supp/A1_抽检处置表_audit_disposition.csv').open(encoding='utf-8-sig',newline='') as f:records=list(csv.DictReader(f))
    result=[]
    for row in records:
        facts=api.graph.provenance(row['记录ID'])
        if not facts:continue
        e=facts[0]['edge']
        result.append({'记录号':row['记录ID'],'主体':api.name(e['source']),'关系':e['type'],'客体':api.name(e['target']),
           '当前状态':'待核实' if e.get('review_flag') else '已登记','资料依据':row['依据文件或链接'],
           '材料位置':row['页码或段落'],'来源ID':e.get('source_ids',[])})
    return result
