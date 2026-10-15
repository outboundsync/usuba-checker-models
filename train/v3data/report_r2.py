#!/usr/bin/env python3
"""GATE_REPORT.md + SAMPLES.md for v3-data-r2. usage: report_r2.py DIR"""
import sys, os, re, json, gzip, random, collections, hashlib, statistics, difflib
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
sys.path[:0] = [T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), H, "/workspace/r2"]
import build_train_set as B, exactline as X
from build_v3_data import BAD_WORDS, v2_user_files
import prompt_v2 as PA, prompt_v3 as PB
D = sys.argv[1] if len(sys.argv) > 1 else "/workspace/usuba-runs/v3-data-r2"
OLD = "/workspace/usuba-runs/v3-data"
load = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]
tr, va = load(f"{D}/train.jsonl.gz"), load(f"{D}/val.jsonl.gz"); allr = tr + va
otr, ova = load(f"{OLD}/train.jsonl.gz"), load(f"{OLD}/val.jsonl.gz"); oldall = otr + ova
tgt = lambda r: json.loads(r["messages"][-1]["content"])
bs = json.load(open(f"{D}/build_stats.json")); st, drops = bs["stats"], bs["drops"]
def lines_of(files, fn):
    t = files.get(fn)
    return None if t is None else t.split("\n")
def exact_stats(rs):
    c = collections.Counter(); per_row_ok = 0; per_row_n = 0; bykind = collections.defaultdict(collections.Counter)
    for r in rs:
        files = X.parse_files(r["messages"][-2]["content"]); ok = True; any_f = False
        for f in tgt(r)["findings"]:
            if not f.get("file") or not isinstance(f.get("line"), int): continue
            ls = lines_of(files, f["file"]); res = "file_missing" if ls is None else X.check(f["finding"], ls, f["line"], f["file"])
            c[res] += 1; any_f = True
            k = f["category"] if r["source"] == "hancore_concrete" else "dell/" + f["category"].split(":")[0] if r["source"].startswith("dell") and r["verdict"] != "approve" else "approve-warning"
            bykind[k][res] += 1
            if res not in ("strict", "two_line", "nocheck"): ok = False
        if any_f: per_row_n += 1; per_row_ok += ok
    return c, per_row_ok, per_row_n, bykind
def pr(c): 
    chk = sum(v for k, v in c.items() if k != "nocheck"); ok = c["strict"] + c["two_line"]
    return ok / max(1, chk), ok / max(1, sum(c.values()))
ca, rok, rn, bk = exact_stats(allr); co, rok_o, rn_o, bk_o = exact_stats(oldall)
rep = {}
# counts
spl = lambda rs: collections.Counter(r["source"] for r in rs)
share = lambda rs: round(sum(r["verdict"] == "approve" for r in rs) / max(1, len(rs)), 3)
br = [r for r in allr if r["verdict"] == "changes_requested"]; hc = [r for r in br if r["source"] == "hancore_concrete"]
dl = [r for r in br if r["source"].startswith("dell")]
# per kind
K = collections.defaultdict(lambda: dict(rows=set(), f=0, fl=0))
for r in br:
    for f in tgt(r)["findings"]:
        if f["severity"] != "blocker": continue
        k = f["category"] if r["source"] == "hancore_concrete" else "dell-sourced/" + f["category"].split(":")[0] + ":*"
        K[k]["rows"].add(r["id"]); K[k]["f"] += 1; K[k]["fl"] += bool(f.get("file") and isinstance(f.get("line"), int))
tok = sorted(r["tokens"] for r in allr); q = lambda p: tok[min(len(tok) - 1, int(p * len(tok)))]
# kind agreement before / after
def agree(path):
    V = json.load(open(path)); mj = lambda v: collections.Counter(v).most_common(1)[0][0]
    return dict(n=len(V), majority=round(sum(mj(o["votes"]) == o["assigned"] for o in V) / len(V), 3), unanimous=round(sum(len(set(o["votes"])) == 1 and o["votes"][0] == o["assigned"] for o in V) / len(V), 3),
                majority_n=sum(mj(o["votes"]) == o["assigned"] for o in V))
