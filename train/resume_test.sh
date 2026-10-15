#!/usr/bin/env bash
# Reboot/resume test (run on the Vast GPU instance, paid, ~15 min, AFTER dry_run.sh and BEFORE the real run). Proves that a hard kill / reboot
# loses at most save_every_steps steps and that training continues from the checkpoint with no step counter reset, with NO manual restart:
# the watchdog (tmux "wd", started by autostart.sh = Vast onstart hook) must restart it. FIX: the test arms the watchdog for out/resumetest.
#   bash resume_test.sh            # start test run, kill -9 it, wait for the WATCHDOG to resume it, verify (step advanced, GPU busy)
#   bash resume_test.sh --reboot   # (after the kill test) record state; then reboot via the Vast API (`vastai reboot instance ID`), wait, run --verify
#   bash resume_test.sh --verify   # check the result after the reboot (needs pre_reboot.json) or after the kill
#   bash resume_test.sh --disarm   # stop the test run and disarm the watchdog (do this before the real run)
# Output goes to out/resumetest; PASS/FAIL in /workspace/usuba/RESUMETEST_REPORT.txt.
set -uo pipefail
U=/workspace/usuba; cd $U/train; O=out/resumetest; REP=$U/RESUMETEST_REPORT.txt; MODE=${1:-}
steps() { grep -o '"step": [0-9]*' $O/train_log.jsonl 2>/dev/null | grep -o '[0-9]*' | tail -1; }
lastck() { ls -d $O/checkpoints/step-*/COMPLETE 2>/dev/null | sed -E 's#.*step-([0-9]+)/.*#\1#' | sort -n | tail -1 | sed -E 's/^0+([0-9])/\1/'; }
gpu() { nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader; }
verify() {  # $1 = pre-state json
  python3 - $1 <<PY | tee $REP
import json,sys
rows=[json.loads(l) for l in open("$O/train_log.jsonl") if '"loss"' in l]; st=[r["step"] for r in rows]
pre=json.load(open(sys.argv[1]))
reset = any(b==1 and a>3 for a,b in zip(st,st[1:]))
ok = max(st) > pre["step_at_kill"] and not reset
print(("PASS" if ok else "FAIL"), f"{sys.argv[1]}: stopped at step {pre['step_at_kill']}, newest complete checkpoint {pre['ckpt']}, now at step {max(st)}; lost steps <= {pre['step_at_kill']-pre['ckpt']}; counter reset: {reset}")
PY
  grep -q ^PASS $REP
}
if [ "$MODE" = --disarm ]; then rm -f $U/ARMED; touch $U/NO_RESTART; pkill -f "[c]onfig_resumetest.yaml"; tmux kill-session -t train 2>/dev/null; echo disarmed; exit 0; fi
if [ "$MODE" = --verify ]; then verify $O/$( [ -f $O/pre_reboot.json ] && echo pre_reboot.json || echo pre_kill.json ); exit $?; fi
if [ "$MODE" = --reboot ]; then echo "{\"step_at_kill\": $(steps), \"ckpt\": $(lastck)}" > $O/pre_reboot.json; date +%s > $O/reboot_t; sync; echo "recorded $(cat $O/pre_reboot.json); now reboot via Vast API"; exit 0; fi
bash $U/train/deps.sh || { echo "FAIL: deps" | tee $REP; exit 1; }
rm -rf $O $U/NO_RESTART; python3 - <<PY
import yaml; c=yaml.safe_load(open("config.yaml")); c.update(save_every_steps=2, eval_every_steps=1000, max_hours=1.0, output_dir="$O"); yaml.safe_dump(c, open("config_resumetest.yaml","w"))
PY
mkdir -p $O; printf '%s\n%s\n%s\n' "$O" "SKIP_INITIAL_EVAL=1 python3 train_lora.py --config config_resumetest.yaml --resume" 30 > $U/ARMED
pgrep -f "[w]atchdog.sh" >/dev/null || bash $U/train/autostart.sh
export SKIP_INITIAL_EVAL=1; nohup python3 train_lora.py --config config_resumetest.yaml --resume > $U/resumetest_run1.log 2>&1 & P=$!
echo "waiting for >=2 complete checkpoints (steps >= 4)..."
for i in $(seq 1 240); do c=$(lastck); [ -n "${c:-}" ] && [ "$c" -ge 4 ] && break; sleep 15; done
c=$(lastck); [ -n "${c:-}" ] || { echo "FAIL: no checkpoint within 60 min" | tee $REP; kill $P; exit 1; }
sleep 20; s=$(steps); kill -9 $P; pkill -9 -f "[c]onfig_resumetest.yaml.*--resume$" ; sleep 1
echo "{\"step_at_kill\": ${s:-$c}, \"ckpt\": $(lastck)}" > $O/pre_kill.json; echo "KILLED at step ${s:-?} (newest complete checkpoint $(lastck)) $(date -u +%T)Z; waiting for the watchdog to resume it"
for i in $(seq 1 90); do sleep 20; n=$(steps); [ -n "${n:-}" ] && [ "$n" -gt "${s:-$c}" ] && break; done
echo "after $((i*20))s: step ${n:-?} gpu: $(gpu) alive: $(pgrep -f '[c]onfig_resumetest.yaml' | wc -l)"
grep "resumed from" $U/watchdog_train.log | tail -1 || { echo "FAIL: watchdog run did not report 'resumed from'" | tee $REP; exit 1; }
verify $O/pre_kill.json
