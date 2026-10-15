import gzip,json,re,collections,os,sys
V3='/workspace/usuba-runs/v3-data/'
def load_rows():
    rows=[]
    for sp in ('train','val'):
        for l in gzip.open(V3+sp+'.jsonl.gz','rt'): rows.append(json.loads(l))
    return rows
def target(r): return json.loads(r['messages'][-1]['content'])
def last_user(r): return r['messages'][-2]['content']
FILEBLK=re.compile(r"^### (.+?)\n```\n(.*?)\n```$",re.S|re.M)
def parse_files(u):
    i=u.find('## Plugin source'); s=u[i:]
    return {m.group(1):m.group(2) for m in FILEBLK.finditer(s)}
def dell_res():
    res={}
    for l in open('/workspace/wt-retrain-v2/dell/sweep/results.jsonl'):
        d=json.loads(l)
        if d.get('dell'): res[d['dell']['job']]=d
    return res
