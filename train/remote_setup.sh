#!/usr/bin/env bash
# Runs ON the Vast instance (/workspace/usuba). Idempotent: re-running resumes from the newest complete checkpoint.
set -uo pipefail
cd /workspace/usuba/train
exec > >(tee -a /workspace/usuba/run.log) 2>&1
echo "== setup $(date -u +%FT%TZ)"; nvidia-smi --query-gpu=name,memory.total --format=csv; df -h / /dev/shm | tail -2
# Vast container disks can be far smaller than requested (32 GB seen on a --disk 150 rental). The 18 GB base model lives in
# RAM-backed /dev/shm when it is big enough, leaving the disk for checkpoints and the final GGUF.
if [ "$(df --output=avail -B1G /dev/shm | tail -1)" -gt 60 ]; then export HF_HOME=/dev/shm/hf; mkdir -p $HF_HOME; echo "HF_HOME=$HF_HOME"; fi
[ "$(df --output=avail -B1G / | tail -1)" -ge 15 ] || { echo "FATAL: under 15 GB free on / (need checkpoints + 5.5 GB GGUF)"; exit 1; }
if [ ! -f /workspace/usuba/.deps_ok ]; then
  pip uninstall -y -q torchaudio 2>/dev/null   # unused; breaks imports once transformers/torchvision pull a newer torch
  pip install -q -U "transformers>=5.2,<6" "peft>=0.18" accelerate pyyaml sentencepiece torchvision pillow safetensors || exit 1
  pip install -q flash-linear-attention || echo "WARN: flash-linear-attention not installed"
  # causal-conv1d has no wheel for every torch/CUDA combo; building needs torch visible (no build isolation) and nvcc
  MAX_JOBS=16 pip install -q --no-build-isolation causal-conv1d || echo "WARN: causal-conv1d not installed (conv falls back to torch; minor)"
  python3 -c "import fla; print('fla', fla.__version__)" || { echo "FATAL: flash-linear-attention missing (Gated DeltaNet would be very slow)"; exit 1; }
  touch /workspace/usuba/.deps_ok
fi
[ -d out/usuba-9b-lora/checkpoints ] || python3 train_lora.py --config config.yaml --dry-run || exit 1
if [ "${SMOKE_STEPS:-0}" != 0 ]; then   # paid smoke test: a few optimizer steps, a checkpoint, then exit
  python3 - <<PY
import yaml; c=yaml.safe_load(open("config.yaml")); c.update(save_every_steps=2, eval_every_steps=2, max_hours=${SMOKE_HOURS:-0.15}, output_dir="out/smoke")
yaml.safe_dump(c, open("config_smoke.yaml","w"))
PY
  python3 train_lora.py --config config_smoke.yaml --resume; echo "== smoke train exit $? $(date -u +%FT%TZ)"
  if [ "${SMOKE_EXPORT:-1}" = 1 ]; then python3 export_gguf.py --adapter out/smoke/last --out out/smoke_export && rm -rf out/smoke_export/merged-bf16 out/smoke_export/usuba-9b-bf16.gguf; echo "== smoke export exit $?"; fi
  touch /workspace/usuba/SMOKE_DONE; exit 0
fi
python3 train_lora.py --config config.yaml --resume; rc=$?
echo "== train exit $rc $(date -u +%FT%TZ)"
[ -f out/usuba-9b-lora/DONE ] || { echo "training not finished (rc=$rc); re-run this script to resume"; touch /workspace/usuba/TRAIN_STOPPED; exit $rc; }
echo "== merge + export $(date -u +%FT%TZ)"
python3 export_gguf.py --adapter out/usuba-9b-lora/best --out out/export || exit 1
rm -rf out/export/merged-bf16 out/export/usuba-9b-bf16.gguf   # regenerable from the adapter; keeps the sync small
touch /workspace/usuba/ALL_DONE; echo "== done $(date -u +%FT%TZ)"
