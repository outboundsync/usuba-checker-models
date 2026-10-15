#!/usr/bin/env bash
# Reproduce usuba v3-data-r4 (on top of v3-data-r3). No training, no GPU, no Dell commands. Dell key: ids/paths only (exclusion). hancore_holdout: exclusion fingerprints only.
# Models (open weights, OpenRouter, data_collection=deny): qwen/qwen3.5-397b-a17b (reasoning none, temperature 0; kind votes temperature 0.3 seeds 1700-1702) and openai/gpt-oss-120b (reasoning low; 40-pair spot check + second line re-check).
# Round-2 selection (cost control): all thin-kind pairs (null-guard, missing-dependency, shell-quoting, error-handling, security, api-compat; max 4 per repo) + 180 others, seed 4242 (R4_OTHER_CAP). Thin-kind history rows are kept ~2x as often under the 40% source cap and get weight 2.0.
# Seeds: spot check random.Random(4040); assemble random.Random(2027); samples random.Random(20261015+404). Extra budget cap: R_CAP=5.3 (r2+r3 ledger was 1.42 USD; r4 limit 4 USD).
# Offline replay: every model reply is in r3_cache/llm_cache.jsonl.gz (refreshed at the end of r4) -> no API call, zero cost, same rows.
# Inputs: /workspace/usuba-runs/version-history/data/verified_pairs.jsonl (669 round-1 pairs) + verified_pairs_2.jsonl (2,118 round-2 pairs; 2,787 combined; bare clones in /workspace/vh_repos), /workspace/usuba-runs/jankeesvw-history/rows.jsonl,
#         the r3 pipeline inputs (see reproduce_r3.sh), /workspace/usuba-runs/v3-fixes/{synthetic,winners}_rows.jsonl.
set -euo pipefail
REPO=${REPO:-/workspace/wt-retrain-v2}; cd "$REPO/train/v3data"
export R_WORK=${R_WORK:-/workspace/r2} R_OUT=${R_OUT:-/workspace/r3/out} R_CAP=${R_CAP:-5.3}; W=${W:-/workspace/r4}; OUT=${OUT:-/workspace/usuba-runs/v3-data-r4}
[ -n "${OPENROUTER_API_KEY:-}" ] || export OPENROUTER_API_KEY=unused-offline-replay
mkdir -p "$W/hist" "$OUT"
# 0. r3 pool after report regeneration / prompt_v3 rewrap / v3-fixes drops (run reproduce_r3.sh first so /workspace/r3/refined and rep_*.json exist)
DUMP_FINAL=$W/r3_pool_final.jsonl.gz python3 assemble_r3.py /workspace/r3/refined/pool_refined.jsonl.gz /tmp/asm_r3_tmp
# 1. license filter, exclusions, pre/post source trees, exact-line class
python3 r4_prepare.py "$W"
cp "$W/prepared.jsonl" "$W/hist/"
# 2. finding text + exact-line gate + kind votes + 40-pair spot check (gpt-oss-120b) + approve rows from post-fix versions
python3 build_r4_hist.py "$W/hist"
# 3. jankeesvw rows: gzip, Checker reports old (v3-fixes tree) vs current
gzip -c /workspace/usuba-runs/jankeesvw-history/rows.jsonl > "$W/jank_rows.jsonl.gz"
rm -rf "$W/oldtree_vf"; mkdir -p "$W/oldtree_vf"; git -C "$REPO" archive v3-fixes functest/usuba functest/dell_env functest/static_checks.py train/checker_report.py train/build_reviewer_scrub.py | tar -x -C "$W/oldtree_vf"
python3 dump_reports.py "$W/oldtree_vf" "$W/jank_rows.jsonl.gz" "$W/jank_rep_old.json"; python3 dump_reports.py "$REPO" "$W/jank_rows.jsonl.gz" "$W/jank_rep_new.json"
# 4. merge, dedupe, caps (source<=40%, kind<=20%, unbounded-only<=20% of broken), val (repo-disjoint, >=3 per kind where possible), train
python3 assemble_r4.py "$W" "$W/asm"
# 5. report (re-checks with qwen and gpt-oss), NOTICE, COST, SHA256SUMS
python3 finalize_r4.py "$W" "$W/asm" "$OUT"
