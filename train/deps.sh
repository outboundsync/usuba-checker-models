#!/usr/bin/env bash
# Idempotent dependency install (sourced/run by remote_setup.sh, dry_run.sh, resume_test.sh)
# FIX: unpinned pip -U pulled torch 2.14+cu130, which the host driver (570 / CUDA 12.8) cannot run; torch stays pinned to the image's 2.9.1+cu128
if [ ! -f /workspace/usuba/.deps_ok ]; then
  pip uninstall -y -q torchaudio 2>/dev/null   # unused; breaks imports once transformers/torchvision pull a newer torch
  # H: pinned by uv.lock (pyproject.toml [train] extra, exported to requirements-train.lock); torch/torchvision stay the image's pinned builds
  # the lock pins triton==3.8.0 (fla needs >= 3.7.1) but torch 2.9.1 requires triton 3.5.1: resolving them together is impossible, so install the lock WITHOUT triton, then force triton
  grep -v '^triton==' "$(dirname "${BASH_SOURCE[0]:-$0}")/requirements-train.lock" > /tmp/req-notriton.lock
  pip install -q "torch==2.9.1" "torchvision==0.24.1" -r /tmp/req-notriton.lock || return 1 2>/dev/null || exit 1
  pip install -q --no-deps "triton==3.8.0" || return 1 2>/dev/null || exit 1
  # FIX: fla refuses Triton 3.4-3.7.0 on Hopper (wrong gated bwd results); torch 2.9.1 pins 3.5.1, so override it (pip warns, works)
  # causal-conv1d has no wheel for every torch/CUDA combo; building needs torch visible (no build isolation) and nvcc
  MAX_JOBS=16 pip install -q --no-build-isolation causal-conv1d || echo "WARN: causal-conv1d not installed (conv falls back to torch; minor)"
  pip install -q --no-deps "triton==3.8.0" || { echo "FATAL: triton 3.8.0 install failed"; return 1 2>/dev/null || exit 1; }   # again: building causal-conv1d re-pulls torch's triton 3.5.1, which fla refuses on Hopper
  python3 -c "import fla; print('fla', fla.__version__)" || { echo "FATAL: flash-linear-attention missing (Gated DeltaNet would be very slow)"; return 1 2>/dev/null || exit 1; }
  python3 -c "import torch,sys;sys.exit(0 if torch.cuda.is_available() else 1)" || { echo "FATAL: torch cannot see the GPU"; return 1 2>/dev/null || exit 1; }
  touch /workspace/usuba/.deps_ok
fi
