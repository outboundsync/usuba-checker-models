#!/usr/bin/env python3
"""r4 step 2: version-history pairs -> prompt_v3 rows (broken from the pre-fix tree; minority approve from the post-fix tree).
Models: qwen/qwen3.5-397b-a17b (finding text, kind votes, line gate, post-fix check) and openai/gpt-oss-120b (independent 40-pair spot check); both open weights, via OpenRouter, temperature 0 (votes 0.3 with seeds).
usage: build_r4_hist.py WORKDIR   (needs r4_prepare.py output). Seeds: spot check random.Random(4040); approve selection random.Random(4141)."""
import sys, os, re, json, gzip, random, collections, hashlib
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
W = sys.argv[1]; sys.argv = [sys.argv[0], W]
sys.path[:0] = [os.path.join(H, "r2_helpers"), H, T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), os.path.join(T, "v2", "distill")]
import exactline as X, llm, functest as FT, checker_report as CR
import refine_r3 as R
import build_v3_data as BV
from build_reviewer_scrub import scrub
import train_prompt_loader as _pl
PV3 = _pl.load()
from concurrent.futures import ThreadPoolExecutor
ntok = R.ntok; GPT = "openai/gpt-oss-120b"
BV.CITED_CAP = 48000   # history defects sit deep in large QML files; token cap (32k) still enforced per row
st = collections.Counter(); drops = collections.Counter()
# ---- kind mapping: history kind -> allowed categories of the EXISTING taxonomy (HANCORE 13 kinds + the Dell-style runtime/in-use/qml/load ones used by earlier rows)
KMAP = {
 "wrong-condition-or-logic": ["runtime:logic-error", "in-use:stale-or-wrong-display"],
 "ui-layout-or-state": ["in-use:stale-or-wrong-display", "runtime:logic-error"],
 "api-compat-change": ["runtime-qml-api-compat", "runtime:undefined-method", "runtime:undefined-property"],
 "race-or-timing": ["runtime:state-or-race", "process-lifecycle-timeouts"],
 "security": ["secrets-credentials", "file-safety-symlink-perms", "shell-lua-injection", "rich-text-markup-injection", "url-scheme-network", "privileged-system", "remote-code-pinning", "unbounded-input-resource"],
 "process-or-resource-lifecycle": ["process-lifecycle-timeouts", "unbounded-input-resource", "runtime:state-or-race"],
 "wrong-path-or-command": ["in-use:invalid-command-arg", "runtime:logic-error"],
 "env-or-config-assumption": ["in-use:invalid-command-arg", "runtime:logic-error", "user-config-modification", "install-deps-packaging"],
 "error-handling": ["runtime:error-handling", "runtime:logic-error"],
 "syntax-or-parse-error": ["runtime:logic-error", "runtime:undefined-property", "runtime:undefined-method"],
 "missing-dependency-or-install": ["install-deps-packaging", "in-use:missing-binary", "remote-code-pinning"],
 "shell-quoting-or-expansion": ["shell-lua-injection", "runtime:logic-error"],
 "null-or-missing-guard": ["runtime:undefined-property", "runtime:error-handling"],
}
CATDESC = {**{k: v for k, v in __import__("classify_kinds").KINDS.items()},
 "runtime:logic-error": "wrong condition/branch/value logic that makes the plugin do the wrong thing at runtime",
 "in-use:stale-or-wrong-display": "UI shows stale, wrong or mis-laid-out content or state while the plugin is in use",
 "runtime:state-or-race": "state machine / ordering / timing race that leaves wrong state",
 "runtime:error-handling": "missing or wrong error handling (unhandled failure, swallowed error, bad fallback)",
 "in-use:invalid-command-arg": "a command, path or argument passed to a program is wrong or does not exist",
 "runtime:undefined-method": "calls a method/function that does not exist or has a different signature",
 "runtime:undefined-property": "reads a property/variable that is undefined, null or shadowed",
 "in-use:missing-binary": "needs a program that is not installed on stock Omarchy"}
