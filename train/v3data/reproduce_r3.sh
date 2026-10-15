#!/usr/bin/env bash
# Reproduce usuba v3-data-r3 from the repo + the local plugin source caches. No training, no GPU, no Dell commands.
# Model: qwen/qwen3.5-397b-a17b via OpenRouter (open weights), reasoning effort "none", provider data_collection=deny. Total spend for r2+r3 stages: see COST.md (<$10 cap enforced in r2_helpers/llm.py).
# Offline/free replay: every model reply is in r3_cache/llm_cache.jsonl.gz (seeded into $R_WORK/cache.jsonl automatically); with the cache present no API call is made.
# Seeds: build_v3_data.py random.Random(1337); refine_r3.py Random(1337); assemble_r3.py Random(2026); kind votes seeds 100..102 (before) / 900..902 (after); sample picker 20261015+77.
# Inputs (read-only): /workspace/usuba-runs/hancore-labels/concrete_findings.jsonl (1446 findings), /workspace/usuba-runs/hancore-labels-r2/recovered.jsonl (319 recovered findings),
#   /workspace/usuba-runs/hancore-labels/excluded_plugins.json, /workspace/hancore_cache + hancore-labels/src_full (plugin trees), v2 store rows (STORE in build_v3_data.py),
#   functest/dell_ground_truth.jsonl (ids/paths only, for exclusion), dell/sweep/results.jsonl, functest/dell_env/*_bins.txt.
set -euo pipefail
REPO=${REPO:-/workspace/wt-retrain-v2}; cd "$REPO/train/v3data"
export R_WORK=${R_WORK:-/workspace/r3/work} R_OUT=${R_OUT:-/workspace/r3/out} R_BASE=${R_BASE:-/workspace/r3/v3-plus/}
OUT=${OUT:-/workspace/usuba-runs/v3-data-r3}; mkdir -p "$R_WORK" "$R_OUT" "$OUT" /workspace/r3
[ -n "${OPENROUTER_API_KEY:-}" ] || export OPENROUTER_API_KEY=unused-offline-replay   # only needed if a prompt is not in the cache
# 1. HANCORE findings = original + recovered; build the v3-style pool (pool.jsonl.gz = every row that passes build gates, no approve trimming)
cat /workspace/usuba-runs/hancore-labels/concrete_findings.jsonl /workspace/usuba-runs/hancore-labels-r2/recovered.jsonl > /workspace/r3/conc_plus.jsonl
DUMP_POOL=1 CONC_FINDINGS=/workspace/r3/conc_plus.jsonl python3 build_v3_data.py --out "${R_BASE%/}"
# 2. kind votes (3 per HANCORE finding) and Dell finding audit
python3 classify_kinds.py before
python3 dell_audit.py
# 3. clean-up, exact-line anchoring, model gate (writes $R_WORK-independent pool_refined.jsonl.gz)
python3 refine_r3.py /workspace/r3/refined
# 3b. Checker reports: r2 tree (what the stored reports came from) vs this repo (FP fixes + v3-fixes lifecycle rules), on the visible files of every pool row
rm -rf /workspace/r3/oldtree; mkdir -p /workspace/r3/oldtree
git -C "$REPO" archive v3-data-r2 functest/usuba functest/dell_env functest/static_checks.py train/checker_report.py train/build_reviewer_scrub.py | tar -x -C /workspace/r3/oldtree
python3 dump_reports.py /workspace/r3/oldtree /workspace/r3/refined/pool_refined.jsonl.gz /workspace/r3/rep_old.json &
python3 dump_reports.py "$REPO" /workspace/r3/refined/pool_refined.jsonl.gz /workspace/r3/rep_new.json; wait
# v3-fixes inputs (branch v3-fixes already merged into v3-data-r3): /workspace/usuba-runs/v3-fixes/{retraction_drop_ids,retraction_review_ids,audit_approve_lifecycle_ids,relabel_broken_to_works_candidates}.txt, synthetic_rows.jsonl, winners_rows.jsonl
# 4. Checker report regeneration (old vs fixed checker), caps, 64-row repo-disjoint val, train
python3 dump_reports_full.py /workspace/r3/refined/pool_refined.jsonl.gz /workspace/r3/rep_full.json
python3 assemble_r3.py /workspace/r3/refined/pool_refined.jsonl.gz /workspace/r3/asm
# 5. after-vote on final findings, report, checksums
python3 finalize_r3.py /workspace/r3/asm "$OUT"
