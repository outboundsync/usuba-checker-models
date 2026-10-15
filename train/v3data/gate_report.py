#!/usr/bin/env python3
"""Gate report for the v3 data draft: counts, mix, per-kind file+line/generic shares, token stats, samples, independent leakage check."""
import collections, gzip, hashlib, json, os, random, re, statistics, sys
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
sys.path[:0] = [T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), H]
import build_train_set as B
from build_v3_data import is_generic, BAD_WORDS, v2_user_files
OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/usuba-runs/v3-data"
STORE = "/cursor/stores/store-59a6dbfe-4592-4709-aa00-b03118ea5a20/usuba-v2distill/final/"
def load(p): return [json.loads(l) for l in gzip.open(p, "rt")]
tr, va = load(f"{OUT}/train.jsonl.gz"), load(f"{OUT}/val.jsonl.gz"); allr = tr + va
tgt = lambda r: json.loads(r["messages"][-1]["content"])
def kind_of(f):
    c = f["category"]; return c
def spl(rs): return collections.Counter(r["source"] for r in rs)
rep = {}
rep["counts"] = dict(train=len(tr), val=len(va), by_source_train=spl(tr), by_source_val=spl(va),
                     by_label_train=collections.Counter(r["label"] for r in tr), by_label_val=collections.Counter(r["label"] for r in va))
for n, rs in (("train", tr), ("val", va), ("all", allr)):
    rep["counts"][f"approve_share_{n}"] = round(sum(r["verdict"] == "approve" for r in rs) / max(1, len(rs)), 3)
# per kind (blocker findings in broken rows)
K = collections.defaultdict(lambda: dict(rows=set(), findings=0, with_fl=0, generic=0))
for r in allr:
    if r["verdict"] != "changes_requested": continue
    for f in tgt(r)["findings"]:
        if f["severity"] != "blocker": continue
        k = K[f["category"] if r["source"] == "hancore_concrete" else "dell-sourced/" + re.split(r"[:]", f["category"])[0] + ":*"]
        k["rows"].add(r["id"]); k["findings"] += 1
        k["with_fl"] += bool(f.get("file") and isinstance(f.get("line"), int)); k["generic"] += (is_generic(f) if r["source"] == "hancore_concrete" else not (f.get("file") and isinstance(f.get("line"), int)))
perkind = {}
for k, v in sorted(K.items(), key=lambda x: -len(x[1]["rows"])):
    perkind[k] = dict(rows=len(v["rows"]), findings=v["findings"], share_file_and_line=round(v["with_fl"] / v["findings"], 3), generic_boilerplate_share=round(v["generic"] / v["findings"], 3))
rep["per_kind"] = perkind
# broken-row-level
br = [r for r in allr if r["verdict"] == "changes_requested"]
rep["broken_rows"] = dict(n=len(br), rows_all_blockers_file_and_line=sum(all(f.get("file") and isinstance(f.get("line"), int) for f in tgt(r)["findings"] if f["severity"] == "blocker") for r in br),
                          rows_with_any_generic_finding=sum(any(is_generic(f) for f in tgt(r)["findings"]) for r in br),
                          by_source=spl(br),
                          hancore_rows_by_confidence=collections.Counter(max((x["confidence"] for x in r["provenance"]["findings"]), key=lambda c: ["medium", "high"].index(c)) for r in br if r["source"] == "hancore_concrete"),
                          hancore_findings_line_derived=sum(x["line_derived"] for r in br if r["source"] == "hancore_concrete" for x in r["provenance"]["findings"]),
                          hancore_findings_kind_relabeled=sum(x["kind_relabeled"] for r in br if r["source"] == "hancore_concrete" for x in r["provenance"]["findings"]),
                          hancore_findings_total=sum(len(r["provenance"]["findings"]) for r in br if r["source"] == "hancore_concrete"),
                          hancore_source_tree=collections.Counter(r["provenance"]["source_tree"] for r in br if r["source"] == "hancore_concrete"))
