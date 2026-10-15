# copy of eval_local.py scoring only names in argv; writes summary_14b.json, no samples
"""Score stock vs tuned holdout generations with validator/validate.py + pyside6-qmllint (syntax only).
Full-plugin tasks (build_from_spec, add_panel) are validated standalone. Tree tasks (chunk_*, fix_manifest)
are validated on a stub tree: sibling files named in the prompt + reference-answer files as empty/real placeholders,
with the model's files overlaid on top (manifest validity + entry point existence)."""
import json,os,re,sys,subprocess,tempfile,collections
V=os.path.abspath('../../validator'); sys.path.insert(0,V)
from validate import validate_files
from build_parse import parse
QL=os.path.abspath('../../.venv/bin/pyside6-qmllint')
hold=[json.loads(l) for l in open('../../data/holdout.jsonl')]
def lint(files):
    n=bad=errs=0
    with tempfile.TemporaryDirectory() as t:
        for p,c in files.items():
            if not p.endswith('.qml') or '..' in p or p.startswith('/'): continue
            fp=os.path.join(t,p); os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,'w').write(c); n+=1
            try: r=subprocess.run([QL,'--bare','--disable-plugins','all',fp],capture_output=True,text=True,timeout=30); k=(r.stdout+r.stderr).count('[syntax]')
            except subprocess.TimeoutExpired: k=1
            errs+=k; bad+=k>0
    return n,bad,errs
res={}
import glob
NAMES=[n for n in sys.argv[1:] if os.path.exists(f'gen_{n}.jsonl')]
for name in NAMES:
    rows=[json.loads(l) for l in open(f'gen_{name}.jsonl')]; out=[]
    for h,g in zip(hold,rows):
        task=h['task'].split(':')[0]; files=parse(g['output'])
        full=task in('build_from_spec','add_panel')
        if full or not h['meta'].get('validate_tree') and task!='fix_manifest': tree=dict(files)
        else:
            tree={m.group(1):'x\n' for m in re.finditer(r'^- (\S+) \(\d+ KB\)',h['messages'][1]['content'],re.M)}
            ref=parse(h['messages'][2]['content'])
            um=re.search(r'Other files in the folder: (.*)',h['messages'][1]['content'])
            if um: tree.update({p.strip():'x\n' for p in um.group(1).split(',') if p.strip()})
            pm=re.search(r'```json\n(.*?)\n```',h['messages'][1]['content'],re.S)
            if pm and task!='fix_manifest': tree['manifest.json']=pm.group(1)+'\n'
            for p in ref: tree.setdefault(p,'x\n')
            if task=='fix_manifest':  # stub tree = reference files except manifest
                tree.update({p:'x\n' for p in ref if p!='manifest.json'}); tree.pop('manifest.json',None)
            tree.update(files)
            if 'manifest.json' not in tree and 'manifest.json' in ref: tree['manifest.json']=ref['manifest.json']
        safe={p:c for p,c in tree.items() if '..' not in p and not p.startswith('/')}
        err=validate_files(safe) if files else 'no files parsed'
        n,bad,errs=lint(files)
        out.append(dict(task=h['task'],pass_=err is None,err=err,qml=n,qml_bad=bad,syntax_errs=errs,finish=g['finish']))
    res[name]=out
    json.dump(out,open(f'scores_{name}.json','w'),indent=1)
def summ(o):
    c=collections.defaultdict(lambda:[0,0])
    for r in o: t=r['task'].split(':')[0]; c[t][0]+=r['pass_']; c[t][1]+=1
    return dict(validate_pass=f"{sum(r['pass_'] for r in o)}/{len(o)}",per_task={k:f'{a}/{b}' for k,(a,b) in c.items()},
      full_plugin_pass=f"{sum(r['pass_'] for r in o if r['task'] in('build_from_spec','add_panel'))}/{sum(r['task'] in('build_from_spec','add_panel') for r in o)}",
      qml_files=sum(r['qml'] for r in o),qml_files_with_syntax_err=sum(r['qml_bad'] for r in o),qmllint_syntax_errors=sum(r['syntax_errs'] for r in o),
      truncated=sum(r['finish']=='length' for r in o))
S={k:summ(v) for k,v in res.items()}; json.dump(S,open('summary_14b.json','w'),indent=1); print(json.dumps(S,indent=1))
