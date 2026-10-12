# Build RFT train set: for each TRAIN prompt pick the shortest stock sample passing the validator (same tree logic as eval_local)
import json,os,re,sys
os.chdir('/workspace/omarchy-specialist/runs/smoke-2026-10-11')
V=os.path.abspath('../../validator'); sys.path.insert(0,V)
from validate import validate_files
from build_parse import parse
def ok(h,out):
    task=h['task'].split(':')[0]; files=parse(out)
    if not files: return False
    full=task in('build_from_spec','add_panel')
    if full or not h.get('meta',{}).get('validate_tree') and task!='fix_manifest': tree=dict(files)
    else:
        tree={m.group(1):'x\n' for m in re.finditer(r'^- (\S+) \(\d+ KB\)',h['messages'][1]['content'],re.M)}
        ref=parse(h['messages'][2]['content'])
        um=re.search(r'Other files in the folder: (.*)',h['messages'][1]['content'])
        if um: tree.update({p.strip():'x\n' for p in um.group(1).split(',') if p.strip()})
        pm=re.search(r'```json\n(.*?)\n```',h['messages'][1]['content'],re.S)
        if pm and task!='fix_manifest': tree['manifest.json']=pm.group(1)+'\n'
        for p in ref: tree.setdefault(p,'x\n')
        if task=='fix_manifest': tree.update({p:'x\n' for p in ref if p!='manifest.json'}); tree.pop('manifest.json',None)
        tree.update(files)
        if 'manifest.json' not in tree and 'manifest.json' in ref: tree['manifest.json']=ref['manifest.json']
    safe={p:c for p,c in tree.items() if '..' not in p and not p.startswith('/')}
    try: return validate_files(safe) is None
    except Exception: return False
T=[json.loads(l) for l in open('../../data/train.jsonl')]
S=[json.loads(l) for l in open('../fix/gen_train_samples.jsonl')]
out=[];st=dict(sample=0,gold=0,drop=0)
for h,ss in zip(T,S):
    good=[s['output'] for s in ss if s['finish']=='stop' and ok(h,s['output'])]
    if good: a=min(good,key=len); st['sample']+=1
    elif len(h['messages'][2]['content'])<24000: a=h['messages'][2]['content']; st['gold']+=1
    else: st['drop']+=1; continue
    out.append({**h,'messages':h['messages'][:2]+[{'role':'assistant','content':a}]})
open('../fix/train_rft.jsonl','w').write(''.join(json.dumps(x)+'\n' for x in out)); print(st,len(out))
