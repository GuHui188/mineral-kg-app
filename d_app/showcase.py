from d_app.ux import RELATION_SCOPE_LABEL,RELATION_SCOPE_HELP
SCOPE_WORDING_VERSION='wording-v1'
"""Course application views: data, methods, and executable results."""
from collections import Counter
import csv,json
import streamlit as st
from kg import ROOT,SCHEMA
from d_app.service import LABELS,RELATIONS,AS_OF
from d_app.public_view import industry_rows,source_rows,basis_rows,scenario_cases,scenario_case_rows,audit_record_rows,public_value

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def download_records(rows,name,key):
    st.download_button('下载记录 JSON',json.dumps(public_value(rows),ensure_ascii=False,indent=2),file_name=name+'.json',mime='application/json',key=key)

def construction_page(api,table,graph_panel,sources,downloadable):
    data,extraction=st.tabs(['数据与来源','抽取与审核'])
    with data:
        st.subheader('数据范围与产业环节')
        counts=api.overview()['nodes_by_type']
        table([{'数据类别':LABELS[label],'数量':counts[label]} for label in ['Country','Company','Mineral','Product','PolicyEvent','Source']])
        stages=industry_rows(api);table(stages)
        st.bar_chart({r['产业环节']:r['企业数'] for r in stages})
        st.caption('企业按登记的产业环节分类；企业类型在完整目录中单独展示。')
        st.subheader('资料来源与支撑范围')
        table(source_rows(api))
        st.caption('资料等级沿用来源登记：A为官方统计或法规公告，B为企业披露，C为媒体或机构资料。等级用于说明来源性质。')
        nodes=api.catalog('','Source')
        sid=st.selectbox('查看来源关联的事实',[n['id'] for n in nodes],format_func=lambda i:i+' · '+api.name(i),key='a_source')
        from d_app.workbench import fact_rows
        table(fact_rows(api,[e for e in api.graph.edges if e['type']!='CITES' and sid in e['source_ids']]))
        sources([api.nodes[sid]])
        with st.expander('字段字典与取值说明'):
            dictionary=read_csv(next((ROOT/'A').glob('00*')));table(dictionary)
            download_records(dictionary,'data_dictionary','dictionary_download')
        samples=read_csv(next((ROOT/'originals/A_full_v3').glob('08*')))
        with st.expander(f'数据抽检样本目录 · {len(samples)}条'):
            sample_rows=[{k:r.get(k) for k in ['抽检序号','抽样方式','表名','记录ID','来源编号']} for r in samples]
            table(sample_rows)
            st.caption('按记录号和来源查看抽检覆盖范围；当前关系状态在图谱记录中显示。')
            download_records(sample_rows,'data_audit_samples','data_audit_samples_download')
        with st.expander('重点记录与资料依据'):
            records=audit_record_rows(api);table(records)
            st.caption('当前状态取自图谱标记；资料位置取自登记材料，未开展逐条在线更新。')
            download_records(records,'record_sources','record_sources_download')
        with st.expander('替代候选的资料依据'):
            records=basis_rows(api);table(records)
            st.caption('路线方向和适用条件对应图谱中的实际关系；关联资料供查看，不作为替代性能的计算参数。')
            download_records(records,'substitution_sources','substitution_sources_download')
        with st.expander('国家储量记录'):
            reserves=[]
            for n in api.catalog('','Country'):
                for field,mid in [('reserve_li_t','M_LI'),('reserve_reo_t','M_RE'),('reserve_ni_t','M_NI'),('reserve_co_t','M_CO')]:
                    if n.get(field) is not None:reserves.append({'国家':n['name'],'矿产':api.name(mid),'储量':n[field],'单位':'吨（各矿种金属量/REO口径）','待核实':field in (n.get('field_review_flags') or []),'来源ID':n.get('source_ids')})
            table(reserves);st.caption('只列出已登记数值，未收录数据不填零。')
    with extraction:
        st.subheader('政策文本、结构化抽取与人工审核')
        st.write('政策文本 → 结构化抽取记录 → 人工审核 → 实体名称匹配 → 关系入图 → 来源回查')
        st.caption('本页查看已保存的抽取输入、输出和人工审核记录。')
        records=read_csv(ROOT/'B/new_triples_v2.csv')
        metrics=json.loads((ROOT/'reports/B_metrics.json').read_text(encoding='utf8'))
        cols=st.columns(4)
        for c,t,v in zip(cols,['抽取审核记录','正确记录','部分正确 / 错误','抽取审核准确率'],[metrics['audited_count'],metrics['correct'],f"{metrics['partial']} / {metrics['wrong']}",f"{metrics['strict_accuracy']:.2%}"]):c.metric(t,v)
        st.caption(f"抽取审核准确率 = {metrics['correct']}条正确 ÷ {metrics['audited_count']}条审核记录；部分正确不计入正确数。")
        judgement=st.selectbox('人工审核结果',['全部','正确','部分正确','错误'],key='b_judgement')
        flag=st.selectbox('入图标记',['全部','是','否'],key='b_import_flag')
        shown=[r for r in records if (judgement=='全部' or r['人工判定']==judgement) and (flag=='全部' or r['import_flag']==flag)]
        table([{'记录号':r['triple_id'],'主体':r['subject_name'],'关系':r['predicate'],'客体':r['object_name'],
                '原文依据':r['evidence'],'人工判定':r['人工判定'],'入图标记':r['import_flag'],'待核实':r.get('review_flag'),'来源ID':r['source_id']} for r in shown])
        st.caption(f'当前 {len(shown)} / {len(records)} 条。入图标记为“是”的记录可独立入图或与相同关系合并；未独立入图不等于错误。')
        rid=st.selectbox('查看抽取记录及关联事实',[r['triple_id'] for r in records],key='b_record')
        row=next(r for r in records if r['triple_id']==rid)
        table([{'记录号':rid,'主体':row['subject_name'],'关系':row['predicate'],'客体':row['object_name'],'原文依据':row['evidence'],'人工判定':row['人工判定']}])
        prov=api.graph.provenance(rid)
        if not prov and row.get('support_of'):
            for record in row['support_of'].split('|'):prov.extend(api.graph.provenance(record))
        from d_app.workbench import fact_rows
        if prov:table(fact_rows(api,[r['edge'] for r in prov]))
        else:st.info('该记录未作为独立事实登记，可结合人工判定和原文查看。')
        sources(api.sources(row['source_id'].split('|')))
        sid=st.selectbox('抽取文本与模型输出',['S11','S12','S13','S20','S21','S23','S24'],key='b_source')
        text=next((ROOT/'originals/B_to_D/policy_texts').glob(sid+'*'))
        with st.expander('抽取输入文本'):st.text(text.read_text(encoding='utf-8-sig'))
        output=json.loads((ROOT/'originals/B_to_D/llm_outputs'/f'{sid}.json').read_text(encoding='utf-8-sig'))
        with st.expander('保存的结构化输出'):st.json(output)
        download_records(records,'extraction_audit','extraction_audit_download')
        st.subheader('实体名称与关系结构')
        aliases=read_csv(ROOT/'B/extend_alias.csv');table(aliases)
        totals=Counter(e['type'] for e in api.graph.edges)
        table([{'关系':RELATIONS.get(r,r),'允许起点':' / '.join(LABELS[x] for x in sorted(v[0])),
                '允许终点':' / '.join(LABELS[x] for x in sorted(v[1])),'存储数量':totals[r]} for r,v in SCHEMA.items()])
        st.graphviz_chart('digraph {rankdir=TB; node [shape=box]; "国家/地区" -> "矿产" [label="出产"]; "矿产" -> "企业" [label="供应"]; "企业" -> "企业" [label="供应 / 控股 / 参股"]; "产品" -> "矿产" [label="需要"]; "产品" -> "产品" [label="技术替代"]; "矿产" -> "政策/事件" [label="受管制"]; "政策/事件" -> "国家/地区" [label="发布方 / 对象"]; "企业" -> "来源" [label="引用"];}')
        st.caption('关系结构用于查询与连接，具体方向以图谱记录为准。')

