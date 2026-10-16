#!/bin/bash
# waits for the armed final merge, then writes the tradeoff table over ALL candidate rows (no caps) -> final_tradeoff.md
V=/workspace/usuba-runs/v3-data-r7; S=$V/STATUS.md
exec 8>/workspace/r6/r7_tradeoff.lock; flock -n 8 || exit 0
while ! grep -q "^- FINAL merge+report done" $S; do
  grep -q "^- FINAL stopped\|^- FINAL blocked" $S && ! pgrep -f r7_final_armed >/dev/null && { echo "- TRADEOFF skipped $(date +%H:%M): final build stopped/blocked" >> $S; exit 1; }
  sleep 180; done
cd /workspace/usuba-runs/audit-fixes-B/usuba-checker-models/train/v3data
export R6S_FLOOR=0 USUBA_CHECKER_ROOT=/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts PYTHONPATH=/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts/functest:/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts/hancore:/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts
python3 r7_tradeoff.py $V/final_tradeoff.md $V/scope_r6 $V/security_w $V/shards40/s* > $V/final_tradeoff.log 2>&1 && echo "- TRADEOFF done $(date +%H:%M): $V/final_tradeoff.md" >> $S || echo "- TRADEOFF FAILED, see final_tradeoff.log" >> $S
