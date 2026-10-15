#!/usr/bin/env bash
# Reboot/resume test (run on the Vast GPU instance, paid, ~10-15 min, AFTER dry_run.sh and BEFORE the real run). Proves that a hard kill / reboot
# loses at most save_every_steps steps and that training continues from the checkpoint with the same data order (no step counter reset).
#   bash /workspace/usuba/train/resume_test.sh            # kill -9 the trainer, then let the watchdog (CHECK_SEC=30) restart it
#   bash /workspace/usuba/train/resume_test.sh --reboot   # same, but then `reboot` the container; autostart.sh (Vast onstart) must bring everything back;
#                                                         # run again with --verify afterwards
#   bash /workspace/usuba/train/resume_test.sh --verify   # check the result after a reboot
# Output goes to out/resumetest; PASS/FAIL in /workspace/usuba/RESUMETEST_REPORT.txt.
set -uo pipefail
U=/workspace/usuba; cd $U/train; O=out/resumetest; REP=$U/RESUMETEST_REPORT.txt; MODE=${1:-}
steps() { grep -o '"step": [0-9]*' $O/train_log.jsonl 2>/dev/null | grep -o '[0-9]*' | tail -1; }
lastck() { ls -d $O/checkpoints/step-*/COMPLETE 2>/dev/null | sed -E 's#.*step-([0-9]+)/.*#\1#' | sort -n | tail -1; }
verify() {
  python3 - <<PY | tee $REP
import json,re
rows=[json.loads(l) for l in open("$O/train_log.jsonl") if '"loss"' in l]; st=[r["step"] for r in rows]
pre=json.load(open("$O/pre_kill.json"))
resumed_ok = max(st) > pre["step_at_kill"] and st.count(pre["ckpt"]+1) >= 1
reset = any(b==1 and a>3 for a,b in zip(st,st[1:]))
ok = resumed_ok and not reset
print(("PASS" if ok else "FAIL"), f"killed at step {pre['step_at_kill']}, newest complete checkpoint {pre['ckpt']}, now at step {max(st)}; lost steps <= {pre['step_at_kill']-pre['ckpt']}; counter reset: {reset}")
PY
  grep -q ^PASS $REP
}
[ "$MODE" = --verify ] && { verify; exit $?; }
rm -rf $O; python3 - <<PY
import yaml; c=yaml.safe_load(open("config.yaml")); c.update(save_every_steps=2, eval_every_steps=1000, max_hours=1.0, output_dir="$O"); yaml.safe_dump(c, open("config_resumetest.yaml","w"))
PY
nohup python3 train_lora.py --config config_resumetest.yaml --resume > $U/resumetest_run1.log 2>&1 & P=$!
echo "waiting for >=2 complete checkpoints (steps >= 4)..."
for i in $(seq 1 240); do c=$(lastck); [ -n "${c:-}" ] && [ "$c" -ge 4 ] && break; sleep 15; done
c=$(lastck); [ -n "${c:-}" ] || { echo "FAIL: no checkpoint within 60 min" | tee $REP; kill $P; exit 1; }
sleep 20; s=$(steps); kill -9 $P; pkill -9 -f config_resumetest.yaml; sleep 3
echo "{\"step_at_kill\": ${s:-$c}, \"ckpt\": $(lastck)}" > $O/pre_kill.json; echo "KILLED at step ${s:-?} (newest complete checkpoint $(lastck))"
if [ "$MODE" = --reboot ]; then echo "rebooting; after it is back and training has progressed, run: bash $U/train/resume_test.sh --verify"; sync; reboot; exit 0; fi
echo "restarting with --resume (what the watchdog does)"
timeout 600 python3 train_lora.py --config config_resumetest.yaml --resume --max-steps $(( ${s:-$c} + 3 )) > $U/resumetest_run2.log 2>&1
grep -m1 "resumed from" $U/resumetest_run2.log || { echo "FAIL: second run did not report 'resumed from'" | tee $REP; exit 1; }
verify
