#!/usr/bin/env bash
# Usuba 9B bf16-LoRA run on ONE Vast GPU, data-loss proof.
#   plan                       build data, show credit + best offers (no spend)
#   up --yes [--gpu h100|a100] [--max-dph 3.6] [--smoke]   rent + start (--smoke: ~10 min paid smoke: few steps, checkpoint, GGUF export)
#   watch                      run on the box (nohup): sync every 10 min until ALL_DONE / SMOKE_DONE / TRAIN_STOPPED, then a final fetch
#   sync                       copy new files off the instance -> box (sha256-verified) -> R2 bucket (chunked)
#   fetch                      final sync + writes FETCH_VERIFIED when every remote artifact matches locally by sha256
#   down                       destroy; REFUSES unless a fresh fetch verifies against the instance right now (--i-accept-data-loss overrides)
#   resume --yes               rent a new instance and continue from the newest synced checkpoint (after a lost instance)
#   status | logs
# Secrets: vastai CLI key file and CLOUDFLARE_API_TOKEN stay on the box; nothing secret is sent to the instance or printed.
set -euo pipefail
command -v ssh >/dev/null && command -v scp >/dev/null || { echo "ssh/scp missing on this machine: sudo apt-get install -y openssh-client"; exit 4; }
cd "$(dirname "$0")"; T=$PWD; ROOT=$(dirname "$T"); ST=$T/.vast_instance
IMAGE=${IMAGE:-pytorch/pytorch:2.9.1-cuda12.8-cudnn9-devel}; DISK=${DISK:-150}
RUNS=${USUBA_RUNS:-/workspace/usuba-runs}; R2_BUCKET=${R2_BUCKET:-usuba-training}; CHUNK=${CHUNK:-200M}
GPU=h100; MAXDPH=3.6; YES=0; SMOKE=0; FORCE=0; CMD=${1:-plan}; shift || true
while [ $# -gt 0 ]; do case $1 in --yes) YES=1;; --smoke) SMOKE=1;; --i-accept-data-loss) FORCE=1;; --gpu) GPU=$2; shift;; --max-dph) MAXDPH=$2; shift;; esac; shift; done
Q_H100="gpu_name in [H100_SXM,H100_PCIE,H100_NVL] num_gpus=1 gpu_ram>=79 disk_space>=$DISK reliability>0.98 inet_down>=500 inet_up>=200 cuda_vers>=12.8 dph_total<=$MAXDPH"
Q_A100="gpu_name in [A100_SXM4,A100_PCIE] num_gpus=1 gpu_ram>=79 disk_space>=$DISK reliability>0.98 inet_down>=500 inet_up>=200 cuda_vers>=12.8 dph_total<=$MAXDPH"
query() { [ "$GPU" = a100 ] && echo "$Q_A100" || echo "$Q_H100"; }
best() { vastai search offers "$(query)" -o dph_total --limit 1 --storage $DISK --raw | python3 -c "import json,sys;o=json.load(sys.stdin);print(o[0]['id'],round(o[0]['dph_total'],3),o[0]['gpu_name'].replace(' ','_')) if o else print('NONE 0 none')"; }
KEY=${VAST_SSH_KEY:-$HOME/.ssh/vast_ed25519}
SO="-o StrictHostKeyChecking=no -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=20 -o ServerAliveInterval=30 -i $KEY"
IID() { cat $ST; }
LOCAL() { echo "$RUNS/$(IID)"; }
ssh_of() { vastai ssh-url "$(IID)" | sed 's#ssh://##'; }
# MOCK_REMOTE=<dir> stands in for the instance's /workspace/usuba (local test of sync/fetch/down without renting)
rsh() { if [ -n "${MOCK_REMOTE:-}" ]; then local c="$*"; bash -c "${c//\/workspace\/usuba/$MOCK_REMOTE}"; return; fi
        local S; S=$(ssh_of); ssh $SO -p ${S##*:} ${S%:*} "$@"; }
rcp() { if [ -n "${MOCK_REMOTE:-}" ]; then cp "${1/\/workspace\/usuba/$MOCK_REMOTE}" "$2"; return; fi
        local S; S=$(ssh_of); scp -q $SO -P ${S##*:} "${S%:*}:$1" "$2"; }
bundle() {
  [ -s data/train.jsonl ] || python3 build_train_set.py
  python3 -c "import json,hashlib;m=json.load(open('data/manifest.json'));assert all(hashlib.sha256(open('data/'+f,'rb').read()).hexdigest()==h for f,h in m['sha256'].items()),'train data does not match manifest sha256'"
  tar czf /tmp/usuba_train_bundle.tgz -C "$ROOT" train/config.yaml train/train_lora.py train/export_gguf.py train/remote_setup.sh train/prompt.py train/data/train.jsonl train/data/val.jsonl train/data/manifest.json
}
# remote artifact list: checkpoints, adapters, logs, final GGUF (merged bf16 is deleted on the instance: regenerable)
REMOTE_LIST='cd /workspace/usuba && { ls run.log ALL_DONE SMOKE_DONE TRAIN_STOPPED 2>/dev/null; find train/out -type f ! -path "*/merged-bf16/*" ! -name "*bf16.gguf" ! -path "*.tmp/*" 2>/dev/null; } | sort'
CF_ACCT=""
r2_up() {  # r2_up <file> <key>: Cloudflare R2 object API; the token goes in a header file descriptor, never on argv or stdout
  [ -n "$CF_ACCT" ] || CF_ACCT=$(curl -s -H @<(printf 'Authorization: Bearer %s' "$CLOUDFLARE_API_TOKEN") https://api.cloudflare.com/client/v4/accounts | python3 -c "import json,sys;print(json.load(sys.stdin)['result'][0]['id'])")
  curl -s -X PUT -H @<(printf 'Authorization: Bearer %s' "$CLOUDFLARE_API_TOKEN") --data-binary @"$1" \
    "https://api.cloudflare.com/client/v4/accounts/$CF_ACCT/r2/buckets/$R2_BUCKET/objects/$2" | python3 -c "import json,sys;sys.exit(0 if json.load(sys.stdin).get('success') else 1)"
}
r2_put() {  # r2_put <local file> <key>; files over $CHUNK go up as numbered parts plus parts.sha256
  [ -n "${CLOUDFLARE_API_TOKEN:-}" ] || { echo "  (no CLOUDFLARE_API_TOKEN: box copy only)"; return 0; }
  local f=$1 k=$2 sz; sz=$(stat -c %s "$f")
  if [ "$sz" -le 209715200 ]; then r2_up "$f" "$k" || { echo "  R2 upload FAILED: $k"; return 1; }
  else
    local d; d=$(mktemp -d); split -b $CHUNK -d -a 3 "$f" "$d/part."; ( cd "$d" && sha256sum part.* ) > "$d/parts.sha256"
    for p in "$d"/part.* "$d/parts.sha256"; do r2_up "$p" "$k.parts/$(basename $p)" || { echo "  R2 upload FAILED: $k $(basename $p)"; rm -rf "$d"; return 1; }; done
    rm -rf "$d"
  fi
  echo "  R2 ok: $k"
}
sync_once() {  # copies every new/changed remote artifact, verifies sha256, uploads to R2; prints "OK <n files>" when all match
  local L; L=$(LOCAL); mkdir -p "$L"
  rsh "$REMOTE_LIST | grep -v -e '^run.log\$' -e 'train_log.jsonl\$' | while read f; do d=\${f%/*}; case \$f in */checkpoints/step-*) [ -f \$(echo \$f | sed -E 's#(step-[0-9]+)/.*#\\1#')/COMPLETE ] || continue;; esac; sha256sum \"\$f\"; done" > "$L/.remote.sha256.new" || { echo "instance unreachable"; return 2; }
  local bad=0 n=0
  while read -r h f; do
    n=$((n+1))
    [ -f "$L/$f" ] && [ "$(sha256sum "$L/$f" | cut -d' ' -f1)" = "$h" ] && continue
    mkdir -p "$(dirname "$L/$f")"; rcp "/workspace/usuba/$f" "$L/$f.part" || { echo "  copy failed: $f"; bad=1; continue; }
    if [ "$(sha256sum "$L/$f.part" | cut -d' ' -f1)" = "$h" ]; then mv "$L/$f.part" "$L/$f"; echo "  synced $f"
      r2_put "$L/$f" "runs/$(IID)/$f" || true   # box copy is the source of truth; R2 failure is reported, not fatal
    else echo "  checksum mismatch (file still being written?): $f"; rm -f "$L/$f.part"; bad=1; fi
  done < "$L/.remote.sha256.new"
  for f in run.log train/out/usuba-9b-lora/train_log.jsonl; do   # live-appended logs: snapshot copy, never checksum-gated
    mkdir -p "$(dirname "$L/$f")"; rcp "/workspace/usuba/$f" "$L/$f.snap" 2>/dev/null && mv "$L/$f.snap" "$L/$f" && { r2_put "$L/$f" "runs/$(IID)/$f" >/dev/null || true; }
  done
  mv "$L/.remote.sha256.new" "$L/remote.sha256"; date -u +%FT%TZ > "$L/last_sync"
  [ $bad = 0 ] && echo "OK $n files" || return 1
}
start_remote() {
  local S P HST; S=$(ssh_of); P=${S##*:}; HST=${S%:*}
  scp -q $SO -P $P /tmp/usuba_train_bundle.tgz $HST:/workspace/
  ssh $SO -p $P $HST "mkdir -p /workspace/usuba && tar xzf /workspace/usuba_train_bundle.tgz -C /workspace/usuba"
  if [ -n "${RESUME_FROM:-}" ]; then   # push the newest synced checkpoint so train_lora.py --resume continues from it
    ( cd "$RESUME_FROM" && tar cf - train/out/usuba-9b-lora ) | ssh $SO -p $P $HST "tar xf - -C /workspace/usuba"
  fi
  ssh $SO -p $P $HST "(command -v tmux >/dev/null || (apt-get update -qq && apt-get install -y -qq tmux git cmake build-essential >/dev/null)) && tmux new -d -s train 'SMOKE_STEPS=$SMOKE bash /workspace/usuba/train/remote_setup.sh'"
}
rent() {
  [ $YES = 1 ] || { echo "refusing to rent without --yes"; exit 2; }
  [ -f $ST ] && { echo "instance $(IID) already recorded in $ST (run down first)"; exit 2; }
  if [ "$(vastai show ssh-keys --raw | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')" = 0 ]; then echo "registering $KEY.pub with Vast"; vastai create ssh-key "$(cat $KEY.pub)" >/dev/null; fi
  bundle; read -r OID DPH NAME < <(best); [ "$OID" = NONE ] && { echo "no $GPU offer under \$$MAXDPH/h"; exit 3; }
  echo "renting $NAME offer $OID at \$$DPH/h"
  vastai create instance $OID --image $IMAGE --disk $DISK --ssh --direct --label usuba-9b-lora --raw | python3 -c "import json,sys;print(json.load(sys.stdin)['new_contract'])" > $ST
  mkdir -p "$(LOCAL)"; echo "$DPH $NAME $(date -u +%FT%TZ) smoke=$SMOKE" > "$(LOCAL)/rental.txt"
  echo "instance $(IID); waiting for ssh..."
  for i in $(seq 1 60); do rsh true 2>/dev/null && break; sleep 20; done
  start_remote; echo "started. now run: nohup train/launch_vast.sh watch > $(LOCAL)/watch.log 2>&1 &"
}
case $CMD in
plan)
  bundle; ls -la /tmp/usuba_train_bundle.tgz; cat dry_run_stats.json 2>/dev/null || true
  echo "credit: $(vastai show user --raw | python3 -c 'import json,sys;print(round(json.load(sys.stdin)["credit"],2))') USD"
  echo "H100: $(GPU=h100; best)"; echo "A100: $(GPU=a100; best)"
  echo "box free: $(df -h --output=avail / | tail -1)  R2 bucket: $R2_BUCKET";;
up) rent;;
start) bundle; start_remote; echo "started on $(IID)";;   # (re)start the job on the already-rented instance
resume)
  P=$(ls -d $RUNS/*/train/out/usuba-9b-lora/checkpoints/step-*/COMPLETE 2>/dev/null | awk -F/ '{print $(NF-1)" "$0}' | sort | tail -1 | cut -d' ' -f2 || true)
  [ -n "$P" ] || { echo "no synced complete checkpoint under $RUNS"; exit 2; }
  export RESUME_FROM=${P%/train/out/*}; echo "resuming from $(dirname $P)"; rm -f $ST; rent;;
watch)
  while true; do
    echo "[$(date)] sync"; sync_once || true
    L=$(LOCAL); if grep -qE "  (ALL_DONE|SMOKE_DONE|TRAIN_STOPPED)$" "$L/remote.sha256" 2>/dev/null; then   # markers present on the instance now
      echo "run finished; final fetch"; "$0" fetch && echo "FETCH VERIFIED. safe to: train/launch_vast.sh down"; break; fi
    # heartbeat: no new optimizer step for STALL_MIN (10) minutes -> STALLED + resume via /root/onstart.sh
    st=$(rsh "tail -n 1 /workspace/usuba/train/out/usuba-9b-lora/train_log.jsonl 2>/dev/null | grep -o '\"step\": [0-9]*'" 2>/dev/null || true)
    now=$(date +%s); [ "$st" != "${last_st:-x}" ] && { last_st=$st; last_t=$now; }
    if [ $((now-${last_t:-$now})) -ge $((${STALL_MIN:-10}*60)) ]; then
      echo "[$(date)] STALLED: no new step since $(date -d @$last_t) ($st); attempting resume"
      rsh "tmux kill-session -t train 2>/dev/null; pkill -f train_lora.py; sleep 5; rm -f /workspace/usuba/TRAIN_STOPPED; bash /root/onstart.sh" || echo "  resume attempt failed (instance unreachable?)"
      last_t=$((now+15*60))   # grace for setup + model load before the next stall check
    fi
    sleep ${SYNC_EVERY:-120}
  done;;
sync) sync_once;;
fetch)
  sync_once
  L=$(LOCAL); ( cd "$L" && sha256sum -c --quiet remote.sha256 ) || { echo "local copy does not verify"; exit 1; }
  grep -q "train/out/" "$L/remote.sha256" || { echo "no training artifacts on the instance yet"; exit 1; }
  sha256sum "$L/remote.sha256" | cut -d' ' -f1 > "$L/FETCH_VERIFIED"; echo "verified $(wc -l < "$L/remote.sha256") files in $L";;
down)
  [ -f $ST ] || { echo "no instance recorded"; exit 1; }
  if [ $FORCE = 0 ]; then
    L=$(LOCAL); [ -f "$L/FETCH_VERIFIED" ] || { echo "REFUSING: no verified fetch. run: train/launch_vast.sh fetch"; exit 3; }
    # re-check against the instance right now: anything written after the last fetch must be fetched too
    rsh "$REMOTE_LIST | grep -v -e '^run.log\$' -e 'train_log.jsonl\$' | while read f; do d=\${f%/*}; case \$f in */checkpoints/step-*) [ -f \$(echo \$f | sed -E 's#(step-[0-9]+)/.*#\\1#')/COMPLETE ] || continue;; esac; sha256sum \"\$f\"; done" > /tmp/usuba_down_check || { echo "REFUSING: cannot reach instance to verify (use --i-accept-data-loss if it is already gone)"; exit 3; }
    cmp -s /tmp/usuba_down_check "$L/remote.sha256" || { echo "REFUSING: instance has files not in the verified fetch. run fetch again"; exit 3; }
    ( cd "$L" && sha256sum -c --quiet remote.sha256 ) || { echo "REFUSING: local copy no longer verifies"; exit 3; }
  fi
  [ -n "${MOCK_REMOTE:-}" ] && { echo "MOCK: would destroy $(IID)"; exit 0; }
  vastai destroy instance -y "$(IID)" && rm -f $ST && echo destroyed;;
status) vastai show instance "$(IID)";;
logs) rsh "tail -n 40 /workspace/usuba/run.log; ls /workspace/usuba/ | grep -E 'DONE|STOPPED' || true";;
*) sed -n 2,14p "$0"; exit 1;;
esac
