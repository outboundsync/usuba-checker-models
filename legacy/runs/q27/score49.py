#!/usr/bin/env python3
"""Score gens on the 49-prompt clean holdout with the real functest (functest/rescore.py logic).
usage: score49.py [--loops-only] name=path.jsonl ...   path may have 49 rows (clean order) or 56 rows (full holdout; filtered by holdout_i)."""
import json, os, sys, collections, re
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
# FUNCTEST_DIR lets us score with a pinned functest (e.g. a git worktree of the committed version) while functest/ is being rebuilt
sys.path.insert(0, os.environ.get("FUNCTEST_DIR", os.path.join(ROOT, "functest")))
import rescore
clean = [json.loads(l) for l in open(os.path.join(ROOT, "clean/holdout_clean.jsonl"))]
idx = [c["holdout_i"] for c in clean]
out = os.environ.get("OUT", os.path.join(HERE, "results49.json"))
res = json.load(open(out)) if os.path.exists(out) else {"models": {}, "rows": {}}
sys.path.insert(0, HERE)
from loopdet import loopy
LOOPS_ONLY = "--loops-only" in sys.argv
if LOOPS_ONLY: sys.argv.remove("--loops-only")
for spec in sys.argv[1:]:
    n, p = spec.split("=", 1)
    g = [json.loads(l) for l in open(p)]
    if len(g) == 56: g = [g[i] for i in idx]
    assert len(g) == 49, (n, len(g))
    for c, x in zip(clean, g): assert x.get("task", c["task"]) == c["task"], (n, c["task"], x.get("task"))
    if LOOPS_ONLY:  # recompute loop flags only, keep functest results
        rows = res["rows"][n]
        for r, x in zip(rows, g): r["loop"] = loopy(x["output"])
        res["models"][n]["looping"] = sum(r["loop"] for r in rows); json.dump(res, open(out, "w"), indent=1)
        print(n, "loop", res["models"][n]["looping"], flush=True); continue
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda a: rescore.score_row(*a), [(i, rescore.hold[i], x) for i, x in zip(idx, g)]))
    for r, x in zip(rows, g): r["chars"] = len(x["output"]); r["loop"] = loopy(x["output"])
    s = rescore.summarize(rows, {})
    s = {k: v for k, v in s.items() if not k.startswith("old_")}
    s["looping"] = sum(r["loop"] for r in rows); s["median_chars"] = sorted(r["chars"] for r in rows)[24]
    res["rows"][n] = rows; res["models"][n] = s
    print(n, s["new_overall"], s["new_full_plugin"], "trunc", s["truncated"], "loop", s["looping"], flush=True)
    json.dump(res, open(out, "w"), indent=1)
