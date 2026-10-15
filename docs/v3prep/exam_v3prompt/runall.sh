#!/bin/bash
cd /workspace/usuba-runs/exam-v3prompt
run(){ ./or_run_v3.sh "$@"; }
( run qwen/qwen3.5-9b stock-qwen3.5-9b 262144; run mistralai/ministral-14b-2512 ministral-14b 262144; run meta-llama/llama-3.1-8b-instruct llama-3.1-8b 131072 ) &
( run google/gemma-4-26b-a4b-it gemma-4-26b 262144; run google/gemma-3-12b-it gemma-3-12b 131072; run z-ai/glm-4.7-flash glm-4.7-flash 202752 ) &
( run qwen/qwen3-coder-30b-a3b-instruct qwen3-coder-30b-a3b 262144; run nvidia/nemotron-3-nano-30b-a3b nemotron-3-nano 262144 ) &
wait; echo ALL_DONE > logs/ALL_DONE
