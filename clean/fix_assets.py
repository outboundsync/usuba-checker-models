"""Re-test training answers that fail only because binary assets (svg/png) aren't in the text answer:
the upstream plugin's asset files are installed alongside the answer (assets are not something the model writes)."""
import json, os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_train as st
import runtime, functest
tr=[json.loads(l) for l in open(st.ROOT+"/data/train.jsonl")]
sc=json.load(open("score_train.json"))
ASSET_EXT=(".svg",".png",".jpg",".jpeg",".gif",".webp",".ttf",".otf")
orig=runtime.install_files
def make(src):
    def inst(dst, files):
        orig(dst, files)
        for r,ds,fs in os.walk(src):
            ds[:]=[d for d in ds if d!=".git"]
            for f in fs:
                if f.lower().endswith(ASSET_EXT):
                    rel=os.path.relpath(os.path.join(r,f),src); t=os.path.join(dst,rel)
                    if not os.path.exists(t): os.makedirs(os.path.dirname(t),exist_ok=True); shutil.copy(os.path.join(r,f),t)
    return inst
fixed={}
for s in sc:
    if s["pass_"]: continue
    errs=s["runtime_errors"]+s["static_fails"]
    if not errs or not all("Cannot open:" in e for e in errs): continue
    h=tr[s["i"]]; runtime.install_files=make(st.tree_dir(h))
    st.cached=lambda files: functest.test(files=files)   # no cache: results depend on assets
    r=st.one((s["i"],h)); fixed[s["i"]]=r; print(s["i"],s["task"],r["pass_"],r["runtime_errors"][:2])
runtime.install_files=orig
for s in sc:
    if s["i"] in fixed and fixed[s["i"]]["pass_"]: s.update(pass_=True,categories=[],asset_fix=True,runtime_errors=[])
json.dump(sc,open("score_train.json","w"),indent=1)
