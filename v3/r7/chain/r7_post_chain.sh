#!/bin/bash
# r7 POST-MERGE CHAIN (tee'd up; does nothing irreversible unless /workspace/r6/r7_post_chain.ARMED exists).
# waits FINAL merge + TRADEOFF done -> SHA256SUMS -> hard checks -> widen eval interval -> launch_r7.sh (gates) -> [ARMED && all pass] launch_r7.sh --go
# Single copy (flock), idempotent, restart-safe (state in $P). Any stop writes $P/REASON.md and $S line "- POSTCHAIN stopped ...". Never deletes data.
V=${R7_V:-/workspace/usuba-runs/v3-data-r7}; S=$V/STATUS.md; P=$V/post_chain; F=$V/final_merged
T=${R7_TRAIN_DIR:-/workspace/wt-r7-train/train}; ARMED=${R7_ARMED:-/workspace/r6/r7_post_chain.ARMED}; mkdir -p $P
exec 7>${R7_LOCK:-/workspace/r6/r7_post_chain.lock}; flock -n 7 || { echo "another r7_post_chain holds the lock"; exit 0; }
say() { echo "$(date +%F\ %T) $*" >> $P/chain.log; }
stop() { # stop <hard|soft> <reason>   hard = same data will not be retried; soft = rerun re-evaluates (e.g. not armed)
  { echo "# r7 post-chain STOPPED $(date +%F\ %T) ($1)"; echo; echo "$2"; } > $P/REASON.md; echo "- POSTCHAIN stopped $(date +%H:%M) ($1): $(echo "$2"|head -1|cut -c1-300) -> $P/REASON.md" >> $S; say "STOP $1: $2"
  [ "$1" = hard ] && [ -f $F/train.jsonl.gz ] && cat $F/train.jsonl.gz $F/val.jsonl.gz | sha256sum | cut -d' ' -f1 > $P/HARD_STOP; exit 1; }
[ -f $T/.vast_instance ] && { say "instance $(cat $T/.vast_instance) already recorded: nothing to do"; exit 0; }
[ -f $P/GO_LAUNCHING ] && stop hard "launch_r7.sh --go was already started at $(cat $P/GO_LAUNCHING) but no .vast_instance is recorded: do NOT auto-retry (could double-rent). Check 'vastai show instances', $P/go.log, then remove $P/GO_LAUNCHING."
# 1. wait for FINAL merge + TRADEOFF
dead=0; say "chain started pid $$"
while :; do
  grep -q "^- FINAL merge+report done" $S && grep -q "^- TRADEOFF done" $S && break
  grep -q "^- TRADEOFF FAILED\|^- TRADEOFF skipped" $S && stop hard "tradeoff step failed/skipped (see $V/final_tradeoff.log); Harris wants the tradeoff table before training"
  if ! pgrep -f "r7_final_armed.sh|r7_final_merge_only|run_r7_units|r7_tradeoff_after|r7_tradeoff.py|r7_merge.py" >/dev/null; then dead=$((dead+1)); else dead=0; fi
  [ $dead -ge 5 ] && stop hard "no build/merge/tradeoff process alive for 5 min and FINAL merge / TRADEOFF done lines are missing (last STATUS: $(tail -1 $S|cut -c1-200)). Restart /workspace/r6/r7_final_armed.sh (resumes)."
  touch $P/heartbeat; sleep 60
done
say "FINAL + TRADEOFF done"
[ -f $P/HARD_STOP ] && [ "$(cat $F/train.jsonl.gz $F/val.jsonl.gz | sha256sum | cut -d' ' -f1)" = "$(cat $P/HARD_STOP)" ] && { say "same data already hard-stopped; see $P/REASON.md"; exit 1; }
rm -f $P/HARD_STOP
[ -f $F/train.jsonl.gz ] && [ -f $F/val.jsonl.gz ] || stop hard "final_merged lacks train/val.jsonl.gz"
# 2. SHA256SUMS (merge does not write it; preflight/launch need it). Never overwritten if present.
[ -f $F/SHA256SUMS ] || ( cd $F && sha256sum train.jsonl.gz val.jsonl.gz > SHA256SUMS ) ; say "SHA256SUMS ok"
# 3. hard checks (rows, kinds, file+line, approve 45-50%, split); guards + schema + prompt sha + drop rate run inside preflight (step 5)
python3 /workspace/r6/r7_hard_checks.py $F $P > $P/hard_checks.log 2>&1; rc=$?
cp $P/NOTIFY_HARRIS.md $V/NOTIFY_HARRIS.md 2>/dev/null; touch $P/NOTIFY_READY
case $rc in 0) say "hard checks PASS (warnings in NOTIFY_HARRIS.md)";; 10) stop hard "$(grep -m1 'RECOMMEND' $P/hard_checks.log || echo 'final set below minimum rows'). Recommend the stop rule; no training. Numbers: $P/NOTIFY_HARRIS.md";;
  *) stop hard "hard checks FAILED: $(python3 -c "import json;print('; '.join(json.load(open('$P/hard_checks.json'))['fails']))" 2>&1 | cut -c1-900). Numbers: $P/NOTIFY_HARRIS.md";; esac