ag_b, ag_a = agree("/workspace/r2/out/kind_votes_before.json"), agree("/workspace/r2/out/kind_votes_after.json")
# leakage
h_repos, h_ids, h_trees = B.holdout_fingerprint()
key_ids, key_trees = set(), []
import functest as FT
for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")):
    k = json.loads(l); key_ids.add(k["id"].lower())     # ids/paths only; labels are never read
    if k.get("path") and os.path.isdir(os.path.join(ROOT, k["path"])): key_trees.append(B.file_hashes(FT.read_dir(os.path.join(ROOT, k["path"]))))
excl = {B.norm_repo(u) for u in json.load(open("/workspace/usuba-runs/hancore-labels/excluded_plugins.json"))}
leak = collections.Counter(); bad = []
for r in allr:
    files, u = v2_user_files(r); repo = B.norm_repo(r["id"].split(":", 1)[1].rsplit(":", 1)[0]); fh = B.file_hashes(files); mid = B.manifest_id({"manifest.json": files.get("manifest.json", "")})
    chk = dict(holdout_repo=repo in h_repos, excluded_repo_list=repo in excl, holdout_manifest_id=bool(mid and mid.lower() in h_ids), dellkey_manifest_id=bool(mid and mid.lower() in key_ids),
               holdout_near_dup=B.near_dup(fh, h_trees), dellkey_near_dup=B.near_dup(fh, key_trees), forbidden_vendor_word=bool(BAD_WORDS.search(r["messages"][-1]["content"])),
               dellkey_id_in_text=any(len(i) >= 8 and i in u.lower() for i in key_ids))
    for k, v in chk.items():
        if v and k == "dellkey_id_in_text": leak["INFO_incidental_key_id_string_in_other_plugin_text"] += 1
        elif v: leak[k] += 1; bad.append((r["id"], k))
fp = [hashlib.sha1(re.sub(r"\s+", "", "".join(sorted(B.file_hashes(v2_user_files(r)[0])))).encode()).hexdigest() for r in allr]; ids = [r["id"] for r in allr]
repo_of = lambda r: r["id"].split(":", 1)[1].rsplit(":", 1)[0]
leakage = dict(rows_checked=len(allr), dell_key_ids=len(key_ids), dell_key_trees_loaded=len(key_trees), holdout_repos=len(h_repos), holdout_trees=len(h_trees), holdout_manifest_ids=len(h_ids), hits=dict(leak), hard_hit_examples=bad[:10],
               duplicate_row_ids=len(ids) - len(set(ids)), exact_duplicate_trees=len(fp) - len(set(fp)), train_val_repo_overlap=len({repo_of(r) for r in tr} & {repo_of(r) for r in va}))
# near-dup among kept rows
idx = collections.defaultdict(list); nd = 0; fhs = [set(B.file_hashes(v2_user_files(r)[0])) for r in allr]
for i, fh in enumerate(fhs):
    cand = collections.Counter(j for h in fh for j in idx[h])
    if fh and any(n / max(1, min(len(fh), len(fhs[j]))) >= 0.5 for j, n in cand.items()): nd += 1
    for h in fh: idx[h].append(i)
leakage["near_dup_pairs_ge50pct_among_kept"] = nd
# hancore/dell stats
hf = [f for r in hc for f in tgt(r)["findings"]]
mix = collections.Counter(f["category"] for f in hf)
dellcat = collections.Counter(f["category"] for r in dl for f in tgt(r)["findings"] if f["severity"] == "blocker")
dell_audit_log = [json.loads(l) for l in open(f"{D}/r2_dell_audit_log.jsonl")]
da = collections.Counter(x["action"] for x in dell_audit_log)
import importlib.util as _iu
_sp = _iu.spec_from_file_location('r2common', '/workspace/r2/common.py'); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m)
_dr = _m.dell_res(); ev = collections.Counter()
for r in dl:
    d = _dr[r["provenance"]["dell_job"]]["dell"]; ev["dell_runtime_error_or_missing_bin" if (d["qml_errors"] or d["missing_bins"]) else "checker_static_only"] += 1
