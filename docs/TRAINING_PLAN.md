# Usuba Vast training-run plan

> **Provenance:** proprietary models (Claude, GPT, etc.) in the tables below are evaluation baselines only; none of their outputs are training data. See README "Training data provenance".


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
**Export**: merge into bf16, then llama.cpp `convert_hf_to_gguf.py`, then `llama-quantize Q4_K_M`. The result is about 5.5 GB and runs on a 32 GB laptop (CPU/iGPU) with `llama-server -c 32768 -np 1` (one slot; `-c` is total context shared by all slots).
**Head-to-head** on the 329-plugin holdout (`run_eval.py`): verdict accuracy, positive recall, false alarms on negatives, per-category recall/precision, JSON validity, $ cost and seconds per plugin. Baseline already measured, Checker scripts alone: accuracy 0.650, positive recall 0.673, negative false alarm 0.586, category recall 0.131, category precision 0.442 (`eval/hancore_holdout/results/checker-baseline.json`).

### Holdout baselines (HANCORE holdout: 329 plugins, 300 positive / 29 negative; same skill prompt)
Category names are normalised to the HANCORE slugs (`run_eval.norm_cat`; rescored from the raw outputs with `rescore.py`).
| system | verdict acc | positive recall | false alarm (neg) | category recall | category precision | JSON valid | cost | median s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Checker scripts alone | 0.650 | 0.673 | 0.586 | 0.131 | 0.442 | 1.00 | $0 | 0 |
| stock Qwen 3.5 9B (OpenRouter, no thinking) | 0.699 | 0.737 | 0.690 | 0.173 | 0.420 | 0.766 | $0.25 | 10.4 |
| Claude Sonnet 5.5 skill (OpenRouter, reasoning on; it cannot be turned off) | 0.374 | 0.330 | 0.172 | 0.347 | 0.397 | 0.997 | $11.05 | 11.0 |
| **Usuba 9B Q4_K_M (this run)** | **0.812** | **0.883** | **0.931** | **0.402** | **0.427** | **0.909** | **$0** | **5.23** |
Always answering "changes_requested" would score 0.912 here, so judge on category recall/precision and false alarms, not verdict accuracy.

### In-use eval: Dell answer key (90 decided rows: 33 broken, 57 works; excluded from training)
`run_eval.py --set dellkey`. The functest (real Quickshell) scores 90/90 on these; the models see only code + Checker report.
| system | verdict acc | broken caught | false alarm on works | JSON valid | cost |
|---|---:|---:|---:|---:|---:|
| stock Qwen 3.5 9B | 0.567 | 0.879 | 0.614 | 0.822 | $0.04 |
| Claude Sonnet 5.5 skill | 0.867 | 0.848 | 0.123 | 1.00 | $2.08 |
| **Usuba 9B Q4_K_M (this run)** | **0.756** | **0.939** | **0.351** | **0.978** | **$0** |

## Run log: Qwen 3.5 9B bf16 LoRA (2026-10-13/14)

**Finished** 2026-10-14 ~9:30 AM MT on Vast H100_NVL instance 55864967 (label usuba-9b-lora). Final val loss **1.073459** at step **568** (~5.0 train hours). Q4_K_M GGUF exported and sha256-verified on the box. Exam ran on the same H100 (llama-server `-c 131072 -np 4` after a failed `-c 16384` attempt that was invalid). Instance destroyed; Vast shows **0** instances. Estimated rental cost ~**$34** (~11.1 h × $3.07/hr); credit left ~$72.56.

### Holdout exam (Usuba 9B Q4_K_M on H100)

| system | verdict acc | positive recall | false alarm (neg) | category recall | category precision | JSON valid | cost | median s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Checker scripts alone | 0.650 | 0.673 | 0.586 | 0.131 | 0.442 | 1.00 | $0 | 0 |
| stock Qwen 3.5 9B (OpenRouter) | 0.699 | 0.737 | 0.690 | 0.173 | 0.420 | 0.766 | $0.25 | 10.4 |
| Claude Sonnet 5.5 skill | 0.374 | 0.330 | 0.172 | 0.347 | 0.397 | 0.997 | $11.05 | 11.0 |
| **Usuba 9B Q4_K_M (this run)** | **0.812** | **0.883** | **0.931** | **0.402** | **0.427** | **0.909** | **$0** | **5.23** |

### Dell answer key (90 plugins)

| system | verdict acc | broken caught | false alarm on works | JSON valid | median s |
|---|---:|---:|---:|---:|---:|
| stock Qwen 3.5 9B | 0.567 | 0.879 | 0.614 | 0.822 | 7.67 |
| Claude Sonnet 5.5 skill | 0.867 | 0.848 | 0.123 | 1.00 | 8.99 |
| **Usuba 9B Q4_K_M (this run)** | **0.756** | **0.939** | **0.351** | **0.978** | **2.88** |

