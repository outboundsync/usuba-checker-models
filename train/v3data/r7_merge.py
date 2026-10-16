#!/usr/bin/env python3
"""r7: merge scope-v4 row sets (r6 scope build + below-floor rows + security subset + history-mining output), dedupe by plugin+version, per-slug floor (>=15 else dropped), caps
(<= SRC_MAX of any source, Dell <= DELL_SHARE, approve <= APPROVE_MAX), plugin-level split (all rows of a plugin in one split). usage: r7_merge.py OUTDIR DIR [DIR ...]"""
import sys, os, json, gzip, random, collections, glob, tempfile
OUT = sys.argv[1]; DIRS = sys.argv[2:]; os.makedirs(OUT, exist_ok=True)
sys.argv = ["x", tempfile.mkdtemp(), OUT]
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import build_scope as B
E_ = os.environ.get; SRC_MAX = float(E_("R7_SRC_MAX", "0.40"))
rows = []; seen = set()
for d in DIRS:
    for fn in ("train", "val", "below_floor"):
        p = os.path.join(d, fn + ".jsonl.gz")
        if not os.path.exists(p): continue
        for l in gzip.open(p, "rt"):
            r = json.loads(l); k = (r["meta"]["repo"], r["meta"]["commit"], r["row_type"])
            if r["id"] in seen or k in seen: continue
            seen.add(r["id"]); seen.add(k); r["_repo"] = r["meta"]["repo"]; r["_fh"] = frozenset(); r.pop("split", None); rows.append(r)
st = dict(input_rows=len(rows), by_source_in=dict(collections.Counter(r["source"] for r in rows)))
ver, c, low = B.enforce_floor(rows); st["floor_dropped_slugs"] = low; st["after_floor"] = len(ver)
ap = lambda r: json.loads(r["messages"][-1]["content"])["verdict"] == "approve"
pri = lambda r: ({"extend": 0, "triage": 1, "clean": 2}[r["row_type"]], r["meta"]["provisional"], r["id"])
ver = B.cap_dell(ver); st["after_dell_cap"] = len(ver)
# per-source cap: iterate, trimming the lowest-priority rows of any source above SRC_MAX, then re-trimming approves above APPROVE_MAX
for _ in range(50):
    n = len(ver); cnt = collections.Counter(r["source"] for r in ver); worst, w = cnt.most_common(1)[0]
    if w / n <= SRC_MAX: break
    cands = sorted([r for r in ver if r["source"] == worst], key=pri, reverse=True); drop = cands[:max(1, w - int(SRC_MAX * (n - 1)))]
    ids = {r["id"] for r in drop}; ver = [r for r in ver if r["id"] not in ids]
st["after_source_cap"] = len(ver)
while sum(map(ap, ver)) / len(ver) > float(E_("R6S_APPROVE_MAX", "0.50")):
    c_ = [r for r in ver if ap(r) and r["row_type"] == "clean"] or [r for r in ver if ap(r)]
    ver.remove(sorted(c_, key=pri, reverse=True)[0])
st["after_approve_cap"] = len(ver)
ver, c, low2 = B.enforce_floor(ver)       # trimming never creates a new low slug unless it removed extend rows: re-check
# plugin-level split: val = ~10% of plugins, chosen by hash so a plugin's versions never straddle
rnd = random.Random(7); plugins = sorted({r["_repo"] for r in ver}); rnd.shuffle(plugins); val = set(plugins[:max(1, len(plugins) // 10)]); tr, va = [], []
for r in ver:
    r = {k: v for k, v in r.items() if not k.startswith("_")}; r["split"] = "val" if r["meta"]["repo"] in val else "train"; (va if r["split"] == "val" else tr).append(r)
for name, rs in (("train", tr), ("val", va)):
    with gzip.open(os.path.join(OUT, name + ".jsonl.gz"), "wt") as f:
        for r in rs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
st.update(rows=len(tr) + len(va), train=len(tr), val=len(va), plugins=len(plugins), slug_counts=dict(c)); json.dump(st, open(os.path.join(OUT, "merge_stats.json"), "w"), indent=1); print(st)
