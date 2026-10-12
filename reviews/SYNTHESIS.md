# Outside review synthesis (2026-10-12)

## Reviewers
| requested | model id used | result | cost |
|---|---|---|---|
| latest GLM | `z-ai/glm-5.3-prime` | **blocked**: account zero-data-retention setting excludes its only endpoint (no settings changed) | $0 |
| latest GLM, fallback | `z-ai/glm-5.3` | review in `glm-5.3.md` | $0.041 |
| latest DeepSeek Pro | `deepseek/deepseek-v4-pro-0813` | review in `deepseek-v4-pro-0813.md` | $0.081 |
| Meta Wonder | `meta/muse-wonder` (it exists) | **blocked**: account needs an 18+ age attestation in OpenRouter preferences (no settings changed) | $0 |
| Meta, fallback attempt | `meta/muse-spark-1.3` | blocked by the same gate | $0 |

**This is two reviews, not three.** Total spend was $0.12. Both calls used reasoning effort high and max_tokens 32000, and both finished with `stop`. The prompt context is in `context_pack.md` (~30k tokens).

## Our checks against the code and data (run on the box)
- Qwen2.5-Coder tokenizer `eos_token` = `<|im_end|>`, so the `eos in labels` print in train_hf.py is a valid check.
- Rows dropped by the 32768 cap: **0 of 593**. Median prompt is **392 tokens**.
- Training answers: median 5.8k tokens, max 25.6k. **57 are over 16k tokens and 108 are over 12k.**
- Holdout reference answers: median 7.4k tokens. 4 are over 16k and 11 are over 12k.
- clean_b outputs have a median of 60.8k chars (about 15k tokens), which is about 2x the gold length. The model overshoots on length. The 16k cap is not the only problem.
- `loopy()` counts only exact duplicate lines. The `...AndUnitAndUnit...` growth sample is scored `loop=False`, so the loop count is undercounted.
- functest.py:53 removes "zero size" errors when the entry file has a conditional `visible/implicitWidth/width:` line. runtime.py `SOFT_PAT` suppresses "Binding loop detected" and others. Both can be exploited under RL.
- gen_m.py loads only the first spec's model and ignores `ad` in later specs. This is a real bug, but it doesn't affect the current numbers (pipe.sh passes one spec).
- No run exists for clean_b at rp 1.0 or at a larger decode budget (results49 has stock_7b_rp1.0 only).

