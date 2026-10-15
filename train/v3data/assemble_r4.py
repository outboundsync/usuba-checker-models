#!/usr/bin/env python3
"""r4 assembly: r3 pool (after report regeneration/drops) + version-history rows + jankeesvw-history rows (+ synthetic/winners) -> caps, dedupe, repo-disjoint kind-stratified val, train.
usage: assemble_r4.py WORKDIR OUTDIR     seeds: Random(2027)"""
import sys, os, re, json, gzip, random, collections, hashlib
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
W, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
sys.path[:0] = [os.path.join(H, "r2_helpers"), H, T, os.path.join(ROOT, "functest")]
import exactline as X, build_train_set as B
from build_reviewer_scrub import scrub
import train_prompt_loader as _pl
PV3 = _pl.load()
from tokenizers import Tokenizer
_tk = Tokenizer.from_file(os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a/tokenizer.json")); ntok = lambda s: len(_tk.encode(s).ids)
rnd = random.Random(2027); st = collections.Counter(); drops = collections.Counter()
tgt = lambda r: json.loads(r["messages"][-1]["content"])
rd = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]
FX = "/workspace/usuba-runs/v3-fixes/"
# ---- inputs
r3 = rd(W + "/r3_pool_final.jsonl.gz")
hb = rd(W + "/hist/hist_broken.jsonl.gz"); ha = rd(W + "/hist/hist_approve_candidates.jsonl.gz")
def copyright_of(r):
    """first real copyright line of the repo LICENSE at the commit (year or (c)/© required; Apache boilerplate and placeholders ignored)"""
    d = f"{W}/trees2/{r['provenance']['repo'].replace('/', '__')}_{r['provenance']['commit'][:10]}_pre"
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if re.match(r"(LICEN[CS]E|COPYING)", fn, re.I):
            for ln in open(os.path.join(d, fn), errors="replace").read().split("\n"):
                m = re.match(r"\s*((?:copyright\s*(?:\(c\)|©)?|\(c\)|©)\s*(?:19|20)\d\d[^\n]{0,80})$", ln, re.I)
                if m and "[yyyy]" not in ln and "owner" not in ln.lower(): return m.group(1).strip()
    import subprocess   # fallback: LICENSE at the clone's default branch (license text of the same repository)
    for fn in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "LICENCE"):
        t = subprocess.run(["git", "-C", "/workspace/vh_repos/" + r["provenance"]["repo"].replace("/", "__"), "show", "HEAD:" + fn], capture_output=True, text=True, errors="replace").stdout
        for ln in t.split("\n"):
            m = re.match(r"\s*((?:copyright\s*(?:\(c\)|©)?|\(c\)|©)\s*(?:19|20)\d\d[^\n]{0,80})$", ln, re.I)
            if m and "[yyyy]" not in ln and "owner" not in ln.lower(): r["provenance"]["license_file_at_commit"] = False; return m.group(1).strip()
    return None
for r in hb + ha: r["provenance"]["copyright"] = copyright_of(r); st["history_rows_without_copyright_line"] += r["provenance"]["copyright"] is None
# jankeesvw rows: re-wrap with current prompt_v3, report diff (v3-fixes Checker -> current), token cap, exclusions
HDR = "## Checker report\n"; old = json.load(open(W + "/jank_rep_old.json")); new = json.load(open(W + "/jank_rep_new.json")); jank = []
for r in rd(W + "/jank_rows.jsonl.gz"):
    if r["id"].endswith(":approve") and False: pass
    u = r["messages"][-2]["content"]; i = u.index(HDR); j = u.index("\n\n## Plugin source"); body = u[i + len(HDR):j]
    stored = [] if body.startswith("(") else body.split("\n"); o, n = old[r["id"]] or [], new[r["id"]] or []
    removed = set(o) - set(n); keep = [x for x in stored if x not in removed]; add = [x for x in n if x not in o and x not in keep]
    keep = sorted(keep + add, key=lambda x: {y: k for k, y in enumerate(n)}.get(x, 10 ** 6)); st["jank_report_lines_removed"] += len(stored) - len([x for x in stored if x not in removed]); st["jank_report_lines_added"] += len(add)
    msgs = [dict(m) for m in r["messages"]]; msgs[-2]["content"] = u[:i + len(HDR)] + ("\n".join(keep) if keep else "(no Checker findings)") + u[j:]
    msgs = PV3.rebuild(msgs); tk = ntok(json.dumps(msgs))
    if tk > 32000: drops["jank:over_32k"] += 1; continue
    jank.append(dict(r, split="train", source="jankeesvw-history", messages=msgs, tokens=tk))
