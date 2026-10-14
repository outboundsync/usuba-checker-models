#!/usr/bin/env python3
"""Teacher pilot (2026-10-14): 30 known-label train rows (none in the dellkey exam: candidates.jsonl already excludes it), 12 blind Dell-works,
3 blind fixes, 15 guided code-visible broken. `pilot.py pick` -> teacher/pilot_cids.txt; `pilot.py score m1 m2 ...` -> teacher/pilot.json
using the exact assemble.judge filter (parse, verdict agreement, invented SHA/name, right-reason rubric, hint leak, cited file/line)."""
import collections, hashlib, json, os, sys
from common import *
import assemble as A
P = os.path.join(WORK, "teacher", "pilot_cids.txt")
def H(k): return hashlib.sha1(("pilot:" + k).encode()).hexdigest()
def load():
    C = {c["cid"]: c for c in jl(os.path.join(WORK, "candidates.jsonl"))}; G = {g["cid"]: g for g in jl(os.path.join(WORK, "guided.jsonl"))}; return C, G
def pick():
    import batches as BT
    C, G = load(); Q, _ = BT.queue(); tr = [c for c in C.values() if c["split"] == "train" and c["cid"] in Q]
    w = sorted((c["cid"] for c in tr if c["source"] == "dell_works_verified"), key=H)[:12]
    f = sorted((c["cid"] for c in tr if c["source"].startswith("fix_") and not A.fix_incomplete(c) and c["repo"] not in A.DELL_CONTRADICTED), key=H)[:3]
    g = sorted((k for k, v in G.items() if C[v["orig"]]["split"] == "train"), key=H)[:15]
    os.makedirs(os.path.dirname(P), exist_ok=True); open(P, "w").write(",".join(w + f + g)); print(len(w), len(f), len(g))
def score(models):
    C, G = load(); ids = open(P).read().split(","); T = {}
    for m in models:
        res = A.load_results(m); st = json.load(open(os.path.join(WORK, "teacher", m.replace("/", "__"), "state.json")))
        s = collections.Counter(); why_c = collections.Counter()
        for k in ids:
            g = G.get(k); c = C[g["orig"]] if g else C[k]
            if g: c = dict(c, target=dict(c["target"], findings=g["vis"]))
            want = "approve" if c["label"] == "works" else "changes_requested"; r = res.get(k)
            why, out = A.judge(c, g, r, want) if r else ("no_result", None)
            kind = "guided" if g else "blind"; s[kind + "_n"] += 1
            if out is not None and why not in ("truncated", "invalid_json"): s["parsed"] += 1
            if out is not None and out.get("verdict") == want: s[kind + "_agree"] += 1
            if why in ("invented_sha", "invented_plugin_name"): s["invented"] += 1
            if why is None: s[kind + "_kept"] += 1
            why_c[why or "kept"] += 1
        T[m] = dict(counts=dict(s), reasons=dict(why_c), kept=s["blind_kept"] + s["guided_kept"], spend_usd=round(st["spend_usd"], 4), n=len(ids))
    wjson(os.path.join(WORK, "teacher", "pilot.json"), T); print(json.dumps(T, indent=1))
if __name__ == "__main__": pick() if sys.argv[1] == "pick" else score(sys.argv[2:])
