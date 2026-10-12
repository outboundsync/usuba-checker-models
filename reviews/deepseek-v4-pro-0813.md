# Review by deepseek/deepseek-v4-pro-0813

usage: {"prompt_tokens": 30287, "completion_tokens": 22819, "total_tokens": 53106, "cost": 0.0805718, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0805718, "upstream_inference_prompt_cost": 0.0121148, "upstream_inference_completions_cost": 0.068457}, "completion_tokens_details": {"reasoning_tokens": 18604, "image_tokens": 0, "audio_tokens": 0}}
finish: stop

## 1) Why the fine-tuned 7B loops / fails to finish

The loop problem is mostly an interaction of **long SFT targets**, **weak stopping signal**, and **generation settings that hit a fixed cap before the model decides to stop**.

### 1.1 The training data teaches the model to generate very long answers

From the provided data:

- `train_final stats`: answer chars `median 23748 max 90043 p90 64225`.
- `DATASET.md`: rendered examples up to `23,789` tokens, near the 32k context.
- `runs/clean/train_hf.py` trains on the full assistant sequence:

```python
ids = pi + ai
ex.append({"input_ids": ids,
           "attention_mask": [1]*len(ids),
           "labels": [-100]*len(pi) + ai})
```

The model gets exactly one EOS/end-of-turn token at the end of a 10k–24k token assistant answer. So the end-of-answer token is a tiny fraction of the total training loss. Given `pipe.sh` uses:

```bash
TRAIN=train_$T.jsonl python3 train_hf.py $T 1e-4 2 32768
```

the model learns the format and the long QML well, but not a strongly calibrated “stop now” behavior.

### 1.2 Generation settings cap and encourage the failure

From `runs/clean/gen_m.py`:

```python
sp = SamplingParams(temperature=0, max_tokens=16000, repetition_penalty=1.05)
```

and:

```python
llm = LLM(sys.argv[3].split(":")[1], max_model_len=32768, ...)
```

There are two immediate issues:

1. **16k max tokens is shorter than the training distribution’s upper range.**  
   The dataset has examples up to ~23.8k tokens. Some complete holdout-style full-plugin targets are naturally longer than the 16k output budget.  
   Outcome: the clean 7B has `40/49` outputs with `finish_reason == "length"`, `median_chars 60,810`, `looping 10`, from `score49.py`/results table.

2. **There is no explicit stop other than model EOS**, and `temperature=0` with `repetition_penalty=1.05` does not prevent local attractor loops in long low-entropy QML. The included failing outputs show exactly this:

```qml
property string previousWallpaperPath: ""
...
property string previousWallpaperPath: ""
...
property string previousWallpaperPath: ""
```

and:

```qml
insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnitAndUnitAndUnitAndUnit...
```

These are degenerate continuation loops, not merely long correct completions.

### 1.3 The score pattern confirms the diagnosis

From the score table for `clean_b`:

```text
new_overall: 10/49
new_full_plugin: 1/32
truncated: 40
looping: 10
per_task:
  build_from_spec: 1/26
  add_panel: 0/6
  chunk_manifest_entry: 0/3
  chunk_component: 1/6
  chunk_add_kind: 3/3
  fix_manifest: 5/5
```

The model succeeds on short, structured tasks like `fix_manifest` and `chunk_add_kind`, but fails badly on `build_from_spec` and `add_panel`, i.e. the tasks that require generating a full plugin and then actually stopping.

So the loop/non-stop behavior is not random. It is the model imitating the length of real Omarchy plugins while underpredicting the end-of-answer token.

---

## 2) Critique of data, training, eval, and RL plan

### 2.1 Data: good provenance, but wrong emphasis for the eval

Strong points:

- The licensing policy is unusually careful.
- The data is real Omarchy/Quickshell code.
- `functest` is a genuinely functional evaluation, not just manifest validation.

Weak points:

- `train_final` task distribution is dominated by `chunk_component`:

```text
chunk_component: 254
build_from_spec:  181
chunk_manifest_entry: 84
...
add_panel: 7
```

But the holdout is dominated by full-plugin tasks:

