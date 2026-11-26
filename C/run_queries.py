"""Execute and record all 12 Cypher templates on actual Neo4j."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import ROOT,save_json
from neo4j_client import Neo4j
from queries import QUERIES,PARAMS
if __name__=='__main__':
 db=Neo4j();results={}
 for qid,(name,query) in QUERIES.items():results[qid]={'name':name,'rows':db.run(query,PARAMS)}
 save_json(ROOT/'reports'/'neo4j_queries.json',results)
 print('12 Cypher templates executed successfully')