dell_evidence = dict(ev)
# ---------- samples ----------
prev_text = open(f"{OLD}/SAMPLES.md").read() + open(f"{OLD}/GATE_REPORT.md").read()
rnd = random.Random(20261015 + 77)
def snippet(r, f, ctx=4):
    files = X.parse_files(r["messages"][-2]["content"]); ls = lines_of(files, f["file"])
    if ls is None or not isinstance(f.get("line"), int): return "(no line)"
    a = max(0, f["line"] - 1 - ctx); b = min(len(ls), f["line"] + ctx)
    return "\n".join(f"{'>' if i + 1 == f['line'] else ' '}{i + 1:5d}| {ls[i][:170]}" for i in range(a, b))
def render(r, why):
    a = tgt(r); u = r["messages"][-2]["content"]; rep_t = u.split("## Plugin source")[0].replace("## Checker report\n", "").strip(); files = X.parse_files(u)
    o = [f"### `{r['id']}` — {why}", f"- source: {r['source']}; tokens: {r['tokens']}; files shown: {len(files)}", f"- Checker report shown to the model:\n```\n{rep_t[:500]}\n```"]
    for f in a["findings"]:
        ls = lines_of(files, f["file"]) if f.get("file") else None
        res = X.check(f["finding"], ls, f["line"], f["file"]) if ls is not None and isinstance(f.get("line"), int) else "n/a"
        mark = "PASS" if res in ("strict", "two_line") else ("NO CHECKABLE CONSTRUCT" if res == "nocheck" else "N/A (no line cited)" if res == "n/a" else "FAIL")
        o.append(f"- **[{f['severity']}] {f['category']}** `{f['file']}:{f['line']}`: {f['finding']}\n  - **automated check 'cited line contains the described construct': {mark}** ({res}; constructs: {X.spans(f['finding'])[:4]})\n```\n{snippet(r, f)}\n```")
    if not a["findings"]: o.append("- no findings (clean approve); no cited line to check")
    o.append("- **full answer taught:**\n```json\n" + json.dumps(a, indent=1, ensure_ascii=False) + "\n```\n")
    return "\n".join(o)
def fresh(r): return r["id"] not in prev_text and r["tokens"] < 22000
ex, app, picked = [], [], set()
kinds = sorted(mix); rnd.shuffle(kinds); sel_kinds = kinds[:9]
for k in sel_kinds:
    c = [r for r in hc if fresh(r) and r["id"] not in picked and any(f["category"] == k for f in tgt(r)["findings"])]
    r = rnd.choice(c); picked.add(r["id"]); ex.append((r, "HANCORE kind " + k))
for pref, why in (("load:", "Dell-derived load bug"), ("in-use:", "Dell-derived in-use bug"), (("runtime:", "config:", "security:", "qml:", "logic:", "missing-file", "packaging:", "syntax:"), "Dell-derived other bug")):
    c = [r for r in dl if fresh(r) and r["id"] not in picked and tgt(r)["findings"][0]["category"].startswith(pref)]
    r = rnd.choice(c); picked.add(r["id"]); ex.append((r, why))
for pred, why in ((lambda r: r["source"] == "dell_works_verified" and tgt(r)["findings"], "APPROVE with a warning (trusted-and-small exception)"), (lambda r: r["source"] == "dell_works_verified" and not tgt(r)["findings"], "APPROVE clean"),
                  (lambda r: r["source"] in ("fix_upstream", "nudged_approve"), "APPROVE after upstream fix / nudged")):
    c = [r for r in allr if pred(r) and fresh(r) and r["id"] not in picked]
    r = rnd.choice(c); picked.add(r["id"]); app.append((r, why))