# synthetic + winners (v3-fixes), include_in_train honoured
extra = []
for fn in ("synthetic_rows.jsonl", "winners_rows.jsonl"):
    for l in open(FX + fn):
        r = json.loads(l)
        if r["provenance"].get("include_in_train", True) is False: continue
        msgs = PV3.rebuild(r["messages"]); tk = ntok(json.dumps(msgs))
        if tk <= 32000: extra.append(dict(r, split="train", messages=msgs, tokens=tk))
# ---- fingerprints (leakage + near-dup)
h_repos, h_ids, h_trees = B.holdout_fingerprint(); key_ids, key_trees = set(), []
import functest as FT
for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")):
    k = json.loads(l); key_ids.add(k["id"].lower()); p = os.path.join(ROOT, k.get("path") or "")
    if k.get("path") and os.path.isdir(p):
        fh = B.file_hashes(FT.read_dir(p))
        if fh: key_trees.append(fh)
excl = {B.norm_repo(u) for u in json.load(open("/workspace/usuba-runs/hancore-labels/excluded_plugins.json"))}
def fhash(r):
    files = X.parse_files(r["messages"][-2]["content"])
    return {hashlib.sha1(re.sub(r"\s+", "", c).encode()).hexdigest() for p, c in files.items() if not p.lower().startswith(("readme", "license")) and c.strip()}, files
def repo_of(r):
    if r["source"] in ("version_history", "jankeesvw-history"): return r["provenance"]["repo"].lower()
    return (r["id"].split(":", 1)[1].rsplit(":", 1)[0] if ":" in r["id"] else r["id"]).lower()
allrows = [dict(r, _prio=(0 if r["source"] in ("hancore_concrete", "dell_broken_verified", "dell_inuse_close", "dell_inuse_missing_binary") else 1 if r["source"] == "jankeesvw-history" else 2 if r["source"] == "version_history" else 3)) for r in r3 + jank + hb + ha + extra]
rows = []
for r in allrows:
    r["_fh"], files = fhash(r); r["_repo"] = repo_of(r); mid = B.manifest_id({"manifest.json": files.get("manifest.json", "")})
    if r["source"] in ("version_history", "jankeesvw-history"):
        if r["_repo"] in h_repos or r["_repo"] in excl or (mid and (mid.lower() in h_ids or mid.lower() in key_ids)) or B.near_dup(r["_fh"], h_trees) or B.near_dup(r["_fh"], key_trees): drops["excluded_leak:" + r["source"]] += 1; continue
    rows.append(r)
# ---- dedupe: priority r3 broken/dell > jank > history > approve; history broken/approve twins (same commit) are allowed to share a tree
rows.sort(key=lambda r: (r["_prio"], r["id"])); final, idx = [], collections.defaultdict(list)
twin = lambda r: (r["provenance"].get("commit"), r["_repo"]) if r["source"] == "version_history" else None
for r in rows:
    cand = collections.Counter(j for h in r["_fh"] for j in idx[h]); dup = None
    for j, n in cand.items():
        o = final[j]
        if n / max(1, min(len(r["_fh"]), len(o["_fh"]))) >= 0.5 and not (twin(r) and twin(r) == twin(o)) and not (r["source"] == "synthetic_lifecycle"):
            dup = o; break
    if dup is not None: drops[f"dedupe_near_dup:{r['source']}_vs_{dup['source']}"] += 1; continue
    final.append(r)
    for h in r["_fh"]: idx[h].append(len(final) - 1)
rows = final
broken = [r for r in rows if r["verdict"] != "approve"]; approve = [r for r in rows if r["verdict"] == "approve"]
kind = lambda r: tgt(r)["findings"][0]["category"] if tgt(r)["findings"] else None
kinds = lambda r: {f["category"] for f in tgt(r)["findings"]}
THIN = {"null-or-missing-guard", "missing-dependency-or-install", "shell-quoting-or-expansion", "error-handling", "security", "api-compat-change"}
def hist_priority(r):   # larger = dropped first. Thin kinds are kept preferentially (score u*0.5, so kept about twice as often) but other kinds keep a share (score u); insertion anchors rank later
    u = int(hashlib.sha1(r["id"].encode()).hexdigest(), 16) / 2**160; pv = r["provenance"]
    return ((u * 0.5 if pv.get("history_bug_kind") in THIN else u) + (0.1 if pv.get("exact_class") != "exact_removed" else 0), r["id"])