QUERY_SCOPES={
 'Q01':'统计数据库中图谱实体及其关系，包含来源节点和来源导航关系。',
 'Q02':'筛选基准日有效、未标待核实且产量与份额为正的国家记录。',
 'Q03':'对已登记正产量国家的份额求和、平方求和；覆盖不足时结果为部分HHI。',
 'Q04':'读取所选矿种的有效、未标待核实出口记录；份额按出口方记录口径解释。',
 'Q05':'沿矿产向企业的供应方向查找1至4跳路径，使用有效、未标待核实关系。',
 'Q06':'按事件指向的国家查询政策，并读取发布方及登记生效日期。',
 'Q07':'从企业沿供应、控股与参股关系逆向检索1至4跳上游路径。',
 'Q08':'查询避开目标矿产的候选：替代方依赖范围已登记完整，且未登记目标矿产依赖；使用有效、未标待核实关系。',
 'Q09':'在有效、未标待核实的有向业务子图上计算入度加出度；排除来源导航关系和非正产量国家出产边。',
 'Q10':'读取事件日期、涉及矿种和登记年份，用于定位当前数据范围。',
 'Q11':'按事实记录号读取实际关系及其关联来源，支持查看登记链接。',
 'Q12':'按来源统计去重业务关系数；一条关系可关联多个来源。',
}

