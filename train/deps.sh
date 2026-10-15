#!/usr/bin/env bash
# Idempotent dependency install (sourced/run by remote_setup.sh, dry_run.sh, resume_test.sh)
# FIX: unpinned pip -U pulled torch 2.14+cu130, which the host driver (570 / CUDA 12.8) cannot run; torch stays pinned to the image's 2.9.1+cu128
if [ ! -f /workspace/usuba/.deps_ok ]; then
  pip uninstall -y -q torchaudio 2>/dev/null   # unused; breaks imports once transformers/torchvision pull a newer torch
  pip install -q -U "transformers>=5.2,<6" "peft>=0.18" accelerate pyyaml sentencepiece torchvision pillow safetensors "torch==2.9.1" "torchvision==0.24.1" || return 1 2>/dev/null || exit 1
  pip install -q flash-linear-attention || echo "WARN: flash-linear-attention not installed"
  # causal-conv1d has no wheel for every torch/CUDA combo; building needs torch visible (no build isolation) and nvcc
  MAX_JOBS=16 pip install -q --no-build-isolation causal-conv1d || echo "WARN: causal-conv1d not installed (conv falls back to torch; minor)"
  python3 -c "import fla; print('fla', fla.__version__)" || { echo "FATAL: flash-linear-attention missing (Gated DeltaNet would be very slow)"; return 1 2>/dev/null || exit 1; }
  touch /workspace/usuba/.deps_ok
fi
