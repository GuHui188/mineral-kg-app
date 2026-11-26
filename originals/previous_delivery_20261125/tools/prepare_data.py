from pathlib import Path
import csv, json, hashlib, shutil, collections

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT
SOURCES = {tag:ROOT/'originals'/tag for tag in ['A_full_v3','A_supp','B_to_A','B_to_D','B_to_C','C_original']}
ZIP_NAMES = {'A_full_v3':'关键矿产供应链数据包--李天语_v3.zip','A_supp':'A_补充材料.zip',
 'B_to_A':'给A_替代核对.zip','B_to_D':'给D_B补充材料.zip','B_to_C':'给C_v6.1交付.zip','C_original':'C_part.zip'}
LOG = []
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write(p,rows,fields=None):
 p.parent.mkdir(parents=True,exist_ok=True)
 fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def js(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def log(owner,file,rid,field,before,after,reason,category='必须修改'):
 LOG.append(dict(owner=owner,category=category,source_zip=ZIP_NAMES.get('A_full_v3' if owner=='A' else 'B_to_C' if owner=='B' else 'C_original'),file=file,record_id=rid,field=field,before=str(before),after=str(after),reason=reason))
def change(row,key,val,file,rid,why):
 old=row.get(key,'');val=str(val)
 if old!=val: row[key]=val;log('A','A/'+file,rid,key,old,val,why)

def main():
 ROOT.mkdir(exist_ok=True)
 manifest=json.loads((ROOT/'reports'/'original_manifest.json').read_text(encoding='utf-8'))
 for item in manifest:
  assert hashlib.sha256((ROOT/item['archive_file']).read_bytes()).hexdigest()==item['sha256']
 for name,tag in [('A','A_full_v3'),('B','B_to_C')]:
  d=ROOT/name
  if not d.exists():shutil.copytree(SOURCES[tag],d)
 b=ROOT/'B'
 for p in SOURCES['B_to_D'].rglob('*'):
  if p.is_file():
   q=b/p.relative_to(SOURCES['B_to_D']);q.parent.mkdir(parents=True,exist_ok=True)
   if not q.exists():shutil.copy2(p,q)
 a=ROOT/'A'
 # All decisions start from immutable v3 on each rebuild.
 for p in SOURCES['A_full_v3'].glob('*.csv'):shutil.copy2(p,a/p.name)
 pf='05_dim_policy_event.csv';rows=read(a/pf)
 for r in rows:
  assert float(r['confidence'])>1900 and 0<=float(r['valid_year'])<=1
  oldc,oldy=r['confidence'],r['valid_year']
  change(r,'confidence',oldy,pf,r['event_id'],'15行均为年份与置信度错列，按字段类型恢复')
  change(r,'valid_year',oldc,pf,r['event_id'],'同步恢复统计年份；非新增政策时点')
 write(a/pf,rows)
 pf='04_dim_product.csv';products=read(a/pf);pm={r['product_id']:r for r in products}
 change(pm['P_NISO4'],'key_minerals','镍',pf,'P_NISO4','NiSO4不含钴；原字段与化学式及contains_cobalt矛盾')
 # Synthetic graphite does not require mined natural graphite; silicon-carbon depends on formulation.
 for pid in ['P_GRA_ANODE','P_SIC_ANODE']:
  change(pm[pid],'key_minerals','NA',pf,pid,'M_GRA在矿产表限定为天然石墨，不能把人造石墨或全部硅碳配方确定映射为天然矿依赖')
  change(pm[pid],'dependency_scope_complete','False',pf,pid,'依赖关系不完整，缺边不用于证明可完全绕开矿种')
  change(pm[pid],'note',pm[pid]['note']+'；本次整合：天然/人造石墨口径拆分，未确认天然石墨必要用量，不生成确定REQUIRES；参见S36。',pf,pid,'区分材料名称相近与上游矿种依赖')
  change(pm[pid],'source_id',pm[pid]['source_id']+'|S36',pf,pid,'补充已阅读的DOE官方工艺范围说明')
 change(pm['P_EV'],'key_minerals','锂|铜',pf,'P_EV','本包限定锂离子动力路线共同依赖；镍钴及天然石墨均依车型/配方条件出现')
 change(pm['P_EV'],'conditional_minerals','镍|钴|石墨',pf,'P_EV','显式保存原可选依赖，防止一删了之')
 change(pm['P_EV'],'contains_cobalt','CONDITIONAL',pf,'P_EV','泛化整车不能一律断言不含钴')
 change(pm['P_EV'],'dependency_scope_complete','False',pf,'P_EV','混合车型范围不支持完全避矿判断')
 change(pm['P_EV'],'note',pm['P_EV']['note']+'；本包锂离子路线：锂/铜为共同项；镍、钴、天然石墨依电池与负极配方而定；不能解读为全部新能源车型。',pf,'P_EV','明确产品集合及条件依赖')
 for r in products:
  r.setdefault('conditional_minerals','NA');r.setdefault('dependency_scope_complete','True')
 write(a/pf,products)
 pf='07_来源登记表_source_registry.csv';sources=read(a/pf)
 sources.append(dict(zip(sources[0],['S36','官方报告','Grid Energy Storage Supply Chain Deep Dive Assessment (2022)','U.S. Department of Energy','2022-02-24','https://www.energy.gov/sites/default/files/2022-02/Energy%20Storage%20Supply%20Chain%20Report%20-%20final.pdf','直达链接','2026-11-25','A','04产品天然/人造石墨范围核对','自然石墨与以石油/煤焦为原料的人造石墨是不同原料路线；不提供具体企业合同或配方证据。'])))
 write(a/pf,sources);log('A','A/'+pf,'S36','新增来源','无','DOE 2022官方报告','为天然/人造石墨范围修订登记依据')
 pf='06_fact_relation.csv';facts=read(a/pf)
 subs={
 'R0209':('P_NCM_CELL','P_LFP_CELL','三元电芯可在追求能量密度的车型设计中替代LFP电芯；须重新适配，不属于绕开镍钴的方案。'),
 'R0210':('P_LFP_CELL','P_NCM_CELL','LFP电芯可在接受相应性能取舍、重新适配的场景替代三元电芯；在本包矿种范围可绕开镍钴。'),
 'R0211':('P_LFP_CATH','P_NCM','磷酸铁锂正极路线可在重新设计配方与工艺的条件下替代三元正极路线，属于无镍钴技术路线。'),
 'R0212':('P_SIC_ANODE','P_GRA_ANODE','硅碳负极在配方与电芯工艺适配后可作为负极技术替代候选；不能据此认定完全绕开天然石墨。'),
 'R0213':('P_NA_CELL','P_LFP_CELL','钠离子电芯仅在储能、低续航车辆等可接受性能取舍的场景作为LFP替代候选，仍待核实具体应用条件。'),
 'R0214':('P_NISO4','P_COSO4','原备注实际指高镍低钴配方调整；硫酸镍与硫酸钴不是可直接互换的化学品，本边仅存作待核参考，排除正式替代推荐。')}
 for r in facts:
  rid=r['triple_id'];review=float(r['confidence'])<.8
  if r['predicate']=='出产' and r['quantity']=='0' and '未列' in r['note']:
   for f,v in [('quantity','NA'),('share_pct','NA'),('value_status','来源未列'),('evidence_type','来源覆盖说明')]:change(r,f,v,pf,rid,'原备注仅说明来源未列，不能据此断定零产量')
   change(r,'note','原始备注：'+r['note']+'；本次修正：未列不等于零，不用于产量、替代供给或HHI统计。',pf,rid,'保留原判断文字并注明本轮处置');review=True
  if rid in ['R0006','R0167','R0174','R0192','R0214']:review=True
  if rid=='R0173':change(r,'evidence_type','企业披露',pf,rid,'与A2和A1处置表已提供的企业IR依据一致；保留0.80及集团层简化说明')
  if rid in subs:
   sid,oid,note=subs[rid]
   for f,v in [('subject_id',sid),('subject_name',pm[sid]['name_zh']),('object_id',oid),('object_name',pm[oid]['name_zh']),('note',note),('substitution_condition',note)]:change(r,f,v,pf,rid,'统一替代方→被替代方，并明确技术路线适配限制')
  change(r,'review_flag',str(review),pf,rid,'按A低于0.80复核规则、补充处置表及明确未核项统一处理')
  change(r,'original_data_year',r['data_year'],pf,rid,'保留源表历史年份，避免采集年份覆盖统计或关系时间')
  years=[s['accessed_date'][:4] for s in sources if s['source_id'] in r['source_id'].split('|') and s['accessed_date'][:4].isdigit()]
  change(r,'collection_year',max(years) if years else 'NA',pf,rid,'单独记录来源登记的访问年份，不冒充关系生效年份')
  change(r,'stat_year',r['data_year'] if r['predicate']=='出产' else 'NA',pf,rid,'只将出产记录作为现有统计年份，其余不臆造历史切片')
 write(a/pf,facts)
 pf='03_dim_mineral.csv';minerals=read(a/pf)
 for r in minerals:
  rr=[f for f in facts if f['predicate']=='出产' and f['object_id']==r['mineral_id'] and f['subject_id'].startswith('C_') and f['share_pct'] not in ['','NA'] and float(f['share_pct'])>0]
  for k,v in [('hhi_scope','已收录国家产量份额的平方和，非完整全球HHI'),('hhi_coverage_pct',round(sum(float(f['share_pct']) for f in rr),2)),('hhi_recomputed',round(sum(float(f['share_pct'])**2 for f in rr),2))]:change(r,k,v,pf,r['mineral_id'],'补充覆盖范围；原hhi保留用于追踪，正式查询读取重算字段')
 write(a/pf,minerals)
 pf='00_数据字典_data_dictionary.csv';dictionary=read(a/pf)
 for r in dictionary:
  if r['字段名']=='source_id':change(r,'取值范围','S01—S36，多值用竖线',pf,'source_id','来源从35补至36；历史来源不删除')
  if r['字段名']=='confidence':change(r,'定义与口径','人工可信度评分，非统计校准概率；A记录<0.80进入待核视图。B无评分时保留缺失，以人工判定及review_flag处理。',pf,'confidence','避免将人工分数表述为测得概率')
  if r['字段名']=='valid_year':change(r,'定义与口径','维表原有数据年份；05表本轮恢复年份/置信度错列；不能当政策有效区间。',pf,'valid_year','区分数据年份和valid_from/valid_to')
  if r['字段名']=='contains_cobalt':
   change(r,'取值范围','Y/N/CONDITIONAL',pf,'contains_cobalt','泛化整车按电池路线决定，替代搜索同时核查完整依赖而不只用本字段')
   change(r,'定义与口径','Y确定含钴，N本表产品路线不含钴，CONDITIONAL依车型/配方；单靠N或缺失依赖不能证明避矿。',pf,'contains_cobalt','避免泛化整车与确定配方混淆')
  if r['字段名']=='evidence_type':change(r,'取值范围','原表数值/公告原文/年报披露/企业披露/媒体报道/推算/来源覆盖说明',pf,'evidence_type','登记新增企业披露及未列来源的分类')
  if r['字段名']=='value_status':change(r,'取值范围','实测/估计/未公布/不适用/无规模产量/来源未列',pf,'value_status','显式区分来源覆盖与数值零')
 for field,definition in {
 'review_flag':'True待核；False按现有记录保留；不表示已重新回访全部来源。默认分析排除待核关系。',
 'collection_year':'来自来源登记表accessed_date的访问年份；不覆盖data_year。',
 'original_data_year':'原06表data_year原样保留，供审计。',
 'stat_year':'目前只对出产记录保留原data_year，不能构造多年份面板。',
 'conditional_minerals':'产品按配方可选依赖；不能用于确定需要，也不能忽略后宣称完全避矿。',
 'dependency_scope_complete':'仅在本项目七矿种范围的依赖完整性声明；False时不可用缺边作避矿证明。',
 'hhi_coverage_pct':'已收录正产量国家的share_pct之和，单位%。',
 'hhi_recomputed':'已收录正产量国家share_pct平方和，未归一化；不评全球集中等级。',
 'hhi_scope':'明确不完整国家覆盖范围。',
 'substitution_condition':'替代方→被替代方成立的技术/应用限制；不等于直接互换。'}.items():
  dictionary.append({'表名':'整合新增','字段名':field,'中文名':field,'数据类型':'boolean' if field in ['review_flag','dependency_scope_complete'] else 'string/number','单位':'—','取值范围':'见定义','必填':'否','示例':'见整合表','定义与口径':definition})
 write(a/pf,dictionary)
 # B original human judgements and v6.1 triples are intentionally preserved.
 js(ROOT/'reports'/'preparation_status.json',{'date':'2026-11-25','original_archived_files':len(manifest),'original_hashes_verified':True,'neo4j_actual_run':'pending','llm_rerun':False,'gold_list_available':False,'B_human_audit_count':65})
 write(ROOT/'reports'/'A_field_changes.csv',LOG)
 print(json.dumps({'root':str(ROOT),'archived':len(manifest),'A_field_changes':len(LOG),'A_facts':len(facts),'review_flags':collections.Counter(r['review_flag'] for r in facts)},ensure_ascii=False))

if __name__=='__main__':main()
