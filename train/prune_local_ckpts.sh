#!/usr/bin/env bash
# Box-side disk guard for an overnight run: launch_vast.sh sync keeps EVERY checkpoint it ever copied (~1-1.5 GB each; checkpoint every 14 steps = 15-30 of them),
# and the box has ~18 GB free. Keep the newest KEEP (4) local checkpoints (the instance itself keeps 3, so `down`'s sha256 re-check still covers every file it lists)
# plus best/ last/ untouched; delete older intermediates only while the run is syncing. Usage: nohup bash prune_local_ckpts.sh <instance_id> &
I=${1:?instance id}; KEEP=${KEEP:-4}; MIN_FREE_G=${MIN_FREE_G:-12}; D=${USUBA_RUNS:-/workspace/usuba-runs}/$I/train/$(sed -n 's/^output_dir:[[:space:]]*\([^ #]*\).*/\1/p' "$(dirname "$0")/config.yaml")/checkpoints
while pgrep -f 'launch_vast.sh watch' >/dev/null; do
  free=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "$free" -lt "$MIN_FREE_G" ] && [ -d "$D" ]; then for s in $(ls -1 "$D" | grep -E '^step-[0-9]+$' | sort | head -n -$KEEP); do rm -rf "$D/$s"; echo "$(date) pruned $s (free ${free}G)"; done; fi
  sleep 300
done
