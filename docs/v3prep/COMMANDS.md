# v3-prep: exact commands, inputs, models, seeds, costs (2026-10-15)
Repo worktree: branch v3-prep (off v3-data cff8fe5). Keys come from env `OPENROUTER_API_KEY` (never stored).
## 1. Exam rerun on prompt v3 (stock Qwen3.5 9B + 7 open peers; no Usuba, DeepSeek or Anthropic comparison rows)
- Scripts: `exam_v3prompt/or_run_v3.sh SLUG SHORT CTX` (per system), `exam_v3prompt/runall.sh` (3 parallel lanes). Per system it runs
  `python3 eval/hancore_holdout/run_eval.py --set dellkey --backend openai --base-url https://openrouter.ai/api/v1 --model SLUG --key-env OPENROUTER_API_KEY --model-ctx CTX --prompt v3 --workers 6 --max-cost 1.0 --name dellkey-v3p-SHORT`,
  then `python3 eval/dellkey/reason_grade.py dellkey-v3p-SHORT --judge` (judge anthropic/claude-haiku-5.5 via OpenRouter, grading only), then the same run_eval with `--set hancore --name holdout-v3p-SHORT`.
- Models (slug, ctx cap): qwen/qwen3.5-9b 262144; mistralai/ministral-14b-2512 262144; google/gemma-4-26b-a4b-it 262144; google/gemma-3-12b-it 131072; qwen/qwen3-coder-30b-a3b-instruct 262144; z-ai/glm-4.7-flash 202752; nvidia/nemotron-3-nano-30b-a3b 262144; meta-llama/llama-3.1-8b-instruct 131072.
- Inputs: Dell key 90 decided rows (functest/dell_ground_truth.jsonl, whole files), HANCORE holdout 329 (eval/hancore_holdout/manifest.jsonl). Seeds: none; request temperature=0, one run per system.
- Cost: $3.02 OpenRouter (eval + judge), cap was $5. Results/tables/sha256: `exam_v3prompt/`. 4 Dell rows across three systems hit context overflow (scored invalid; see logs).
## 2. HANCORE recovery r2
- `python3 hancore/label_recover.py --max-cost 8.5 --workers 8` (run from hancore/; needs /workspace/hancore_cache, hancore-labels/src_full, gh for tarballs). Model qwen/qwen3.5-397b-a17b, temperature 0, reasoning off, data_collection deny. Output dir default /workspace/usuba-runs/hancore-labels-r2 (copied here as `hancore_labels_r2/`). Result: 319/1719 recovered (179 high, 140 medium), $6.22. See hancore_labels_r2/REPORT.md. Resumable via raw.jsonl. Not merged into training data.
## 3. Midcheck
- `python3 train/train_lora.py --config train/config.yaml --midcheck 100 [--midcheck-n 30 --midcheck-pool POOL.jsonl --midcheck-max-new 400 --midcheck-max-secs 1200]` (training seed 1337 in config; midcheck decoding is greedy). Test: `python3 -m pytest train/tests/test_midcheck.py -q` (CPU, 3 tests pass).
