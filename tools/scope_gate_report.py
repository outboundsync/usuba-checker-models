#!/usr/bin/env python3
"""Gate numbers for a scope-v4 build (train/val.jsonl.gz from train/v3data/build_scope.py): row types, rows per added-finding slug, triage decisions, source mix, Dell share,
empty-added share, exact-quote pass rate (re-checked from the prompt text, not from builder state), 12 deterministic samples. usage: scope_gate_report.py DIR > report.md"""
import sys, os, json, gzip, collections, random, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.dirname(HERE), os.path.join(os.path.dirname(HERE), "train")]
from scope import schema as S, postfilter as PF
import holdout_guard as HG


def rows(d):
    out = []
    for sp in ("train", "val"):
        p = os.path.join(d, sp + ".jsonl.gz")
        if os.path.exists(p): out += [json.loads(l) for l in gzip.open(p, "rt")]
    return out


def report(d):
    R = rows(d); n = len(R); L = []; P = lambda s="": L.append(s)
    T = [json.loads(r["messages"][-1]["content"]) for r in R]
    P(f"# Scope-v4 r6 gate report\n\nrows {n} (train {sum(r['split']=='train' for r in R)}, val {sum(r['split']=='val' for r in R)}); prompt `{R[0]['meta']['prompt_id']}` sha {R[0]['meta']['prompt_sha256'][:12]}")
    P("\n## Row types"); c = collections.Counter(r["row_type"] for r in R); P("| type | rows |\n|---|---|"); [P(f"| {k} | {v} |") for k, v in sorted(c.items())]
    P(f"\ntier: verified {sum(not r['meta']['provisional'] for r in R)}, provisional {sum(r['meta']['provisional'] for r in R)}")
    ea = sum(not t["added_findings"] for t in T); P(f"rows with an EMPTY added_findings list: {ea} ({ea/n:.1%}; spec needs >= 50%)")
    P("\n## Rows / findings per added-finding slug (floor 15 across train+val)"); sc = collections.Counter(a["category"] for t in T for a in t["added_findings"]); P("| slug | findings | rows | verdict |\n|---|---|---|---|")
    for s in S.ADDED_CATEGORIES: P(f"| {s} | {sc[s]} | {sum(any(a['category']==s for a in t['added_findings']) for t in T)} | {'kept' if sc[s]>=15 else 'OUT_OF_SCOPE (below 15)'} |")
    bb = collections.Counter(b for r in R for b in r["meta"].get("added_finding_basis", [])); P("\nadded-finding basis (location/attribution): " + json.dumps(dict(bb)))
    P("\n## Triage items"); tri = [x for t in T for x in t["scripts_triage"]]; dc = collections.Counter(x["decision"] for x in tri)
    P(f"items {len(tri)} over {sum(bool(t['scripts_triage']) for t in T)} rows: confirm {dc['confirm']}, dismiss {dc['dismiss']} ({dc['dismiss']/max(1,len(tri)):.1%}; spec target 25-35%, M3 needs real-confirm to dominate)")
    rc = collections.Counter((x["rule"], x["decision"]) for x in tri); P("\n| rule | confirm | dismiss |\n|---|---|---|")
    for rule in sorted({k[0] for k in rc}): P(f"| {rule} | {rc[(rule,'confirm')]} | {rc[(rule,'dismiss')]} |")
    lb = collections.Counter(b for r in R for b in r["meta"]["label_basis"] for _ in range(r["meta"]["label_basis"][b])); P("\ntriage label basis (items): " + json.dumps(dict(lb)))
    P("\n## Approve mix by source"); ap = collections.Counter(); tot = collections.Counter()
    for r, t in zip(R, T): tot[r["source"]] += 1; ap[r["source"]] += t["verdict"] == "approve"
    P("| source | rows | approve | share of rows |\n|---|---|---|---|")
    for s, v in tot.most_common(): P(f"| {s} | {v} | {ap[s]} | {v/n:.1%} |")
    P(f"\napprove total {sum(ap.values())} ({sum(ap.values())/n:.1%})")
    dell = sum(v for s, v in tot.items() if s.startswith("dell") or s == "nudged_approve"); P(f"Dell-sweep-pipeline share (dell_* + nudged): {dell}/{n} = {dell/n:.1%}. Dell-key scores must be reported next to HANCORE-holdout and clean-set scores.")
    P("\n## Exact-quote pass rate (re-checked from the prompt text)"); ok_t = ok_a = line_a = nt = na = 0
    for r, t in zip(R, T):
        files = HG.parse_blob(r["messages"][1]["content"])
        for x in t["scripts_triage"]: nt += 1; ok_t += PF.quote_in_file(x["quote"], files.get(x["file"], ""))
        for a in t["added_findings"]: na += 1; ok_a += PF.quote_in_file(a["quote"], files.get(a["file"], "")); line_a += PF.quote_on_line(a["quote"], files.get(a["file"], ""), a["line"], 2)
    P(f"triage quotes in cited file: {ok_t}/{nt} = {ok_t/max(1,nt):.1%}; added quotes in file: {ok_a}/{na} = {ok_a/max(1,na):.1%}; within 2 lines of the cited line: {line_a}/{na}")
    bad = sum(bool(S.structure_errors(t)) for t in T); P(f"schema structure errors: {bad}")
    P("\n## 12 samples (deterministic)"); rnd = random.Random(12); strata = [[i for i, r in enumerate(R) if r["row_type"] == k] for k in ("extend", "triage", "clean")]; pick = []
    for st_, k in zip(strata, (6, 4, 2)): pick += rnd.sample(st_, min(k, len(st_)))
    for i in pick:
        r, t = R[i], T[i]; P(f"\n### {r['id']}  [{r['row_type']}, {r['meta']['tier']}, {r['source']}]"); P("```json\n" + json.dumps(t, indent=1, ensure_ascii=False)[:2400] + "\n```")
    return "\n".join(L)


if __name__ == "__main__": print(report(sys.argv[1]))
