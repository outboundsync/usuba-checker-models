#!/usr/bin/env bash
# B0 baseline for the r7 comparison: STOCK Qwen3.5-9B (open weights, OpenRouter) through the SAME scope prompt v4 (few-shot + schema in the system prompt),
# the SAME output schema validator and the SAME quote post-filter as the Checker model. API only, no GPU. NOT run automatically.
#   OPENROUTER_API_KEY=... bash scope/run_b0_r7.sh [TAG=b0r7]
# Spend: previous B0 runs cost $0.07 (dell) + $0.19 (s4) + $0.88 (holdout) = $1.14; per-run cap below, global cap $5 in $USUBA_RUNS/scope-v4/spend.json.
# Resumable: run_b0 caches per-plugin results (rerun the same command). Results: $USUBA_RUNS/scope-v4/b0/<TAG>-*.summary.json (aggregates only).
set -euo pipefail
cd "$(dirname "$0")/.."; TAG=${1:-b0r7}
[ -n "${OPENROUTER_API_KEY:-}" ] || { echo "no OPENROUTER_API_KEY"; exit 2; }
export USUBA_CHECKER_ROOT=${USUBA_CHECKER_ROOT:-/workspace/uc/usuba-checker-scripts}
for s in dell s4 holdout; do
  case $s in dell) cap=0.30;; s4) cap=0.50;; holdout) cap=1.20;; esac
  python3 -m scope.run_b0 --set $s --name $TAG-$s --max-cost $cap --max-tokens 3000 --workers 6
done
echo "B0 done: $USUBA_RUNS/scope-v4/b0/$TAG-*.summary.json (compare with the Checker model's run through the SAME harness: --model <endpoint> --name r7-<set>)"
