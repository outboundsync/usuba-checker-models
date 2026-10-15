#!/bin/bash
set -x; cd /root/w

(HF_XET_HIGH_PERFORMANCE=1 hf download Qwen/Qwen3.6-27B --local-dir /root/base --max-workers 16 >dl.log 2>&1; echo DL_DONE >>dl.log) &
pip install -q peft datasets accelerate flash-linear-attention >pip.log 2>&1; echo PIP_DONE >>pip.log
python3 -c "import flash_attn" 2>/dev/null && export FA=1 || export FA=0; echo FA=$FA
wait
python3 train_q27.py 1e-4 2 16384 || exit 1
python3 gen_q27.py merged_q27 || exit 1
echo PIPE_DONE
