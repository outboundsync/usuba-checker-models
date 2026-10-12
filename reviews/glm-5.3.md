# Review by z-ai/glm-5.3

usage: {"prompt_tokens": 28430, "completion_tokens": 10339, "total_tokens": 38769, "cost": 0.0408386, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0408386, "upstream_inference_prompt_cost": 0.005686, "upstream_inference_completions_cost": 0.0351526}, "completion_tokens_details": {"reasoning_tokens": 7183, "image_tokens": 0, "audio_tokens": 0}}
finish: stop

# External review: Omarchy specialist (Qwen2.5-Coder LoRA → GRPO)

## 1. Diagnosis: why the tuned 7B loops and fails to finish

**The headline: your model is trained to emit answers longer than your inference budget, and greedy + repetition_penalty 1.05 turns the resulting uncertainty into mutating loops.**

**1a. Truncation (40/49, `finish=length`) is mostly a budget/distribution mismatch, not a capability failure.**

- `train_final` stats: answer chars **median 23,748, p90 64,225, max 90,043**. At QML's ~3–4 chars/token, p90 answers are ~18–20k tokens.
- `gen_m.py` decodes with `SamplingParams(temperature=0, max_tokens=16000, ...)`. 16k tokens ≈ 50–60k chars of QML.
- `train_hf.py` keeps any example with `len(ids) <= cap` where cap = 32768 total (prompt+answer). So you explicitly train on assistant answers up to ~28–30k tokens, then cap generation at 16k. Over 10% of your training distribution is *unfinishable at eval time by construction*.
- The model complied: `clean_b` `median_chars` = **60,810** vs stock 7B's 1,731. It learned "produce a large plugin," which is exactly what your data says a good answer is.
- Supporting evidence: `clean_b` finish reasons are `Counter({'length': 40, 'stop': 9})` — essentially *every* hard task runs out of budget, while the 10 passes come from the short tasks (fix_manifest 5/5, chunk_add_kind 3/3). The model didn't get worse at QML; it got committed to long outputs.

**1b. The loops are repetition-penalty artifacts layered on an over-sharp fine-tuned distribution.**

Look at the three failing samples:

- Sample 1 and 2: verbatim 4-line block repetition (`previousWallpaperPath` / `previousImageUnloadRequestedAt`). This is the classic greedy repetition attractor.
- Sample 3 is the smoking gun for rp=1.05 harm: `insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnit...` growing forever. **Repetition penalty at temperature 0 doesn't break a repeating model — it forces it to mutate.** The model wants to emit the same line again; rp makes that token expensive, so it appends "AndUnit" to stay novel. You get infinite *novel* tokens, i.e. unbounded output with no semantic progress. Note this sample is flagged `loop=False` (58,913 chars) because `loopy()` in `score49.py` counts *exact duplicate lines* — the growth loop evades it. So your true loop count is >10, and your loop detector (reused as the RL `-0.3` loop penalty) has a hole.
- Cross-check: `stock_7b_rp1.0` loops 2 vs `stock_7b` (rp 1.05) loops 0 — but stock outputs are ~1.7k chars median, so there's nothing to loop on. You never ran **clean_b at rp=1.0**. That's a missing ablation.

Contributing factors to the attractor itself:

- **Likely overfitting**: 2 epochs, lr 1e-4, LoRA r16 on 593 rows, `save_strategy="no"` (only the final adapter, no per-epoch checkpoint to pick from), no val loss. Sharp memorized modes are exactly what degenerates under greedy decoding.
- The system prompt ("Return every file in full") plus chunk-training (43% of rows are `chunk_component`, which teaches maximal single-file elaboration) pushes toward unbounded elaboration.

**1c. One correctness nit worth verifying:** in `train_hf.py` the sanity print checks `tok.eos_token_id in lab`. For Qwen2.5, `eos_token_id` is `<|endoftext|>` while chat turns end with `<|im_end|>` — so this check can print False even when termination *is* being trained. The `label tail` decode will show it; verify `<|im_end|>` is in the labels (it should be, since `apply_chat_template` on full messages appends it). Not the root cause, but you want this verified before RL.

## 2. Critique

