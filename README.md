# usuba-checker-models

Training code, data policy, exam results and release notes for **Usuba**, a local reviewer model (LoRA on **Qwen3.5-9B**, Apache-2.0 base) that reads an Omarchy
plugin plus the [Usuba Checker](https://github.com/outboundsync/usuba-checker-scripts) report and answers with a JSON verdict and findings.
The deterministic Checker, mining pipelines and exam harness live in `usuba-checker-scripts`; this repository is everything that trains, ships and reports the model.

> Status: research artefact, not production-ready. The numbers below are the honest ones, including the bad one.

## Results (329-plugin sealed HANCORE holdout: 300 positives, 29 negatives; summary tables only)
Verified against the result files in `eval/hancore_holdout/results/` (copied from the exam runs); one run per system, no confidence intervals.

**Always answering "changes requested" scores 0.912 verdict accuracy (300/329), recall 1.0 and false alarm 1.0**, so verdict accuracy alone proves little: read it together with the false-alarm and category columns.

Headline rows (prompt v1, i.e. the prompt Usuba 9B was trained with; `usuba-9b-q4km.json`, `stock-qwen3.5-9b-openrouter.json`, `checker-baseline.json`, `frontier-sonnet-5.5.json`):
| System | verdict acc | positive recall | false alarm (29 neg) | category recall | category precision | JSON valid |
|---|---|---|---|---|---|---|
| **Usuba 9B (Q4_K_M)** | 0.812 | 0.883 | 0.931 | 0.402 | 0.427 | 0.909 |
| Stock Qwen3.5-9B (OpenRouter) | 0.699 | 0.737 | 0.690 | 0.173 | 0.420 | 0.766 |
| Checker alone (no model) | 0.650 | 0.673 | 0.586 | 0.131 | 0.442 | 1.000 |
| Claude Sonnet 5.5 with its own skill prompt (score only) | 0.374 | 0.330 | 0.172 | 0.347 | 0.397 | 0.997 |

Like-for-like re-run of stock and open peers on prompt v3 (Usuba 9B was **not** run on prompt v3; Oct 15 re-run; `holdout-v3p-*.json`) and on prompt v2 (`holdout-v2-*.json`):
| System | v3 acc / recall / false alarm / cat. recall | v2 acc / cat. recall |
|---|---|---|
| Qwen3.5-9B stock | 0.745 / 0.790 / 0.724 / 0.070 | 0.541 / 0.004 |
| Nemotron 3 Nano 30B | 0.888 / 0.967 / 0.931 / 0.055 | 0.909 / 0.003 |
| Gemma 3 12B | 0.751 / 0.797 / 0.724 / 0.058 | 0.802 / 0.018 |
| Ministral 14B | 0.699 / 0.727 / 0.586 / 0.116 | 0.529 / 0.001 |
| Gemma 4 26B-A4B | 0.638 / 0.673 / 0.724 / 0.031 | 0.757 / 0.001 |
| Llama 3.1 8B | 0.526 / 0.527 / 0.483 / 0.021 | 0.331 / 0.020 |
| GLM 4.7 Flash | 0.465 / 0.427 / 0.138 / 0.032 | 0.371 / 0.037 |
| Qwen3-Coder 30B-A3B | 0.471 / 0.443 / 0.241 / 0.007 | 0.240 / 0.001 |

What the numbers say: Usuba 9B has by far the best category recall (0.402 vs at most 0.116 for any open peer) but flags 27 of 29 clean plugins, so it is not a usable gate on its own. Stock Qwen3.5-9B moves from 0.699 to 0.745 to 0.541 accuracy depending only on the prompt, so single numbers are prompt-sensitive.
Full tables: `docs/TRAINING_PLAN.md`. Raw model outputs (including all proprietary-model outputs) are **not** published.

## Training data provenance
No proprietary-model output (Anthropic, OpenAI, Google, xAI or any closed model) was used to train Usuba. Rows come from licensed real plugins, public review findings,
Checker reports, real upstream fix commits, and review text written by the open-weights teacher Qwen3.5-397B-A17B (Apache-2.0). Method: `train/v2/distill/METHODS.md`,
`TEACHER.md`, `docs/PROVENANCE.md`. Proprietary models appear only as evaluation baselines (score tables).

## Where things are
| Path | Content |
|---|---|
| `train/` | Training: `build_train_set.py`, `config.yaml`, `train_lora.py`, `launch_vast.sh`, `export_gguf.py`, prompts, watchdog, tests; `v2/` distillation; `v3data/` data builders (r2 to r4) |
| `clean/`, `v3/`, `data/`, `v3fixes/` | Dataset builders, manifests, reports (the dataset files themselves are on Hugging Face, see `docs/DATA_HOSTING.md`) |
| `sources/` | `plugin_sources.json` (repo URL + commit SHA + licence of every third-party plugin source), `fetch_plugin_sources.py`, licences, `SOURCES.md` |
| `NOTICE`, `sources/licenses/` | Per-source attribution and licence texts that must travel with the data and model |
| `docs/` | `REPLICATION.md`, `TRAINING_CHECKLIST.md`, `TRAINING_PLAN.md`, `MODEL_CARD.md`, `PROVENANCE.md`, `DATA_HOSTING.md`, method notes |
| `runs/` | Experiment scripts, score tables, charts (no raw generations) |
| `hf/` | Hugging Face cards and SHA-256 manifest for datasets and adapters (datasets prepared, not uploaded; adapter weights withheld, hashes only) |

## Replicate
Read [`docs/REPLICATION.md`](docs/REPLICATION.md), then follow [`docs/TRAINING_CHECKLIST.md`](docs/TRAINING_CHECKLIST.md) step by step.

## Licences
- Code and documentation: MIT (`LICENSE`).
- Datasets: each row keeps the licence of the plugin it came from (`meta.license`: MIT, Apache-2.0, ISC), with attribution in `NOTICE`. They are not relicensed.
- Adapters: follow the base model's licence. Base model Qwen3.5-9B is Apache-2.0 (verified 2026-10-15 on https://huggingface.co/Qwen/Qwen3.5-9B, `license: apache-2.0`). Earlier experiments on Qwen2.5-Coder-7B-Instruct are also Apache-2.0.

## Security
See `SECURITY.md`. CI runs gitleaks and `tools/scan_public.py`.