Artifacts: `/workspace/usuba-runs/55864967/` (model, checkpoints, logs, GGUF) + `exam/` (eval JSON/raw + logs). Raw results also copied to `eval/hancore_holdout/results/usuba-9b-q4km*.json*`.

### Exam pitfall: llama-server context is shared across slots (2026-10-14)
- The first final exam on Vast 55864967 ran `llama-server -c 16384` with 4 parallel slots. That attempt was invalid: `-c` is the total context, so each slot got 4k tokens, but HANCORE / Dell exam prompts are ~6.7k-8k tokens (plus up to 2,048 output). 1002 of 1054 requests failed with "Context size has been exceeded", and those rows would have scored as invalid output.
- Fix: restarted llama-server with 32k per slot (`-c 131072 -np 4 -ngl 99`, same Q4_K_M GGUF) and relaunched the exam; 0 context errors.
- The failed logs were kept on the instance as `exam_*_ctx16k_failed.log`.
- Required setup: start the server with `eval/hancore_holdout/serve_llama.sh MODEL.gguf` (defaults `CTX_PER_SLOT=32768`, `PARALLEL=4`, so `-c 131072`; it refuses less than 32k per slot). `run_eval.py` reads llama-server `/props` and aborts if the per-slot context is under 32k, and aborts the exam if more than 10% of the first 20+ responses hit context overflow (`--ctx-check-n`, `--ctx-max-rate`).

## Dell key, reason-graded and leak-free (2026-10-14)
See `eval/dellkey/README.md`. Two fixes change every earlier Dell-key number: `SOURCE.txt` / `checklist.md` (which state the functest failure)
are no longer shown to models, and files are no longer cut at 8000/24000 chars. Train and eval now build the Checker report with the same
function (`train/checker_report.py`); v1 Dell training rows used the sweep's static_fails and left out the `warn` lines the eval showed.
Headline: Usuba v1 names the real bug for 0/26 flagged broken plugins and invents a commit SHA in 46/90 outputs. Stock Ministral 14B with the
improved prompt names it for 15/27; Sonnet 5.5 (improved prompt) for 22/24 at 0.07 false alarms.

## Local hardware learnings (reference laptop, CPU only)
Provenance reminder: no proprietary-model outputs are training data; the Dell baselines below are open models (Usuba v1, stock Qwen3.5-9B) on our own runs.
- Speeds: prefill about 24 tok/s, generation 5-7 tok/s. Memory about 10 GB for the 9B Q4_K_M server.
- Context: about 10k prompt tokens at `-c 12288`; 32k-token plugins need about 25 min of prefill, so local runs skip or cap the biggest plugins. Plan 32k per slot on the GPU exam (already enforced by `serve_llama.sh`).
- Baseline, 8 broken Dell-key plugins (small sample): v1 names the real bug 0/8 and invents commit SHAs on 7/8; stock Qwen3.5-9B names it 1/8 (+1 loose) and invents 0/8. The exam table carries these rows (see `eval/dellkey/dell_baseline.json`). One hit in 8 is within noise.

## Vast run config for v2 (prepared, NOT launched)
- `train/config.yaml`: `max_hours: 11` (was 9), `max_len: 32768`, `save_every_steps: 20`, `eval_every_steps: 145`.
- `train/dry_run.sh [MIN]`: a few paid minutes on the real data and config (output in `out/dryrun`), reports s/step, peak memory, checkpoint written, projected total hours vs `max_hours`.
- `train/resume_test.sh [--reboot|--verify]`: kill -9 (or reboot) the trainer mid-run and prove `--resume` continues from the newest complete checkpoint with no step-counter reset.
- `train/watchdog.sh`: every 5 minutes checks process alive, GPU util/memory and that the optimizer step advanced; restarts from the checkpoint after a dead process or `STALL_MIN` (15) minutes without a step; appends to `/workspace/usuba/ALERT` (surfaced by `launch_vast.sh watch`); gives up after 6 restarts. Started by `autostart.sh` (Vast onstart), so it survives reboots.
- Order on the instance: `dry_run.sh` -> `resume_test.sh` -> real run. Neither script has been run yet; they were only syntax-checked (`bash -n`).