# ---- caps (iterative): unbounded-only <=20%, any single kind <=20%, any single source <=40% of broken rows. Drop order: history rows (weakest first), then jank, never r3/Dell rows unless they alone break a cap.
def drop_rows(ids, why): global rows, broken, approve; rows = [r for r in rows if r["id"] not in ids]; broken = [r for r in rows if r["verdict"] != "approve"]; approve = [r for r in rows if r["verdict"] == "approve"]; drops[why] += len(ids)
def enforce():
    changed = False
    nb = len(broken)
    # source cap 40%
    for src in sorted({r["source"] for r in broken}):
        rs = [r for r in broken if r["source"] == src]; cap = int((nb - len(rs)) * 0.385 / 0.615)   # n <= 0.385 (n + others): margin so later val/train dedupe still ends <= 40%
        if len(rs) > cap:
            order = sorted(rs, key=hist_priority, reverse=True) if src == "version_history" else sorted(rs, key=lambda r: hashlib.sha1((str(rnd.random()) + r["id"]).encode()).hexdigest())
            k = len(rs) - cap; rs_drop = order[:k]; ids = {r["id"] for r in rs_drop}
            if src == "version_history": ids |= {r["id"].replace(":broken", ":fixed") for r in rs_drop}
            drop_rows(ids, f"cap:source_{src}_40pct"); return True
    # per-kind cap 20%
    kc = collections.Counter(c for r in broken for c in kinds(r))
    for c, n in kc.most_common():
        if n > int(0.20 * nb):
            rs = [r for r in broken if c in kinds(r)]; pri = sorted(rs, key=lambda r: (0 if r["source"] == "version_history" else 1 if r["source"] == "jankeesvw-history" else 2, ) + (hist_priority(r) if r["source"] == "version_history" else (hashlib.sha1(r["id"].encode()).hexdigest(),)), reverse=False)
            # drop from the end of the *least valuable* group first: history weakest, else others at random
            hist = sorted([r for r in rs if r["source"] == "version_history"], key=hist_priority, reverse=True)
            oth = [r for r in rs if r["source"] != "version_history"]; rnd.shuffle(oth)
            k = -(-(n - 0.20 * nb) // 0.80) and int(-(-(n - 0.20 * nb) // 0.80)); vict = (hist + oth)[:k]; ids = {r["id"] for r in vict} | {r["id"].replace(":broken", ":fixed") for r in vict if r["source"] == "version_history"}
            drop_rows(ids, f"cap:kind_{c}_20pct"); return True
    ub = [r for r in broken if kinds(r) == {"unbounded-input-resource"}]
    if len(ub) > int(0.20 * nb):
        hist = sorted([r for r in ub if r["source"] == "version_history"], key=hist_priority, reverse=True); oth = [r for r in ub if r["source"] != "version_history"]; rnd.shuffle(oth)
        vict = (hist + oth)[:int(-(-(len(ub) - 0.20 * nb) // 0.80))]; drop_rows({r["id"] for r in vict} | {r["id"].replace(":broken", ":fixed") for r in vict if r["source"] == "version_history"}, "cap:unbounded_only_20pct"); return True
    return False
print('before caps', dict(collections.Counter(r['source'] for r in broken)), 'approve', dict(collections.Counter(r['source'] for r in approve)))
print('before caps kinds', dict(collections.Counter(r['provenance'].get('history_bug_kind') for r in broken if r['source']=='version_history')))
while enforce(): pass
print('after caps kinds', dict(collections.Counter(r['provenance'].get('history_bug_kind') for r in broken if r['source']=='version_history')))
print('after caps', dict(collections.Counter(r['source'] for r in broken)))
# approve history rows are a minority: <= 1/3 of history broken rows, and only if their broken twin survived
hbk = {r["id"] for r in broken if r["source"] == "version_history"}
orph = {r["id"] for r in approve if r["source"] == "version_history" and r["id"].replace(":fixed", ":broken") not in hbk}
if orph: drop_rows(orph, "approve_history_twin_dropped")
hap = [r for r in approve if r["source"] == "version_history"]; mx = len(hbk) // 3
if len(hap) > mx:
    hap.sort(key=lambda r: hashlib.sha1(r["id"].encode()).hexdigest()); drop_rows({r["id"] for r in hap[mx:]}, "approve_history_minority_cap")
print('after minority', dict(collections.Counter(r['source'] for r in rows if r['verdict']!='approve')))
# ---- val: repo-disjoint, per-kind quota (>=3 where >=6 rows exist), balanced approve
byrepo = collections.defaultdict(list)
for r in rows: byrepo[r["_repo"]].append(r)
tot = collections.Counter(c for r in broken for c in kinds(r)); quota = {c: (max(3, round(0.08 * n)) if n >= 6 else (1 if n >= 3 else 0)) for c, n in tot.items()}
got = collections.Counter(); val_repos = set(); repos = sorted(byrepo); rnd.shuffle(repos)
def gain(rs): return sum(1 for r in rs if r["verdict"] != "approve" for c in kinds(r) if got[c] < quota[c])
while True:
    best = max((rp for rp in repos if rp not in val_repos and gain(byrepo[rp]) > 0 and not any(r["source"] == "synthetic_lifecycle" for r in byrepo[rp])), key=lambda rp: (gain(byrepo[rp]), -len(byrepo[rp])), default=None)
    if best is None: break
    val_repos.add(best)
    for r in byrepo[best]:
        if r["verdict"] != "approve":
            for c in kinds(r): got[c] += 1
val_b = [r for rp in val_repos for r in byrepo[rp] if r["verdict"] != "approve"]; val_a = [r for rp in val_repos for r in byrepo[rp] if r["verdict"] == "approve"]
cands = [r for r in approve if r["_repo"] not in val_repos and r["source"] not in ("synthetic_lifecycle", "winners_mit", "version_history")]; rnd.shuffle(cands)   # history approve rows join val only with their own (val) repo, never by removing a train repo
vrs = set(val_repos)
for r in cands:
    if len(val_a) >= len(val_b): break
    if r["_repo"] in vrs: continue
    val_a.append(r); vrs.add(r["_repo"])
val = val_b + val_a; val_repos = {r["_repo"] for r in val}
# train: everything else; drop train rows that near-dup a val row (other repo)
def dup(a, b): return len(a["_fh"] & b["_fh"]) / max(1, min(len(a["_fh"]), len(b["_fh"]))) >= 0.5 if a["_fh"] and b["_fh"] else False
tr = [r for r in rows if r["_repo"] not in val_repos]; ld = {r["id"] for r in tr if any(dup(r, v) for v in val)}; tr = [r for r in tr if r["id"] not in ld]; st["train_rows_dropped_near_dup_with_val"] = len(ld)
tb = [r for r in tr if r["verdict"] != "approve"]; ta = [r for r in tr if r["verdict"] == "approve"]
prio = lambda r: {"synthetic_lifecycle": -2, "winners_mit": -2, "version_history": -1, "fix_upstream": 0, "nudged_approve": 0}.get(r["source"], 1)
mx = int(len(tb) * 0.9)
if len(ta) > mx: ta.sort(key=lambda r: (prio(r), rnd.random(), r["id"])); st["cap_approve_trim_train"] = len(ta) - mx; ta = ta[:mx]
print('tb', dict(collections.Counter(r['source'] for r in tb)), 'val_b', dict(collections.Counter(r['source'] for r in val_b)))
train = tb + ta; rnd.shuffle(train); rnd.shuffle(val)
for sp, rs in (("train", train), ("val", val)):
    with gzip.open(os.path.join(OUT, sp + ".jsonl.gz"), "wt") as f:
        for r in rs: f.write(json.dumps(dict({k: v for k, v in r.items() if not k.startswith("_")}, split=sp, **({"weight": 2.0} if r["source"] == "version_history" and r["verdict"] != "approve" and r["provenance"].get("history_bug_kind") in THIN else {})), ensure_ascii=False) + "\n")
src = lambda rs: dict(collections.Counter(r["source"] for r in rs))
bsrc = lambda rs: dict(collections.Counter(r["source"] for r in rs if r["verdict"] != "approve"))
json.dump(dict(stats=dict(st), drops=dict(drops), train=len(train), val=len(val), train_broken=len(tb), train_approve=len(ta), val_broken=len(val_b), val_approve=len(val_a), source_mix_all=src(train + val), broken_source_mix=bsrc(train + val),
               val_kind_counts={c: got[c] for c in sorted(got)}, kind_totals=dict(tot), quota=quota, val_repos=len(val_repos)), open(os.path.join(OUT, "assemble_stats.json"), "w"), indent=1)
print(json.dumps(dict(stats=dict(st), drops=dict(drops)), indent=1)); print("train", len(train), len(tb), len(ta), "val", len(val), len(val_b), len(val_a)); print(bsrc(train + val))