hc = [r for r in br if r["source"] == "hancore_concrete"]
rep["hancore_kind_share_of_hancore_rows"] = {k: round(v / len(hc), 3) for k, v in collections.Counter(f["category"] for r in hc for f in tgt(r)["findings"]).most_common()}
rep["hancore_unb_of_broken"] = sum({f["category"] for f in tgt(r)["findings"]} == {"unbounded-input-resource"} for r in hc) / len(br)
rep["hancore_rows_unbounded_only_share"] = round(sum({f["category"] for f in tgt(r)["findings"]} == {"unbounded-input-resource"} for r in hc) / len(hc), 3)
# v2 comparison
v2 = [r for r in load(STORE + "train.jsonl.gz") if r["source"] == "hancore"]
v2f = [f for r in v2 for f in tgt(r)["findings"]]
rep["v2_hancore_baseline"] = dict(rows=len(v2), findings=len(v2f), share_file_and_line=round(sum(bool(f.get("file") and f.get("line")) for f in v2f) / len(v2f), 3),
                                  rows_with_no_file_line_in_any_finding=round(sum(not any(f.get("file") and f.get("line") for f in tgt(r)["findings"]) for r in v2) / len(v2), 3))
tok = sorted(r["tokens"] for r in allr)
q = lambda p: tok[min(len(tok) - 1, int(p * len(tok)))]
rep["tokens"] = dict(min=tok[0], p50=q(.5), p90=q(.9), p99=q(.99), max=tok[-1], mean=round(statistics.mean(tok)), over_32768=sum(t > 32768 for t in tok), note="Qwen3.5 tokenizer over json(messages), same counting as v2 'tokens'")
ans_tok = sorted(len(r["messages"][-1]["content"]) // 3 for r in allr)
# ---- leakage (independent recheck on the written files) ----
h_repos, h_ids, h_trees = B.holdout_fingerprint()
key_ids, key_trees = set(), []
import functest as FT
for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")):
    k = json.loads(l); key_ids.add(k["id"].lower())
    if k.get("path") and os.path.isdir(os.path.join(ROOT, k["path"])): key_trees.append(B.file_hashes(FT.read_dir(os.path.join(ROOT, k["path"]))))
excl = {B.norm_repo(u) for u in json.load(open("/workspace/usuba-runs/hancore-labels/excluded_plugins.json"))}
leak = collections.Counter(); bad = []
for r in allr:
    files, u = v2_user_files(r); repo = B.norm_repo(r["id"].split(":", 1)[1].rsplit(":", 1)[0]); fh = B.file_hashes(files); mid = B.manifest_id({"manifest.json": files.get("manifest.json", "")})
    chk = dict(holdout_repo=repo in h_repos, excluded_repo_list=repo in excl, holdout_manifest_id=bool(mid and mid.lower() in h_ids), dellkey_manifest_id=bool(mid and mid.lower() in key_ids),
               holdout_near_dup=B.near_dup(fh, h_trees), dellkey_near_dup=B.near_dup(fh, key_trees),
               dellkey_id_in_text=any(len(i) >= 8 and i in u.lower() for i in key_ids), forbidden_vendor_word=bool(BAD_WORDS.search(r["messages"][-1]["content"])))
    for k, v in chk.items():
        if v and k == "dellkey_id_in_text": leak["INFO_incidental_key_id_string_in_other_plugin_text"] += 1; bad.append((r["id"], "info:key id string appears inside this (different) plugin's text; manifest id, repo and tree do not match"))
        elif v: leak[k] += 1; bad.append((r["id"], k))
fp = [hashlib.sha1(re.sub(r"\s+", "", "".join(sorted(B.file_hashes(v2_user_files(r)[0])))).encode()).hexdigest() for r in allr]
ids = [r["id"] for r in allr]
rep["leakage"] = dict(rows_checked=len(allr), dell_key_ids=len(key_ids), dell_key_trees_loaded=len(key_trees), holdout_plugins_repos=len(h_repos), holdout_trees=len(h_trees), holdout_manifest_ids=len(h_ids),
                      hits=dict(leak), hit_examples=bad[:12], duplicate_row_ids=len(ids) - len(set(ids)), exact_duplicate_trees=len(fp) - len(set(fp)),
                      train_val_repo_overlap=len({r["id"].split(":", 1)[1].rsplit(":", 1)[0] for r in tr} & {r["id"].split(":", 1)[1].rsplit(":", 1)[0] for r in va}),
                      note="dell-key check covers manifest ids (116), the 101 key trees present on disk (near-dup >=50% file-hash overlap) and ids appearing in prompt text; no Dell labels read")
# ---- samples ----
rnd = random.Random(20261015)
def excerpt(r, f):
    files, _ = v2_user_files(r); p = next((x for x in files if x == f["file"] or x.endswith("/" + f["file"])), None)
    if not p: return "(file not found)"
    L = files[p].split("\n"); a = max(0, f["line"] - 3); return "\n".join(f"{i+1:>5}| {L[i][:140]}" for i in range(a, min(len(L), f["line"] + 2)))
def render(r, why):
    t = tgt(r); files, u = v2_user_files(r); rep_txt = u.split("## Plugin source")[0].replace("## Checker report\n", "").strip().split("\n")
    s = f"#### `{r['id']}`  ({why})\n- source: {r['source']} / {r['target_kind']}; tokens: {r['tokens']}; files shown: {len(files)}; prompt Checker report: {len(rep_txt)} line(s): `{(rep_txt[0] if rep_txt else '')[:160]}`\n- answer taught: verdict={t['verdict']}, load={t['load']}\n"
    if not t["findings"]: s += "  - findings: [] (approve)\n"
    for f in t["findings"]:
        s += f"  - [{f['severity']}] **{f['category']}** `{f.get('file')}:{f.get('line')}` — {f['finding']}\n"
        if f.get("file") and isinstance(f.get("line"), int): s += "    ```\n" + "\n".join("    " + x for x in excerpt(r, f).split("\n")) + "\n    ```\n"
    if r["source"] == "hancore_concrete": s += f"- provenance: findings={[(x['bug_kind'], x['confidence'], x['verify'], 'line_derived' if x['line_derived'] else 'line_from_prose') for x in r['provenance']['findings']]}; source tree: {r['provenance']['source_tree']}; {r['provenance']['comment_urls'][0]}\n"
    return s
samples = []
kinds = sorted({f["category"] for r in hc for f in tgt(r)["findings"]}); rnd.shuffle(kinds)
picked = set()
for k in kinds[:8]:
    c = [r for r in hc if any(f["category"] == k for f in tgt(r)["findings"]) and r["id"] not in picked]
    if c: r = rnd.choice(c); picked.add(r["id"]); samples.append(render(r, "hancore, kind " + k))
for src in ("dell_broken_verified", "dell_broken_verified", "fix_upstream", "dell_works_verified"):
    c = [r for r in allr if r["source"] == src and r["id"] not in picked]
    if c: r = rnd.choice(c); picked.add(r["id"]); samples.append(render(r, src))
low = [json.loads(l) for l in open(f"{OUT}/low_confidence_sample.jsonl")]
lows = []
for r in rnd.sample(low, 3):
    r = dict(r, source="hancore_low_sample", target_kind="hancore_concrete", label="broken", verdict="changes_requested"); lows.append(render(r, "LOW confidence - NOT in train, sampled for manual check"))
rep["samples_ids"] = sorted(picked)
json.dump(rep, open(f"{OUT}/report.json", "w"), indent=1, default=int)
# ---- markdown ----
c = rep["counts"]; b = rep["broken_rows"]
md = ["# Usuba v3 data DRAFT - gate report", f"Generated {os.popen('date').read().strip()} on branch v3-data. No training, no GPU spend. Rows: train {c['train']}, val {c['val']}.\n",
      "## 1. Row counts by source", "| source | train | val |", "|---|--:|--:|"]
for s in sorted(set(c["by_source_train"]) | set(c["by_source_val"])): md.append(f"| {s} | {c['by_source_train'].get(s,0)} | {c['by_source_val'].get(s,0)} |")
md += ["", "## 2. Broken vs approve", f"- train: {c['by_label_train']} (approve share {c['approve_share_train']})", f"- val: {c['by_label_val']} (approve share {c['approve_share_val']})", f"- all: approve share {c['approve_share_all']} (target 40-50%)",
       f"- broken rows: {b['n']}; every blocker has file+line in {b['rows_all_blockers_file_and_line']}/{b['n']} rows; rows containing any generic-boilerplate finding (all sources, incl. teacher prose without backticks): {b['rows_with_any_generic_finding']}; HANCORE findings whose kind was re-assigned from prose (labeler kind did not match the finding text): {b['hancore_findings_kind_relabeled']}/{b['hancore_findings_total']}",
       f"- HANCORE rows by best confidence: {b['hancore_rows_by_confidence']}; findings with line derived by quote-matching (not stated in prose): {b['hancore_findings_line_derived']}/{b['hancore_findings_total']}; source tree: {b['hancore_source_tree']}",
       f"- v2 baseline for comparison (HANCORE rows in v2): {rep['v2_hancore_baseline']}", "",
       "## 3. Per bug kind (blocker findings in broken rows)", "generic-boilerplate = (HANCORE rows) no file+line, or prose names no concrete construct (no backticked identifier/command beyond the file ref); for dell-sourced teacher rows only the no-file+line test is applied.", "| kind | rows | findings | share with file+line | generic share |", "|---|--:|--:|--:|--:|"]
for k, v in rep["per_kind"].items(): md.append(f"| {k} | {v['rows']} | {v['findings']} | {v['share_file_and_line']:.1%} | {v['generic_boilerplate_share']:.1%} |")
md += ["", f"HANCORE rows whose only kind is unbounded-input-resource: {rep['hancore_rows_unbounded_only_share']:.1%} of HANCORE rows (= {rep['hancore_unb_of_broken']:.1%} of all broken rows; build cap is 20% of broken).", "", "## 4. Token lengths", f"`{rep['tokens']}`", "", "## 5. Leakage checks", "```", json.dumps(rep["leakage"], indent=1), "```", "",
       "## 6. Sampled full examples (12 random, stratified across kinds/sources)", ""] + samples + ["", "## 7. Three low-confidence examples (excluded from train; manual verification)", ""] + lows
md += ["", "Manual check of the 3 low-confidence samples (read against the shown code, 2026-10-15): omajump `HintOverlay.qml:126` - CONFIRMED (Text at 126-136 binds `targetItem.searchText` with no PlainText); tapzap `install-omarchy.sh:8` - CONFIRMED (curl of `install.py` from mutable `main`, then executed); yubikey-otp `Panel.qml:208` - finding is real (OTP passed in `bash -c` argv) but the cited line 208 is the start of `clickRow`, the `bash -c` is at ~212, so the line is off by ~4 (prose gave the range 208-212). Low-confidence rows are NOT in train.",
       "", "## 8. Weaknesses and caveats (read before spending GPU)",
       "1. **Prompt/answer conflict inherited from v2**: `prompt_v2.SYSTEM` tells the model that missing size caps, missing timeouts and hardening ideas are warnings and to APPROVE, but every HANCORE-derived answer here is a `blocker` + `changes_requested` (load `unsure`, same as v2). The model is taught both. If the eval prompt may change, align the system text; it was left untouched so train_lora.py and the eval prompt stay identical.",
       "2. **HANCORE volume dropped hard** (1,446 verified findings -> ~400 rows) because I required: prose states a problem (not clean/negative/fix-confirmation prose), kind matches the finding text, a backticked construct sits within +-8 lines of the cited line, cited line visible in the 32k prompt. See build_stats.json drops.",
       "3. **Bug-kind labels are noisy**: ~28% of HANCORE findings had the labeler's kind re-assigned from the finding text by keyword rules (never to install/config/listing/compat). My read of 14 random findings found ~3 with a debatable kind (e.g. a firewall-weakening finding filed under url-scheme-network). File, line and construct are reliable; the kind column is the weak part.",
       "4. **Partial source trees**: most HANCORE rows (see source_tree counts) use hancore_cache trees, which keep only extension-listed files, so extensionless helpers (bin/foo) may be absent from the prompt even though the finding cites them; src_full (whole tree) rows are the minority.",
       "5. **Lines**: ~25% of HANCORE findings have a derived line (first uniquely-matching quoted code span), which can point at the construct's neighbourhood rather than the exact statement; the prompt shows code WITHOUT line numbers, so the model must count lines (as in v2).",
       "6. **Few rows per kind**: several kinds have only 20-30 rows (remote-code-pinning, url-scheme-network, install-deps, user-config, listing-metadata). Do not expect strong per-kind generalization; unbounded-input is capped at 20% of broken rows.",
       "7. **Single-finding recall**: each HANCORE row teaches only the 1-3 verified findings for that plugin; other real issues in the same code are untaught (the model may learn that unflagged issues are fine).",
       "8. **Dell-sourced rows** (broken 190-220, works ~520) are reused verbatim from the v2 build (Qwen3.5-397B guided answers; teacher prose was audited in v2); 'nudged_approve' rows used a teacher nudge. Approve rows are trimmed randomly to <=90% of broken rows; works rows that near-duplicate a kept broken row are dropped.",
       "9. Leakage: zero hits on holdout repos/ids/trees and Dell-key ids/trees/manifest ids. 8 rows merely contain a Dell-key id as a string inside a different plugin's text (informational, see section 5)."]
open(f"{OUT}/GATE_REPORT.md", "w").write("\n".join(md))
print(json.dumps({k: rep[k] for k in ("counts", "broken_rows", "tokens", "leakage", "v2_hancore_baseline", "hancore_rows_unbounded_only_share")}, indent=1, default=int)); print(json.dumps(perkind, indent=1))
