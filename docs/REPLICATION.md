# Replication guide: usuba-checker-models

Companion to `usuba-checker-scripts/docs/REPLICATION.md`. Order of operations: `docs/TRAINING_CHECKLIST.md`.

## What you can reproduce without anything private
- The dataset **as published** (Hugging Face, `docs/DATA_HOSTING.md`), verified by `hf/MANIFEST.sha256`.
- Training from it: `train/build_train_set.py` reads it, `train/launch_vast.sh` or `train/train_lora.py` trains (config in `train/config.yaml`, seed 1337).
- Export and exam: `train/export_gguf.py`, `scripts:eval/hancore_holdout/*` (needs the holdout manifest, which only the owner has; use your own holdout to compare).
- Plugin sources: `sources/plugin_sources.json` + `sources/fetch_plugin_sources.py` (pinned commits, permissive licences only).

## What needs private or unpublished inputs
| Step | Missing input | Workaround |
|---|---|---|
| `train/v3data/reproduce_r3.sh`, `reproduce_r4.sh`, `dell_audit.py`, `build_v3_data.py` | hardware-verified answer key (exclusion ids), device sweep run records, review-label corpus, offline LLM-reply cache | Re-fetch reviews via `scripts:hancore/fetch.py`, run your own device sweep, and pay for the teacher calls (`[$]`, a few USD); or start from the published dataset |
| r4 dataset | pending | `train/v3data/R4_TODO.md` |
| `runs/*` experiments | raw generations are not published | score tables only; rerun the generation scripts |
| `data/reviews`, `data/hancore_reviewer` | raw review text (other people's posts) | re-fetch, see `scripts:hancore/` |

Absolute paths such as `/workspace/...` in older scripts are the original working layout; override with the documented env vars (`REPO`, `R_WORK`, `R_OUT`, `OUT`) or edit them.

## Licences you inherit
Dataset rows keep their per-row licence (see `NOTICE`, `sources/licenses/`): attribution must travel with any copy. Adapters follow the base model (Apache-2.0 for Qwen3.5-9B).
