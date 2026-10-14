# Usuba Vast training-run plan

## Base model (locked 2026-10-13, Harris)
- **Base: Qwen 3.5 9B**, for the Omarchy plugin checker fine-tune.
- Hardware floor: a typical laptop with 32 GB RAM and integrated graphics (no dedicated GPU).
- It must run at 4-bit quantization, about 5.5 GB of weights.

## Training data (unchanged)
- Labeled results from the Dell corpus sweep (branch `sweep`, dell/sweep/)
- Uplift test scores (runs/uplift/results.csv)
- The 76-plugin Dell answer key (functest/dell_ground_truth.jsonl)
- Fizzy.do bug examples (dell/pair_scripts/p10.sh, data/reviews)

## Guardrails (unchanged)
- A human presses merge, send and deploy.
- Any agent work uses Cursor house models only: composer-2.5 by default, grok-4.6 for planning or audit. No subagents on non-house models.

## Ready-to-launch setup (2026-10-13)
Everything is in `train/` and `eval/hancore_holdout/run_eval.py`. No GPU has been rented yet.

**Data** (`python3 train/build_train_set.py`, deterministic, seed 1337, about 15 s): 4,592 train / 148 val chat examples (val is split by repo).
`train/data/manifest.json` has the counts and exclusions, and every row carries its provenance.
| source | train | what it teaches |
|---|---:|---|
| HANCORE reviewer (strong/likely/open findings, 784 weak-label rows dropped) | 3,114 | review findings in HANCORE's categories |
| Dell in-use: missing binary on a stock system | 396 | `in-use:missing-binary` |
| Dell in-use: toggle opened nothing / memory growth | 75 | `in-use:toggle-opens-nothing`, `in-use:memory-growth` |
| Dell in-use: read-only close path (USB-D06 class, issue-confirmed) | 104 | `in-use:panel-cannot-close` |
| Grader-verified broken (Dell broken and Checker FAIL agree) | 397 | load blockers with the Checker's reason |
| Grader-verified works (Dell works and Checker PASS agree, no finding) | 506 | approve, so the model does not raise false alarms |
Exclusions: all 329 `eval/hancore_holdout` plugins, matched by repo, by manifest id, and by near-duplicate code tree (at least 50% shared file hashes; this caught 16 HANCORE forks and 5 Dell ones). The 116-row Dell answer key is also excluded, so it stays a clean regression set. That departs from the "Training data" list above, which includes the key. Exact duplicate code is dropped too. The same prompt (`train/prompt.py`) is used for training and for every eval backend.

**CPU dry run (box)**: 4,539 train rows fit 12,288 tokens; 53 longer rows are dropped. Token median is 7,022 and p95 is 9,195. That is 31.6 M tokens per epoch (0.95 M assistant tokens) and 284 optimizer steps per epoch at an effective batch of 16. A tiny-Qwen3.5 CPU smoke run of `train_lora.py` completed: LoRA attached to the 12 language-model projection types (attention, Gated DeltaNet, MLP) and none in the vision tower; loss went down; best/last adapters were saved.

**Run**: bf16 LoRA r=32/alpha=64 on all LM linear layers, lr 1e-4 cosine, 2 epochs, gradient checkpointing, and loss on the assistant tail only (only those positions go through lm_head). HANCORE strength weights scale the loss. `max_hours: 9` is a hard stop.
Estimate: about 63 M tokens at roughly 3k tok/s on an H100 (this needs flash-linear-attention and causal-conv1d; without them Gated DeltaNet is many times slower) comes to about 6 h. At $3.1-3.3/h (best reliable H100 offers on 2026-10-13) that is about $20 plus export. An A100 80GB is about $1.16/h at roughly 1/3 the speed, about 17 h for 2 epochs, so on an A100 use `epochs: 1` or raise `max_hours`.
**Export**: merge into bf16, then llama.cpp `convert_hf_to_gguf.py`, then `llama-quantize Q4_K_M`. The result is about 5.5 GB and runs on a 32 GB laptop (CPU/iGPU) with `llama-server -c 16384`.
**Head-to-head** on the 329-plugin holdout (`run_eval.py`): verdict accuracy, positive recall, false alarms on negatives, per-category recall/precision, JSON validity, $ cost and seconds per plugin. Baseline already measured, Checker scripts alone: accuracy 0.650, positive recall 0.673, negative false alarm 0.586, category recall 0.131, category precision 0.442 (`eval/hancore_holdout/results/checker-baseline.json`).

### Holdout baselines (HANCORE holdout: 329 plugins, 300 positive / 29 negative; same skill prompt)
Category names are normalised to the HANCORE slugs (`run_eval.norm_cat`; rescored from the raw outputs with `rescore.py`).
| system | verdict acc | positive recall | false alarm (neg) | category recall | category precision | JSON valid | cost | median s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Checker scripts alone | 0.650 | 0.673 | 0.586 | 0.131 | 0.442 | 1.00 | $0 | 0 |
| stock Qwen 3.5 9B (OpenRouter, no thinking) | 0.699 | 0.737 | 0.690 | 0.173 | 0.420 | 0.766 | $0.25 | 10.4 |
| Claude Sonnet 5.5 skill (OpenRouter, reasoning on; it cannot be turned off) | 0.374 | 0.330 | 0.172 | 0.347 | 0.397 | 0.997 | $11.05 | 11.0 |
Always answering "changes_requested" would score 0.912 here, so judge on category recall/precision and false alarms, not verdict accuracy.

### In-use eval: Dell answer key (90 decided rows: 33 broken, 57 works; excluded from training)
`run_eval.py --set dellkey`. The functest (real Quickshell) scores 90/90 on these; the models see only code + Checker report.
| system | verdict acc | broken caught | false alarm on works | JSON valid | cost |
|---|---:|---:|---:|---:|---:|
| stock Qwen 3.5 9B | 0.567 | 0.879 | 0.614 | 0.822 | $0.04 |
| Claude Sonnet 5.5 skill | 0.867 | 0.848 | 0.123 | 1.00 | $2.08 |
