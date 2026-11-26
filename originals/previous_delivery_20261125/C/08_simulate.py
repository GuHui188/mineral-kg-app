"""Compatibility CLI; D should import `from d_adapter import KGService`."""
from pathlib import Path
import argparse,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,Graph,save_json
def simulate_supply_cut(graph,country,mineral,hops=4,as_of='2026-11-25',include_review=False):return graph.simulate(country,mineral,hops,as_of,include_review)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--country',default='刚果（金）');p.add_argument('--mineral',default='钴');p.add_argument('--hops',type=int,default=4);p.add_argument('--as-of',default='2026-11-25');p.add_argument('--include-review',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'reports'/'simulation_custom.json');a=p.parse_args()
 result=Graph().simulate(a.country,a.mineral,a.hops,a.as_of,a.include_review);save_json(a.output,result);print(json.dumps(result,ensure_ascii=False,indent=2))