```text
build_from_spec: 26/49
add_panel: 6/49
```

That is 32/49 full-plugin eval tasks, while the SFT mix heavily favors chunk tasks. The model gets much more practice writing one component file than writing and stopping a complete plugin.

- `clean/README.md` says `fix_manifest` rows were dropped as synthetic. But the current 7B scores `5/5` on `fix_manifest`. That may mean those were cheap useful rows for manifest-rule reinforcement. Re-adding them could be worth it.

- `clean/build_pool.py` / `clean/build_chunked.py` added many registry-derived rows, but `clean/README.md` notes chunk rows were not individually rerun after splitting:

> Rows are slices of plugins that pass functest as a whole; individual chunk rows were not re-run.

That is acceptable as long as the tasks are inserted into the known-good tree, but it should not be treated as independent full-plugin training signal.

### 2.2 Training: reasonable simplicity, weak length/termination control

`train_hf.py` is simple and mostly correct for SFT, but:

- No checkpointing:

```python
save_strategy="no"
```

- No eval split/early stopping.

- No weighting by task type.

- No explicit focal/weighted loss on EOS or final answer tokens.

- For very long samples, EOS signal is diluted.

The training script also has no test of generation behavior during training. The first time they see that the model does not know when to stop is only after an expensive merge + generation run.

If the plan is doing SFT warm-up on 14B first, this same issue will likely appear in 14B unless termination is explicitly addressed.

### 2.3 Eval: functest is good, but sample size and metric variance are real

Strong points:

- `functest/runtime.py` boots a real Omarchy shell under Wayland/bwrap.
- `functest/rescore.py` does baseline subtraction for tree tasks.
- Caching by file hash avoids redundant expensive runtime tests.

Weak points:

- 49 holdout rows is very small. The difference between `GPT-5.6 24/49` and `Opus 23/49` is not meaningful.
- `full_plugin` is only 32 examples. A 1-pass vs 0-pass difference is noise.
- Some reference solutions reportedly score 51/56 on the original holdout, meaning the harness itself may not perfectly handle every gold task. If a gold sample fails in the harness, that row should probably be removed or treated specially.
- `loopy()` in `score49.py` is a heuristic:

```python
def loopy(t):
    lines = [l for l in t.splitlines() if l.strip()]
    return len(lines) > 50 and collections.Counter(lines).most_common(1)[0][1] > max(30, len(lines) // 5)
```

This is useful for diagnostics, but exact repeated lines in QML can also be legitimate in some declarations/initializers. It is fine for tracking, but not a rigorous quality metric.

- `gen_m.py` has a bug if used with multiple adapters:

```python
llm = LLM(sys.argv[3].split(":")[1], ...)
...
for k, spec in enumerate(sys.argv[3:]):
    name, ad = spec.split(":")
    outs = llm.generate(ps, sp)
```

It loads only the first model path and reuses that same `llm` object for every subsequent `name:adapter`. In `pipe.sh` this is masked because only one adapter is passed, but it makes the script misleading for comparisons.

### 2.4 RL plan: right direction, but the protocol is not yet safe for long code generation

The GRPO plan correctly identifies the core issue:

> SFT teaches the format, but the model still doesn't learn to finish.

But there are several serious concerns.

#### Fixed 12k RL max is too short for many tasks

`runs/rl/PLAN.md`:

> max_completion_length **12k tokens** (16k in eval). Shorter during RL is deliberate, because the length pressure is the point.

But `train_final` has answer chars up to `90043`, and the original tokenized examples go up to ~23.8k. For any prompt whose gold answer exceeds 12k tokens, a successful rollout is impossible. The RL policy will be trained to stop early on those tasks, not necessarily to solve them.

I would use **per-prompt dynamic max length** based on the gold/reference length, not a fixed 12k.

#### Sparse and tied rewards in a group can zero out the gradient

With G=8, if most rollouts for a prompt are truncated, looping, or produce similar static failures, they may all receive similar negative rewards. Advantage normalization inside a group then provides little contrast.

The plan has shaped reward components:

