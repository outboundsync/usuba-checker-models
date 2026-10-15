#!/usr/bin/env python3
"""r4 finalize: assembled rows -> OUTDIR with report, NOTICE additions, COST.md, SHA256SUMS. usage: finalize_r4.py WORKDIR ASMDIR OUTDIR"""
import sys, os, json, gzip, shutil, subprocess, hashlib, collections, re
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
W, A, D = sys.argv[1:4]; os.makedirs(D + "/audit", exist_ok=True)
for f in ("train.jsonl.gz", "val.jsonl.gz", "assemble_stats.json"): shutil.copy(os.path.join(A, f), D)
for f in ("prepare_stats.json",): shutil.copy(os.path.join(W, f), D + "/audit")
for f in ("hist_build_stats.json", "spot_check_40.json"): shutil.copy(os.path.join(W, "hist", f), D + "/audit")
rows = [json.loads(l) for sp in ("train", "val") for l in gzip.open(f"{D}/{sp}.jsonl.gz", "rt")]
# ---- NOTICE (repo): one entry per upstream repo/commit used by a version-history row
vh = [r for r in rows if r["source"] == "version_history"]; ent = collections.OrderedDict()
for r in sorted(vh, key=lambda r: r["provenance"]["repo"].lower()):
    p = r["provenance"]; k = (p["repo_url"], p["commit"]); e = ent.setdefault(k, dict(lic=p["license"], cr=p["copyright"], n=0)); e["n"] += 1
marker = "v3-data-r4 additions (2026-10-15)"
lines = [marker, "  - Text sources (QML/JS/shell/Python/JSON/TOML/Markdown; no binaries) from the repositories below at the pre-fix commit's parent and at the fix commit, used in train/v3data rows with source `version_history`; each repository is MIT, Apache-2.0, BSD or ISC and its license text and copyright line are kept in the row provenance (repo_url, commit, parent, license, copyright). GPL, unlicensed and unrecognised-license repositories were excluded. Rows whose license has no copyright line in the repository LICENSE file say so.",
         "    License terms: MIT/BSD/ISC require that the copyright notice and permission notice be retained; Apache-2.0 requires retaining the license, notices and attribution; this NOTICE and the per-row provenance carry them.",
         "    jankeesvw-history rows (source `jankeesvw-history`): MIT, Copyright (c) 2026 Jankees van Woezik, jankeesvw/* repositories listed in usuba-runs/jankeesvw-history/NOTICE (rows_tierB and rows_extra not used)."]
for (url, c), e in ent.items(): lines.append(f"  - {url.replace('https://github.com/', '')} @ {c} — {e['lic']} — {e['cr'] or 'no copyright line in LICENSE'} ({e['n']} rows)")
nt = open(os.path.join(ROOT, "NOTICE")).read()
if marker in nt: nt = nt[:nt.index(marker)].rstrip("\n") + "\n"
open(os.path.join(ROOT, "NOTICE"), "w").write(nt.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n")
subprocess.check_call([sys.executable, os.path.join(H, "report_r4.py"), D, W])
start = float(os.environ.get("R4_START_USD", "1.4194407800000013")); end = json.load(open(os.path.join(os.environ.get("R_WORK", "/workspace/r2"), "ledger.json")))["usd"]
open(D + "/COST.md", "w").write(f"# Open-model cost (OpenRouter usage.cost)\nr4 extra spend: ${end-start:.3f} (ledger {start:.4f} -> {end:.4f}; budget < 4 USD; r2+r3+r4 cumulative ${end:.3f}).\nModels: qwen/qwen3.5-397b-a17b (finding text, 3-vote kind mapping, exact-line gate, post-fix check, line re-check) and openai/gpt-oss-120b (40-pair spot check, second line re-check). Open weights only; reasoning effort none/low; data_collection=deny; API key read from the environment, never printed or written.\n")
with open(D + "/SHA256SUMS", "w") as o:
    for root, ds, fs in os.walk(D):
        for f in sorted(fs):
            p = os.path.join(root, f)
            if f != "SHA256SUMS": o.write(hashlib.sha256(open(p, "rb").read()).hexdigest() + "  " + os.path.relpath(p, D) + "\n")
print("done", D)
