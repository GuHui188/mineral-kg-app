"""Neo4j 5 transactional HTTP client. Credentials only from environment."""
import base64,json,os,urllib.request,urllib.error
class Neo4j:
 def __init__(self,url=None,user=None,password=None,database=None):
  self.base=(url or os.getenv('NEO4J_HTTP_URL','http://127.0.0.1:7474')).rstrip('/');self.database=database or os.getenv('NEO4J_DATABASE','neo4j')
  if not self.database.replace('-','').replace('_','').isalnum():raise ValueError('非法数据库名称')
  self.url=f'{self.base}/db/{self.database}/tx/commit';self.user=user or os.getenv('NEO4J_USER','neo4j');self.password=password if password is not None else os.getenv('NEO4J_PASSWORD','')
 def batch(self,statements):
  headers={'Content-Type':'application/json'}
  if self.password:headers['Authorization']='Basic '+base64.b64encode(f'{self.user}:{self.password}'.encode()).decode()
  req=urllib.request.Request(self.url,data=json.dumps({'statements':[{'statement':s,'parameters':p} for s,p in statements]},ensure_ascii=False).encode('utf-8'),headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=40) as r:data=json.load(r)
  except urllib.error.HTTPError as e:raise RuntimeError(f'Neo4j HTTP {e.code}；检查服务版本、数据库名与本地凭据') from None
  except urllib.error.URLError as e:raise ConnectionError('Neo4j连接失败：'+str(e.reason)) from None
  if data.get('errors'):raise RuntimeError('; '.join(e['code']+': '+e['message'] for e in data['errors']))
  return [[dict(zip(r['columns'],x['row'])) for x in r['data']] for r in data['results']]
 def run(self,statement,parameters=None):return self.batch([(statement,parameters or {})])[0]
