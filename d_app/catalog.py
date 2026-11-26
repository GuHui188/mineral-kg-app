import copy
from d_app.service import LABELS

def catalog_entities(service,text='',label=None):
    if label and label not in LABELS:raise ValueError('未知实体类型')
    term=text.strip().casefold()
    matched={i for alias,ids in service.graph.aliases.items() if term in alias for i in ids}
    return [copy.deepcopy(service.nodes[i]) for i in sorted(matched) if not label or service.nodes[i]['label']==label]
