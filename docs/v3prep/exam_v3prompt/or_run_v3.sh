#!/bin/bash
# usage: or_run_v3.sh slug short ctx ; Dell key then holdout, prompt v3, reason grading with the open-weights judge (the original run used a Haiku judge; superseded, see docs/ANTHROPIC_TERMS_COMPLIANCE.md)
cd /workspace/wt-retrain-v2
slug=$1; short=$2; ctx=$3
L=/workspace/usuba-runs/exam-v3prompt/logs
python3 eval/hancore_holdout/run_eval.py --set dellkey --backend openai --base-url https://openrouter.ai/api/v1 --model $slug --key-env OPENROUTER_API_KEY --model-ctx $ctx --prompt v3 --workers 6 --max-cost 1.0 --name dellkey-v3p-$short > $L/dell-$short.log 2>&1
python3 eval/dellkey/reason_grade.py dellkey-v3p-$short --judge >> $L/dell-$short.log 2>&1
python3 eval/hancore_holdout/run_eval.py --set hancore --backend openai --base-url https://openrouter.ai/api/v1 --model $slug --key-env OPENROUTER_API_KEY --model-ctx $ctx --prompt v3 --workers 6 --max-cost 1.0 --name holdout-v3p-$short > $L/hold-$short.log 2>&1
echo FINISHED > $L/done-$short
