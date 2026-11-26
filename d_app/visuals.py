"""Embedded PyVis and pyecharts assets for offline classroom display."""
import html
import json
import re
import textwrap
from pathlib import Path
from kg import ROOT
from d_app.service import LABELS, RELATIONS
from d_app.public_view import business_text
from d_app.ux import hierarchy_levels
VISUAL_VERSION='ux-v5d'

COLORS={'Country':'#5486b8','Mineral':'#de9a26','Company':'#35a38f','Product':'#8b70bd','PolicyEvent':'#d66d72','Source':'#96a3b2'}
MAP_NAMES={'CHN':'China','AUS':'Australia','CHL':'Chile','COD':'Dem. Rep. Congo','IDN':'Indonesia','ARG':'Argentina','ZWE':'Zimbabwe','BRA':'Brazil','CAN':'Canada','USA':'United States','RUS':'Russia','PHL':'Philippines','ZAF':'South Africa','MDG':'Madagascar','MOZ':'Mozambique','MMR':'Myanmar','DEU':'Germany','JPN':'Japan','KOR':'South Korea','FIN':'Finland','CHE':'Switzerland','GAB':'Gabon','VNM':'Vietnam','MEX':'Mexico','PER':'Peru'}

def graph_html(graph, highlight_paths=None, selected_path=None, height=460, layout='free'):
    from pyvis.network import Network
    paths=highlight_paths or []
    if selected_path is not None and paths:paths=[paths[selected_path]]
    hot_edges={i for p in paths for i in p['edge_ids']}
    hot_nodes={i for p in paths for i in p['node_ids']}
    net=Network(height=f'{height}px',width='100%',directed=True,bgcolor='#f8fafc',font_color='#24384d',cdn_resources='in_line')
    levels=hierarchy_levels(graph,paths)
    for n in graph['nodes']:
        title=html.escape(n.get('name') or n['id'])+'<br>'+html.escape(LABELS.get(n['label'],n['label']))+' · '+html.escape(n['id'])
        options={'level':levels[n['id']],'margin':8} if layout=='hierarchical' else {}
        name=n.get('name') or n['id'];color=COLORS.get(n['label'],'#96a3b2')
        if layout=='hierarchical':color={'background':'#f8fbff','border':color,'highlight':{'background':'#eaf2fa','border':color}}
        net.add_node(n['id'],**options,label=textwrap.fill(name,width=12) if layout=='hierarchical' else name,title=title,color=color,shape='box' if layout=='hierarchical' else 'dot',size=23 if n['id'] in hot_nodes else 16,borderWidth=3 if n['id'] in hot_nodes else 1)
    for e in graph['edges']:
        tip=html.escape(RELATIONS.get(e['type'],e['type']))+'<br>记录：'+html.escape(' / '.join(e.get('record_ids',[])))+'<br>来源：'+html.escape(', '.join(e.get('source_ids',[])))
        if e.get('note'):tip+='<br>'+html.escape(business_text(str(e['note']))[:240])
        status=e.get('display_status','')
        if status:tip+='<br>状态：'+html.escape(status)
        if e.get('display_only'):tip+='<br>关联依据：产品材料登记，范围待确认'
        future=status=='未来安排'
        net.add_edge(e['source'],e['target'],id=e['id'],label=business_text(e.get('display_relation_label') or RELATIONS.get(e['type'],e['type'])),title=tip,color='#518cc4' if future else '#e08026' if e['id'] in hot_edges else ('#c5cdd6' if e['type']=='CITES' or e.get('review_flag') else '#8ca6bb'),width=4 if e['id'] in hot_edges else 1.2,dashes=bool(e.get('review_flag') or future),arrows='to')
    options={'interaction':{'hover':True,'navigationButtons':True,'keyboard':True},
      'physics':{'enabled':layout!='hierarchical','solver':'forceAtlas2Based','stabilization':{'iterations':120}},
      'edges':{'smooth':{'type':'cubicBezier' if layout=='hierarchical' else 'dynamic'},'font':{'size':11,'align':'middle'}},
      'nodes':{'font':{'size':14}}}
    if layout=='hierarchical':options['layout']={'hierarchical':{'enabled':True,'direction':'LR','sortMethod':'directed','levelSeparation':200,'nodeSpacing':45,'treeSpacing':70}}
    net.set_options(json.dumps(options))
    output=net.generate_html(notebook=False)
    # PyVis includes Bootstrap CDNs unrelated to its embedded graph resources.
    output=re.sub(r'<link[^>]+href="https://[^>]+>','',output)
    output=re.sub(r'<script[^>]+src="https://[^>]+>\s*</script>','',output)
    output=output.replace('</head>','<style>.vis-network div.vis-navigation div.vis-button{filter:grayscale(1) sepia(.8) saturate(4) hue-rotate(165deg);background-color:#eef4fa;border-radius:50%}</style></head>')
    if layout!='hierarchical':output=output.replace('</body>',"<script>network.once('stabilizationIterationsDone',function(){network.setOptions({physics:false});network.fit({animation:false});});</script></body>")
    return output

def map_html(rows, mineral_name):
    from pyecharts import options as opts
    from pyecharts.charts import Map
    values=[(MAP_NAMES[r['iso_alpha3']],r['share_pct']) for r in rows if r['map_eligible'] and r['share_pct'] is not None and r['iso_alpha3'] in MAP_NAMES]
    chart=Map(init_opts=opts.InitOpts(width='100%',height='395px',bg_color='#f8fafc'))
    chart.add('已记录产量份额（%）',values,maptype='world',is_map_symbol_show=False)
    chart.set_series_opts(label_opts=opts.LabelOpts(is_show=False),itemstyle_opts=opts.ItemStyleOpts(area_color='#e5ebf1',border_color='#ffffff'))
    chart.set_global_opts(title_opts=opts.TitleOpts(title=f'{mineral_name} · 已记录产量分布',subtitle='灰色：未收录正产量，不能视为零产量'),visualmap_opts=opts.VisualMapOpts(min_=0,max_=100,range_color=['#d9e8f4','#5b94c4','#144e7d']),legend_opts=opts.LegendOpts(is_show=False),tooltip_opts=opts.TooltipOpts(formatter='{b}<br>已记录产量份额：{c}%'))
    # pyecharts output has its ordinary js dependencies. Replace each with the
    # same bundled file, so map rendering does not depend on CDN availability.
    output=chart.render_embed()
    assets=ROOT/'d_app/assets'
    def inline(match):
        src=match.group(1);path=assets/('world.js' if '/world.js' in src else 'echarts.min.js')
        if not path.exists():raise FileNotFoundError('缺少地图资源 '+path.name)
        return '<script>'+path.read_text(encoding='utf-8')+'</script>'
    return re.sub(r'<script[^>]+src="([^"]+)"[^>]*>\s*</script>',inline,output)
