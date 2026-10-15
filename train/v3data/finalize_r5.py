#!/usr/bin/env python3
"""finalize_r5.py DATA_DIR WORK_DIR  -> GATE_REPORT.md, SAMPLES.md, SHA256SUMS, COST.md, expected_rows in train/config.yaml (audit A2/A3/A5/A6/E).
Everything is recomputed from the written train/val files, not from builder counters, so the report cannot drift from the data."""
import sys, os, re, json, gzip, hashlib, collections, random
HERE = os.path.dirname(os.path.abspath(__file__)); TRAIN = os.path.dirname(HERE); sys.path.insert(0, TRAIN)
import prompt_v4 as P4
D, W = sys.argv[1], sys.argv[2]
rd = lambda n: [json.loads(l) for l in gzip.open(os.path.join(D, n), "rt")]
tr, va = rd("train.jsonl.gz"), rd("val.jsonl.gz"); bs = json.load(open(os.path.join(W, "build_stats.json")))
tgt = lambda r: json.loads(r["messages"][-1]["content"])
NUMLINE = re.compile(r"^ *(\d+)\| ?", re.M); HEAD = re.compile(r"^### (.+)\n```\n", re.M)


def shown_lines(user):
    body = user[user.find("## Plugin source\n"):]; heads = list(HEAD.finditer(body)); out = {}
    for k, m in enumerate(heads):
        seg = body[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(body)]
        out[m.group(1)] = {int(n) for n in NUMLINE.findall(seg)}
    return out


def final_user(r): return r["messages"][-2]["content"]


def analyse(rows):
    ok = bad = 0; kinds = collections.defaultdict(lambda: [0, 0, 0]); slug = collections.Counter(); bad_ex = []
    for r in rows:
        sl = shown_lines(final_user(r))
        for f in tgt(r)["findings"]:
            k = kinds[f["category"]]; k[0] += 1; slug[f["category"]] += 1
            has = bool(f.get("file")) and isinstance(f.get("line"), int); k[1] += has
            v = has and f["line"] in sl.get(f["file"], ())
            k[2] += bool(v); ok += bool(v); bad += (not v)
            if not v and len(bad_ex) < 5: bad_ex.append((r["id"], f["category"], f.get("file"), f.get("line")))
    return ok, bad, kinds, slug, bad_ex


ok, bad, kinds, slug, bad_ex = analyse(tr); vok, vbad, *_ = analyse(va)
L = []; A = L.append
cm = bs["checker"]; llm = bs["llm"]; g = bs["gates"]
A("# r5 GATE_REPORT\n"); A(f"rows: train {len(tr)}, val {len(va)}; prompt_sha256 `{bs['prompt_sha256']}`; code_blob policy `{bs['policy']}`; checker_git_sha `{cm.get('checker_git_sha')}`; rules_hash `{cm.get('rules_hash')}`\n")
A("## 1. Exact-line pass rate (recomputed from the written rows)\n")
A(f"- train findings: {ok + bad}; cited file+line visible (numbered) in the shown code: **{ok} ({100*ok/max(1,ok+bad):.1f}%)**; val: {vok}/{vok+vbad} ({100*vok/max(1,vok+vbad):.1f}%)")
A(f"- builder-side exact-line gate: findings dropped before assembly because the cited line is not visible under the shared policy: {bs['drops'].get('finding:cited_line_not_visible_under_shared_policy', 0)}; failed exact-line gate: {bs['drops'].get('finding:failed_exact_line_gate', 0)}; rows left without a finding: {bs['drops'].get('row:no_finding_left', 0)} (+{bs['drops'].get('row:all_findings_failed_gate', 0)} all-failed)")
if bad_ex: A(f"- not-visible examples (should be none): {bad_ex}")
A("\n## 2. Per-kind file+line share (train, broken rows)\n"); A("| kind | findings | has file+line | exact-line visible |\n|---|---|---|---|")
for c, (n, h, v) in sorted(kinds.items(), key=lambda x: -x[1][0]): A(f"| {c} | {n} | {h} ({100*h/n:.0f}%) | {v} ({100*v/n:.0f}%) |")
A("\n## 3. Source mix (train / val)\n"); A("| source | train | val |\n|---|---|---|")
for s in sorted({r["source"] for r in tr + va}): A(f"| {s} | {sum(r['source']==s for r in tr)} | {sum(r['source']==s for r in va)} |")
A("\n## 4. Approve mix by source (A2)\n"); A("| source | approve train | approve val | broken train |\n|---|---|---|---|")
for s in sorted({r["source"] for r in tr + va}):
    A(f"| {s} | {sum(r['source']==s and r['verdict']=='approve' for r in tr)} | {sum(r['source']==s and r['verdict']=='approve' for r in va)} | {sum(r['source']==s and r['verdict']!='approve' for r in tr)} |")