- parse +0.1
- load +0.3
- functest +0.6
- truncation -0.5 and zero functest
- loop -0.3
- length shaping -0.1 per extra 1x, capped -0.3

This is reasonable, but the reward function should be tested for **within-group variance**. If `G=8` all score the same, the policy gradient contribution is near zero even though the task is unsolved.

#### Sandbox throughput estimate is optimistic

The plan estimates 64 completions scored in 30–60 seconds with 16 CPU workers. But `functest/runtime.py` has:

- a `timeout=40` second runtime
- possible retry for async timing issues

Worst case, 64 completions / 16 workers = 4 batches, and if some need near-40s runtime, that is ~160 seconds just for scoring, not including parsing, setup, teardown, or the next rollout. I would budget 2–5 minutes per RL step rather than 30–60 seconds.

#### No reported 14B SFT baseline

The plan says:

> Start from the warm-up SFT checkpoint in `runs/clean14`

but no score for that checkpoint is reported here. You cannot know whether GRPO helps unless you first measure the SFT-14B baseline on the same 49 prompts with the same generation settings.

#### Framework and budget

TRL `GRPOTrainer` with `use_vllm=True` is a reasonable stack. But long completions with 14B on 2× H100, reward sandboxing, debugging, and reruns can eat the $150–300 budget quickly. I would not start with 250 steps and G=8 before a much smaller 7B or short-prompt dry run.

---

## 3) Ranked concrete improvements

Here is what I would do, in order.

### Rank 1: Fix answer termination and length budget before any RL

**What**

Add an explicit end-of-answer marker to the SFT data, e.g. after the final fenced block:

```text
### END
```

Then:

- Train the model to emit `### END`.
- At inference, set:

```python
SamplingParams(
    stop=["### END"],
    max_tokens=...,
    repetition_penalty=...,
)
```

Also increase inference max_tokens from `16000` to a per-task value based on the tokenized reference length:

```python
max_tokens = min(28000, max(1024, ref_tokens * 1.25 + 512))
```

This fixes the “model does not know how to stop” and “valid answer does not fit in 16k” issues at the same time.

**Impact**

Likely the single largest improvement. Current `clean_b` has `40/49` truncated and `10/49` looping. This should substantially reduce both.

I would expect a meaningful pass-rate improvement, though I am unsure whether the model will then solve many full `build_from_spec` tasks or simply stop with shorter invalid output. That needs a retraining test.

**Cost**

Low to medium: one 7B/14B SFT rerun on the same data, plus generation rerun. Maybe $10–40 on rented hardware.

---

### Rank 2: Rebalance SFT toward full-plugin tasks and short examples

**What**

Upsample `build_from_spec` and `add_panel` so full-plugin-style tasks are the primary supervision. A rough target:

```text
build_from_spec: 45–55%
chunk_component: 25–30%
fix_manifest: 10–15%
add_panel: 5–10%
chunk_* other: remainder
```

Also intentionally include some short complete plugins under 3k tokens. The model currently learns that an Omarchy answer is extremely long. Short examples re-teach EOS timing.

**Impact**

Directly targets the eval distribution: 26/49 `build_from_spec` and 6/49 `add_panel`.

**Cost**

Low. Data already exists; this is mostly resampling and a new training run.

---

### Rank 3: Fix generation/eval harness and run a shorter diagnostic sweep before GRPO

**What**

Fix `gen_m.py` so each adapter actually loads its own model:

- either create a new `LLM` per spec;
- or use `LoRARequest` correctly.

Also test generation variants on the current 7B checkpoint before retraining larger models:

```text
1. max_tokens=16000, repetition_penalty=1.05
2. max_tokens=24000, repetition_penalty=1.05
3. max_tokens=24000, repetition_penalty=1.10
4. max_tokens=24000, temperature=0.2
```

Measure `truncated`, `looping`, `median_chars`, and pass rate.

This tells you whether the main issue is the cap, the lack of stop signal, or both.

**Impact**

Diagnosis and potentially immediate pass improvement.

**Cost**

Low; only inference reruns.

---

### Rank 4: Do SFT warm-up on 14B, but evaluate it immediately before GRPO

**What**