# 4. widen eval interval (save_every stays 14 = resume granularity). ~3 mid-run evals, multiple of 14. Idempotent; backup once.
python3 - "$T" "$F" <<'PY' >> $P/chain.log 2>&1 || stop hard "could not widen eval interval (see chain.log)"
import sys, re, os, json, gzip, math, shutil, yaml
T, F = sys.argv[1], sys.argv[2]; p = f"{T}/config.yaml"; C = yaml.safe_load(open(p))
if not os.path.exists(p + ".pre_r7_chain"): shutil.copy(p, p + ".pre_r7_chain")
n = sum(1 for _ in gzip.open(f"{F}/train.jsonl.gz", "rt")); spe = math.ceil(n / C["per_device_batch"] / C["grad_accum"]); total = spe * C["epochs"]
every = max(14, math.ceil(total / 4 / 14) * 14)
if every >= total: every = max(1, total // 2)          # always keep >= 1 mid-run eval
t = open(p).read(); t2 = re.sub(r"^eval_every_steps:\s*\d+", f"eval_every_steps: {every}", t, flags=re.M)
if t2 != t: open(p, "w").write(t2)
print(f"eval_every_steps -> {every} (train rows {n}, total steps {total}, save_every {C['save_every_steps']})")
PY
# 5. gates (no spend): preflight (SHA, prompt sha, code_blob v2, schema, guards, drop rate, schedule, hours) + vast plan
(cd $T && bash launch_r7.sh) > $P/gates.log 2>&1 || stop hard "launch_r7.sh gates FAILED: $(grep -E 'FAIL|BLOCKED|REFUSING|DATASET' $P/gates.log | head -5 | tr '\n' ' ') (full: $P/gates.log)"
grep -q "gates passed" $P/gates.log || stop hard "gates log lacks 'gates passed' ($P/gates.log)"; est=$(grep -o 'x \$2.35/h = \$[0-9]*' $P/gates.log | grep -o '[0-9]*$' | tail -1); cr=$(grep -o 'vast credit \$[0-9.]*' $P/gates.log | tail -1 | tr -dc '0-9.')
python3 -c "import sys;sys.exit(0 if float('${cr:-0}')>=max(10.0,1.3*float('${est:-0}')) else 1)" || stop hard "insufficient credit: \$${cr:-?} vs estimated run \$${est:-?} (need >= max 10, 1.3x estimate)"
say "gates PASS"; touch $P/GATES_PASS
# 6. go only if ARMED
[ -f $ARMED ] || stop soft "all hard checks + gates PASSED, but $ARMED does not exist (not armed): NOT launching. To arm: touch $ARMED then rerun: nohup setsid bash /workspace/r6/r7_post_chain.sh >> $P/chain.out 2>&1 &"
[ -f $T/.vast_instance ] && exit 0
date +%FT%T > $P/GO_LAUNCHING; say "ARMED present: launch_r7.sh --go"
(cd $T && bash launch_r7.sh --go) > $P/go.log 2>&1; rc=$?
if [ $rc = 0 ] && [ -f $T/.vast_instance ]; then echo "- POSTCHAIN LAUNCHED $(date +%H:%M): instance $(cat $T/.vast_instance); watch $(ls -d /workspace/usuba-runs/$(cat $T/.vast_instance)/watch.log)" >> $S; say "LAUNCHED"; touch $P/LAUNCHED
else stop hard "launch_r7.sh --go exit $rc without a recorded instance (see $P/go.log). Check 'vastai show instances' before any retry."; fi
