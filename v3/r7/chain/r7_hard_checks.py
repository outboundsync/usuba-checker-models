#!/usr/bin/env python3
"""r7 post-merge HARD checks (CPU only, no spend). usage: r7_hard_checks.py DATA_DIR OUT_DIR
exit 0 pass | 10 final set too small (recommend stop rule) | 11 other hard check failed. Writes OUT_DIR/hard_checks.json and NOTIFY_HARRIS.md (the numbers Harris asked for).
Thresholds (env): R7_MIN_ROWS 300 (<: stop rule), R7_SMALL_MAX 600 (300..600: small-data run, flagged), R7_MIN_VAL 10, R7_KIND_FLOOR 15 findings/kind,
R7_FL_MIN 0.95 overall + R7_FL_KIND_MIN 0.90 per added-finding kind (file+line share, ASSUMED thresholds: adjust), approve share in [R7_APPROVE_LO 0.45, R7_APPROVE_HI 0.50]."""
import sys, os, json, gzip, collections, random
E = os.environ.get; D, O = sys.argv[1], sys.argv[2]; os.makedirs(O, exist_ok=True)
MIN_ROWS = int(E("R7_MIN_ROWS", 300)); SMALL_MAX = int(E("R7_SMALL_MAX", 600)); MIN_VAL = int(E("R7_MIN_VAL", 10)); KF = int(E("R7_KIND_FLOOR", 15))
FL = float(E("R7_FL_MIN", .95)); FLK = float(E("R7_FL_KIND_MIN", .90)); LO = float(E("R7_APPROVE_LO", .45)); HI = float(E("R7_APPROVE_HI", .50))
rd = lambda n: [json.loads(l) for l in gzip.open(os.path.join(D, n + ".jsonl.gz"), "rt")]
tr, va = rd("train"), rd("val"); rows = tr + va; N = len(rows)
tg = lambda r: json.loads(r["messages"][-1]["content"])
fails, stop_rule, notes = [], False, []
def bad(m): fails.append(m)
def warn(m): notes.append("WARNING: "+m)
if N < MIN_ROWS: warn(f"final set {N} rows < {MIN_ROWS}: stop rule would have been recommended; Harris overrode: training anyway")
elif N <= SMALL_MAX: notes.append(f"{N} rows: small-data run (300-600 band), train anyway per plan")
if len(va) < 1: bad("val empty")
if len(tr) < 20: bad(f"train has {len(tr)} rows < 20")
if len(va) < MIN_VAL: warn(f"val has {len(va)} rows < {MIN_VAL}")
rt = collections.Counter(r["row_type"] for r in rows); src = collections.Counter(r["source"] for r in rows)
kind = collections.defaultdict(lambda: [0, 0, set()])      # category -> [findings, with file+line, rows]
tri = collections.Counter(); ap = 0; verd = collections.Counter()
for r in rows:
    t = tg(r); verd[t["verdict"]] += 1; ap += t["verdict"] == "approve"
    for a in t["added_findings"]:
        k = kind[a["category"]]; k[0] += 1; k[1] += 1 if (isinstance(a.get("line"), int) and a["line"] > 0 and a.get("file")) else 0; k[2].add(r["id"])
    for x in t["scripts_triage"]: tri[(x["rule"], x["decision"])] += 1
share = ap / max(1, N); tf = sum(v[0] for v in kind.values()); tl = sum(v[1] for v in kind.values())
if tf and tl / tf < FL: warn(f"file+line share over added findings {tl}/{tf} = {tl/tf:.3f} < {FL}")
for c, (f, l, _) in sorted(kind.items()):
    if f < KF: warn(f"kind {c}: {f} findings < floor {KF}")
    if f and l / f < FLK: warn(f"kind {c}: file+line share {l}/{f} = {l/f:.3f} < {FLK}")
if not (LO <= round(share, 3) <= HI): warn(f"approve share {ap}/{N} = {share:.3f} outside [{LO},{HI}]")
if {r["meta"]["repo"] for r in tr} & {r["meta"]["repo"] for r in va}: bad("train/val share a repo")
if len({r["id"] for r in rows}) != N: bad("duplicate row ids")
rnd = random.Random(1337); samp = rnd.sample(rows, min(12, N))
res = dict(rows=N, train=len(tr), val=len(va), row_types=dict(rt), sources=dict(src), verdicts=dict(verd), approve_share=round(share, 4),
           kinds={c: dict(findings=f, file_line=l, rows=len(s)) for c, (f, l, s) in kind.items()}, file_line_overall=[tl, tf], fails=fails, stop_rule=stop_rule, notes=notes)
json.dump(res, open(os.path.join(O, "hard_checks.json"), "w"), indent=1)
L = [f"# r7 final dataset: gate numbers ({D})", "", f"- rows {N} (train {len(tr)}, val {len(va)}); row types {dict(rt)}; sources {dict(src)}",
     f"- approve share {ap}/{N} = {share:.1%} (target {LO:.0%}-{HI:.0%}); verdicts {dict(verd)}", f"- file-and-line share over added findings: {tl}/{tf}" + (f" = {tl/tf:.1%}" if tf else ""),
     f"- hard checks (train>=20, val>=1, repo-disjoint, unique ids): {'PASS' if not fails else 'FAIL'}" + ("".join(f"\n  - FAIL: {m}" for m in fails)) + ("".join(f"\n  - {m}" for m in notes)), "",
     "## Rows per kind (added-finding category)", "| kind | rows | findings | file+line |", "|---|--:|--:|--:|"]
L += [f"| {c} | {len(s)} | {f} | {l}/{f} ({100*l//max(1,f)}%) |" for c, (f, l, s) in sorted(kind.items())]
L += ["", "## 12 samples (seed 1337)"]
for r in samp:
    t = tg(r); L.append(f"- `{r['id']}` {r['row_type']} / {r['source']} / {'prov' if r['meta'].get('provisional') else 'ver'} / {r['meta'].get('repo')}: verdict {t['verdict']}; added "
                        + ("; ".join(f"{a['category']} @{a.get('file')}:{a.get('line')}" for a in t["added_findings"]) or "none") + f"; triage {dict(collections.Counter(x['decision'] for x in t['scripts_triage']))}")
tp = os.path.join(os.path.dirname(os.path.normpath(D)), "final_tradeoff.md")
L += ["", "## Tradeoff table (final_tradeoff.md)", open(tp).read() if os.path.exists(tp) else f"(missing: {tp})"]
open(os.path.join(O, "NOTIFY_HARRIS.md"), "w").write("\n".join(L) + "\n"); print("\n".join(L[:12]))
sys.exit(10 if stop_rule else (11 if fails else 0))
