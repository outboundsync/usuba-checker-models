"""print comma list of queue cids whose latest stage result is rejected by assemble.judge. usage: rejected.py <stage-tag-list-already-run, e.g. '' or retry1,retry2> -> stdout ids"""
import sys, os, json
from common import *
import assemble as A, queuelib as Q
tags = [t for t in (sys.argv[1].split(",") if len(sys.argv) > 1 else []) if t]
C = {c["cid"]: c for c in jl(os.path.join(WORK, "candidates.jsonl"))}; G = {g["cid"]: g for g in jl(os.path.join(WORK, "guided.jsonl"))}
_, order = Q.queue(); stages = [("", False)] + [(t, t in ("nudge", "loc")) for t in tags]; R = {t: A.load_results(tag=t) for t, _ in stages}
bad = []
for k in order:
    g = G.get(k); c = C[g["orig"]] if g else C[k]
    if g: c = dict(c, target=dict(c["target"], findings=g["vis"]))
    want = "approve" if c["label"] == "works" else "changes_requested"; ok = False
    for t, nd in stages:
        if k in R[t] and A.judge(c, g, R[t][k], want, nudged=nd, loc=(t == "loc"))[0] is None: ok = True; break
    if not ok: bad.append(k)
print(",".join(bad))