## Vast setup learnings (2026-10-14, first real run of the v2 scripts)
The prep scripts had only passed `bash -n`; running them on a rented H100 NVL (instance 56016890) found these issues. Each was fixed on `retrain-v2-data`.
1. **torch/CUDA mismatch.** `pip install -U transformers ...` pulled torch 2.14.1+cu130, but the host driver (570) supports CUDA 12.8 only, so `torch.cuda.is_available()` was False and the trainer asserted. Fix: `deps.sh` pins `torch==2.9.1 torchvision==0.24.1` (cu128). Always run `python3 -c "import torch;print(torch.cuda.is_available())"` right after installing.
2. **Watchdog started the real run on a fresh instance.** With no training running, the watchdog saw "process dead" and launched `remote_setup.sh` (the full run). Fix: the watchdog only acts when `/workspace/usuba/ARMED` exists (line 1 output dir, line 2 command, line 3 optional CHECK_SEC); `launch_vast.sh start` arms the real run, `resume_test.sh` arms its own test run.
3. **`dry_run.sh` assumed deps were installed.** Dependency install moved to `deps.sh` (idempotent), called by `remote_setup.sh`, `dry_run.sh` and `resume_test.sh`.
4. **`pkill -f` can kill its own ssh command** (the pattern appears in the remote command line). Use the bracket trick: `pkill -f "[t]rain_lora"`.
5. **Pick offers by driver CUDA version.** Filter `cuda_vers>=12.8` is not enough to guarantee the image's torch build runs; check `nvidia-smi` CUDA version against the torch build before the first paid step.
6. **`resume_test.sh --reboot` called `reboot` inside the container**, which does not work on Vast. It now records state and the reboot is done with `vastai reboot instance ID`.
7. **fla needs Triton >= 3.7.1 on Hopper.** flash-linear-attention raises for Triton 3.4-3.7.0 (wrong gated backward). torch 2.9.1 pins triton 3.5.1; `deps.sh` overrides with `triton>=3.7.1` (pip prints a conflict warning; an fla fwd/bwd smoke test passed) and now fails loudly if `torch.cuda.is_available()` is False.
8. **The first dry run reported a misleading "OK".** The initial validation pass (152 examples at up to 32k tokens) takes ~5 min, and it counted against `max_hours` (dry run = 6 min), so one optimizer step logged and "460 s/step / 37 h" was an artifact. Fixes: the `max_hours` clock starts after the initial eval, step records carry a wall-clock `t`, and `dry_run.sh` computes s/step from consecutive step times. Lesson: a dry-run number must be checked against how it is computed before it is believed. Initial eval can be skipped with `SKIP_INITIAL_EVAL=1` (used by the resume test).
9. **Watchdog stale timers.** While unarmed it let `LAST_T` age, so arming it later triggered a false "no progress for 50 min" restart that killed a healthy run. Unarmed iterations now reset the timers.
10. **resume_test.sh bugs:** checkpoint numbers like `000004` produced invalid JSON (leading zeros), and it grepped the wrong log for "resumed from" (the watchdog logs to `watchdog_train.log`), so a successful watchdog recovery was reported FAIL. Both fixed. Lesson: when a test says FAIL, read the raw evidence before deciding which side is wrong.
11. **Measured numbers (H100 NVL, real data, cu128, fla, bf16 LoRA r32):** 68.8 s/step (9 steps), peak 41.3 GB allocated (~52 GB seen in nvidia-smi), 290 steps -> 5.5 h, plus ~170 s per validation pass and checkpoint saves; well under the 11 h cap. Initial dry-run training starts ~5 min after launch (tokenise ~95 s, model load, eval 170 s).
12. **Recovery evidence.** kill -9 at step 4 (checkpoint 4): the watchdog restarted from step-000004 in ~50 s, GPU busy, step 5 logged ~3.5 min after the kill, loss at step 5 matched the earlier run (0.857 vs 0.858), i.e. same data order. Reboot via `vastai reboot instance`: container back and watchdog + trainer up within ~25 s of the call (onstart hook), resumed from step-000006, GPU 100%, step 8 logged ~5 min after reboot (loss 0.7467 vs 0.7454 in the dry run). Steps after the newest checkpoint are recomputed, not lost.
13. **Sync (2026-10-14).** `launch_vast.sh watch` first copied the dry-run and resume-test outputs (GBs) to the box and R2; `REMOTE_LIST` now only lists `train/out/usuba-9b-lora` and `train/out/export`. The watcher's stall action used `pkill -f train_lora.py` over ssh (kills its own ssh command); now `[t]rain_lora.py`. `/workspace/usuba/ALERT` keeps old test alerts, so the watcher prints them once at start (harmless; clear the file before a real run). Verified: step-20 checkpoint (adapter, 693 MB trainer_state.pt) synced, remote sha256 matched, `sha256sum -c SHA256SUMS` OK, uploaded to R2 in chunks.
