#!/usr/bin/env bash
# Runs ON the Vast instance (inside /workspace/usuba). Installs deps, trains, merges, exports 4-bit GGUF.
set -euo pipefail
cd /workspace/usuba/train
exec > >(tee -a /workspace/usuba/run.log) 2>&1
echo "== setup $(date -u +%FT%TZ)"; nvidia-smi --query-gpu=name,memory.total --format=csv
pip install -q -U "transformers>=5.2,<6" "peft>=0.18" accelerate pyyaml sentencepiece torchvision pillow
pip install -q flash-linear-attention causal-conv1d || echo "WARN: fla/causal-conv1d not installed; Gated DeltaNet falls back to the slow torch path"
python3 train_lora.py --config config.yaml --dry-run
python3 train_lora.py --config config.yaml
echo "== merge + export $(date -u +%FT%TZ)"
python3 export_gguf.py --adapter out/usuba-9b-lora/best --out out/export
touch /workspace/usuba/ALL_DONE; echo "== done $(date -u +%FT%TZ)"
