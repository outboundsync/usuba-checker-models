# omarchy-specialist

Experiment: fine-tune small open models (Qwen-coder 7B "Santoku", and a 14B) with QLoRA to write valid **Omarchy (Quattro / omarchy-shell) plugins**, and measure them honestly.

## Honest current status
- The original "validator-style" shallow checker (manifest/static checks only) gave **invalid, inflated scores**. Do not trust any numbers derived from it (`functest/old_scores.py` exists only for comparison).
- On the real functional test (`functest/`, 56 holdout tasks, plugins actually loaded and exercised):

| Model | Pass /56 |
|---|---|
| Reference solutions | 51 |
| GPT-5.6 | 29 |
| Opus | 28 |
| Santoku 7B LoRA (`runs/fix/adapter_b`) | **8** |

The fine-tuned 7B is far behind frontier models. Not production-ready. The tuned 14B (`runs/fix14/adapter_b14`) is included for further evaluation.

## Layout
- `validator/` – upstream `omarchy-plugin-validate` contract (MIT, see NOTICE).
- `functest/` – real functional test harness (`functest.py`, `runtime.py`, `static_checks.py`), calibration and `results.json`. `functest/cache/` is git-ignored.
- `build_dataset.py`, `build_dataset_v1.py`, `gen_docs.py`, `tools_analyze.py` – dataset build scripts. See `DATASET.md` for the dataset doc.
- `data/` – `train.jsonl`, `holdout.jsonl`, stats.
- `sources/` – source catalog metadata and licenses. Third-party repo clones (`sources/repos/`, ~900MB) are **not** committed; re-clone with `sources/clone.sh`.
- `runs/` – training/generation/eval scripts and outputs (jsonl) per run; LoRA adapters via Git LFS:
  - `runs/fix/adapter_b` – Santoku 7B LoRA
  - `runs/fix14/adapter_b14` – tuned 14B LoRA
- `clean/` – holdout dedupe/rescoring work (in progress).
- `dell-smoke/` – sample plugins for on-device smoke testing.

## Running the functest
```bash
python -m venv .venv && . .venv/bin/activate
python functest/functest.py --help      # entry point
python functest/rescore.py              # rescore generated outputs into results.json
```
Needs the Omarchy shell runtime deps described in `functest/runtime.py`. API-backed generators read keys only from env vars (`OPENROUTER_API_KEY`, `XAI_API_KEY`); no keys are stored in this repo.

Clone with `git lfs install` first to get the adapter weights.
