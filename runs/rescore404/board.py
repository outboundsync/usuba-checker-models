"""Scoreboard on the 49 clean-holdout prompts, refreshed grader (Omarchy 4.0.4-1). Harris rule: runaway loops and truncations are
plain fails; pass counts only, no best-case bars."""
import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
R = json.load(open(os.path.join(H, "results49.json")))["rows"]
ref = json.load(open(os.path.join(ROOT, "functest/ref49_results.json")))["rows"]
FULL = ("build_from_spec", "add_panel")
ok = lambda r: r["pass_"] and not r["loop"] and r["finish"] != "length"
rows = [("human reference (ceiling)", sum(x["new"] for x in ref), sum(x["new"] for x in ref if x["task"].split(":")[0] in FULL), 0, 0)]
for n, rr in R.items():
    rows.append((n, sum(map(ok, rr)), sum(ok(r) for r in rr if r["task"].split(":")[0] in FULL), sum(r["loop"] for r in rr), sum(r["finish"] == "length" for r in rr)))
rows.sort(key=lambda x: (-x[1], x[0]))
md = ["| model | pass /49 | full-plugin /32 | loops | truncated |", "|---|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
open(os.path.join(H, "SCOREBOARD.md"), "w").write(__doc__ + "\n\n" + "\n".join(md) + "\n"); print("\n".join(md))
fig, ax = plt.subplots(figsize=(9, 0.38 * len(rows) + 1))
names = [r[0] for r in rows][::-1]; vals = [r[1] for r in rows][::-1]
ax.barh(names, vals, color=["#888" if n.startswith("human") else ("#d9822b" if n.startswith("v3") else "#4a7ab7") for n in names])
for i, v in enumerate(vals): ax.text(v + 0.3, i, str(v), va="center", fontsize=8)
ax.set_xlim(0, 49); ax.set_xlabel("passes out of 49 (loops/truncations count as fails)"); ax.set_title("Omarchy plugin holdout, functest on Omarchy 4.0.4-1")
plt.tight_layout(); plt.savefig(os.path.join(H, "scoreboard.png"), dpi=130)
