#!/usr/bin/env python3
"""GATE_REPORT.md + SAMPLES.md + report.json for v3-data-r4. usage: report_r4.py DIR WORKDIR. Independent line re-checks: qwen (fresh prompt tag) and openai/gpt-oss-120b (different open model)."""
import sys, os, re, json, gzip, random, collections, hashlib, statistics
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
D, W = sys.argv[1:3]; sys.argv = [sys.argv[0], W]
sys.path[:0] = [os.path.join(H, "r2_helpers"), H, T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore")]
import build_train_set as B, exactline as X, functest as FT, llm
from build_v3_data import BAD_WORDS, v2_user_files
import refine_r3 as R
from concurrent.futures import ThreadPoolExecutor
load = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]
tr, va = load(f"{D}/train.jsonl.gz"), load(f"{D}/val.jsonl.gz"); allr = tr + va
prev = load("/workspace/usuba-runs/v3-data-r3/train.jsonl.gz") + load("/workspace/usuba-runs/v3-data-r3/val.jsonl.gz")
tgt = lambda r: json.loads(r["messages"][-1]["content"]); AS = json.load(open(f"{D}/assemble_stats.json")); HS = json.load(open(f"{W}/hist/hist_build_stats.json"))
prev_text = open("/workspace/usuba-runs/v3-data-r3/SAMPLES.md").read()
lines_of = lambda files, fn: (files.get(fn).split("\n") if files.get(fn) is not None else None)
isb = lambda r: r["verdict"] != "approve"
def cat_group(r, f): return f["category"] if not r["source"].startswith("dell") else "dell-sourced/" + f["category"].split(":")[0] + ":*"
# ---- exact-line (mechanical) over ALL findings
mech = collections.Counter(); bysrc = collections.defaultdict(collections.Counter); jobs = []
for r in allr:
    files = X.parse_files(r["messages"][-2]["content"])
    for f in tgt(r)["findings"]:
        if not f.get("file") or not isinstance(f.get("line"), int): continue
        ls = lines_of(files, f["file"]); res = "file_missing" if ls is None else X.check(f["finding"], ls, f["line"], f["file"])
        mech[res] += 1; bysrc[r["source"]][res] += 1
        if ls is not None: jobs.append((r, f, ls))
ok = lambda c: c["strict"] + c["two_line"]; chk = lambda c: sum(v for k, v in c.items() if k != "nocheck")
# ---- independent model re-checks (fresh prompt tags)
def vq(j): r, f, ls = j; return R._vcall(f["finding"], ls, f["line"], f["file"], "r4_lineverify_final")
def vg(j):
    r, f, ls = j; return llm.call(R.VSYS, f"FINDING: {f['finding']}\n\nFILE: {f['file']}\n{R.vwindow(ls, f['line'])}", tag="r4_lineverify_gptoss", model="openai/gpt-oss-120b", effort="low", max_tokens=1500)
with ThreadPoolExecutor(14) as pool: VQ = list(pool.map(vq, jobs)); VG = list(pool.map(vg, jobs))
def tally(V):
    t = collections.defaultdict(collections.Counter)
    for (r, f, ls), v in zip(jobs, V): t[r["source"]]["n"] += 1; t[r["source"]]["exact"] += v.get("exact") is True; t[r["source"]]["defect"] += v.get("defect_stated") is not False
    return {k: dict(v) for k, v in t.items()}
tq, tg = tally(VQ), tally(VG); nq = sum(v["n"] for v in tq.values()); eq = sum(v["exact"] for v in tq.values()); eg = sum(v["exact"] for v in tg.values())
# ---- per-kind
K = collections.defaultdict(lambda: dict(rows=set(), f=0, fl=0))
for r in allr:
    if not isb(r): continue
    for f in tgt(r)["findings"]:
        if f["severity"] != "blocker": continue
        k = cat_group(r, f); K[k]["rows"].add(r["id"]); K[k]["f"] += 1; K[k]["fl"] += bool(f.get("file") and isinstance(f.get("line"), int))