HARD = {"secrets-credentials", "file-safety-symlink-perms", "shell-lua-injection", "rich-text-markup-injection", "url-scheme-network", "privileged-system", "remote-code-pinning", "unbounded-input-resource", "process-lifecycle-timeouts", "user-config-modification", "install-deps-packaging", "listing-metadata-docs", "runtime-qml-api-compat"}
def load_of(cat): return "unsure" if cat in HARD else "broken"
def cls_vote(txt, allowed, seed):
    ks = list(allowed); random.Random(seed).shuffle(ks)
    u = "KINDS:\n" + "\n".join(f"- {k}: {CATDESC.get(k, k)}" for k in ks) + f"\n\nFINDING:\n{txt}"
    o = llm.call("You classify one code-review finding about an Omarchy/Quickshell plugin into exactly one of the listed bug kinds: the PRIMARY problem it describes. Reply JSON only: {\"kind\": \"<one of the listed kinds>\"}", u, tag=f"r4kind{seed}", temperature=0.3, max_tokens=60, seed=seed)
    k = o.get("kind"); return k if k in allowed else "ERR"
WSYS = """You write one code-review finding about a plugin's source (Omarchy / Quickshell QML, shell, Python, JS). You get numbered source lines around the CITED line ('>' marks it) and a short description of the defect.
Write ONE finding of 1-2 sentences, 120-300 characters, that states the concrete defect in the code AS IT IS NOW and its consequence for the user or system. Rules:
- Quote the offending construct from the cited line in backticks (an identifier, call or expression that literally appears ON the cited line).
- Describe the code, not a change: never mention commits, fixes, patches, 'should be changed to', 'previously', 'the update', reviews or issues.
- No hedging (may/might/possibly); state what happens.
Reply JSON only: {"finding": "..."}"""
def window(lines, L, ctx=8):
    a = max(0, L - 1 - ctx); b = min(len(lines), L + ctx)
    return "\n".join(f"{'>' if i + 1 == L else ' '}{i + 1:5d}| {lines[i][:200]}" for i in range(a, b))
SPOT_SYS = """You independently review one claimed defect in plugin source. You get numbered source lines around the CITED line ('>' marks it), a finding, and the diff of the later change that touched this code.
Answer JSON only: {"defect_real": true|false, "cited_line_exact": true|false, "why": "<one short sentence>"}
defect_real: the finding describes a concrete defect that exists in the shown code. cited_line_exact: the cited line is the exact statement the finding is about."""
APP_SYS = """You check a fixed version of plugin source. You get numbered lines around the area that was just fixed ('>' marks the first changed line) and a description of the defect that was fixed.
Answer JSON only: {"remaining_defect": true|false, "what": "<short>"}
remaining_defect: true if the shown fixed code still contains an obvious functional or security defect near the fixed area (same bug not fully fixed, or a new one introduced); false if the area looks correct."""
def _rep(tree):
    fl = {k: v for k, v in FT.read_dir(tree).items() if k != ".done" and k not in CR.HARNESS_FILES}
    return CR.report(fl)
def err_lines(rep): return [x for x in (rep or []) if not re.match(r"\[[\w-]+ (warn|heuristic/(medium|low))", x)]
def job(p):
    rid = f"{p['repo']}_{p['commit'][:10]}"; res = dict(id=f"version_history:{p['url'].split('github.com/')[-1].lower()}:{p['commit'][:10]}", p=p)
    files = {k: v for k, v in FT.read_dir(p["tree_pre"]).items() if k != ".done" and k not in CR.HARNESS_FILES}
    lines = files[p["file"]].split("\n"); L = p["pre_fix_line"]
    o = llm.call(WSYS, f"DEFECT DESCRIPTION: {p['defect']}\nKIND HINT: {p['bug_kind']}\nFILE: {p['file']}\n{window(lines, L)}", tag="r4write", max_tokens=400)
    txt = R.clean_text(o.get("finding", "")) if isinstance(o, dict) else None
    if not txt or R.HYG.search(txt) or R.HEDGE.search(txt): res["drop"] = "finding_text_unusable"; return res
    if X.check(txt, lines, L, p["file"]) != "strict": res["drop"] = "mechanical_exact_line_failed"; return res
    L2, why = R.accept_line(txt, lines, L, p["file"], True)
    if L2 != L: res["drop"] = "model_gate_" + (why if L2 is None else "moved"); return res
    allowed = KMAP.get(p["bug_kind"])
    if not allowed: res["drop"] = "kind_unmapped"; return res
    votes = [cls_vote(txt, allowed, 1700 + i) for i in range(3)]
    if len(set(votes)) != 1 or votes[0] == "ERR": res["drop"] = "kind_vote_split"; res["votes"] = votes; return res
    res.update(finding=txt, category=votes[0], files=files, lines=lines, votes=votes); return res
