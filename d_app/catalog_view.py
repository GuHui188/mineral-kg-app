from d_app.ux import RELATION_SCOPE_LABEL,RELATION_SCOPE_HELP
SCOPE_WORDING_VERSION='wording-v1'
"""Typed catalog, with counts and details using the same display range."""
import hashlib,json
import pandas as pd
import streamlit as st
from d_app.service import LABELS
from d_app.public_view import public_value
from d_app.ux import catalog_rows,display_rows

def catalog_page(api,table,graph_panel,sources,downloadable):
    a,b=st.columns([1,2])
    label=a.selectbox('目录类型',list(LABELS),index=3,format_func=LABELS.get,key='catalog_label')
    keyword=b.text_input('搜索名称、别名或编号',key='catalog_keyword')
    nodes=api.catalog(keyword,label)
    if label=='Product':
        categories=sorted({n.get('product_category') or '未分类' for n in nodes})
        category=st.selectbox('材料/产品类别',['全部']+categories,key='catalog_category')
        if category!='全部':nodes=[n for n in nodes if (n.get('product_category') or '未分类')==category]
    if label=='Company':
        stages=sorted({n.get('stage') or n.get('company_type') or '未分类' for n in nodes})
        stage=st.selectbox('产业环节',['全部']+stages,key='catalog_stage')
        if stage!='全部':nodes=[n for n in nodes if (n.get('stage') or n.get('company_type') or '未分类')==stage]
    a,b=st.columns(2)
    review=a.checkbox(RELATION_SCOPE_LABEL,help=RELATION_SCOPE_HELP,value=True,key='catalog_review_v3')
    future=b.checkbox('包含未来安排与历史关系',value=True,key='catalog_future')
    scope=('包含' if review else '不含')+'待核实关系 · '+('包含' if future else '不含')+'未来与历史关系'
    st.caption(f'{len(nodes)}个条目｜{scope}。关系计数与下方详情使用相同范围。')
    rows=catalog_rows(api,nodes,label,review,future)
    if not nodes:st.info('没有匹配条目，请调整名称或筛选条件。');return
    signature=hashlib.sha256(('|'.join(n['id'] for n in nodes)+str(review)+str(future)).encode()).hexdigest()[:12]
    selection=st.dataframe(pd.DataFrame(display_rows(rows)),hide_index=True,width='stretch',height=min(360,80+len(rows)*35),
                           key='catalog_grid_'+signature,on_select='rerun',selection_mode='single-row')
    selected=list(selection.selection.rows)
    event=(signature,tuple(selected))
    if selected and st.session_state.get('catalog_row_event')!=event:
        st.session_state['catalog_entity']=nodes[selected[0]]['id']
    st.session_state['catalog_row_event']=event
    st.caption('选中一行查看详情，也可以使用下方名称选择框。')
    eid=st.selectbox('查看目录条目',[n['id'] for n in nodes],format_func=api.name,key='catalog_entity')
    st.subheader(api.name(eid))
    from d_app.ui import Views
    Views(api).entity_actions(api.nodes[eid])
    result=api.entity(eid,1,review,include_future=future)
    from d_app.workbench import fact_rows
    if label=='Source':
        stored={e['id'] for e in api.graph.edges if e['type']!='CITES'}
        facts=[e for e in api.browse_edges(review,future) if e['id'] in stored and eid in e['source_ids']]
        table(fact_rows(api,facts));sources([api.nodes[eid]])
        st.caption('图谱关系引用数只统计正式关系的来源登记；补充资料说明可在“构建与审核”查看。')
    else:
        if not result['facts']:st.info('已收录该对象，当前范围内暂无关系。可查看属性与资料出处。')
        else:graph_panel(result['graph'],key='catalog_graph')
        with st.expander('关系记录'):table(fact_rows(api,result['facts']))
        sources(result['sources'] or api.sources(api.nodes[eid].get('source_ids',[])))
    with st.expander('完整属性与编号'):st.json(public_value(api.nodes[eid]))
    downloadable({'rows':rows,'selected':result},'catalog_export')
