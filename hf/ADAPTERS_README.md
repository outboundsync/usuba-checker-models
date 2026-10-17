---
license: apache-2.0
base_model: Qwen/Qwen3.5-9B
library_name: peft
pipeline_tag: text-generation
tags: [omarchy, quickshell, qml, code-review, lora]
---
# Usuba Checker Model v0.1.0 (run 2)

**Status: released as v0.1.0 (2026-10-17).** An early release, shared as an invitation to help. Advisory only: do not use it as an automated accept/reject gate. The verdict comes from the Usuba Checker Scripts ([v0.1.0](https://github.com/outboundsync/usuba-checker-scripts/releases/tag/checker-v0.1.0)); this model reads their report and explains. Release notes: [GitHub, model-v0.1.0](https://github.com/outboundsync/usuba-checker-models/releases/tag/model-v0.1.0). Project site: [usuba.dev](https://usuba.dev).

## What is here
| path | what |
|---|---|
| `adapter/` | LoRA adapter (PEFT, r=32, alpha=64, dropout 0.05, all attention/MLP projections), `best` checkpoint of **run 2**. `adapter_model.safetensors`: 346,294,736 bytes, sha256 `79cb47183b6577aa046ae2c89f961bd5538f3353ab3eee48455b026946242bb2` |
| `gguf/usuba-9b-usuba-9b-lora-r7-best-Q4_K_M.gguf` | Adapter merged into the base and quantised to Q4_K_M with llama.cpp. 5,629,108,800 bytes, sha256 `7d2b54a24f335aa31d53a47fca8e0848add83bef8246f0f7f831c0e80c9e4f8e` |

## Training
- Base: **Qwen/Qwen3.5-9B** (Apache-2.0), revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`.
- Run 2: **221 train / 23 validation rows**, 28 steps, lr 1e-4 cosine, seed 1337, scope prompt v4. Final validation loss 0.263.
- Task: read an Omarchy (Quickshell/QML) plugin plus the Checker Scripts report; answer in a fixed JSON format with a verdict and findings.

## How it was scored — read this first
**All scores below are for the bf16 merge of base + adapter, not for the Q4_K_M file in this repo.** The Q4_K_M file has not been tested on any exam set; its speed and accuracy are unmeasured. One-shot, same harness, schema, quote filter and greedy decoding as the stock Qwen3.5-9B comparison. Labels are machine drafts; invalid answers count as wrong. Sets are small (Dell 75: 28 broken, 47 working; S4 60: mined upstream bug locations; HANCORE holdout 329: 300 positives, 29 negatives), so differences of a few points are noise. Source: `docs/post/draft.md` (usuba-checker-scripts) and `R7_RUN2_EXAM.md`.

## What it did well
It learned the fixed review format. Valid-answer rate, Usuba run 2 vs stock Qwen3.5-9B:

| exam set | Usuba run 2 | stock Qwen3.5-9B |
|---|---|---|
| Dell 75 | **0.987** | 0.893 |
| S4 60 | **0.917** | 0.567 |
| HANCORE holdout 329 | **0.939** | 0.638 |

Against the other open models in the same one-shot panel (Set 2), it has the best valid-answer rate on all three sets (Dell / S4 / holdout):

| model | valid: Dell / S4 / holdout |
|---|---|
| **Usuba run 2** | **0.987 / 0.917 / 0.939** |
| Stock Qwen3.5 9B | 0.893 / 0.567 / 0.638 |
| Gemma 4 26B | 0.853 / 0.783 / 0.824 |
| Qwen3-Coder 30B | 0.840 / 0.733 / 0.763 |
| GLM 4.7 Flash | 0.880 / 0.717 / 0.781 |
| Nemotron 3 Nano 30B | 0.813 / 0.633 / 0.650 |
| Ministral 14B | 0.680 / 0.467 / 0.571 |
| Llama 3.1 8B | 0.493 / 0.417 / 0.453 |

Other differences from stock (also within small-sample noise):
- Dell 75: it flags more broken plugins (0.607 vs 0.286).
- S4 60: bugs found 8 of 60 vs 4 of 60 for stock (within noise).
- It keeps far fewer of its own added findings after the quote filter: 13 vs 47 on S4, 64 vs 139 on the holdout, 30 vs 41 on Dell.
- HANCORE holdout: 8 of 29 clean plugins got a blocker or an invalid answer, vs 11 of 29 for stock.
- With the Checker feedback loop (Set 3) it stays at 0.93 [0.90-0.95] valid on the holdout; 70 of 75 Dell answers already passed every Checker check before any revision.

## Where it did not beat stock
- **Verdict accuracy is flat vs stock on the Dell 75: 0.480 [0.37-0.59] vs 0.507 [0.40-0.61]**; the intervals overlap heavily. With the Checker loop: 0.47 [0.36-0.57] vs 0.57 [0.47-0.68] for stock + loop.
- **The Checker Scripts alone score 0.773 [0.667-0.853] on the Dell 75 with no model.** In one-shot runs no model in the panel is above 0.56 (Gemma 4 26B); the best with the loop is Gemma 4 26B at 0.65 [0.55-0.76]. Always answering "broken" scores 0.373.
- False alarms on working Dell plugins rose from 0.277 (stock) to 0.574; on the 47 working Dell plugins it added a blocker 25 times vs 9 for stock. It rarely disagrees with the Checker (dismissed 3 of 80 Checker findings on Dell, vs 43 of 71 for stock).
- The valid-answer charts show **format reliability, not better judgment.**

## Limitations
Only 221 training rows; one run, one seed; machine-draft labels; the Q4_K_M file is untested; Dell results come from one laptop (Omarchy 4.0.4).

## Reproducing
`REPRODUCE.md` lists the exact base revision, data hashes, hyperparameters, software versions, llama.cpp commit and Checker Scripts commit, and what is still missing. `training/` holds the run metadata, loss log and pinned requirements. The training data (public subset, with a row index) and the evaluation outputs of the latest round are in the dataset repo (`run2_data/`, `eval_2026-10-16/`). Verify this repo with `SHA256SUMS` (`sha256sum -c SHA256SUMS`; `adapter/SHA256SUMS` is the instance's own file and also lists an `adapter/README.md` that is not uploaded).

## Licence
The Usuba model weights and adapters (this repo) are Apache-2.0, matching the base model (Qwen/Qwen3.5-9B). Training data keeps each source plugin's licence (MIT, Apache-2.0, ISC); attribution in `NOTICE` here and `sources/licenses/` in the GitHub repo. The Checker Scripts and all code and docs in the GitHub repos are MIT (`LICENSE-repo-MIT.txt`).

## Links
- Models repo (training, data builders, docs): https://github.com/outboundsync/usuba-checker-models
- Checker Scripts repo: https://github.com/outboundsync/usuba-checker-scripts
- Training data: https://huggingface.co/datasets/osiharris/usuba-checker-data

Earlier experiment adapters (Qwen2.5-Coder-7B x2, Qwen3.5-9B run 1) are not uploaded; their hashes are in `hf/ADAPTERS_CARD.md` of the models repo.
