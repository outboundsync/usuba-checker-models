#!/usr/bin/env python3
"""r3 finalize: assemble output -> OUTDIR with after-vote, merged build_stats, GATE_REPORT/SAMPLES (report_r3.py), COST.md, SHA256SUMS. usage: finalize_r3.py ASMDIR OUTDIR"""
import sys, os, json, gzip, shutil, subprocess, hashlib
H = os.path.dirname(os.path.abspath(__file__)); A, D = sys.argv[1], sys.argv[2]; os.makedirs(D, exist_ok=True)
OUTD = os.environ.get("R_OUT", "/workspace/r3/out"); WORK = os.environ.get("R_WORK", "/workspace/r3/work")
for f in ("train.jsonl.gz", "val.jsonl.gz", "assemble_stats.json", "checker_report_removed_lines.jsonl"): shutil.copy(os.path.join(A, f), D)
for f in ("r3_anchor_log.jsonl", "r3_dell_audit_log.jsonl", "r3_kind_log.jsonl"): shutil.copy(os.path.join("/workspace/r3/refined", f), D)
rf = []
for sp in ("train", "val"):
    for l in gzip.open(os.path.join(D, sp + ".jsonl.gz"), "rt"):
        r = json.loads(l)
        if r["source"] != "hancore_concrete": continue
        for i, f in enumerate(json.loads(r["messages"][-1]["content"])["findings"]): rf.append([r["id"], i, f["category"], f["finding"]])
json.dump(rf, open(os.path.join(OUTD, "refined_findings.json"), "w"))
subprocess.check_call([sys.executable, os.path.join(H, "classify_kinds.py"), "after"])
rs = json.load(open("/workspace/r3/refined/build_stats.json")); asm = json.load(open(os.path.join(A, "assemble_stats.json")))
drops = dict(rs["drops"]); drops.update({"cap:" + k: v for k, v in asm["stats"].items() if k.startswith(("cap", "train_rows"))})
json.dump(dict(stats=dict(rs["stats"], **{k: v for k, v in asm["stats"].items() if not k.startswith(("cap", "train_rows"))}), drops=drops), open(os.path.join(D, "build_stats.json"), "w"), indent=1)
os.makedirs(os.path.join(D, "audit"), exist_ok=True)
for f in ("dell_audit.json", "kind_votes_before.json", "kind_votes_after.json"): shutil.copy(os.path.join(OUTD, f), os.path.join(D, "audit", f))
subprocess.check_call([sys.executable, os.path.join(H, "report_r3.py"), D])
try: usd = json.load(open(os.path.join(WORK, "ledger.json")))["usd"]
except Exception: usd = None
open(os.path.join(D, "COST.md"), "w").write("# Open-model cost (OpenRouter usage.cost; model qwen/qwen3.5-397b-a17b, open weights; reasoning effort none; data_collection=deny)\n"
    f"Ledger of the run that produced this build (r2 + r3 stages, cumulative): ${usd if usd is not None else 'n/a (offline replay from r3_cache; no API call made)'} (cap 9 USD enforced in r2_helpers/llm.py, task budget < 10 USD).\n"
    "Stages: Dell finding audit, HANCORE kind votes (before 3x, after 3x), exact-line + defect-stated verification, independent re-check ('lineverify_final'), recovered-finding rows. No Anthropic / DeepSeek / Sonnet / proprietary model. API key read from the environment only, never printed or written.\n")
with open(os.path.join(D, "SHA256SUMS"), "w") as o:
    for f in sorted(os.listdir(D)):
        p = os.path.join(D, f)
        if os.path.isfile(p) and f != "SHA256SUMS": o.write(hashlib.sha256(open(p, "rb").read()).hexdigest() + "  " + f + "\n")
print("done", D)
