#!/usr/bin/env python3
"""r3 assembly (no training/GPU/Dell): refined pool -> (1) Checker report regeneration (old-vs-new Checker diff, only lines the FIXED rules no longer emit are removed),
(2) unbounded-only cap, (3) repo-disjoint balanced val set (>=60 rows, 50% approve, kind-stratified, near-dup/leakage-checked against train, Dell key and holdout),
(4) train with approve share <=47%. usage: assemble_r3.py POOL_REFINED OUTDIR"""
import sys, os, re, json, gzip, random, collections, hashlib, importlib.util
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2_helpers"), "/workspace/wt-retrain-v2/train/v3data", "/workspace/wt-retrain-v2/train", "/workspace/wt-retrain-v2/functest"]
import exactline as X, build_train_set as B
import checker_report as CR
from build_reviewer_scrub import scrub
from usuba import checks as NEW
_sp = importlib.util.spec_from_file_location("usuba.checks_old_r2ref", "/workspace/wt-retrain-v2/functest/usuba/checks_old_r2ref.py"); OLD = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(OLD)
POOL, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
rnd = random.Random(2026); st = collections.Counter(); rule_removed = collections.Counter(); samples = []
from tokenizers import Tokenizer
_tk = Tokenizer.from_file(os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a/tokenizer.json")); ntok = lambda s: len(_tk.encode(s).ids)
tgt = lambda r: json.loads(r["messages"][-1]["content"])
def lines_with(mod, files):
    CR.checks = mod
    try: rep = CR.report(files)
    finally: CR.checks = NEW
    return None if rep is None else [scrub(x) for x in rep]
HDR = "## Checker report\n"
def regen(r):
    u = r["messages"][-2]["content"]; i = u.index(HDR); j = u.index("\n\n## Plugin source")
    body = u[i + len(HDR):j]
    if body.startswith("(") : return r, 0
    files = {p: c for p, c in X.parse_files(u).items() if p not in CR.HARNESS_FILES}
    old = lines_with(OLD, files); new = lines_with(NEW, files)
    if old is None or new is None: st["regen_checker_unavailable"] += 1; return r, 0
    removed = [x for x in old if x not in set(new)]
    stored = body.split("\n"); keep = []; n = 0
    for ln in stored:
        if ln in removed:
            n += 1; m = re.match(r"\[(USB-\w+)", ln); rule_removed[m.group(1) if m else "?"] += 1
            if len(samples) < 400: samples.append(dict(id=r["id"], rule=m.group(1) if m else "?", line=ln[:300]))
        else: keep.append(ln)
    if not n: return r, 0
    nb = "\n".join(keep) if keep else "(no Checker findings)"
    msgs = [dict(m) for m in r["messages"]]; msgs[-2]["content"] = u[:i + len(HDR)] + nb + u[j:]
    return dict(r, messages=msgs, tokens=ntok(json.dumps(msgs)), provenance=dict(r["provenance"], checker_report_regenerated_r3=n)), n
RC = os.path.join(OUT, "regen_rows.jsonl.gz")   # cache of the (slow, deterministic) report regeneration; delete to recompute
if os.path.exists(RC) and not os.environ.get("NO_REGEN_CACHE"):
    rows = [json.loads(l) for l in gzip.open(RC, "rt")]; st["rows_with_removed_lines"] = sum(1 for r in rows if r["provenance"].get("checker_report_regenerated_r3")); st["report_lines_removed"] = sum(r["provenance"].get("checker_report_regenerated_r3", 0) for r in rows)
    for r in rows:
        for ln in [x for x in json.load(open(os.path.join(OUT, "rule_removed.json"))).items()][:0]: pass
    rule_removed.update(json.load(open(os.path.join(OUT, "rule_removed.json"))))
else:
    rows = [json.loads(l) for l in gzip.open(POOL, "rt")]
    out = []
    for r in rows:
        r2, n = regen(r); st["rows_with_removed_lines"] += bool(n); st["report_lines_removed"] += n; out.append(r2)
    rows = out
    with gzip.open(RC, "wt") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(dict(rule_removed), open(os.path.join(OUT, "rule_removed.json"), "w"))
# ---- leakage fingerprints
h_repos, h_ids, h_trees = B.holdout_fingerprint()
def fhash(r):
    files = X.parse_files(r["messages"][-2]["content"])
    return {hashlib.sha1(re.sub(r"\s+", "", c).encode()).hexdigest() for p, c in files.items() if not p.lower().startswith(("readme", "license")) and c.strip()}
for r in rows: r["_fh"] = fhash(r); r["_repo"] = (r["id"].split(":", 1)[1].rsplit(":", 1)[0] if ":" in r["id"] else r["id"]).lower()
kinds = lambda r: {f["category"] for f in tgt(r)["findings"]}
broken = [r for r in rows if r["verdict"] == "changes_requested"]; approve = [r for r in rows if r["verdict"] == "approve"]
ub = [r for r in broken if r["source"] == "hancore_concrete" and kinds(r) == {"unbounded-input-resource"}]; cap_ub = int(0.20 * len(broken))
if len(ub) > cap_ub:
    rnd.shuffle(ub); dr = {r["id"] for r in ub[cap_ub:]}; st["cap_unbounded_only_dropped"] = len(dr); rows = [r for r in rows if r["id"] not in dr]
    broken = [r for r in rows if r["verdict"] == "changes_requested"]
# ---- near-dup helper
def dup(a, b): return len(a["_fh"] & b["_fh"]) / max(1, min(len(a["_fh"]), len(b["_fh"]))) >= 0.5 if a["_fh"] and b["_fh"] else False
# ---- val selection: repo-disjoint, kind-stratified broken (>=32) + approve (equal count), no near-dup with any other-repo row
VAL_B = 32   # target broken rows after filtering; total val >= 64
byrepo = collections.defaultdict(list)
for r in broken: byrepo[r["_repo"]].append(r)
def tags(r): return {("H:" if r["source"] == "hancore_concrete" else "D:") + c for c in kinds(r)}
tot = collections.Counter(t for r in broken for t in tags(r))
quota = {t: max(1, round(n * 0.12)) for t, n in tot.items()}
got = collections.Counter(); val_b = []; repos = sorted(byrepo); rnd.shuffle(repos)
cross = lambda r, others: any(dup(r, o) for o in others if o["_repo"] != r["_repo"])
def need(r): return any(got[t] < quota[t] for t in tags(r))
for rp in repos:
    if len(val_b) >= VAL_B: break
    rs = byrepo[rp]
    if not all(need(r) for r in rs) and not any(need(r) for r in rs): continue
    if any(cross(r, [x for x in rows if x["split"] != "val"] if False else []) for r in rs): pass
    for r in rs:
        for t in tags(r): got[t] += 1
    val_b += rs
for rp in repos:   # fill pass: kind quotas exhausted before reaching the target size -> add more repos (random order) until VAL_B broken rows
    if len(val_b) >= VAL_B + 10: break
    if rp in {r["_repo"] for r in val_b}: continue
    val_b += byrepo[rp]
val_ids = {r["id"] for r in val_b}; val_repos = {r["_repo"] for r in val_b}
# drop val broken rows near-dup to any non-val row of another repo (conservative: exclude from val, keep in train)
others = [r for r in rows if r["_repo"] not in val_repos]
bad = {r["id"] for r in val_b if any(dup(r, o) for o in others)}
val_b = [r for r in val_b if r["id"] not in bad]; val_repos = {r["_repo"] for r in val_b}
# approve for val: same count, source-mixed, repos disjoint from val broken repos and from train rows' repos; not near-dup with any broken/other row
cands = [r for r in approve if r["_repo"] not in val_repos]
prio = {"fix_upstream": 0, "nudged_approve": 0}; rnd.shuffle(cands); cands.sort(key=lambda r: prio.get(r["source"], 1))
val_a = []; vrs = set(val_repos)
non_val_broken = [r for r in broken if r["_repo"] not in val_repos]
for r in cands:
    if len(val_a) >= len(val_b): break
    if r["_repo"] in vrs: continue
    if any(dup(r, o) for o in non_val_broken) or any(dup(r, o) for o in val_a): continue
    val_a.append(r); vrs.add(r["_repo"])
val = val_b + val_a; val_repos = {r["_repo"] for r in val}
# train: everything else; approve trimmed to <= 90% of broken; drop train rows that share repo with val or near-dup with a val row
tr_b = [r for r in broken if r["_repo"] not in val_repos]
tr_a = [r for r in approve if r["_repo"] not in val_repos]
leak_dup = [r for r in tr_b + tr_a if any(dup(r, v) for v in val)]
ld = {r["id"] for r in leak_dup}; st["train_rows_dropped_near_dup_with_val"] = len(ld)
tr_b = [r for r in tr_b if r["id"] not in ld]; tr_a = [r for r in tr_a if r["id"] not in ld]
max_app = int(len(tr_b) * 0.9)
if len(tr_a) > max_app:
    tr_a.sort(key=lambda r: (prio.get(r["source"], 1), rnd.random(), r["id"])); st["cap_approve_trim_train"] = len(tr_a) - max_app; tr_a = tr_a[:max_app]
train = tr_b + tr_a; rnd.shuffle(train); rnd.shuffle(val)
for sp, rs in (("train", train), ("val", val)):
    with gzip.open(os.path.join(OUT, sp + ".jsonl.gz"), "wt") as f:
        for r in rs: f.write(json.dumps(dict({k: v for k, v in r.items() if not k.startswith("_")}, split=sp), ensure_ascii=False) + "\n")
json.dump(dict(stats=dict(st), rule_removed=dict(rule_removed), train=len(train), val=len(val), val_broken=len(val_b), val_approve=len(val_a), train_broken=len(tr_b), train_approve=len(tr_a),
               val_repos=len(val_repos), val_kind_coverage={t: got[t] for t in sorted(got)}, kind_quota=quota),
          open(os.path.join(OUT, "assemble_stats.json"), "w"), indent=1)
with open(os.path.join(OUT, "checker_report_removed_lines.jsonl"), "w") as f:
    for s in samples: f.write(json.dumps(s) + "\n")
print(json.dumps(dict(st)), dict(rule_removed), "train", len(train), len(tr_b), len(tr_a), "val", len(val), len(val_b), len(val_a))
