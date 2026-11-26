"""ABC contribution views, computed from delivered files without altering them."""
from collections import Counter
from pathlib import Path
import csv,json
import pandas as pd
import streamlit as st
from kg import ROOT,SCHEMA,active
from d_app.service import LABELS,RELATIONS,AS_OF
from d_app.public_view import business_text,public_value
VIEW_VERSION='wording-v1'

def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def download(path,label=None,key=None):
    path=Path(path)
    if path.exists():st.download_button(label or ('下载 '+path.name),path.read_bytes(),file_name=path.name,key=key or str(path.relative_to(ROOT)))

def document(path,label):
    path=Path(path)
    if not path.exists():return
    with st.expander(label):
        st.markdown(path.read_text(encoding='utf-8-sig'))
        download(path,key='doc_'+str(path.relative_to(ROOT)))

def fact_rows(api,edges):
    return [{'关系编号':e['id'],'主体':api.name(e['source']),'关系':RELATIONS.get(e['type'],e['type']),'客体':api.name(e['target']),'矿种':api.name(e.get('mineral_id')) if e.get('mineral_id') else '', '数量':e.get('quantity'),'份额（%）':e.get('share_pct'),'单位':e.get('unit'),'统计年份':e.get('stat_year') or e.get('data_year'),'记录号':e.get('record_ids'),'来源':e.get('source_ids'),'待核实':e.get('review_flag'),'说明':business_text(e.get('note')),'持股比例（%）':e.get('hold_ratio_pct'),'记录状态':e.get('display_status')} for e in edges]

def stage_rows(api,result):
    groups={}
    for row in result['companies']:
        n=api.nodes[row['id']];stage=n.get('stage') or n.get('company_type') or '未分类'
        groups.setdefault(stage,[]).append(n['name'])
    return [{'产业环节':stage,'关联企业数':len(names),'关联企业':'、'.join(names)} for stage,names in sorted(groups.items())]

def policy_trade_page(api,table,graph_panel,sources,downloadable):
    policy,trade=st.tabs(['政策与事件目录','贸易流向'])
    with policy:
        a,b,c=st.columns(3)
        term=a.text_input('政策/事件关键词',key='policy_text')
        issuer=b.selectbox('发布国/地区',['全部']+api.choices('Country'),format_func=lambda i:api.name(i),key='policy_issuer')
        mineral=c.selectbox('关联矿种',['全部']+api.choices('Mineral'),format_func=api.name,key='policy_mineral')
        all_edges=[e for e in api.graph.edges if e['type']!='CITES']
        events=[]
        for n in api.catalog(term,'PolicyEvent'):
            issuers={e['target'] for e in all_edges if e['source']==n['id'] and e['type']=='ISSUED_BY'}
            mids={e['source'] for e in all_edges if e['target']==n['id'] and e['type']=='REGULATED_BY'}
            if issuer!='全部' and issuer not in issuers:continue
            if mineral!='全部' and mineral not in mids and api.name(mineral) not in str(n.get('target_mineral','')):continue
            events.append(n)
        events.sort(key=lambda n:str(n.get('effective_date') or n.get('announce_date') or ''))
        st.caption(f'当前 {len(events)} / 15 条。按登记日期排序；政策和事件状态以资料登记为准。')
        table([{'id':n['id'],'name':n['name'],'事件类型':n.get('event_type'),'发布日期':n.get('announce_date'),'effective_date':n.get('effective_date'),'登记状态':n.get('status'),'涉及矿种':api.name(n.get('target_mineral')) if n.get('target_mineral') else '未登记','发布方':api.name(n.get('issuing_country')) if n.get('issuing_country') else '未登记','涉及国家':api.name(n.get('target_country')) if n.get('target_country') else '未登记'} for n in events])
        if events:
            eid=st.selectbox('查看事件关系',[n['id'] for n in events],format_func=api.name,key='policy_event')
            result=api.entity(eid,1,True)
            graph_panel(result['graph'],key='policy_graph');table(fact_rows(api,result['facts']));sources(api.sources(api.nodes[eid].get('source_ids',[])))
            with st.expander('事件属性'):st.json(public_value(api.nodes[eid]))
        downloadable({'events':events},'policies_export')
    with trade:
        mineral=st.selectbox('贸易矿种',['全部']+api.choices('Mineral'),format_func=api.name,key='trade_mineral')
        target=st.selectbox('进口方',['全部']+api.choices('Country'),format_func=api.name,key='trade_target')
        review=st.checkbox('保留待核实贸易记录',value=True,key='trade_review_v3')
        all_trades=[e for e in api.graph.edges if e['type']=='EXPORTS_TO']
        edges=[e for e in all_trades if active(e,AS_OF,review) and (mineral=='全部' or e.get('mineral_id')==mineral) and (target=='全部' or e['target']==target)]
        st.caption(f'存储 {len(all_trades)} 条；当前筛选 {len(edges)} 条。份额按记录中的出口方口径解释，不能自动视为进口方采购份额。')
        table(fact_rows(api,edges))
        if edges:
            graph_panel(api.view({i for e in edges for i in [e['source'],e['target']]},[e['id'] for e in edges],review),key='trade_graph')
            sources(api.sources(i for e in edges for i in e['source_ids']))
        downloadable({'edges':edges,'scope':'出口流向和原统计口径；不直接推断实际企业采购。'},'trade_export')

import importlib
import d_app.catalog_view as catalog_module
import d_app.showcase as showcase_module
if getattr(catalog_module,'SCOPE_WORDING_VERSION',None)!='wording-v1':catalog_module=importlib.reload(catalog_module)
if getattr(showcase_module,'SCOPE_WORDING_VERSION',None)!='wording-v1':showcase_module=importlib.reload(showcase_module)
catalog_page=catalog_module.catalog_page
construction_page=showcase_module.construction_page
query_quality_page=showcase_module.query_quality_page
