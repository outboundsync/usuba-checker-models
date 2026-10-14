#!/usr/bin/env bash
# Launch the Usuba 9B bf16-LoRA run on ONE Vast GPU, then fetch the adapter + 4-bit GGUF and DESTROY the instance.
# Spends money: requires --yes. Uses the vastai CLI's stored key (~/.config/vastai/vast_api_key); never prints it.
#   train/launch_vast.sh plan                  # build data, show best offers + cost estimate (no spend)
#   train/launch_vast.sh up --yes [--gpu h100|a100] [--max-dph 3.5]
#   train/launch_vast.sh status | logs | fetch | down
set -euo pipefail
cd "$(dirname "$0")"; T=$PWD; ROOT=$(dirname "$T"); ST=$T/.vast_instance
IMAGE=${IMAGE:-pytorch/pytorch:2.9.1-cuda12.8-cudnn9-devel}; DISK=${DISK:-150}
GPU=h100; MAXDPH=3.6; YES=0; CMD=${1:-plan}; shift || true
while [ $# -gt 0 ]; do case $1 in --yes) YES=1;; --gpu) GPU=$2; shift;; --max-dph) MAXDPH=$2; shift;; esac; shift; done
Q_H100="gpu_name in [H100_SXM,H100_PCIE,H100_NVL] num_gpus=1 gpu_ram>=79 disk_space>=$DISK reliability>0.98 inet_down>=500 cuda_vers>=12.8 dph_total<=$MAXDPH"
Q_A100="gpu_name in [A100_SXM4,A100_PCIE] num_gpus=1 gpu_ram>=79 disk_space>=$DISK reliability>0.98 inet_down>=500 cuda_vers>=12.8 dph_total<=$MAXDPH"
query() { [ "$GPU" = a100 ] && echo "$Q_A100" || echo "$Q_H100"; }
best() { vastai search offers "$(query)" -o dph_total --limit 1 --storage $DISK --raw | python3 -c "import json,sys;o=json.load(sys.stdin);print(o[0]['id'],round(o[0]['dph_total'],3),o[0]['gpu_name']) if o else print('NONE')"; }
bundle() {
  [ -s data/train.jsonl ] || python3 build_train_set.py
  tar czf /tmp/usuba_train_bundle.tgz -C "$ROOT" train/config.yaml train/train_lora.py train/export_gguf.py train/remote_setup.sh train/prompt.py train/data/train.jsonl train/data/val.jsonl train/data/manifest.json
  ls -la /tmp/usuba_train_bundle.tgz
}
KEY=${VAST_SSH_KEY:-$HOME/.ssh/vast_ed25519}
SO="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -i $KEY"
ssh_of() { vastai ssh-url "$(cat $ST)" | sed 's#ssh://##'; }
case $CMD in
plan)
  bundle; python3 -c "import json;print(json.load(open('dry_run_stats.json')))" 2>/dev/null || echo "(run the CPU dry run first: python3 train_lora.py --dry-run)"
  echo "credit: $(vastai show user --raw | python3 -c 'import json,sys;print(round(json.load(sys.stdin)["credit"],2))') USD"
  echo "H100 best: $(GPU=h100; best)"; echo "A100 best: $(GPU=a100; best)";;
up)
  [ $YES = 1 ] || { echo "refusing to rent without --yes"; exit 2; }
  [ -f $ST ] && { echo "instance already recorded in $ST"; exit 2; }
  if [ "$(vastai show ssh-keys --raw | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')" = 0 ]; then
    echo "registering $KEY.pub with Vast"; vastai create ssh-key "$(cat $KEY.pub)"; fi
  bundle; read -r OID DPH NAME < <(best); [ "$OID" = NONE ] && { echo "no offer under \$$MAXDPH/h for $GPU"; exit 3; }
  echo "renting $NAME offer $OID at \$$DPH/h"
  vastai create instance $OID --image $IMAGE --disk $DISK --ssh --direct --label usuba-9b-lora --raw | python3 -c "import json,sys;print(json.load(sys.stdin)['new_contract'])" > $ST
  echo "instance $(cat $ST); waiting for ssh..."
  for i in $(seq 1 60); do S=$(ssh_of 2>/dev/null || true); [ -n "$S" ] && ssh $SO -p ${S##*:} ${S%:*} true 2>/dev/null && break; sleep 20; done
  S=$(ssh_of); P=${S##*:}; HST=${S%:*}
  scp $SO -P $P /tmp/usuba_train_bundle.tgz $HST:/workspace/
  ssh $SO -p $P $HST "mkdir -p /workspace/usuba && tar xzf /workspace/usuba_train_bundle.tgz -C /workspace/usuba && (command -v tmux || (apt-get update -qq && apt-get install -y -qq tmux git cmake build-essential)) >/dev/null && tmux new -d -s train 'bash /workspace/usuba/train/remote_setup.sh'"
  echo "started. follow: train/launch_vast.sh logs";;
status) vastai show instance "$(cat $ST)";;
logs) S=$(ssh_of); ssh $SO -p ${S##*:} ${S%:*} "tail -n 40 /workspace/usuba/run.log; ls /workspace/usuba/ALL_DONE 2>/dev/null";;
fetch)
  S=$(ssh_of); P=${S##*:}; HST=${S%:*}; mkdir -p "$T/out"
  scp $SO -P $P -r "$HST:/workspace/usuba/train/out/usuba-9b-lora" "$T/out/"
  scp $SO -P $P "$HST:/workspace/usuba/train/out/export/usuba-9b-Q4_K_M.gguf*" "$HST:/workspace/usuba/run.log" "$T/out/"
  ls -la "$T/out";;
down) vastai destroy instance "$(cat $ST)" && rm -f $ST && echo destroyed;;
*) echo "usage: $0 plan|up --yes|status|logs|fetch|down"; exit 1;;
esac
