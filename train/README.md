# Usuba 9B training (bf16 LoRA, Qwen 3.5 9B)
1. `python3 train/build_train_set.py` builds `train/data/{train,val}.jsonl` and `manifest.json`. The data is not committed (122 MB); it rebuilds deterministically from the repo plus the box sweep repos.
2. `python3 train/train_lora.py --config train/config.yaml --dry-run` does a CPU-only check: tokenization, masking and length stats.
3. `train/launch_vast.sh plan` makes no spend. It shows credit, the best H100/A100 offers and the bundle size.
4. `train/launch_vast.sh up --yes`: rent, upload, run `remote_setup.sh` in tmux (train, then merge, then GGUF Q4_K_M).
5. `train/launch_vast.sh logs` until `ALL_DONE`, then `fetch`, then `down`. Always run `down`, since billing continues until the instance is destroyed.
6. Eval: see `eval/hancore_holdout/run_eval.py --help`.
