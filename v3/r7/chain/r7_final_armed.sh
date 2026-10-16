#!/bin/bash
# Armed by r7 watch 2026-10-15 20:02. Waits for the CURRENT mining run (run_r7_scale.sh pid 3780658) to exit and
# write a NEW "mine scale finished" line (the 19:22 line is stale), then moves the partial pre-mining shards40 aside
# (mv, never delete), rebuilds all 40 shards, and merges ONLY if all 40 shards have DONE. Otherwise records a block.
V=/workspace/usuba-runs/v3-data-r7; S=$V/STATUS.md
exec 9>/workspace/r6/r7_final.lock; flock -n 9 || { echo "another r7_final_armed holds the lock"; exit 0; }
while kill -0 3780658 2>/dev/null; do sleep 120; done
[ "$(grep -c '^- mine scale finished' $S)" -ge 2 ] || { echo "- FINAL blocked $(date +%H:%M): mining wrapper exited without a new 'mine scale finished' line; not building" >> $S; exit 1; }
if [ -d $V/shards40 ] && [ ! -f $V/shards40/.post_mining ]; then
  mv $V/shards40 $V/shards40_partial_pre_mining_1953
  for d in /workspace/r6/r7w_40_*; do [ -d "$d" ] && mv "$d" "/workspace/r6/partial_pre_mining_$(basename $d)"; done
fi
mkdir -p $V/shards40; touch $V/shards40/.post_mining
echo "- FINAL armed run: mining done, partial shards moved to shards40_partial_pre_mining_1953, rebuilding 40 shards $(date +%H:%M)" >> $S
N=40
for i in $(seq 0 $((N-1))); do [ -f $V/shards40/s$i/DONE ] && continue
  bash /workspace/r6/run_r7_units.sh $V/scale $i $N 2>&1 | tail -1
  [ -f $V/shards40/s$i/DONE ] || { echo "- FINAL stopped $(date +%H:%M): shard $i failed (see /workspace/r6/r7w_40_$i/*.log); nothing merged; rerun r7_final_armed.sh to resume" >> $S; exit 1; }
done
miss=""; for i in $(seq 0 $((N-1))); do [ -f $V/shards40/s$i/DONE ] || miss="$miss $i"; done
[ -z "$miss" ] || { echo "- FINAL blocked $(date +%H:%M): shards not built:$miss (no merge; fix and rerun /workspace/r6/r7_final_armed.sh, it resumes)" >> $S; exit 1; }
sed -e '/^while ! grep -q "mine scale finished"/d' -e '/^for i in \$(seq 0/,/^done$/d' -e '/^N=40$/d' /workspace/r6/r7_final.sh > /workspace/r6/r7_final_merge_only.sh
bash /workspace/r6/r7_final_merge_only.sh
