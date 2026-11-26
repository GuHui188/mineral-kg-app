"""Shared user-facing views for charts, records and exports."""
import html,json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from d_app.service import LABELS,RELATIONS
from d_app.public_view import public_value,business_text
from d_app.ux import display_rows,export_tables,csv_bytes
import d_app.visuals as visuals
COLORS=visuals.COLORS
UI_VERSION='ux-v5c'

class Views:
    def __init__(self,api):self.api=api

    def table(self,rows):
        if not rows:st.caption('当前条件下暂无记录。');return
        st.dataframe(pd.DataFrame(display_rows(rows)),hide_index=True,width='stretch',height=360 if len(rows)>12 else 'auto')

    def sources(self,items):
        if not items:return
        short='、'.join(s['id'] for s in items[:4])+('等' if len(items)>4 else '')
        with st.expander(f'资料出处 · {short}（{len(items)}项）'):
            for s in items:
                st.write(f"**{s['id']} · {s.get('title') or s.get('name')}**")
                st.caption(' · '.join(str(x) for x in [s.get('publisher'),s.get('publish_date')] if x))
                url=s.get('url') or ''
                if url.startswith(('https://','http://')):st.link_button('查看资料',url)
                if s.get('note'):st.caption(business_text(s['note']))

    def graph_panel(self,graph,paths=None,key='graph'):
        if not graph.get('nodes'):st.caption('当前范围内暂无关系图。');return
        paths=paths or [];selected=None
        if paths:left,right=st.columns([3,2])
        else:right=st
        if paths:selected=left.selectbox('查看关联路径',[None]+list(range(len(paths))),key=key+'_path',format_func=lambda i:'全部关联路径' if i is None else ' → '.join(self.api.name(n) for n in paths[i]['node_ids']))
        layout=right.selectbox('图谱布局',['供应链分层','自由布局'],index=0 if paths else 1,key=key+'_layout')
        labels=''.join('<span style="display:inline-block;margin-right:14px"><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:'+color+';margin-right:5px"></i>'+html.escape(LABELS[label])+'</span>' for label,color in COLORS.items() if any(n['label']==label for n in graph['nodes']))
        st.markdown('<div style="font-size:12px;margin:5px 0 8px">'+labels+'</div>',unsafe_allow_html=True)
        components.html(visuals.graph_html(graph,paths,selected,height=460,layout='hierarchical' if layout=='供应链分层' else 'free'),height=475,scrolling=False)
        st.caption(f"{len(graph['nodes'])}个节点 · {len(graph['edges'])}条关系｜橙色为所选路径；灰色虚线为待核实或有条件关联；蓝色虚线为未来安排。可拖动、缩放或悬停查看详情。")

    def candidates(self,rows):
        if not rows:st.caption('当前范围内暂无技术替代候选。');return
        # Keep this section's pre-UX columns and content, per the user's request.
        columns={'alternative':'替代候选','replaces':'被替代产品','candidate_kind':'候选类型','condition':'适用条件',
                 'source_ids':'来源 ID','review_flag':'待核实','display_status':'记录状态','scope':'范围说明'}
        rendered=[{columns.get(k,k):json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else public_value(v) for k,v in r.items()} for r in rows]
        st.dataframe(pd.DataFrame(rendered),hide_index=True,width='stretch')

    def downloadable(self,result,key):
        tables=export_tables(result)
        if tables:
            left,right=st.columns([2,3])
            selected=left.selectbox('导出表格',list(tables),key=key+'_export_table')
            right.download_button('下载 CSV（Excel可打开）',csv_bytes(tables[selected]),file_name=key+'_'+selected+'.csv',mime='text/csv',key=key+'_csv')
        with st.expander('完整结构化结果'):
            st.download_button('下载 JSON',json.dumps(public_value(result),ensure_ascii=False,indent=2),file_name=key+'.json',mime='application/json',key=key+'_download')

    def result_panel(self,result,key='answer'):
        st.info(business_text(result['answer']))
        st.caption('回答方式：'+('AI辅助整理' if result.get('llm_called') else '图谱查询'))
        if result.get('graph'):self.graph_panel(result['graph'],result.get('highlight_paths'),key)
        rows=result.get('rows',[])
        if result.get('intent')=='substitution':self.candidates(rows)
        elif result.get('intent')=='provenance':
            for row in rows:
                e=row['edge'];st.write(f"**{self.api.name(e['source'])} → {RELATIONS.get(e['type'],e['type'])} → {self.api.name(e['target'])}**")
                self.table([{k:e.get(k) for k in ['record_ids','source_ids','quantity','share_pct','hold_ratio_pct','note','review_flag']}])
        elif rows:self.table(rows)
        self.sources(result.get('sources',[]))
        with st.expander('查询范围与执行信息'):
            if result.get('limitations'):st.write(business_text(result['limitations']))
            if result.get('execution'):st.json(public_value(result['execution']))
        self.downloadable(result,key)

    def open_analysis(self,mineral,country=None):
        production=self.api.graph.production(mineral)
        if country is None and production:country=max(production,key=lambda r:r['share_pct'])['source']
        st.session_state['page']='情景分析';st.session_state['scenario_mineral']=mineral
        if country:st.session_state['scenario_country']=country

    def open_question(self,question):
        st.session_state['page']='智能问答';st.session_state['question']=question

    def entity_actions(self,node):
        if node['label']=='Mineral':st.button('分析该矿产供应链',on_click=self.open_analysis,args=(node['id'],),key='catalog_to_analysis')
        elif node['label']=='Company':st.button('查询该企业上游',on_click=self.open_question,args=(node['name']+'的上游供应与股权关联',),key='catalog_to_question')