kv = collections.Counter(f["category"] for r in va if isb(r) for f in tgt(r)["findings"]); kt = collections.Counter(f["category"] for r in allr if isb(r) for f in tgt(r)["findings"])
# ---- leakage
h_repos, h_ids, h_trees = B.holdout_fingerprint(); key_ids, key_trees = set(), []
for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")):
    k = json.loads(l); key_ids.add(k["id"].lower())      # ids/paths only; labels are never read
    if k.get("path") and os.path.isdir(os.path.join(ROOT, k["path"])): key_trees.append(B.file_hashes(FT.read_dir(os.path.join(ROOT, k["path"]))))
excl = {B.norm_repo(u) for u in json.load(open("/workspace/usuba-runs/hancore-labels/excluded_plugins.json"))}
def repo_of(r):
    if r["source"] in ("version_history", "jankeesvw-history"): return r["provenance"]["repo"].lower()
    return (r["id"].split(":", 1)[1].rsplit(":", 1)[0] if ":" in r["id"] else r["id"]).lower()
leak = collections.Counter(); fhs = []
for r in allr:
    files, u = v2_user_files(r); repo = B.norm_repo(repo_of(r)); fh = B.file_hashes(files); fhs.append(set(fh)); mid = B.manifest_id({"manifest.json": files.get("manifest.json", "")})
    chk_ = dict(holdout_repo=repo in h_repos, excluded_repo_list=repo in excl, holdout_manifest_id=bool(mid and mid.lower() in h_ids), dellkey_manifest_id=bool(mid and mid.lower() in key_ids),
                holdout_near_dup=B.near_dup(fh, h_trees), dellkey_near_dup=B.near_dup(fh, key_trees), forbidden_vendor_word=bool(BAD_WORDS.search(r["messages"][-1]["content"])))
    for k, v in chk_.items():
        if v: leak[k] += 1
    if any(len(i) >= 8 and i in u.lower() for i in key_ids): leak["INFO_incidental_key_id_string_in_other_plugin_text"] += 1
ids = [r["id"] for r in allr]; rs_tr = {repo_of(r) for r in tr}; rs_va = {repo_of(r) for r in va}
idx = collections.defaultdict(list); nd = 0
for i, fh in enumerate(fhs):
    cand = collections.Counter(j for h in fh for j in idx[h])
    if fh and any(n / max(1, min(len(fh), len(fhs[j]))) >= 0.5 for j, n in cand.items()): nd += 1
    for h in fh: idx[h].append(i)
leakage = dict(rows_checked=len(allr), hits=dict(leak), duplicate_row_ids=len(ids) - len(set(ids)), train_val_repo_overlap=len(rs_tr & rs_va), near_dup_rows_ge50pct_among_kept=nd, dell_key_ids=len(key_ids), dell_key_trees=len(key_trees), holdout_repos=len(h_repos))
tok = sorted(r["tokens"] for r in allr); q = lambda p: tok[min(len(tok) - 1, int(p * len(tok)))]
share = lambda rs: round(sum(not isb(r) for r in rs) / max(1, len(rs)), 3)
src = collections.Counter(r["source"] for r in allr); bsrc = collections.Counter(r["source"] for r in allr if isb(r)); nb = sum(bsrc.values())
vh = [r for r in allr if r["source"] == "version_history"]; vhb = [r for r in vh if isb(r)]
lic = collections.Counter(r["provenance"]["license"] for r in vh); cls = collections.Counter(r["provenance"]["exact_class"] for r in vhb)
ub = sum(1 for r in allr if isb(r) and {f["category"] for f in tgt(r)["findings"]} == {"unbounded-input-resource"})
# ---- samples: 12 fresh answers
rnd = random.Random(20261015 + 404)
fresh = lambda r: r["id"] not in prev_text and r["tokens"] < 24000
def snippet(r, f, ctx=4):
    files = X.parse_files(r["messages"][-2]["content"]); ls = lines_of(files, f["file"])
    if ls is None or not isinstance(f.get("line"), int): return "(no line)"
    a = max(0, f["line"] - 1 - ctx); b = min(len(ls), f["line"] + ctx)
    return "\n".join(f"{'>' if i + 1 == f['line'] else ' '}{i + 1:5d}| {ls[i][:170]}" for i in range(a, b))
