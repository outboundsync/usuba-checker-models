#!/usr/bin/env bash
# Runs ON the Vast instance (/workspace/usuba). Idempotent: re-running resumes from the newest complete checkpoint.
set -uo pipefail
cd /workspace/usuba/train
OUT=$(python3 -c "import yaml;print(yaml.safe_load(open('config.yaml'))['output_dir'])") || { echo FATAL: cannot read config.yaml; exit 1; }
exec > >(tee -a /workspace/usuba/run.log) 2>&1
echo "== setup $(date -u +%FT%TZ)"; nvidia-smi --query-gpu=name,memory.total --format=csv; df -h / /dev/shm | tail -2
# Vast container disks can be far smaller than requested (32 GB seen on a --disk 150 rental). The 18 GB base model lives in
# RAM-backed /dev/shm when it is big enough, leaving the disk for checkpoints and the final GGUF.
if [ "$(df --output=avail -B1G /dev/shm | tail -1)" -gt 60 ]; then export HF_HOME=/dev/shm/hf; mkdir -p $HF_HOME; echo "HF_HOME=$HF_HOME"; fi
[ "$(df --output=avail -B1G / | tail -1)" -ge 15 ] || { echo "FATAL: under 15 GB free on / (need checkpoints + 5.5 GB GGUF)"; exit 1; }
bash /workspace/usuba/train/deps.sh || exit 1
[ -d $OUT/checkpoints ] || python3 train_lora.py --config config.yaml --dry-run || exit 1
if [ "${SMOKE_STEPS:-0}" != 0 ]; then   # paid smoke test: a few optimizer steps, a checkpoint, then exit
  python3 - <<PY
import yaml; c=yaml.safe_load(open("config.yaml")); c.update(save_every_steps=2, eval_every_steps=5, eval_every_epochs=0, allow_no_midrun_eval=True, max_hours=${SMOKE_HOURS:-0.15}, output_dir="out/smoke")
yaml.safe_dump(c, open("config_smoke.yaml","w"))
PY
  python3 train_lora.py --config config_smoke.yaml --resume; echo "== smoke train exit $? $(date -u +%FT%TZ)"
  if [ "${SMOKE_EXPORT:-1}" = 1 ]; then python3 export_gguf.py --adapter out/smoke/last --out out/smoke_export && rm -rf out/smoke_export/merged-bf16 out/smoke_export/usuba-9b-bf16.gguf; echo "== smoke export exit $?"; fi
  if [ "${SMOKE_EXPORT:-1}" = 1 ] && [ "${SMOKE_PARITY:-1}" = 1 ]; then   # parity on the smoke adapter, then drop the 5.5 GB GGUF (sha256 + meta stay) so the smoke fetch is small
    GG=$(ls out/smoke_export/*.gguf 2>/dev/null | head -1)
    [ -n "$GG" ] && timeout ${PARITY_TIMEOUT:-1000} python3 export_parity.py "$GG" out/smoke/last --n ${PARITY_N:-2} --max-new ${PARITY_MAX_NEW:-512} 2>&1 | tee /workspace/usuba/PARITY_REPORT.txt
    echo "== smoke parity done (rc ${PIPESTATUS[0]})"; rm -f out/smoke_export/*.gguf
  fi
  touch /workspace/usuba/SMOKE_DONE; exit 0
fi
# midcheck_args comes from config.yaml (r7: empty. midcheck.py scores the old findings[] schema; scope-v4 targets have scripts_triage/added_findings, so it would be a no-op or fatal setup error)
MIDARGS=$(python3 -c "import yaml;print(yaml.safe_load(open('config.yaml')).get('midcheck_args') or '')")
python3 train_lora.py --config config.yaml --resume $MIDARGS; rc=$?
echo "== train exit $rc $(date -u +%FT%TZ)"
# TRAIN_STOPPED only for a deliberate terminal stop (max_hours / max_steps). A crash or a signal kill leaves no marker, so the on-box watchdog restarts from the checkpoint.
[ -f $OUT/DONE ] || { echo "training not finished (rc=$rc); re-run this script to resume"; grep -qE "max_hours|max_steps" $OUT/STOPPED 2>/dev/null && touch /workspace/usuba/TRAIN_STOPPED; exit $rc; }
echo "== merge + export $(date -u +%FT%TZ)"
AD=$OUT/best-task; [ -d $AD ] || AD=$OUT/best    # checkpoint chosen on the midcheck task metric (negatives included) when it exists, else best val loss
python3 export_gguf.py --adapter $AD --out out/export || exit 1
rm -rf out/export/merged-bf16 out/export/usuba-9b-bf16.gguf   # regenerable from the adapter; keeps the sync small
# export parity (GGUF vs HF+adapter, greedy, VAL rows). Time-boxed and NON-fatal for ALL_DONE (the artifacts are already safe); result in PARITY_REPORT.txt
GG=$(ls out/export/*.gguf | head -1)
[ -n "$GG" ] && PARITY_TIMEOUT=${PARITY_TIMEOUT:-2400} && timeout $PARITY_TIMEOUT python3 export_parity.py "$GG" $AD --n ${PARITY_N:-6} --max-new ${PARITY_MAX_NEW:-768} 2>&1 | tee /workspace/usuba/PARITY_REPORT.txt
touch /workspace/usuba/ALL_DONE; echo "== done $(date -u +%FT%TZ)"