Run the improved SFT recipe on Qwen2.5-Coder-14B-Instruct, merge, and evaluate on the same 49-prompt clean holdout.

Do not go to RL until you have:

```text
14B SFT pass rate
full_plugin pass rate
truncated count
looping count
median chars
failure categories
```

This is the actual baseline the RL plan says it wants to beat.

**Impact**

Critical for measuring whether GRPO is worth the cost.

**Cost**

Medium: 14B training plus inference. Probably $20–60.

---

### Rank 5: Revise the GRPO protocol before running it

**What**

Modify `runs/rl/PLAN.md` as follows:

- Use **per-prompt dynamic max completion length**:

```python
max_completion_length = min(
    24000,
    max(1536, prompt_tokens + int(1.5 * ref_tokens))
)
```

- Do not include prompts whose reference answer is longer than the dynamic cap unless they have a shortened valid variant.

- Add a small positive reward for `finish_reason == "stop"` and a separate penalty for `finish_reason == "length"`, so the model can receive gradient even if the full plugin still fails.

- Prefilter reward evaluation:

```text
if parse returns no files:
    reward = 0
    skip runtime
```

- Cache runtime results by file hash, which `functest/rescore.py` already does for eval; reuse that in GPT/GRPO reward.

- Use LoRA `r=16/alpha=32` for the first RL attempt rather than `r=32/alpha=64`; the latter is likely more than needed for the amount of data.

- Run a small G=4 dry run on 7B or on short prompts before committing to G=8 on 14B.

**Impact**

Makes RL feasible and less likely to collapse from length failures.

**Cost**

Low incremental design cost, but prevents wasting $150–300.

---

### Rank 6: Harden eval statistics and contamination checks

**What**

- Report per-task and overall 95% binomial/bootstrap confidence intervals.
- Use both the 49 clean holdout and, where possible, the original 56-prompt holdout to increase sample size.
- Add prompt-level near-duplicate checks against holdout for RL prompts, not only answer-level line-jaccard.
- Remove or separately report any gold reference task that does not pass the harness itself.

**Impact**

Makes comparisons between stock 7B, 14B, GPT-5.6, and Opus less fragile.

**Cost**

Low.

---

### Rank 7: Add more real full-plugin `build_from_spec` data

**What**

The registry pipeline already produced `pool_registry.jsonl` with 152 `build_from_spec` examples and `pool_chunked.jsonl` with 328 chunked rows.

Use more of the registry repos for full-plugin examples where they fit the improved token budget. Prefer full-plugin rows over additional chunk rows.

**Impact**

Improves full-plugin generation ability, the current weak spot.

**Cost**

Low to medium; data is already cloned/curated, but training cost increases.

---

### Rank 8: Add an inference-time loop breaker for deployment/temporary eval

**What**

Use `loopy()` or a stronger repeated-line detector. If a generation appears stuck:

- terminate early;
- restart with higher `repetition_penalty`;
- or fall back to a shorter `max_tokens` output.

**Impact**

Low to medium immediate improvement, but it does not actually teach the model to finish.

**Cost**

Low.

---

## What I am unsure about

1. **Whether simply raising `max_tokens` will fix many current truncations.**  
   The included failures show true repetition, not just correct code hitting the cap. I would test this before assuming the cap is the main culprit.

2. **Whether an explicit `### END` marker is sufficient with only LoRA SFT.**  
   It is likely to help strongly, but the model may still occasionally ignore it if the QML continuation prior is very strong.

3. **Whether 14B SFT + GRPO can reach GPT-5.6/Opus-level full-plugin quality.**  
   Given that GPT/Opus score `15/32` and `14/32` on full plugins while the 7B SFT scores `1/32`, closing that gap within $150–300 is ambitious. A more realistic goal is beating the existing SFT checkpoint, reducing truncation/loops to near zero, and approaching frontier performance on short manifest/fix tasks.

4. **Whether the missing `build_parse.py` / full `static_checks.py` introduces failure categories I cannot fully diagnose from the pack.**  
   The likely categories are clear, but exact parsing/static behavior is inferred only from the supplied excerpts.