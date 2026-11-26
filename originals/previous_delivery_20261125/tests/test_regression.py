import unittest,sys,importlib.util,tempfile,json,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,Graph,build_graph,active,csv_read,validate
from d_adapter import KGService
class Regression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.graph=Graph();cls.service=KGService()
 def test_structure_valid(self):self.assertTrue(validate(self.graph.data)['passed'])
 def test_original_archive_integrity(self):
  import hashlib
  manifest=json.loads((ROOT/'reports'/'original_manifest.json').read_text(encoding='utf-8'))
  for x in manifest:self.assertEqual(hashlib.sha256((ROOT/x['archive_file']).read_bytes()).hexdigest(),x['sha256'])
 def test_policy_fields(self):
  rows=[n for n in self.graph.nodes.values() if n['label']=='PolicyEvent'];self.assertEqual(len(rows),15)
  self.assertTrue(all(0<=r['confidence']<=1 and r['valid_year']==2025 for r in rows))
 def test_rebuild_deterministic(self):self.assertEqual(build_graph()['sha256'],self.graph.data['sha256'])
 def test_v3_control_preserved(self):
  e=self.graph.provenance('R0191')[0]['edge'];self.assertEqual((e['source'],e['target']),('CO_BAOGANG','CO_NRE'))
 def test_suspect_supplier_excluded(self):
  ids={i for x in self.graph.simulate('刚果金','钴')['companies'] for i in x['path_edge_ids']};self.assertNotIn('R0174',ids)
 def test_unlisted_not_zero(self):
  e=next(e for e in self.graph.edges if e['id']=='R0012');self.assertIsNone(e['quantity']);self.assertTrue(e['review_flag'])
  self.assertEqual(self.graph.simulate('澳大利亚','石墨')['status'],'insufficient_production_evidence')
 def test_alternative_source_positive(self):
  for m in ['钴','锂','石墨']:
   for e in self.graph.production(m):self.assertGreater(e['quantity'],0);self.assertGreater(e['share_pct'],0)
 def test_conditional_ev_not_universal_cobalt(self):
  r=self.graph.simulate('刚果金','钴');self.assertNotIn('P_EV',{p['id'] for p in r['products']})
  self.assertIn('P_EV',{p['id'] for p in self.graph.simulate('刚果金','钴',include_review=True)['products']})
 def test_synthetic_not_mined_graphite(self):
  ids={r['id'] for r in self.graph.simulate('中国','石墨')['products']};self.assertNotIn('P_GRA_ANODE',ids);self.assertNotIn('P_SIC_ANODE',ids)
 def test_substitution_direction_and_avoidance(self):
  r=self.graph.substitutes('钴');self.assertTrue(any(x['alternative_id']=='P_LFP_CELL' and x['replaces_id']=='P_NCM_CELL' for x in r))
  self.assertNotIn('R0214',{r['edge_id'] for r in r})
  for row in r:self.assertNotIn('M_CO',{e['target'] for e in self.graph.edges if e['type']=='REQUIRES' and e['source']==row['alternative_id']})
 def test_future_not_current(self):
  self.assertFalse(active({'valid_from':'2031-01-01','valid_to':'2060-12-31'},'2026-11-25'));self.assertTrue(active({'valid_from':'2031-01-01','valid_to':'2060-12-31'},'2031-01-01'))
  result=self.service.query('upstream',{'company':'Salar Futuro'});self.assertNotIn('E0060',{i for p in result['highlight_paths'] for i in p['edge_ids']})
 def test_bfs_filters_before_visit(self):
  nodes=[{'id':i,'name':i,'label':'Company','source_ids':[]} for i in ['a','b','c']]
  edges=[{'id':'bad','source':'a','target':'b','type':'SUPPLIES','review_flag':True},{'id':'valid1','source':'a','target':'c','type':'SUPPLIES'},{'id':'valid2','source':'c','target':'b','type':'SUPPLIES'}]
  g=Graph({'nodes':nodes,'edges':edges,'sha256':'test'});paths={x['id']:x for x in g.bfs('a')};self.assertEqual(paths['b']['path_edge_ids'],['valid1','valid2'])
 def test_hops_rejected(self):
  for h in [0,7,True,'4']:
   with self.assertRaises(ValueError):self.graph.simulate('中国','石墨',h)
 def test_no_source_edges_in_algorithm(self):
  r=self.graph.centrality();self.assertEqual(len(r),113);self.assertAlmostEqual(sum(x['pagerank'] for x in r),1.,places=9);self.assertFalse(any(x['id'].startswith('S') for x in r))
 def test_brandes_known_directed_path(self):
  nodes=[{'id':i,'name':i,'label':'Company','source_ids':[]} for i in ['a','b','c']];edges=[{'id':str(i),'source':u,'target':v,'type':'SUPPLIES'} for i,(u,v) in enumerate([('a','b'),('b','c')])]
  r=Graph({'nodes':nodes,'edges':edges,'sha256':'test'}).centrality();scores={x['id']:x for x in r};self.assertAlmostEqual(scores['b']['betweenness'],.5);self.assertEqual(scores['a']['betweenness'],0)
 def test_alias_and_d_api(self):
  self.assertEqual(self.graph.resolve('刚果金','Country'),'C_COD');r=self.service.answer('刚果金钴断供会影响哪些企业');self.assertEqual(r['intent'],'potential_impact');self.assertTrue(r['highlight_paths']);self.assertTrue(r['sources'])
 def test_unknown_question_no_llm_fabrication(self):self.assertFalse(self.service.answer('明年股票价格是多少')['context']['llm_called'])
 def test_fact_provenance(self):
  p=self.graph.provenance('R0173')[0];self.assertEqual(p['edge']['evidence_type'],'企业披露');self.assertIn('S32',{s['id'] for s in p['sources']})
 def test_b_human_audit_not_overwritten(self):
  import hashlib
  a=ROOT/'B'/'audit_sheet.xlsx';b=ROOT/'originals'/'B_to_D'/'audit_sheet.xlsx';self.assertEqual(hashlib.sha256(a.read_bytes()).digest(),hashlib.sha256(b.read_bytes()).digest())
 def test_gold_metrics_honest(self):
  m=json.loads((ROOT/'reports'/'B_metrics.json').read_text(encoding='utf-8'));self.assertEqual(m['audited_count'],65);self.assertEqual(m['correct'],46);self.assertIsNone(m['verified_recall']);self.assertAlmostEqual(m['strict_accuracy'],46/65)
 def test_idempotent_b_merge(self):
  for rid in ['E0006','E0007']:self.assertEqual(sum(rid in e['record_ids'] for e in self.graph.edges),1)
if __name__=='__main__':unittest.main()