# independent re-verification of every cited line by the open model (fresh prompt tag, not used while building)
import refine_r2 as R2, llm
from concurrent.futures import ThreadPoolExecutor
jobs = []
for r in allr:
    files = X.parse_files(r["messages"][-2]["content"])
    for f in tgt(r)["findings"]:
        ls = lines_of(files, f["file"]) if f.get("file") else None
        if ls is not None and isinstance(f.get("line"), int): jobs.append((r, f, ls))
def _v(j):
    r, f, ls = j; return R2._vcall(f["finding"], ls, f["line"], f["file"], "lineverify_final")
with ThreadPoolExecutor(14) as pool: VR = list(pool.map(_v, jobs))
grp = lambda r, f: "hancore" if r["source"] == "hancore_concrete" else ("dell_broken" if r["verdict"] != "approve" else "approve_warning")
lv = collections.defaultdict(collections.Counter)
for (r, f, ls), v in zip(jobs, VR):
    g = grp(r, f); lv[g]["n"] += 1; lv[g]["exact"] += v.get("exact") is True; lv[g]["defect_stated"] += v.get("defect_stated") is not False
llm_verify = {k: dict(v) for k, v in lv.items()}; llm_total = sum(v["n"] for v in lv.values()); llm_exact = sum(v["exact"] for v in lv.values())
S_ok = collections.Counter()
for r, _ in ex + app:
    files = X.parse_files(r["messages"][-2]["content"])
    for f in tgt(r)["findings"]:
        ls = lines_of(files, f["file"]) if f.get("file") else None
        S_ok["pass" if ls is not None and isinstance(f.get("line"), int) and X.check(f["finding"], ls, f["line"], f["file"]) in ("strict", "two_line") else "other"] += 1
NOTES = open(os.path.join(H, "samples_notes_r2.md")).read() if os.path.exists(os.path.join(H, "samples_notes_r2.md")) else ""
md = ["# Usuba v3-data-r2 — SAMPLES (prompt_v3)", "", f"Rows: {len(allr)} (train {len(tr)}, val {len(va)}). 12 fresh random examples (9 HANCORE kinds, 3 Dell-derived) + 3 approve; none appears in the earlier v3 SAMPLES.md / GATE_REPORT.md (seed 20261015+77, not curated). "
      f"Each blocker/warning carries the automated check *cited line contains the described construct* (a backticked identifier/command from the finding must be ON the cited line, or within the same 2-line statement; blank/comment lines fail). Line numbers are counted from the top of the file as shown in the prompt (the model sees none).",
      f"Check results on these 15 samples: {dict(S_ok)}. Overall pass rate over ALL rows: see GATE_REPORT.md section 3 ({pr(ca)[0]:.1%} of checkable findings).", "", "## A. 12 examples", ""] + [render(r, w) for r, w in ex] + ["", "## B. 3 approve examples", ""] + [render(r, w) for r, w in app] + ["", "## C. Reviewer notes", "", NOTES]
open(f"{D}/SAMPLES.md", "w").write("\n".join(md))
# ---------- gate report ----------
g = [f"# Usuba v3-data-r2 — gate report", f"Generated {os.popen('date').read().strip()} on branch v3-data-r2. No training, no GPU, no Dell commands. Rows: train {len(tr)}, val {len(va)} (v3 draft was train 1013 / val 41).", "",
     "Changes vs the v3 draft: (1) HANCORE findings re-anchored to the exact statement; (2) Dell-sourced findings audited against source + Checker/Dell evidence; (3) HANCORE kind labels checked by an independent open-model vote. Open model = qwen/qwen3.5-397b-a17b via OpenRouter (open weights); no Anthropic/DeepSeek/proprietary output.", "",
     "## 1. Row counts by source", "| source | train | val | v3 draft (train+val) |", "|---|--:|--:|--:|"]
