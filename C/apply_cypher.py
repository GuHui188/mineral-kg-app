"""Run one allowlisted query; uses environment credentials and parameter JSON."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,save_json
from queries import QUERIES,PARAMS
from neo4j_client import Neo4j
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('template',choices=sorted(QUERIES));p.add_argument('--parameters',type=Path);a=p.parse_args();params=dict(PARAMS)
 if a.parameters:params.update(json.loads(a.parameters.read_text(encoding='utf-8-sig')))
 name,query=QUERIES[a.template];result=Neo4j().run(query,params);save_json(ROOT/'reports'/('neo4j_'+a.template+'.json'),{'name':name,'parameters':params,'rows':result});print(json.dumps(result,ensure_ascii=False,indent=2))
