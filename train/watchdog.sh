#!/usr/bin/env bash
# Runs ON the instance, in tmux session "wd" (started by autostart.sh, which the Vast onstart command runs after every reboot).
# Every CHECK_SEC (default 300 = 5 min) it VERIFIES three things, not just "a process exists":
#   (a) train_lora.py is alive, (b) GPU utilisation / memory (sampled 5x over ~10 s), (c) the optimizer step in train_log.jsonl advanced.
# It restarts training from the newest complete checkpoint (train_lora.py --resume) when the process is dead without a terminal marker,
# or when no new step was logged for STALL_MIN minutes (after a start-up grace period), and writes /workspace/usuba/ALERT (appended, one line per event)
# so launch_vast.sh watch can surface it. Needs no network. Test with train/resume_test.sh.
U=${U:-/workspace/usuba}; O=${O:-$U/train/out/usuba-9b-lora}; LOG=$U/watchdog.log; ALERT=$U/ALERT
CHECK_SEC=${CHECK_SEC:-300}; STALL_MIN=${STALL_MIN:-15}; GRACE_MIN=${GRACE_MIN:-30}; MAX_RESTARTS=${MAX_RESTARTS:-6}
say() { echo "[$(date -u +%FT%TZ)] $*" >> $LOG; }
alert() { echo "[$(date -u +%FT%TZ)] $*" >> $ALERT; say "ALERT: $*"; }
last_step() { [ -f $O/train_log.jsonl ] && tail -n 40 $O/train_log.jsonl 2>/dev/null | grep -o '"step": [0-9]*' | tail -1 | grep -o '[0-9]*'; }
gpu_sample() {   # mean util % and max mem MiB over 5 samples, 2 s apart ("na" if no nvidia-smi)
  command -v nvidia-smi >/dev/null || { echo "na na"; return; }
  for i in 1 2 3 4 5; do nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits 2>/dev/null | head -1; sleep 2; done |
    awk -F', *' '{u+=$1; if($2>m)m=$2; n++} END{if(n)printf "%d %d", u/n, m; else print "na na"}'
}
# FIX: the watchdog must never start training on a fresh instance. It only acts when $U/ARMED exists:
#   line 1 = output dir (relative to $U/train), line 2 = command to run in tmux "train" (default: remote_setup.sh), line 3 = optional CHECK_SEC.
# launch_vast.sh start arms the real run; dry_run.sh/resume_test.sh arm their own test run.
armed() { [ -f $U/ARMED ] || return 1; O=$U/train/$(sed -n 1p $U/ARMED); TCMD=$(sed -n 2p $U/ARMED); CS=$(sed -n 3p $U/ARMED); [ -n "$CS" ] && CHECK_SEC=$CS; return 0; }
start_train() {
  pkill -f train_lora.py 2>/dev/null; tmux kill-session -t train 2>/dev/null; sleep 3
  rm -f $U/TRAIN_STOPPED $O/STOPPED
  tmux new -d -s train "cd $U/train && ${TCMD:-SMOKE_STEPS=$(cat $U/mode_smoke 2>/dev/null || echo 0) SMOKE_HOURS=0.15 bash $U/train/remote_setup.sh} >> $U/watchdog_train.log 2>&1"   # remote_setup.sh runs --resume
  START=$(date +%s); RESTARTS=$((RESTARTS+1)); say "START/RESTART #$RESTARTS from step ${LAST:-0}"
}
RESTARTS=0; LAST=$(last_step); LAST=${LAST:--1}; LAST_T=$(date +%s); START=0; LOWGPU=0
say "watchdog up: check every ${CHECK_SEC}s, stall ${STALL_MIN}m, grace ${GRACE_MIN}m, last step $LAST"
while true; do
  now=$(date +%s)
  armed || { say "not armed; idle"; sleep $CHECK_SEC; continue; }
  if [ -f $U/ALL_DONE ] || [ -f $U/SMOKE_DONE ] || [ -f $U/NO_RESTART ] || { [ -f $O/STOPPED ] && grep -q max_hours $O/STOPPED; }; then say "terminal marker present; idle"; sleep $CHECK_SEC; continue; fi
  if [ -f $O/DONE ]; then say "DONE present; export phase"; sleep $CHECK_SEC; continue; fi   # export runs after DONE; never interfere
  alive=0; pgrep -f "train_lora.py" >/dev/null && alive=1
  read -r gutil gmem <<< "$(gpu_sample)"
  s=$(last_step); s=${s:--1}
  advanced=0; if [ "$s" != "$LAST" ]; then advanced=1; LAST=$s; LAST_T=$now; fi
  say "alive=$alive gpu_util=${gutil}% gpu_mem=${gmem}MiB step=$s advanced=$advanced since_progress=$(( (now-LAST_T)/60 ))m restarts=$RESTARTS"
  # GPU idle while the process is "alive" and no step progress = hung (e.g. dataloader/NCCL/IO wait)
  if [ $alive = 1 ] && [ "$gutil" != na ] && [ "$gutil" -lt 5 ] && [ $advanced = 0 ]; then LOWGPU=$((LOWGPU+1)); else LOWGPU=0; fi
  reason=""
  if [ $alive = 0 ]; then
    { [ $START = 0 ] || [ $((now-START)) -gt 90 ]; } && reason="process dead"
  elif [ $((now-LAST_T)) -gt $((STALL_MIN*60)) ] && [ $((now-START)) -gt $((GRACE_MIN*60)) ]; then
    reason="no step progress for >${STALL_MIN}m (gpu_util=${gutil}%, lowgpu_checks=$LOWGPU)"
  fi
  if [ -n "$reason" ]; then
    if [ $RESTARTS -ge $MAX_RESTARTS ]; then alert "GIVING UP after $RESTARTS restarts: $reason (step $s)"; touch $U/NO_RESTART
    else alert "restart #$((RESTARTS+1)) from newest checkpoint: $reason (step $s)"; start_train; LAST_T=$(date +%s); fi
  fi
  sleep $CHECK_SEC
done