for s in sorted(set(spl(allr)) | set(spl(oldall))): g.append(f"| {s} | {spl(tr).get(s,0)} | {spl(va).get(s,0)} | {spl(oldall).get(s,0)} |")
g += ["", "## 2. Broken vs approve", f"- train: {dict(collections.Counter(r['label'] for r in tr))} (approve share {share(tr)})", f"- val: {dict(collections.Counter(r['label'] for r in va))} (approve share {share(va)})",
      f"- all: broken {len(br)}, approve {len(allr)-len(br)}, approve share {share(allr)} (target 40-50%)", f"- HANCORE rows {len(hc)}, HANCORE findings {len(hf)}; Dell-sourced broken rows {len(dl)} ({sum(dellcat.values())} blockers)", "",
      "## 3. Exact-line check over ALL rows (train+val, every finding that cites file+line, blockers and warnings)",
      "Check = a backticked construct from the finding prose occurs on the cited line ('strict') or within the 2-line statement ('two_line'); blank lines, comment lines and lines without the construct fail. 'nocheck' = the finding names no backticked construct, so it cannot be verified mechanically (counted separately, excluded from the pass rate; the conservative rate counts them as not passing).",
      "| | r2 (this build) | v3 draft |", "|---|--:|--:|"]
for k in ("strict", "two_line", "fail", "blank_or_comment", "out_of_range", "file_missing", "nocheck"): g.append(f"| {k} | {ca.get(k,0)} | {co.get(k,0)} |")
g += [f"| **pass rate over checkable findings** | **{pr(ca)[0]:.1%}** ({ca['strict']+ca['two_line']}/{sum(v for k,v in ca.items() if k!='nocheck')}) | {pr(co)[0]:.1%} |", f"| conservative pass rate (nocheck counts as fail) | {pr(ca)[1]:.1%} | {pr(co)[1]:.1%} |",
      f"| independent open-model re-check 'cited line is the exact statement' (fresh prompt, all findings) | {llm_exact}/{llm_total} = {llm_exact/max(1,llm_total):.1%} | n/a |",
      f"| rows with a cited line where every finding passes or is nocheck | {rok}/{rn} = {rok/rn:.1%} | {rok_o}/{rn_o} = {rok_o/rn_o:.1%} |", "",
      "Open-model re-check by group: " + "; ".join(f"{k}: exact {v['exact']}/{v['n']}, defect-stated {v['defect_stated']}/{v['n']}" for k, v in llm_verify.items()), "", "Pass rate by group (r2): " + "; ".join(f"{k}: {v['strict']+v['two_line']}/{sum(x for kk,x in v.items() if kk!='nocheck')} (+{v['nocheck']} nocheck)" for k, v in sorted(bk.items(), key=lambda x: -sum(x[1].values()))), "",
      "## 4. Fix 1 — HANCORE exact-line anchoring",
      f"- HANCORE findings entering the stage: {st.get('hancore_findings_in')} (rows {st.get('hancore_rows_in')}). Before-state of the cited line under the new check (after text clean-up, before anchoring): strict {st.get('hancore_anchor_before_strict',0)}, two_line {st.get('hancore_anchor_before_two_line',0)}, construct-not-on-line {st.get('hancore_anchor_before_fail',0)}, blank/comment {st.get('hancore_anchor_before_blank_or_comment',0)}, out of range {st.get('hancore_anchor_before_out_of_range',0)}, no checkable construct {st.get('hancore_anchor_before_nocheck',0)}.",
      f"- **Re-anchored: {st.get('hancore_findings_reanchored')} findings** (moved to the nearest line carrying the quoted construct, within -12/+60 lines, else <=150); kept as-is: {st.get('hancore_findings_line_kept')}; **dropped for no exact line: {drops.get('hancore_finding:no_exact_line_found',0)} + {drops.get('hancore_finding:no_checkable_construct',0)} (no checkable construct) + {drops.get('hancore_finding:anchor_check_failed',0)}**.",
      f"- Second gate (open model, per finding, shown the +-10 lines around the cited line): 'is the cited line the exact statement the finding describes' and 'does the finding state a defect (not safe behaviour / scope / a fix confirmation)'. HANCORE: {drops.get('hancore_finding:llm_not_exact_line',0)} findings dropped as not-exact (no better visible line), {st.get('hancore_findings_llm_moved',0)} moved to the line the model named (accepted only if the mechanical check also passes), {drops.get('hancore_finding:not_a_defect_statement',0)} dropped because the prose states no defect. Dell-sourced: {drops.get('dell_finding:llm_not_exact_line',0)} dropped, {st.get('dell_findings_llm_moved',0)} moved; approve warnings: {drops.get('approve_finding:llm_not_exact_line',0)} dropped, {st.get('approve_findings_llm_moved',0)} moved.",
      "- Stale `file:12-34` / `lines 38-56` references inside the prose were stripped (the cited line lives in the structured field); framing like 'Additional current-tree finding:' removed; findings ending in a 300-char ellipsis cut were cut back to the last full sentence or dropped.",
      f"- Row-level: HANCORE rows dropped because no finding was left: {drops.get('hancore_row:no_finding_left',0)}. All drop reasons: `{json.dumps(drops)}`", "",
      "## 5. Fix 2 — Dell-sourced answer audit",
      f"- Audited: {st.get('dell_rows_in')} rows / {st.get('dell_findings_in')} findings (dell_broken_verified, dell_inuse_close, dell_inuse_missing_binary). Evidence per finding: the cited code ±8 lines, other occurrences of the quoted constructs, the Checker report as shown in the prompt, the Dell sweep run record (qml_errors, missing_bins) from dell/sweep/results.jsonl, and stock-binary lookups. No Dell key labels were read; key ids are only used for exclusion.",
      f"- Outcome by action: {dict(da)}.", f"- Dell broken rows kept: {len(dl)} (v3: {sum(1 for r in oldall if r['source'].startswith('dell') and r['verdict']!='approve')}). Dell blocker categories left: `{dict(dellcat.most_common(12))}`.",
      f"- The two known errors: gpasswd@setup.sh:108 -> dropped (stock `shadow` tool); mpv `get_property` -> dropped (IPC method string). The sibling finding for the same razer plugin, `Qt.resolvedUrl` passed as a file:// URL, was ALSO dropped: `Service.qml:18` wraps it in `root.pluginPath()` which strips `file://` (my earlier note called it right; it was wrong). Details per finding in `r2_dell_audit_log.jsonl`.",
      f"- Evidence class of the {len(dl)} kept Dell broken rows: {dell_evidence} (runtime = Dell run recorded QML errors or missing binaries; static-only = the Checker flagged it, the Dell run showed no error but did not necessarily open the panel).",
      f"- `in-use:missing-binary` blockers remaining: {sum(1 for r in dl for f in tgt(r)['findings'] if f['category'].endswith('missing-binary'))} (v3: {sum(1 for r in oldall if r['source'].startswith('dell') and r['verdict']!='approve' for f in tgt(r)['findings'] if f['category'].endswith('missing-binary'))}); `security:*` remaining: {sum(1 for r in dl for f in tgt(r)['findings'] if f['category'].startswith('security:'))} (v3: {sum(1 for r in oldall if r['source'].startswith('dell') and r['verdict']!='approve' for f in tgt(r)['findings'] if f['category'].startswith('security:'))}).", "",
      "## 6. Fix 3 — HANCORE bug-kind labels (independent open-model vote)",
      f"Method: 3 votes per finding from the finding prose only (assigned kind never shown; category order shuffled per vote; temperature 0.3). Keep when 3/3 agree with the assigned kind; relabel when 3/3 agree on another kind; otherwise drop the finding.",
      f"- **Before** (v3 labels, {ag_b['n']} findings): majority vote == assigned {ag_b['majority_n']}/{ag_b['n']} = **{ag_b['majority']:.1%}**; unanimous == assigned {ag_b['unanimous']:.1%}.",
      f"- Actions: kept {st.get('kind_keep_unanimous')}, **relabelled {st.get('kind_relabel_unanimous')}**, **dropped {drops.get('hancore_finding:kind_disagreement',0)}** (split votes).",
      f"- **After** (independent re-vote with fresh seeds on the final {ag_a['n']} findings and final kinds): majority == assigned {ag_a['majority_n']}/{ag_a['n']} = **{ag_a['majority']:.1%}**; unanimous == assigned {ag_a['unanimous']:.1%}.",
      "- Caveat: relabels follow one model's reading; kinds are not human-verified. Many findings genuinely span two kinds (e.g. unbounded read AND no deadline); the vote picks the primary one.", "",
      "## 7. Per bug kind (blocker findings in broken rows)", "| kind | rows | findings | share with file+line |", "|---|--:|--:|--:|"]