## Findings, ranked best to worst
| # | finding (source) | disposition | reason |
|---|---|---|---|
| 1 | **Re-decode the existing clean_b on a cheap sweep before training anything**: max_tokens 24-28k, rp {1.0, 1.05, 1.1}, temp {0, 0.6} (GLM #1, DS #3) | **ADOPT, TOP PICK** | About $5-10 of GPU. It tests the cap, rp and attractor diagnoses directly. A 28k budget fits easily because prompts are only ~400 tokens. Expect limited gains: outputs already run about 2x gold length. |
| 2 | Long training targets plus a diluted stop signal teach the model to over-elaborate. Use a length curriculum: drop or chunk answers over ~12k tokens, 1-1.5 epochs, checkpoint every epoch (GLM #3, DS #1/#2) | **ADOPT** for the 14B warm-up | Verified: 18% of train answers are over 12k and 10% are over 16k, and outputs overshoot gold. `save_strategy="no"` leaves no checkpoint to pick from. |
| 3 | Fix `loopy()` to catch growth/n-gram loops before using it as the RL penalty (GLM #2) | **ADOPT** | Verified hole. Free. |
| 4 | Harden the reward against hacking: disable the zero-size conditional pardon and review SOFT_PAT in the RL path, and hand-audit 15-20 passes (GLM #6) | **ADOPT** | Verified exploit surfaces. The functest is "trustworthy for fails only", which is exactly the case where RL finds false passes. |
| 5 | Run an RFT/rejection-sampling round (sample n=16, keep functest passes, SFT on them) before GRPO, as a $30 check on whether there is any within-group signal (GLM #4) | **ADOPT** as a gate before the GRPO spend | Cheap and gives a pass@16 estimate. If best-of-16 on build_from_spec is near 0, GRPO at G=8 will see mostly all-zero groups. |
| 6 | GRPO cap of 12k vs gold lengths: filter prompts whose gold is over the cap, or use a per-prompt cap (both) | **ADOPT** | 108 train answers are over 12k, so those prompts would carry a guaranteed truncation penalty. |
| 7 | Measure the 14B SFT checkpoint on the 49 before RL (DS #4) | **ADOPT** | PLAN.md assumes it but has no number. |
| 8 | RL prompts overlap the SFT prompts, so group variance collapses. Use held-out or fresh specs (GLM) | **TRY** | Plausible. The pool of unused verified plugins is limited, so mixing in real asks (prompts_real.jsonl) is the practical route. |
| 9 | G=16 with dynamic sampling (DAPO-style) instead of G=8 and drop-all-0/1 (GLM) | **TRY** | Sensible if the RFT gate shows sparse passes. Costs about 2x rollouts per prompt. |
| 10 | n=49 is noisy (Wilson CI about ±13 pts). Grow the holdout to 100-150 and treat "keep best of 49 every 50 steps" as selection on noise (both) | **TRY** | Correct, but limited by how many unused verified plugins exist. At minimum, use the rolling train reward as the kill signal. |
| 11 | Rebalance the mix toward full-plugin tasks. add_panel has only 7 rows (10 in older data/train.jsonl) and 0/6 on eval (both) | **TRY** | Verified counts. Low cost, folded into the #2 retrain. |
| 12 | Add the "base + Quattro skill doc in context" baseline (GLM) | **TRY** | Promised in DATASET.md and missing. One inference run. |
| 13 | Budget 2-5 min per RL step for scoring, not 30-60 s (both) | **ADOPT** (plan edit) | The driver has fixed sleeps plus a 40 s timeout and retry. Re-estimate the cost. |
| 14 | Re-add synthetic fix_manifest rows (DS) | **REJECT** | Already 5/5 on eval. This adds nothing toward the full-plugin target. |
| 15 | Add an explicit `### END` marker plus a stop string (DS #1) | **REJECT** | `<|im_end|>` is already trained (verified) and serves as the stop. A second marker doesn't fix over-elaboration. |
| 16 | Fix the gen_m.py multi-adapter bug (DS) | **ADOPT (trivial)** | Real bug, but not affecting results. Fix it before sweeps that pass several specs. |
| 17 | Doubt about the stock14b ceiling: its failures are knowledge errors (manifest-rejected, bad-import, fake-api), not finishing (GLM) | **NOTE** | Fair point. It's why gates #5 and #7 come before the GRPO spend. |

## Claims we found wrong or unsupported
- GLM: "Qwen2.5 eos is `<|endoftext|>`, so the eos check can print False." **Wrong**: the tokenizer eos is `<|im_end|>`.
- GLM: "median prompt ~5-7k tokens." **Wrong**: 392 tokens.
- GLM: "the over-cap drop is nonzero." **Wrong**: 0 rows are dropped at cap 32768.
- DeepSeek: "the 16k cap is the main reason answers don't fit." **Overstated**: only 4/49 holdout golds are over 16k, while outputs average about 2x gold length.
- DeepSeek: "dataset examples up to 23.8k tokens." Close: the measured max answer is 25.6k tokens.

## Order of work
1. Run the sweep (#1) and the loopy fix (#3), about $10.
2. Run the 14B SFT with the length curriculum, epoch checkpoints and the rebalanced mix (#2, #11), then score it (#7).
3. Harden the reward (#4) and filter prompts by cap (#6).
4. Run the RFT gate (#5). Do GRPO only if pass@16 shows signal.
