"""Hand-check digest of Checker passes: spec head, files, and every line touching data sources/commands/red flags."""
import json, sys, os, re
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); import rescore
m = sys.argv[1]; only = {int(x) for x in sys.argv[2:] if x.isdigit()}; new = "--new" in sys.argv; r0 = "--r0" in sys.argv
RED = r"Process|command\s*:|exec|\.sh\b|\.py\b|http|FileView|path\s*:|Math\.random|simulat|mock|fake|dummy|placeholder|TODO|real implementation|console\.log|catch|Timer\s*\{|interval|setTimeout|hardcod|\b\d{2,}\s*(%|°|GB|MB|ms)"
for l in open(os.path.join(H, m, "rows.jsonl")):
    r = json.loads(l); fp = r["first_pass_round"]
    if fp is None or (only and r["i"] not in only) or (new and fp == 0) or (r0 and fp != 0): continue
    x = r["rounds"][fp]; fs = rescore.parse(x["output"]); h = rescore.hold[r["i"]]
    spec = h["messages"][1]["content"]
    print(f"\n===== {m} i={r['i']} {r['task']} pass@{fp} files={ {k: len(c) for k, c in fs.items()} }")
    print("SPEC:", re.sub(r"\s+", " ", spec)[:350])
    if fp: print("FIXED FROM:", [s[:110] for s in (r["rounds"][fp-1].get("reasons") or r["rounds"][fp-1].get("static_fails") or r["rounds"][fp-1].get("runtime_errors") or [])][:3])
    for k, c in fs.items():
        if k == "manifest.json": print("  manifest:", re.sub(r"\s+", " ", c)[:200]); continue
        n = 0
        for ln in c.splitlines():
            if re.search(RED, ln, re.I) and n < 14: print("   ", k, "|", ln.strip()[:150]); n += 1
