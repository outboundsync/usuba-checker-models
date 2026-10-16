#!/usr/bin/env bash
# THE r7 overnight launch (Qwen3.5-9B LoRA, scope-v4, code_blob/v2). NOT run by anyone automatically; Harris approved training once the dataset is final.
#   bash train/launch_r7.sh            # gates only: preflight on final_merged, plan (offers, credit); spends nothing, starts nothing
#   bash train/launch_r7.sh --go       # gates, then rent + start + nohup watch (AUTO_DOWN=1: instance destroyed after the sha256-verified fetch)
# Refuses (exit != 0) unless: final_merged exists with SHA256SUMS, r7_preflight passes (prompt sha, code_blob/v2 parity, schema, guards, drop rate, schedule, hours),
# config.yaml expected_rows matches, and no instance is already recorded. The on-box watchdog only acts when /workspace/usuba/ARMED exists (written by launch_vast.sh start).
set -euo pipefail
cd "$(dirname "$0")"; T=$PWD; RUNS=${USUBA_RUNS:-/workspace/usuba-runs}; export R5_DATA=${R5_DATA:-$RUNS/v3-data-r7/final_merged}
export PATH=${R7_VENV:-/workspace/venv-r7}/bin:$PATH USUBA_CHECKER_ROOT=${USUBA_CHECKER_ROOT:-/workspace/uc/usuba-checker-scripts}
[ -f $T/.vast_instance ] && { echo "REFUSING: instance $(cat $T/.vast_instance) already recorded"; exit 3; }
python3 r7_preflight.py "$R5_DATA" --write-config
python3 train_utils.py verify config.yaml "$R5_DATA"
[ "$(df --output=avail -BG / | tail -1 | tr -dc 0-9)" -ge 12 ] || { echo "REFUSING: box has under 12 GB free (checkpoint sync needs room; prune_local_ckpts.sh keeps it bounded)"; exit 4; }
./launch_vast.sh plan
[ "${1:-}" = --go ] || { echo "gates passed; add --go to rent and start"; exit 0; }
export INSTANCE_MAX_HOURS=${INSTANCE_MAX_HOURS:-10} AUTO_DOWN=1
./launch_vast.sh up --yes --max-dph ${MAX_DPH:-3.6}
I=$(cat $T/.vast_instance); mkdir -p $RUNS/$I
nohup ./launch_vast.sh watch > $RUNS/$I/watch.log 2>&1 &
nohup bash ./prune_local_ckpts.sh $I > $RUNS/$I/prune.log 2>&1 &
echo "launched instance $I; watch log $RUNS/$I/watch.log; verify with: tail $RUNS/$I/watch.log"