**Data**

- **Length distribution is the core defect** (see 1a). You need the model to finish; your data teaches it to be huge.
- **Task-mix skew vs eval**: eval is 26/49 `build_from_spec` + 6 `add_panel` (32 "full plugin" tasks); training final is 181 build_from_spec but only **7 add_panel** rows. clean_b scores 0/6 on add_panel, and you barely train it.
- Holdout dedupe (line-jaccard ≥0.7 removed 7; registry pool filtered at <0.5) is reasonable but line-jaccard on QML under-detects structural copies (renamed-identifier clones). Given clean_b is 1/32 on full plugins, leakage isn't currently inflating anything — that's actually informative: the model is failing on *capability and length*, not winning on recall.
- Good: license rigor, validator parity (25/25), qmllint syntax gating, baseline-subtraction in `rescore.py`.

**Training**

- No eval/val loss during training, single final checkpoint, silent drop of over-cap examples (`if len(ids)>cap: continue` — count how many of 593 this eats; with p90 at 64k chars + prompt, it's nonzero).
- Boundary tokenization (`pi` + `ai` tokenized separately) can split merged tokens at the prompt/completion seam; minor for Qwen but real.
- 2 epochs at lr 1e-4 is on the hot side for 593 rows with an r16 adapter.

**Eval**

- **n=49 is small.** 10/49 vs 6/49 is within noise (Wilson CI on 10/49 is roughly ±13 points). Your kill criterion for RL ("no improvement by step 100" on the 49) will be noise-driven. Either grow the holdout (the registry has 5,416 listings; 418 curated — build a fresh 100–150 prompt holdout from *unused* verified plugins before RL) or accept pass@k / multi-seed greedy.
- Missing baseline promised in DATASET.md: base model + Quattro skill doc in context. That's your real competitor and it's absent from the score table.
- "Trustworthy for fails only" is unquantified. Before using this as an RL reward you need a false-pass estimate: manually review ~15–20 functest passes. The harness has several exploit surfaces: `SOFT_PAT` in `runtime.py` suppresses whole error classes; `functest.py` *deletes* "zero size" errors if the entry file contains any conditional on `visible|implicitWidth|width` — a model under RL pressure will discover that adding one ternary kills that error. The timing retry and `norm()` error filtering are more mild but similar.
- `loopy()` misses growth-loops (see 1b).

**RL plan**

Right idea (execution reward directly punishes non-termination), several issues:

1. **Same prompts as SFT.** RL prompts are "the specs in train_final, deduped (~250)". The warm-up SFT just trained on these; rollouts will partially regurgitate gold, within-group variance collapses, and GRPO gets weak signal. Use prompts held out from SFT, or fresh specs.
2. **Bootstrap risk is severe.** SFT full-plugin rate is 1/32 greedy. At temp 0.8 with G=8, many prompts will be all-zero even with the 0.1/0.4 partial credit; your curriculum drops exactly those. Net effect: RL trains mostly on the easy tail (fix_manifest-style) that's already 5/5. Mitigations: G=16 on fewer prompts, DAPO-style dynamic sampling (oversample, keep only prompts with within-group variance), and filter prompts whose *gold answer* exceeds the completion cap.
3. **max_completion_length=12k vs gold lengths.** Any prompt whose reference answer is >12k tokens has a negative expected reward ceiling (guaranteed -0.5 truncation term). Filter those prompts out or raise the cap; don't train against impossible targets.
4. **Reward hacking** on the soft/zero-size heuristics (above). Freeze a reward version; consider disabling the zero-size-conditional-removal and SOFT_PAT suppression in the RL reward path; spot-audit new pass modes.
5. **Length penalty uses reference length** — for training prompts that's fine (you have gold), but it caps legitimately long answers and leaks target-size information. It's OK; just know it biases toward short.
6. Eval every 50 steps on 49 prompts + "keep best checkpoint" = selection on noise. Log rolling mean train reward as primary kill signal.
7. Cost/throughput estimates are plausible but optimistic on the reward side: the DRIVER has ~10s of fixed sleeps + up to 10s ping loop; ~15–25s per functest → 64 tests / 16 workers ≈ 100–150s, overlapping rollout. The sha1 cache in `rescore.py` will help a lot once rollouts converge. Total $150–300 is believable.

**A strategic note before spending the GRPO budget:** stock 14B is only 6/49 (vs 3/49 stock 7B) and its failure profile (`rt-manifest-rejected` 29, `bad-import` 27, `fake-api` 24) shows a *knowledge* problem, not just a finishing problem. GPT-5.6 at 24/49 fails mostly on `rt-load-failed` too. So the ceiling for a 14B is genuinely uncertain. Given the budget, I'd spend the first $30–50 proving that the finishing problem is fixable cheaply (see below) and that execution-feedback helps (RFT), before committing to full GRPO.

## 3. Ranked improvements

1. **Re-decode the existing `clean_b` adapter with a bigger budget and a sampling sweep — before any new training.** `max_tokens=24000–28000` (fits your `max_model_len=32768` given median prompt ~5–7k), rp ∈ {1.0, 1.05, 1.1}, temp ∈ {0, 0.6/0.7}. Cost: ~$5–10 of GPU. Expected impact: truncation 40/49 → plausibly 10–20; overall maybe 10 → 14–18/49, because some truncated outputs are near-complete. Uncertainty: how many of the 40 truncated generations are actually close to passing — check what fraction already have a valid manifest + parseable files. This is your highest information-per-dollar experiment and it directly tests diagnosis 1a/1b.
2. **Fix `loopy()` and re-measure loops** (n-gram overlap or token-entropy based; also detect the growth pattern). Zero cost. Matters because this function is your RL loop penalty.
3. **SFT v2 with a length curriculum**: drop/down-weight training answers > ~12–14k tokens (or restrict build_from_spec to small/medium plugins; keep large ones as chunk tasks), 1–1.5 epochs, lr 5e-5–1e-4, `save_strategy="epoch"` + eval each checkpoint on a 100-prompt dev set. Restore `add_panel` rows (10 exist in the original train). Cost: ~$15–25. Expected: loops near 0, truncation low at 24k budget, overall maybe 12–18/49. This also makes the RL warm-up sane.
4. **RFT / rejection-sampling round before GRPO**: sample n=16 at temp 0.8–1.0 on ~250–300 prompts *not* used in SFT, keep functest-passing completions, dedupe, continue SFT (1 epoch, low lr). Cost: ~$20–40 including decoding + functest. Expected: +2–5 points, and it tells you the temp-sampled pass rate per prompt — i.e., whether GRPO will have any within-group variance to exploit. If best-of-16 yields almost nothing on build_from_spec, GRPO at G=8 won't either; that's a $30 answer to a $250 question.
5. **Grow and de-noise the eval set** to 100–150 prompts from unused verified registry plugins; add the in-context-skill baseline; report CIs. Cost: ~1 day CPU, $0 GPU. Do this *before* RL so checkpoint selection and kill criteria mean something.
6. **Quantify the functest false-pass rate** (manually audit ~15–20 passes) and harden the reward path (disable zero-size-conditional removal and SOFT_PAT suppression in the RL copy). Cost: hours. Prevents the most likely way this project "succeeds" spuriously.
7. **Then GRPO, amended**: fresh prompts (held out from SFT), prompts filtered so gold answer ≤ completion cap, G=16 with dynamic/variance-based filtering, max_completion_length raised to 16k to match eval, keep the 0.1/0.4/0.6 shaping, rolling-reward kill signal. Cost: within your $150–300.
8. **If GRPO works, consider a second round of RFT on GRPO outputs** (cheap, compounds) — and only then decide whether 14B justifies its cost; the current stock14b delta (6 vs 3) doesn't yet.

**Where I'm unsure:** (a) how much of the 40-truncation cohort converts to passes at 24k tokens — could be most or almost none; (b) whether rp 1.0 vs 1.05 materially changes loop rate on the *tuned* model (evidence is indirect); (c) TRL colocate + vLLM sleep mode stability at 14B/32k context — your verl fallback is the right call; (d) the true false-pass rate of the functest, which is why I rank item 6 above the RL spend despite it being "just" measurement work.