def build_row(res, files, rep, verdict_target, rid_suffix, label, prov_extra):
    p = res["p"]; cited = {}
    if verdict_target["findings"]:
        f = verdict_target["findings"][0]; off = sum(len(x) + 1 for x in files[f["file"]].split("\n")[:f["line"] + 25]); cited[f["file"]] = off
    blob, shown = BV.v3_blob(files, cited); blob = scrub(blob)
    if verdict_target["findings"]:
        f = verdict_target["findings"][0]; sh = shown.get(f["file"])
        if sh is None or len(sh.split("\n")) < f["line"] or len(files[f["file"]][:len(sh)].split("\n")) != len(scrub(sh).split("\n")): return None, "cited_line_not_visible"
    msgs = PV3.messages(blob, [scrub(x) for x in rep] if rep is not None else None, verdict_target); tk = ntok(json.dumps(msgs))
    if tk > 32000: return None, "over_32k_tokens"
    prov = dict(kind="version-history-fix" if label == "broken" else "version-history-fixed-version", repo_url=p["url"], repo=p["repo"].replace("__", "/"), commit=p["commit"], parent=p["parent"], date=p["date"], subject=p["subject"],
                file=p["file"], line=p["pre_fix_line"], history_bug_kind=p["bug_kind"], exact_class=p["cls"], license=p["license"], copyright=p["copyright"], judge_confidence=p["confidence"],
                models=dict(finding_kind_gate="qwen/qwen3.5-397b-a17b", spot_check="openai/gpt-oss-120b"), **prov_extra)
    return dict(id=res["id"] + (":broken" if label == "broken" else ":fixed"), split="train", source="version_history", orig_source="version_history", synthetic=False, label=("broken" if label == "broken" else "works"),
                verdict=verdict_target["verdict"], target_kind="version_history_fix" if label == "broken" else "version_history_fixed", reject_reason=None, is_pair_parent=False, pair=None, tokens=tk, provenance=prov, weight=1.0, messages=msgs), None
