#!/usr/bin/env python3
"""pass@1 / pass@k per category for best-of-k sampling files (k consecutive rows per prompt, as written by gen_m.py NSAMP=k).
usage: FUNCTEST_DIR=... pass_at_k.py K out.json name=prompts.jsonl:gens.jsonl ...
prompts may be clean/holdout_clean.jsonl (tree tasks scored against the holdout baseline) or any build_from_spec/add_panel file."""
import json, os, sys, collections
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.environ.get("FUNCTEST_DIR", os.path.join(ROOT, "functest")))
sys.path.insert(0, os.path.join(ROOT, "runs/clean"))
import rescore
from loopdet import loopy
K, out = int(sys.argv[1]), sys.argv[2]
res = json.load(open(out)) if os.path.exists(out) else {}
for spec in sys.argv[3:]:
    name, rest = spec.split("=", 1); pf, gf = rest.split(":")
    P = [json.loads(l) for l in open(pf)]; G = [json.loads(l) for l in open(gf)]
    assert len(G) == K * len(P), (len(G), len(P))
    jobs = []
    for pi, p in enumerate(P):
        hi = p.get("holdout_i"); h = rescore.hold[hi] if hi is not None else p
        for g in G[pi * K:(pi + 1) * K]:
            assert g["task"] == p["task"]; jobs.append((hi, h, g))
    with ThreadPoolExecutor(8) as ex: rows = list(ex.map(lambda a: rescore.score_row(*a), jobs))
    for r, (_, _, g) in zip(rows, jobs):   # Harris rule: runaway loops and truncations are plain fails
        if g["finish"] == "length" or loopy(g["output"]): r["pass_"] = False
    per = collections.defaultdict(lambda: [0, 0, 0, 0, 0])  # prompts, sum pass rate, any pass, truncated, looped
    for pi, p in enumerate(P):
        rr = rows[pi * K:(pi + 1) * K]; gg = G[pi * K:(pi + 1) * K]; c = p["task"].split(":")[0]
        for key in (c, "ALL"):
            per[key][0] += 1; per[key][1] += sum(r["pass_"] for r in rr) / K; per[key][2] += any(r["pass_"] for r in rr)
            per[key][3] += sum(g["finish"] == "length" for g in gg) / K; per[key][4] += sum(loopy(g["output"]) for g in gg) / K
    summ = {c: dict(prompts=n, pass_at_1=round(s / n, 3), pass_at_k=f"{a}/{n}", trunc_rate=round(t / n, 3), loop_rate=round(l / n, 3)) for c, (n, s, a, t, l) in per.items()}
    res[name] = dict(k=K, summary=summ, per_prompt=[dict(task=p["task"], passes=sum(r["pass_"] for r in rows[i * K:(i + 1) * K])) for i, p in enumerate(P)])
    print(name, json.dumps(summ, indent=1), flush=True); json.dump(res, open(out, "w"), indent=1)