def render(r, why):
    a = tgt(r); u = r["messages"][-2]["content"]; rep_t = u.split("## Plugin source")[0].replace("## Checker report\n", "").strip(); files = X.parse_files(u); p = r["provenance"]
    o = [f"### `{r['id']}` — {why}", f"- source: {r['source']}; tokens: {r['tokens']}; files shown: {len(files)}" + (f"; license {p.get('license')}; {p.get('repo_url')} @ {str(p.get('commit'))[:10]}" if r["source"] == "version_history" else ""), f"- Checker report shown to the model:\n```\n{rep_t[:450]}\n```"]
    for f in a["findings"]:
        ls = lines_of(files, f["file"]) if f.get("file") else None
        res = X.check(f["finding"], ls, f["line"], f["file"]) if ls is not None and isinstance(f.get("line"), int) else "n/a"
        o.append(f"- **[{f['severity']}] {f['category']}** `{f['file']}:{f['line']}`: {f['finding']}\n  - **automated check 'cited line contains the described construct': {'PASS' if res in ('strict', 'two_line') else 'NO CHECKABLE CONSTRUCT' if res == 'nocheck' else 'FAIL'}** ({res}; constructs: {X.spans(f['finding'])[:4]})\n```\n{snippet(r, f)}\n```")
    if not a["findings"]: o.append("- no findings (clean approve)")
    o.append("- **full answer taught:**\n```json\n" + json.dumps(a, indent=1, ensure_ascii=False) + "\n```\n"); return "\n".join(o), res if a["findings"] else "n/a"
picked, ex = set(), []
def pick(pred, why, n=1):
    c = [r for r in allr if fresh(r) and r["id"] not in picked and pred(r)]; rnd.shuffle(c)
    for r in c[:n]: picked.add(r["id"]); ex.append((r, why))
hk = sorted({tgt(r)["findings"][0]["category"] for r in vhb})
rnd.shuffle(hk)
for k in hk[:7]: pick(lambda r, k=k: r["source"] == "version_history" and isb(r) and tgt(r)["findings"][0]["category"] == k, f"version-history broken, kind {k}")
pick(lambda r: r["source"] == "jankeesvw-history" and isb(r), "jankeesvw-history broken")
pick(lambda r: r["source"] == "hancore_concrete", "HANCORE broken"); pick(lambda r: r["source"].startswith("dell") and isb(r), "Dell-derived broken")
pick(lambda r: r["source"] == "version_history" and not isb(r), "APPROVE: post-fix version (Checker clean + model check)"); pick(lambda r: r["source"] == "dell_works_verified", "APPROVE: Dell-verified working plugin")
ex = ex[:12]; sres = []; body = []
for r, why in ex: t, res = render(r, why); body.append(t); sres.append(res)
S_ok = collections.Counter("pass" if x in ("strict", "two_line") else ("n/a" if x == "n/a" else "other") for x in sres)
md = ["# Usuba v3-data-r4 — SAMPLES (prompt_v3)", "", f"Rows {len(allr)} (train {len(tr)}, val {len(va)}). {len(ex)} fresh random answers (seed 20261015+404; none appears in the r3 SAMPLES.md); each finding carries the automated check *cited line contains the described construct*. Results: {dict(S_ok)}.", ""] + body
open(f"{D}/SAMPLES.md", "w").write("\n".join(md))
# ---- gate report
g = ["# Usuba v3-data-r4 — gate report", f"Generated {os.popen('date').read().strip()} on branch v3-data-r4 (on top of v3-data-r3). No training, no GPU, no Dell commands; Dell key read for ids/paths only (exclusion); hancore_holdout used only as exclusion fingerprints. Open-weights models only: qwen/qwen3.5-397b-a17b and openai/gpt-oss-120b (OpenRouter).", "",
     f"Rows: train {len(tr)}, val {len(va)} (r3: train 516 / val 66).", "", "## 1. Source mix", "| source | train | val | all | broken | share of broken |", "|---|--:|--:|--:|--:|--:|"]