def query_quality_page(api,table,graph_panel,sources,downloadable):
    query,cases,quality,methods=st.tabs(['查询与图分析','三情景分析','数据检查','功能与方法'])
    with query:
        kind=st.selectbox('分析任务',['首位产国与份额提示','图结构指标完整列表','按统计/登记年份分布','来源支撑的事实数量','12条参数化查询'],key='c_query_kind')
        if kind=='首位产国与份额提示':
            data=[]
            for mid in api.choices('Mineral'):
                rows=api.graph.production(mid)
                if rows:
                    first=max(rows,key=lambda r:r['share_pct']);data.append({'矿产':api.name(mid),'首位已记录产国':api.name(first['source']),'份额（%）':first['share_pct'],'超过60%':first['share_pct']>60,'矿种关联企业数':sum(r['label']=='Company' for r in api.graph.bfs(mid,4)),'来源ID':first['source_ids']})
            table(data);st.caption('产国份额来自有效、未标待核实的正产量记录；关联企业沿供应关系检索4跳。60%为展示提示阈值。')
        elif kind=='图结构指标完整列表':
            metric=st.selectbox('排序依据',['pagerank','betweenness','degree'],key='centrality_sort')
            table(sorted(api.graph.centrality(),key=lambda r:r[metric],reverse=True))
            st.caption('在有效、未标待核实的有向无权业务子图上计算；不纳入来源导航关系。指标用于比较图结构中的连接位置。')
        elif kind=='按统计/登记年份分布':
            counts=Counter((str(e.get('stat_year') or e.get('data_year') or '未登记'),RELATIONS.get(e['type'],e['type'])) for e in api.graph.edges if e['type']!='CITES')
            table([{'记录年份':y,'关系':r,'记录数':n} for (y,r),n in sorted(counts.items())])
            st.caption('按现有业务记录年份计数，包含待核实记录；该分布用于查看数据覆盖年份。')
        elif kind=='来源支撑的事实数量':
            table(source_rows(api));st.caption('图谱关系引用数统计正式业务关系；补充资料说明另行列示。')
        else:
            from C.queries import QUERIES
            qid=st.selectbox('查询模板',list(QUERIES),format_func=lambda q:q+' · '+QUERIES[q][0],key='c_template')
            params={'dataset':api.overview()['dataset'],'as_of':AS_OF}
            if qid in ['Q02','Q04','Q05','Q08']:params['mineral_id']=st.selectbox('矿种参数',api.choices('Mineral'),format_func=api.name,key='c_mineral')
            if qid=='Q06':params['country_id']=st.selectbox('国家参数',api.choices('Country'),format_func=api.name,key='c_country')
            if qid=='Q07':params['entity_id']=st.selectbox('上游实体参数',api.choices('Company'),format_func=api.name,key='c_company')
            if qid=='Q10':params['event_id']=st.selectbox('事件参数',api.choices('PolicyEvent'),format_func=api.name,key='c_event')
            if qid=='Q11':params['record_id']=st.text_input('事实记录号','R0191',key='c_record')
            st.info(QUERY_SCOPES[qid])
            with st.expander('查看本项Cypher查询'):st.code(QUERIES[qid][1],language='cypher')
            if api.backend!='neo4j':st.info('选择本机Neo4j数据源后可执行本项查询。')
            if st.button('运行查询',disabled=api.backend!='neo4j',key='c_execute'):
                try:
                    from C.neo4j_client import Neo4j
                    result=Neo4j().run(QUERIES[qid][1],params);table(result);downloadable({'template':qid,'parameters':params,'rows':result,'backend':'neo4j'},'c_query_result')
                except Exception:st.error('查询未成功，请检查数据库连接或参数。')
    with cases:
        st.subheader('典型供应中断情景')
        left,right=st.columns(2)
        hops=left.slider('矿产下游最大层数',1,6,4,key='case_hops')
        include_review=right.checkbox(RELATION_SCOPE_LABEL,help=RELATION_SCOPE_HELP,value=True,key='case_review')
        results=scenario_cases(api,hops,include_review)
        table(scenario_case_rows(api,results))
        st.caption(f'从矿产出发，沿供应方向最多检索{hops}层；'+('包含待核实与有条件线索。' if include_review else '不纳入待核实关系。')+'企业按ID去重。产品按矿产关联单独统计，候选按已有替代关系列出。')
        chosen=st.selectbox('查看案例详情',list(range(len(results))),format_func=lambda i:api.name(results[i]['scenario']['country_id'])+' × '+api.name(results[i]['scenario']['mineral_id']),key='case_select')
        result=results[chosen]
        graph_panel(result['graph'],result['highlight_paths'],key='case_graph')
        from d_app.workbench import stage_rows
        table(stage_rows(api,result))
        with st.expander('产品与材料关联'):table(result['products'])
        with st.expander('技术替代候选'):
            from d_app.ui import Views
            Views(api).candidates(result['alternatives'])
        with st.expander('其他已记录产国'):table(result['other_recorded_producers'])
        sources(result.get('sources',[]));downloadable({'cases':results,'max_hops':hops,'include_review':include_review},'three_cases')
    with quality:
        st.subheader('图谱数据检查')
        edges=[e for e in api.graph.edges if e['type']!='CITES']
        ids={n['id'] for n in api.nodes.values()}
        invalid=[e for e in edges if e['source'] not in ids or e['target'] not in ids or e['type'] not in SCHEMA or api.nodes[e['source']]['label'] not in SCHEMA[e['type']][0] or api.nodes[e['target']]['label'] not in SCHEMA[e['type']][1]]
        linked={i for e in edges for i in [e['source'],e['target']]}
        orphan=[n for n in api.nodes.values() if n['label']!='Source' and n['id'] not in linked]
        table([{'检查项':'关系端点与类型','结果':'通过' if not invalid else '存在异常','涉及记录数':len(invalid)},
               {'检查项':'无业务关系的实体','结果':'可查看实体属性及来源','涉及记录数':len(orphan)}])
        st.caption('端点与类型按当前读取图谱检查；实体收录不要求必须具有业务关系。')
        from d_app.workbench import fact_rows
        with st.expander('待核实关系'):table(fact_rows(api,[e for e in edges if e.get('review_flag')]))
        with st.expander('未来生效关系'):table(fact_rows(api,[e for e in edges if e.get('valid_from') and e['valid_from']>AS_OF]))
        with st.expander(f'全部业务关系 · {len(edges)}条'):table(fact_rows(api,edges))
        downloadable({'structural_errors':invalid,'stored_business_relations':len(edges)},'data_checks')
    with methods:
        table([
          {'功能':'名称与别名检索','页面入口':'完整目录 / 图谱检索','实际方法':'匹配实体ID、中英文名称及登记别名，并按实体类型筛选。'},
          {'功能':'产业环节分析','页面入口':'完整目录 / 构建与审核 / 情景分析','实际方法':'按登记产业环节分组，企业类型作为独立属性。'},
          {'功能':'产量份额与集中度','页面入口':'矿产概览 / 查询与图分析','实际方法':'读取正产量记录；份额平方求和得到部分HHI，同时展示记录覆盖率。'},
          {'功能':'供应中断情景','页面入口':'情景分析 / 三情景分析','实际方法':'从矿产出发逐层查找下游企业并去重，可选择层数和待核实范围。'},
          {'功能':'技术替代候选','页面入口':'情景分析 / 智能问答','实际方法':'按替代关系实际方向列出候选及条件，并标注是否仍涉及目标矿产。'},
          {'功能':'避开目标矿产查询','页面入口':'参数化查询Q08','实际方法':QUERY_SCOPES['Q08']},
          {'功能':'图结构指标','页面入口':'矿产概览 / 图结构指标完整列表','实际方法':'在有向无权业务子图中计算PageRank、中介中心性和度，排除来源导航边。'},
          {'功能':'来源回查','页面入口':'构建与审核 / 图谱检索 / 智能问答','实际方法':'按记录号关联资料来源，展示机构、日期和链接。'},
          {'功能':'自然语言问答','页面入口':'智能问答','实际方法':'识别业务意图调用模板；启用模型时，按设置的图谱深度和记录上限检索后组织回答。'}])
