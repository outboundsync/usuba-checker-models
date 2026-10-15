#!/usr/bin/env bash
# Replicates every v3-fixes output from the repo (branch v3-fixes). CPU only; no GPU, no Dell. Needs: python3, pytest, the corpora under /workspace (see docs/V3_FIXES.md "Inputs"),
# OPENROUTER_API_KEY only for step 4 (model qwen/qwen3.5-397b-a17b, temperature 0, cached in retraction_raw.jsonl, total spend < $1). No seeds: everything is deterministic (the 70/30 split is sha1(repo)).
# For --qs-probe: quickshell 0.3.2 and sway on PATH (headless, WLR_BACKENDS=headless).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${OUT:-/workspace/usuba-runs/v3-fixes}; mkdir -p "$OUT"
R2=/workspace/usuba-runs/v3-data-r2
git show v3-prep:functest/static_checks.py > "$OUT/static_checks_before.py"
(cd functest && python3 -m pytest tests -q)                                           # 1. unit tests (48)
python3 hancore/measure_lifecycle.py --out "$OUT"                                      # 2. new rules, design/test split, writes functest/usuba/lifecycle_rules_enabled.json (decision on design only)
python3 hancore/measure_skip_effect.py --out "$OUT"                                    # 3. skip conditions: HC rules before/after on the pool
[ -n "${OPENROUTER_API_KEY:-}" ] && python3 hancore/retraction_check.py --rows $R2/train.jsonl.gz $R2/val.jsonl.gz --out "$OUT"   # 4. date check (model calls, cached)
python3 hancore/audit_lifecycle.py --pool --out "$OUT" --rows $R2/train.jsonl.gz $R2/val.jsonl.gz /workspace/usuba-runs/v3-data/train.jsonl.gz /workspace/usuba-runs/v3-data/val.jsonl.gz /workspace/r3/v3-plus/train.jsonl.gz /workspace/r3/v3-plus/pool.jsonl.gz   # 5. audit
python3 train/v3data/build_v3_fixes_rows.py --out "$OUT" --qs-probe                   # 6. synthetic + winners rows (verified)
sha256sum "$OUT"/* > "$OUT/SHA256SUMS" 2>/dev/null || true
