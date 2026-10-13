import json,sys,os
sys.path.insert(0,"functest"); sys.path.insert(0,"runs/clean")
import rescore; from loopdet import loopy
from concurrent.futures import ThreadPoolExecutor
P=[json.loads(l) for l in open("runs/v3/probe_bfs32.jsonl")]; G=[json.loads(l) for l in open("runs/q27/gen_bo16q27_t0.8_rp1.05_n16.jsonl")]
keep=[0,1,3,4,6,7,9,11,15,17,19,21,23,29,30]
jobs=[(pi,j,G[pi*16+j]) for pi in keep for j in range(16) if G[pi*16+j]["finish"]!="length" and not loopy(G[pi*16+j]["output"])]
def f(a):
  pi,j,g=a; r=rescore.score_row(None,P[pi],g); return pi,j,bool(r["pass_"])
with ThreadPoolExecutor(8) as ex: out=list(ex.map(f,jobs))
json.dump([o for o in out if o[2]],open("runs/q27/bo16_pass_samples.json","w")); print([o[:2] for o in out if o[2]])
