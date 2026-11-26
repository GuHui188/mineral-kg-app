"""Critical mineral knowledge graph application."""
from __future__ import annotations
import copy,importlib,os
import streamlit as st
import streamlit.components.v1 as components
from d_app.service import AS_OF,LABELS,RELATIONS,load_config,preferred_backend
from d_app.public_view import public_value,business_text
import d_app.ux as ux_module
if not hasattr(ux_module,'RELATION_SCOPE_LABEL'):ux_module=importlib.reload(ux_module)
from d_app.ux import RELATION_SCOPE_LABEL,RELATION_SCOPE_HELP
from d_adapter import INTENTS
import d_app.visuals as visual_module
if getattr(visual_module,'VISUAL_VERSION',None)!='ux-v5d':visual_module=importlib.reload(visual_module)
import d_app.ui as ui_module
if getattr(ui_module,'UI_VERSION',None)!='ux-v5c':ui_module=importlib.reload(ui_module)
Views=ui_module.Views

load_config()
st.set_page_config(page_title='矿链图谱 · 关键矿产供应链分析',page_icon='◈',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.stApp {background:#f5f7fb;color:#203750}.block-container {padding-top:1.6rem;max-width:1500px}
[data-testid="stSidebar"] {background:#eaf0f7} h1,h2,h3 {color:#173f65}
h1 {font-size:1.85rem!important;line-height:1.3!important;padding-bottom:.3rem!important}
h2 {font-size:1.4rem!important} h3 {font-size:1.15rem!important}
[data-testid="stMetric"] {background:white;padding:12px;border:1px solid #dce5ef;border-radius:10px}
[data-testid="stMetricValue"] {font-size:1.7rem}[data-testid="stCaptionContainer"] {color:#536b80}
.intro {font-size:14px;color:#617589;margin-bottom:8px}
@media(max-width:1100px) {h1{font-size:1.55rem!important}[data-testid="stMetric"]{padding:9px}}
</style>''',unsafe_allow_html=True)

try:  # 云端：把 Streamlit Secrets 注入环境变量，供 rag/服务层复用本地 os.getenv 读取逻辑
    for _secret_key,_secret_value in st.secrets.items():
        if isinstance(_secret_value,str) and not os.environ.get(_secret_key):os.environ[_secret_key]=_secret_value
except Exception:pass

_ACCESS_CODE=os.environ.get('KG_ACCESS_CODE','').strip()
if not _ACCESS_CODE:
    try:_ACCESS_CODE=str(st.secrets.get('KG_ACCESS_CODE','')).strip()
    except Exception:_ACCESS_CODE=''
if _ACCESS_CODE and not st.session_state.get('_kg_unlocked'):
    st.markdown('## ◈ 矿链图谱 · 访问验证')
    st.markdown('<div class="intro">本页面已开启访问码保护。请输入组内或老师分享的访问码后进入系统。</div>',unsafe_allow_html=True)
    with st.form('kg_access_form'):
        _input_code=st.text_input('访问码',type='password',placeholder='请输入访问码')
        _submit=st.form_submit_button('进入系统',width='stretch')
    if _submit:
        if _input_code.strip()==_ACCESS_CODE:
            st.session_state['_kg_unlocked']=True
            st.rerun()
        else:
            st.error('访问码不正确，请核对后重试。')
    st.stop()

@st.cache_resource(show_spinner=False)
def get_service(backend,version='ux-v5b'):
    import d_app.presentation as presentation
    if getattr(presentation,'UX_VERSION',None)!='ux-v5b':presentation=importlib.reload(presentation)
    return presentation.PresentationService(backend)

groups={'矿产概览':'数据浏览','完整目录':'数据浏览','政策与贸易':'数据浏览','图谱检索':'分析应用','情景分析':'分析应用','智能问答':'分析应用','构建与审核':'方法与质量','查询与验收':'方法与质量'}
with st.sidebar:
    st.markdown('## ◈ 矿链图谱')
    page=st.radio('工作区',list(groups),format_func=lambda x:groups[x]+' · '+x,key='page')
    st.caption('分析时点：'+AS_OF)
    with st.expander('连接与设置'):
        backends=['snapshot','neo4j'];default=preferred_backend()
        backend=st.selectbox('数据来源',backends,index=backends.index(default) if default in backends else 0,format_func=lambda x:'本地数据快照' if x=='snapshot' else '本机 Neo4j',key='backend')
        if st.button('刷新数据连接',width='stretch'):get_service.clear();st.rerun()
        from d_app.rag import llm_ready
        st.caption('AI辅助回答：'+('已配置' if llm_ready() else '未配置'))

try:
    with st.spinner('读取图谱…'):api=copy.copy(get_service(backend,'ux-v5b'))
except Exception:
    st.error('数据连接未成功。请在“连接与设置”中检查数据库，或选择本地数据快照。');st.stop()
view=Views(api);table=view.table;sources=view.sources;graph_panel=view.graph_panel;downloadable=view.downloadable
titles={'矿产概览':'矿产资源概览','完整目录':'数据目录','政策与贸易':'政策事件与贸易流向','图谱检索':'图谱探索','情景分析':'供应中断分析','智能问答':'智能问答','构建与审核':'数据与审核','查询与验收':'查询分析与数据验证'}
st.title(titles[page])
st.markdown('<div class="intro">资源 — 加工 — 应用｜关键矿产供应链知识图谱</div>',unsafe_allow_html=True)
if getattr(api,'connection_warning',''):st.warning(api.connection_warning)

if page=='矿产概览':
    overview=api.overview();cols=st.columns(4)
    for c,name,value,help_text in zip(cols,['收录对象','业务关系','统计关系','资料来源'],
        [overview['business_nodes'],overview['business_edges_stored'],overview['business_edges_current_default'],overview['nodes_by_type']['Source']],
        ['国家、企业、矿产、产品和事件，不含资料来源节点。','正式存储的业务关系，不含来源导航边和材料展示关联。','基准日有效且未标待核实的默认统计关系；不表示逐条事实已重新核验。','登记的资料来源数量。']):c.metric(name,value,help=help_text)
    left,right=st.columns([2,1])
    mineral=left.selectbox('查看矿产',api.choices('Mineral'),format_func=api.name,key='overview_mineral')
    right.button('分析该矿产供应链',on_click=view.open_analysis,args=(mineral,),key='overview_to_analysis')
    node=api.nodes[mineral];rows=api.map_rows(mineral)
    st.caption('7个矿种 · 21个材料产品 · 48家企业 · 22个国家/地区 · 15个政策事件')
    left,right=st.columns([3,1])
    with left:components.html(visual_module.map_html(rows,api.name(mineral)),height=415,scrolling=False)
    with right:
        st.subheader(api.name(mineral));st.write(node.get('battery_role') or '')
        year=node.get('valid_year');year=str(int(year)) if isinstance(year,(float,int)) else str(year or '未登记')
        st.metric('全球产量（'+year+'）',f"{node['world_production_2025']:,.0f}" if node.get('world_production_2025') is not None else '未登记')
        st.caption(node.get('unit',''))
        st.metric('份额覆盖率',f"{sum(r['share_pct'] or 0 for r in rows):.2f}%",help='已收录国家产量份额之和；未收录数值不填零。')
    a,b,c=st.tabs(['产量与集中度','关键节点','数据范围'])
    with a:
        table(api.graph.concentration())
        st.caption('集中度为已收录产国份额的平方和；数值越大，登记产量越集中。结合份额覆盖率阅读。')
        with st.expander('产国明细与资料出处'):
            table([r for r in rows if r['share_pct'] is not None]);sources(api.sources(s for r in rows for s in r['source_ids']))
    with b:
        table(api.graph.centrality()[:10])
        st.caption('连接重要性反映网络位置；中介中心性反映路径桥梁作用；度为按方向计数的直接连接数。分值在当前业务子图内比较。')
    with c:
        st.write(f"图谱浏览包含{overview['review_edges']}条待核实关系和{overview['future_edges']}条未来安排，按状态标注。统计卡片与各分析结果在对应范围内计数。")
        st.caption('数据年份以记录为准。材料展示关联单独标注，不计入正式业务关系总数。')

elif page=='图谱检索':
    a,b=st.columns([2,1]);term=a.text_input('搜索名称、别名或编号','宁德时代',key='search_term')
    label=b.selectbox('实体类型',['全部']+list(LABELS),format_func=lambda x:LABELS.get(x,x))
    candidates=api.catalog(term,None if label=='全部' else label)
    st.caption(f'已找到{len(candidates)}个匹配对象。')
    if not candidates:st.info('没有匹配对象，请调整名称或类型。')
    else:
        selected=st.selectbox('选择对象',[n['id'] for n in candidates],format_func=lambda i:api.name(i)+' · '+LABELS[api.nodes[i]['label']],key='entity_id')
        with st.expander('检索范围'):
            hops=st.slider('关联深度（跳）',1,6,1,key='entity_hops_v3')
            a,b,c=st.columns(3)
            review=a.checkbox(RELATION_SCOPE_LABEL,help=RELATION_SCOPE_HELP,value=True,key='browse_review_v3')
            citations=b.checkbox('显示来源节点',key='browse_citations')
            future=c.checkbox('包含未来安排与历史关系',value=True,key='browse_future_v3')
            relation_types=[r for r in RELATIONS if r!='CITES']+['RELATED_MATERIAL']
            types=st.multiselect('关系类型',relation_types,default=relation_types,format_func=lambda x:'材料关联（范围待确认）' if x=='RELATED_MATERIAL' else RELATIONS.get(x,x),key='relation_filter')
        result=api.entity(selected,hops,review,citations,types,include_future=future)
        graph_panel(result['graph'],key='entity_graph')
        view.entity_actions(api.nodes[selected])
        with st.expander('对象属性与编号'):st.json(public_value(result['entity']))
        with st.expander('关系记录'):
            from d_app.workbench import fact_rows
            table(fact_rows(api,result['facts']))
        sources(result['sources']);downloadable(result,'entity_result')

elif page=='情景分析':
    with st.form('scenario_form'):
        a,b=st.columns(2);countries=api.choices('Country');minerals=api.choices('Mineral')
        country=a.selectbox('假设供应中断的国家/地区',countries,index=countries.index('C_COD'),format_func=api.name,key='scenario_country')
        mineral=b.selectbox('矿产',minerals,index=minerals.index('M_CO'),format_func=api.name,key='scenario_mineral')
        a,b=st.columns(2)
        hops=a.slider('矿产下游最大层数',1,6,4,key='scenario_hops_v3',help='从矿产节点开始计数，国家到矿产的关系不计入下游层数。')
        review=b.checkbox(RELATION_SCOPE_LABEL,help=RELATION_SCOPE_HELP,value=True,key='scenario_review_v3')
        run=st.form_submit_button('运行情景分析',type='primary')
    signature=('ux-v5b',backend,country,mineral,hops,review)
    if run or st.session_state.get('scenario_signature',(None,))[0]!='ux-v5b':
        st.session_state.scenario_result=api.simulate(country,mineral,hops,review);st.session_state.scenario_signature=signature
    result=st.session_state.scenario_result
    if st.session_state.scenario_signature!=signature:st.info('参数已变化，请运行分析以更新结果。')
    if result.get('reason'):st.warning(business_text(result['reason']))
    st.subheader(api.name(result['scenario']['country_id'])+' × '+api.name(result['scenario']['mineral_id']))
    share=result.get('observed_country_share_pct');cols=st.columns(4)
    for c,name,value,help_text in zip(cols,['产量份额','关联企业','产品与材料','技术替代候选'],
      [f'{share:.2f}%' if share is not None else '未收录',len(result['companies']),len(result['products']),len(result['alternatives'])],
      ['情景国产量占来源登记全球产量的份额。','沿矿产供应关系识别的企业，按ID去重。','矿产关联的产品与材料，独立于企业列表统计。','已有技术替代候选，按原有记录列出适用条件与候选类型。']):c.metric(name,value,help=help_text)
    st.caption(f"结果范围：矿产下游最多{result['scenario']['max_hops']}层 · "+('包含' if result['scenario']['include_review'] else '不含')+'待核实关系。企业采购来源以实际披露为准。')
    graph_panel(result['graph'],result['highlight_paths'],'scenario_graph')
    a,b,c,d=st.tabs(['企业与关联路径','产品与材料','技术替代候选','其他产国'])
    with a:
        from collections import Counter
        from d_app.workbench import stage_rows
        levels=Counter(r['level'] for r in result['companies'])
        table([{'矿产下游层级':'第'+str(level)+'层','企业数':count} for level,count in sorted(levels.items())])
        table(stage_rows(api,result))
        table([{'名称':r['name'],'矿产下游层级':'第'+str(r['level'])+'层','路径状态':r.get('path_status'),'关联路径':' → '.join(api.name(i) for i in ([result['scenario']['country_id']] if result['production'] else [])+r['path_node_ids'])} for r in result['companies']])
    with b:table(result['products'])
    with c:view.candidates(result['alternatives']);st.caption(result['alternatives_scope'])
    with d:table(result['other_recorded_producers']);st.caption('展示已登记产国及份额，可调用产能需另行确认。')
    sources(result.get('sources',[]));downloadable(result,'scenario_result')

elif page in ['完整目录','政策与贸易','构建与审核','查询与验收']:
    import d_app.workbench as workbench
    if getattr(workbench,'VIEW_VERSION',None)!='wording-v1':workbench=importlib.reload(workbench)
    render={'完整目录':workbench.catalog_page,'政策与贸易':workbench.policy_trade_page,'构建与审核':workbench.construction_page,'查询与验收':workbench.query_quality_page}[page]
    render(api,table,graph_panel,sources,downloadable)

elif page=='智能问答':
    natural,templates=st.tabs(['自然语言问答','业务模板'])
    with natural:
        examples=['钴的主要产国和产量','宁德时代上游供应与股权关联','有哪些锂替代路线']
        def example_question(q):st.session_state['question']=q
        cols=st.columns(3)
        for i,q in enumerate(examples):cols[i].button(q,on_click=example_question,args=(q,),key='qa_example_'+str(i))
        with st.expander('高级检索设置'):
            a,b=st.columns(2)
            api.retrieval_max_hops=a.slider('图谱检索深度',1,6,3,key='rag_hops_v3')
            api.retrieval_max_facts=b.selectbox('最多检索记录数',[30,60,80,120],index=2,key='rag_facts_v3')
        with st.form('qa_form'):
            question=st.text_input('输入问题',value='刚果（金）钴断供会影响哪些企业',key='question')
            use_llm=st.checkbox('复杂问题使用 AI 辅助回答',key='use_llm')
            ask=st.form_submit_button('查询',type='primary')
        st.caption('已识别的业务问题直接查询图谱；启用AI后，其他问题可基于检索记录组织回答。')
        if ask:
            try:
                with st.spinner('查询图谱…'):st.session_state.qa_result=api.answer(question,use_llm)
                st.session_state.qa_backend=backend
            except (ConnectionError,RuntimeError):st.error('查询暂时不可用，请检查数据连接后重试。')
            except ValueError:st.error('请输入有效问题。')
        if 'qa_result' in st.session_state:
            if st.session_state.get('qa_backend')==backend:view.result_panel(st.session_state.qa_result,'qa_result')
            else:st.info('数据源已切换，请重新查询。')
    with templates:
        intent=st.selectbox('查询任务',list(INTENTS),format_func=lambda x:INTENTS[x]['name'],key='template_intent')
        with st.form('template_form'):
            params={}
            if intent in ['potential_impact','policy']:params['country']=st.selectbox('国家/地区',api.choices('Country'),format_func=api.name,key='template_country')
            if intent in ['potential_impact','substitution','production']:params['mineral']=st.selectbox('矿产',api.choices('Mineral'),format_func=api.name,key='template_mineral')
            if intent=='upstream':params['company']=st.selectbox('企业',api.choices('Company'),format_func=api.name,key='template_company')
            if intent=='provenance':params['record_id']=st.text_input('事实记录号','R0191',key='template_record')
            if intent in ['potential_impact','upstream']:params['max_hops']=st.slider('关系检索层数',1,4,4,key='template_hops')
            submit=st.form_submit_button('运行查询')
        if submit:
            try:st.session_state.template_result=api.query(intent,params);st.session_state.template_backend=backend
            except (ValueError,KeyError):st.error('参数无法识别，请检查对象或记录号。')
            except (ConnectionError,RuntimeError):st.error('查询暂时不可用，请检查数据连接。')
        if 'template_result' in st.session_state and st.session_state.get('template_backend')==backend:view.result_panel(st.session_state.template_result,'template_result')