def main():
    P = [json.loads(l) for l in open(W + "/prepared.jsonl")]
    st["pairs_class_other_excluded"] = sum(p["cls"] == "other" for p in P); P = [p for p in P if p["cls"] != "other"]
    # ---- round-2 selection (cost control, extra budget < 4 USD): every round-1 pair is processed (replayed from cache); round-2 pairs: all thin-kind pairs, plus a seeded sample of the other kinds, at most 4 pairs per repo
    THIN = {"null-or-missing-guard", "missing-dependency-or-install", "shell-quoting-or-expansion", "error-handling", "security", "api-compat-change"}
    r1 = [p for p in P if p.get("round", 1) == 1]; r2 = [p for p in P if p.get("round", 1) == 2]
    rs = random.Random(4242); rs.shuffle(r2); per = collections.Counter(); thin2, oth2 = [], []
    for p in sorted(r2, key=lambda p: (p["bug_kind"] not in THIN, p["cls"] != "exact_removed")):
        if per[p["repo"]] >= int(os.environ.get("R4_PER_REPO", "4")): continue
        per[p["repo"]] += 1; (thin2 if p["bug_kind"] in THIN else oth2).append(p)
    LOGIC = {"wrong-condition-or-logic", "ui-layout-or-state"}
    if os.environ.get("R4_EXTEND"):   # r6 extension: the r4 selection (first 180) is kept so its cached replies replay; then ALL remaining non-logic kinds, plus up to R4_LOGIC_EXTRA of the two dominant logic/layout kinds
        base, rest = oth2[:180], oth2[180:]
        oth2 = base + [p for p in rest if p["bug_kind"] not in LOGIC] + [p for p in rest if p["bug_kind"] in LOGIC][:int(os.environ.get("R4_LOGIC_EXTRA", "150"))]
    else: oth2 = oth2[:int(os.environ.get("R4_OTHER_CAP", "180"))]
    st["round2_candidates"] = len(r2); st["round2_selected_thin"] = len(thin2); st["round2_selected_other"] = len(oth2)
    P = r1 + thin2 + oth2
    if os.environ.get("LIMIT"): P = P[:int(os.environ["LIMIT"])]
    with ThreadPoolExecutor(12) as pool: RS = list(pool.map(job, P))
    good = [r for r in RS if "drop" not in r]
    for r in RS:
        if "drop" in r: drops[r["drop"]] += 1
    st["pairs_prepared"] = len(P); st["pairs_passed_gates"] = len(good)
    # ---- independent spot check: 40 random gated pairs, second open model (gpt-oss-120b)
    rnd = random.Random(4040); spot = rnd.sample(good, min(40, len(good)))
    def spotjob(r):
        p = r["p"]; diff = "\n".join(["- " + x for x in p["removed"]] + ["+ " + x for x in p["added"]])[:1800]
        return llm.call(SPOT_SYS, f"FINDING: {r['finding']}\nFILE: {p['file']} (cited line {p['pre_fix_line']})\n{window(r['lines'], p['pre_fix_line'], 12)}\n\nLATER CHANGE TO THIS CODE:\n{diff}", tag="r4spot", model=GPT, effort="low", max_tokens=1500)
    with ThreadPoolExecutor(8) as pool: SO = list(pool.map(spotjob, spot))
    agree = [bool(o.get("defect_real") is True and o.get("cited_line_exact") is True) for o in SO]
    st["spot_check_n"] = len(spot); st["spot_check_agree"] = sum(agree); failed = {r["id"] for r, a in zip(spot, agree) if not a}
    json.dump([dict(id=r["id"], agree=a, verdict=o) for r, a, o in zip(spot, agree, SO)], open(W + "/spot_check_40.json", "w"), indent=1)
    good = [r for r in good if r["id"] not in failed]; st["spot_failed_dropped"] = len(failed)
    # ---- Checker reports for pre- and post-fix trees in parallel (CPU bound)
    from multiprocessing import Pool
    trees = [r["p"]["tree_pre"] for r in good] + [r["p"]["tree_post"] for r in good if r["p"]["tree_post"]]
    with Pool(8) as mp: REP = dict(zip(trees, mp.map(_rep, trees, chunksize=2)))
    # ---- broken rows
    broken, approve_cands = [], []
    for r in good:
        p = r["p"]; files = r["files"]
        rep = REP[p["tree_pre"]]
        tgt = dict(verdict="changes_requested", load=load_of(r["category"]), findings=[dict(category=r["category"], severity="blocker", file=p["file"], line=p["pre_fix_line"], finding=r["finding"])])
        row, why = build_row(r, files, rep, tgt, "", "broken", dict(finding_votes=r["votes"], exact_class_detail=p["cls"]))
        if row is None: drops["broken_row:" + why] += 1; continue
        broken.append(row)
        # approve candidate from the post-fix version
        if p["tree_post"]:
            pf = {k: v for k, v in FT.read_dir(p["tree_post"]).items() if k != ".done" and k not in CR.HARNESS_FILES}
            if p["file"] in pf:
                prep = REP[p["tree_post"]]
                if prep is None or err_lines(prep): drops["approve:checker_errors_or_unavailable"] += 1; continue
                pl = pf[p["file"]].split("\n"); a0 = (p["added"][0].strip() if p["added"] else "")
                idx = next((i + 1 for i, x in enumerate(pl) if a0 and x.strip() == a0), None) or min(len(pl), p["pre_fix_line"])
                o = llm.call(APP_SYS, f"DEFECT THAT WAS FIXED: {p['defect']}\nFILE: {p['file']}\n{window(pl, idx, 15)}", tag="r4approve", max_tokens=300)
                if o.get("remaining_defect") is False:
                    tg = dict(verdict="approve", load="works", findings=[])
                    arow, why2 = build_row(r, pf, prep, tg, "", "works", dict(approve_check="checker_no_errors+qwen_no_remaining_defect"))
                    if arow: approve_cands.append(arow)
                    else: drops["approve_row:" + why2] += 1
                else: drops["approve:model_remaining_defect"] += 1
    st["broken_rows"] = len(broken); st["approve_candidates"] = len(approve_cands)
    for sp, rs in (("hist_broken", broken), ("hist_approve_candidates", approve_cands)):
        with gzip.open(f"{W}/{sp}.jsonl.gz", "wt") as f:
            for x in rs: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    json.dump(dict(stats=dict(st), drops=dict(drops), by_class=dict(collections.Counter(r["provenance"]["exact_class"] for r in broken)), by_category=dict(collections.Counter(r["target_cat"] if False else json.loads(r["messages"][-1]["content"])["findings"][0]["category"] for r in broken)),
                   spot_agreement=st["spot_check_agree"] / max(1, st["spot_check_n"]), spend_usd=llm.spent()), open(W + "/hist_build_stats.json", "w"), indent=1)
    print(json.dumps(dict(stats=dict(st), drops=dict(drops), spend=llm.spent()), indent=1))
if __name__ == "__main__": main()
