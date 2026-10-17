# Usuba Checker model

A small local reviewer model for [Omarchy](https://omarchy.org) shell plugins. It reads a plugin together with the report from the **Usuba Checker scripts** (deterministic Python checks, in `outboundsync/usuba-checker-scripts`) and writes a review: what is broken, why, and how to fix it.

## Model card

| | |
|---|---|
| Base | Qwen 3.5 9B |
| Quantization | 4-bit (about 5.5 GB of weights), runs locally on a 32 GB iGPU laptop |
| Training data | Omarchy plugin data: public community plugins from the omarchyplugins.com catalog and GitHub, Checker reports on them, issue/bug pairs, and labeled real-device (Dell) runs. Provenance in `sources/` and `DATASET.md` |
| Input | Plugin source + Checker report (rule ids from the Usuba Standard) |
| Output | A review that explains the failures and proposes fixes |
| Not for | Deciding pass/fail. The Checker scripts make the verdict; the model explains it |

The plan and its reasoning are in [`docs/TRAINING_PLAN.md`](docs/TRAINING_PLAN.md). Earlier experiments (Qwen-coder 7B "Santoku" and a 14B QLoRA writing plugins) are documented in [`docs/LEGACY_README.md`](../../docs/LEGACY_README.md).

## Layout

| Path | What it is |
|---|---|
| `data/`, `clean/`, `v3/` | Training and holdout sets, dedupe/cleaning, v3 dataset build |
| `sources/` | Source catalog, contributor counts, licenses, clone script (clones themselves are not committed) |
| `build_dataset*.py`, `gen_docs.py`, `tools_*.py` | Dataset build scripts. `DATASET.md`, `NOTICE` document them |
| `runs/` | Training, generation and eval runs: `uplift/` (frontier-model uplift, TABLE.md, charts), `rescore404/`, `fix/`, `fix14/` (LoRA adapters via LFS), `q27/`, `v3/`, scoreboards |
| `eval/functest/` | Checker-based eval drivers and results: rescoring, calibration, Dell ground truth, batch results. They import the Checker from the scripts repo |
| `dell/` | Real-device work: `INSIGHTS.md`, `batch3/`, `batch4/`, `smoke/`, `loop/`, `rounds/`, `bugpairs/`, `sweep/` (marketplace corpus and results) |
| `docs/` | `TRAINING_PLAN.md`, outside reviews of the plan (`reviews/`), post drafts |

## Setup

```sh
git lfs install && git clone https://github.com/outboundsync/usuba-checker-models.git
git clone https://github.com/outboundsync/usuba-checker-scripts.git   # the Checker, needed by eval/
```

Files over 10 MB (datasets, adapters, catalogs) are in Git LFS. API-backed generators read keys only from environment variables; no keys are stored here.

**Paths:** this repo was split out of `usuba-model-checker` on 2026-10-13 with history kept. Some older scripts still use the old paths (`functest/`, `dell-batch3/`, `dell_rounds/`, `reviews/`). The new homes: `functest/` → `eval/functest/` (Checker core moved to the scripts repo), `dell-batch3/` → `dell/batch3/`, `dell-smoke/` → `dell/smoke/`, `dell_loop/` → `dell/loop/`, `dell_rounds/` → `dell/rounds/`, `reviews/` → `docs/reviews/`.