for s in sorted(src): g.append(f"| {s} | {sum(r['source']==s for r in tr)} | {sum(r['source']==s for r in va)} | {src[s]} | {bsrc.get(s,0)} | {bsrc.get(s,0)/max(1,nb):.1%} |")
g += ["", f"Largest single source share of broken rows: {max(bsrc.values())/nb:.1%} (cap 40%). Largest single kind share: {max(kt.values())/sum(kt.values()):.1%} of findings ({kt.most_common(1)[0][0]}); cap 20% of broken rows enforced per kind. Unbounded-input-only broken rows: {ub} ({ub/nb:.1%} of broken, cap 20%).",
      "", "## 2. Broken vs approve", f"- train: broken {sum(isb(r) for r in tr)}, approve {sum(not isb(r) for r in tr)} (approve share {share(tr)})", f"- val: broken {sum(isb(r) for r in va)}, approve {sum(not isb(r) for r in va)} (approve share {share(va)})", f"- all: broken {nb}, approve {len(allr)-nb}, approve share {share(allr)} (target 40-50%)", "",
      "## 3. Exact-line pass rate (all findings that cite file+line)", "| | count |", "|---|--:|"] + [f"| {k} | {mech.get(k,0)} |" for k in ("strict", "two_line", "fail", "blank_or_comment", "out_of_range", "file_missing", "nocheck")] + [
      f"| **mechanical pass rate over checkable findings** | **{ok(mech)/max(1,chk(mech)):.1%}** ({ok(mech)}/{chk(mech)}) |", f"| independent re-check, qwen (fresh prompt) 'cited line is the exact statement' | {eq}/{nq} = {eq/max(1,nq):.1%} |", f"| independent re-check, openai/gpt-oss-120b (second open model) | {eg}/{nq} = {eg/max(1,nq):.1%} |", "",
      "Mechanical by source: " + "; ".join(f"{s}: {ok(c)}/{chk(c)}" for s, c in bysrc.items()), "", "Model re-checks by source (exact / n): qwen " + "; ".join(f"{s} {v['exact']}/{v['n']}" for s, v in tq.items()) + " || gpt-oss " + "; ".join(f"{s} {v['exact']}/{v['n']}" for s, v in tg.items()), "",
      "## 4. Version-history rows", f"- Pairs: 669 verified; license filter (MIT / Apache-2.0 / BSD / ISC only; GPL 22, other-license-file 2, none-found 2 excluded); see `r4_out/prepare_stats.json`.", f"- Rows kept in the final set: {len(vhb)} broken, {len(vh)-len(vhb)} approve (post-fix versions; Checker reported no error-level line and qwen found no remaining defect near the fixed area; kept a minority, <= 1/3 of history broken). Licenses: `{dict(lic)}`. Exact class of broken rows: `{dict(cls)}` (exact_removed = the cited line is exactly a removed line; insertion_anchor = pure insertions that passed the same mechanical and model exact-line gates).",
      f"- Build stats: `{json.dumps(HS['stats'])}`; drops `{json.dumps(HS['drops'])}`.", f"- **Spot check**: {HS['stats']['spot_check_agree']}/{HS['stats']['spot_check_n']} of 40 random gated pairs confirmed by a second, independent open model (openai/gpt-oss-120b: real defect AND cited line exact) = **{HS['spot_agreement']:.1%}**; the {HS['stats']['spot_failed_dropped']} that failed were dropped (`spot_check_40.json`).",
      "- Kind mapping (history kind -> existing taxonomy; model vote 3/3 on the finding text among the allowed categories, split votes dropped): see `hist_build_stats.json` by_category in `r4_out/`. HANCORE hardening kinds get load 'unsure'; Dell-style runtime/in-use kinds get load 'broken'.",
      "- Provenance per row: repo url, commit, parent, date, subject, license, copyright line (from the repo LICENSE), judge confidence, models. NOTICE updated (see repo `NOTICE`).", "",
      "## 5. jankeesvw-history rows", f"- {src.get('jankeesvw-history',0)} rows ({bsrc.get('jankeesvw-history',0)} broken) re-wrapped with the current prompt_v3 and Checker reports regenerated by old-vs-new diff (removed {AS['stats'].get('jank_report_lines_removed',0)}, added {AS['stats'].get('jank_report_lines_added',0)}); rows_tierB and rows_extra are not used.", "",
      "## 6. Per bug kind (blocker findings in broken rows)", "| kind | rows | findings | share with file+line |", "|---|--:|--:|--:|"]