for k, v in sorted(K.items(), key=lambda x: -len(x[1]["rows"])): g.append(f"| {k} | {len(v['rows'])} | {v['f']} | {v['fl']/v['f']:.1%} |")
hs = sum({f['category'] for f in tgt(r)['findings']} == {'unbounded-input-resource'} for r in hc)
g += ["", f"HANCORE rows whose only kind is unbounded-input-resource: {hs} ({hs/len(hc):.1%} of HANCORE rows, {hs/len(br):.1%} of broken rows; cap 20% of broken).",
      f"File+line share over all blocker findings: {sum(v['fl'] for v in K.values())}/{sum(v['f'] for v in K.values())}.", "",
      "## 8. Token lengths", f"`{dict(min=tok[0], p50=q(.5), p90=q(.9), p99=q(.99), max=tok[-1], mean=round(statistics.mean(tok)), over_32768=sum(t>32768 for t in tok), over_32000=sum(t>32000 for t in tok))}` (Qwen3.5 tokenizer over json(messages); cap 32000, train max_len 32768).", "",
      "## 9. Leakage + dedupe checks (recomputed on the written files)", "```", json.dumps(leakage, indent=1), "```",
      "'INFO_incidental' = a Dell-key id string occurs inside a different plugin's text; manifest id, repo and tree do not match (same as v3). Schema unchanged (same record keys as v3/v2; train_lora.py unchanged).", "",
      "## 10. Build drops and cost", f"- stats: `{json.dumps(st)}`", f"- drops: `{json.dumps(drops)}`", f"- Open-model spend (OpenRouter usage.cost, qwen/qwen3.5-397b-a17b, all stages): see COST.md", "",
      "## 11. Samples", "See SAMPLES.md (12 fresh random examples + 3 approve, each with its automated cited-line check).", "", "## 12. Remaining weaknesses", open(os.path.join(H, "weaknesses_r2.md")).read() if os.path.exists(os.path.join(H, "weaknesses_r2.md")) else ""]
open(f"{D}/GATE_REPORT.md", "w").write("\n".join(g))
json.dump(dict(llm_line_recheck=llm_verify, exact_line_all=dict(ca), exact_line_v3=dict(co), pass_rate=pr(ca), kind_agreement_before=ag_b, kind_agreement_after=ag_a, leakage=leakage, tokens=dict(p50=q(.5), max=tok[-1]), per_kind={k: dict(rows=len(v['rows']), findings=v['f']) for k, v in K.items()},
               hancore_kind_mix=dict(mix), dell_actions=dict(da), samples=S_ok, approve_share=dict(train=share(tr), val=share(va), all=share(allr)), counts=dict(train=len(tr), val=len(va), broken=len(br), hancore_rows=len(hc), dell_broken_rows=len(dl))), open(f"{D}/report.json", "w"), indent=1, default=int)
print(json.dumps(json.load(open(f"{D}/report.json")), indent=1)[:5000])