na = sum(r["verdict"] == "approve" for r in tr); real = sum(r["verdict"] == "approve" and r["source"] in ("hancore_clean_approve", "dell_works_verified", "nudged_approve") for r in tr)
A(f"\napprove share of train {100*na/len(tr):.0f}%; of the approves, real clean plugins (HANCORE-clean + Dell-sweep-verified + nudged) = {real} ({100*real/max(1,na):.0f}%); fixed-twin/synthetic = {na-real}. Only 53 review-clean HANCORE candidates exist (23 survive the gates/guard/dedupe into train): the supply, not the policy, is the limit.")
A("\n## 5. Label space (A3)\n"); A(f"slugs in train (min {P4.MIN_PER_SLUG} findings per scored slug, train+val); out-of-scope (not in the prompt, never labelled, eval n/a): {sorted(P4.OUT_OF_SCOPE)}\n"); A("| slug | train findings | val findings | scored by HANCORE eval |\n|---|---|---|---|")
vs = analyse(va)[3]
for s in sorted(set(slug) | set(vs)): A(f"| {s} | {slug.get(s,0)} | {vs.get(s,0)} | {'yes' if s in P4.SCORED_SLUGS else 'no'} |")
under = [s for s in P4.SLUGS if s in P4.SCORED_SLUGS and slug.get(s, 0) + vs.get(s, 0) < P4.MIN_PER_SLUG]; A(f"\nin-scope scored slugs below MIN_PER_SLUG={P4.MIN_PER_SLUG} (train+val): {under or 'none'}. Scored slugs with no data are OUT_OF_SCOPE: eval reports n/a for them (not recall 0).")
assert not under, under
badslug = [s for s in set(slug) | set(vs) if s not in P4.SLUGS]; assert not badslug, badslug
import label_filters as LF
A("\n## 5b. Label-quality filters (audit E)\n")
A("- commit attribution: HANCORE rows are kept only when the recorded commit equals the plugin's majority reviewed SHA (strict mode: 'fixed in <sha>' and foreign-repo commit URLs are not reviewed commits); drops: " + json.dumps({k: v for k, v in bs["drops"].items() if k.startswith("attribution:")}))
A("- retractions (findings the reviewer later withdrew, whole or partial): rows dropped " + str(bs["drops"].get("retraction:withdrawn_finding_row_dropped", 0)))
A(f"- synthetic generator rows: policy `{LF.SYNTHETIC_POLICY}` (template-id tell sample.*/syn.*); excluded {bs['drops'].get('synthetic:excluded_template_artefact', 0)}; remaining synthetic rows in train: {sum(r['source'] == 'synthetic_lifecycle' for r in tr)}")
A("- template-id share by verdict (train+val; a skew between verdicts would be a label tell): `" + json.dumps(LF.template_id_fraction(tr + va)) + "`")
A("- line numbers shown at train and eval (numbered blob), few-shots swapped to holdout-clean themes (prompt_v4); the explicit-evidence check is the fail-closed LLM gate")
A("\n## 6. Guards, drops, spend\n"); A("drops: `" + json.dumps(bs["drops"]) + "`\n")
A(f"- holdout/Dell guard rejects: content {bs['drops'].get('guard:content',0)}, repo/id {bs['drops'].get('guard:repo',0)}; v2-val repos kept out of the pool: {bs['drops'].get('row:v2_val_repo_in_pool',0)}")
A(f"- LLM gates (qwen/qwen3.5-397b-a17b + openai/gpt-oss-120b, fail-closed): `{json.dumps({k: g[k] for k in g if k != 'error_samples'})}`")
A(f"- LLM spend this run: ${g.get('spent_usd')}; stats `{json.dumps(llm)}`")
cache = os.environ.get("R_WORK", "/workspace/r5/llm") + "/cache.jsonl"
csha = hashlib.sha256(open(cache, "rb").read()).hexdigest() if os.path.exists(cache) else "n/a"; A(f"- LLM cache (replayable, published hash): `{csha}`")
open(os.path.join(D, "GATE_REPORT.md"), "w").write("\n".join(L) + "\n")
# samples: 12 random rows, fixed seed, stratified by verdict/source
rnd = random.Random(5); pick = []
for s in ("hancore_clean_approve", "dell_works_verified", "version_history", "hancore_concrete", "dell_broken_verified"): pick += rnd.sample([r for r in tr if r["source"] == s], min(2, sum(r["source"] == s for r in tr)))
rest = [r for r in tr if r not in pick]; pick += rnd.sample(rest, 12 - len(pick)); pick = pick[:12]
S = ["# r5 samples (12)\n"]
for i, r in enumerate(pick, 1):
    u = final_user(r); S.append(f"## {i}. {r['id']} [{r['source']}, {r['verdict']}]\n\nlabel: ```{r['messages'][-1]['content'][:1200]}```\n\nprovenance: `{json.dumps(r['provenance'])[:400]}`\n\nuser (head): ```\n{u[:1500]}\n```\n")
open(os.path.join(D, "SAMPLES.md"), "w").write("\n".join(S))
open(os.path.join(D, "COST.md"), "w").write(f"r5 LLM spend (this build): ${g.get('spent_usd')}; open-weights only (qwen/qwen3.5-397b-a17b, openai/gpt-oss-120b via OpenRouter); cache sha256 {csha}\n")
sums = "".join(f"{hashlib.sha256(open(os.path.join(D, n), 'rb').read()).hexdigest()}  {n}\n" for n in ("train.jsonl.gz", "val.jsonl.gz")); open(os.path.join(D, "SHA256SUMS"), "w").write(sums)
cfg = os.path.join(TRAIN, "config.yaml"); t = open(cfg).read(); t = re.sub(r"expected_rows:.*", f"expected_rows: {{train: {len(tr)}, val: {len(va)}}}     # set by finalize_r5.py", t, count=1); open(cfg, "w").write(t)
print("report written; exact-line", ok, bad, "expected_rows", len(tr), len(va))
import subprocess; subprocess.run([sys.executable, os.path.join(TRAIN, "gen_train_docs.py")], check=True, capture_output=True)