for k, v in sorted(K.items(), key=lambda x: -len(x[1]["rows"])): g.append(f"| {k} | {len(v['rows'])} | {v['f']} | {v['fl']/v['f']:.1%} |")
g += ["", f"File+line share over all blocker findings: {sum(v['fl'] for v in K.values())}/{sum(v['f'] for v in K.values())}.", "", "## 7. Val set", f"{len(va)} rows from {len({repo_of(r) for r in va})} repos, repo-disjoint from train. Broken val findings per kind (total available in parentheses; target >= 3 where >= 6 exist):", "", "| kind | val | all |", "|---|--:|--:|"]
for k, n in kt.most_common(): g.append(f"| {k} | {kv.get(k,0)} | {n} |")
g += ["", f"Kinds with fewer than 3 val findings although >= 6 exist: {[k for k,n in kt.items() if n>=6 and kv.get(k,0)<3]}.", "", "## 8. Token lengths", f"`{dict(min=tok[0], p50=q(.5), p90=q(.9), p99=q(.99), max=tok[-1], over_32000=sum(t>32000 for t in tok))}` (cap 32000).", "",
      "## 9. Leakage + dedupe (recomputed on the written files)", "```", json.dumps(leakage, indent=1), "```", "INFO_incidental = a Dell-key id string occurs in another plugin's text; manifest id, repo and tree do not match.", "",
      "## 10. Assembly stats", f"`{json.dumps(AS['stats'])}`", f"drops: `{json.dumps(AS['drops'])}`", "", "## 11. Samples", "See SAMPLES.md.", "", "## 12. Remaining weaknesses", open(os.path.join(H, "weaknesses_r4.md")).read() if os.path.exists(os.path.join(H, "weaknesses_r4.md")) else ""]
open(f"{D}/GATE_REPORT.md", "w").write("\n".join(g))
json.dump(dict(counts=dict(train=len(tr), val=len(va), broken=nb, approve=len(allr) - nb), source_mix=dict(src), broken_source_mix=dict(bsrc), approve_share=dict(train=share(tr), val=share(va), all=share(allr)), mech=dict(mech), mech_pass=ok(mech) / max(1, chk(mech)), qwen_recheck=dict(exact=eq, n=nq), gptoss_recheck=dict(exact=eg, n=nq),
               spot=dict(agree=HS["stats"]["spot_check_agree"], n=HS["stats"]["spot_check_n"], rate=HS["spot_agreement"]), leakage=leakage, samples=dict(S_ok), license_mix=dict(lic), exact_class=dict(cls), tokens=dict(p50=q(.5), max=tok[-1]), unbounded_only=ub, per_kind={k: dict(rows=len(v["rows"]), findings=v["f"], file_line=v["fl"]) for k, v in K.items()}, val_kind_counts=dict(kv)), open(f"{D}/report.json", "w"), indent=1)
print(json.dumps(json.load(open(f"{D}/report.json")), indent=1)[:3500])
