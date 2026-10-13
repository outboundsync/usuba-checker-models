# Base-model tryout (stock, no fine-tune), 2026-10-12
49-prompt clean holdout, same prompt messages as gen_or.py, temp 0, max_tokens 16000 (frontier panel limit), 1 greedy sample.
Scored with runs/clean/score49.py + loopdet (loops/truncations = fail). Reasoning models (qwen3.6/3.8, gpt-oss) ran with reasoning effort low, excluded (gen_fast.py); gemma via the original gen_or.py.
All OpenRouter, ZDR on, no blocks. No Vast used.

| rank | model | params | checker /49 | hand /49 | full /32 | trunc | loop | license |
|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.6-27B | 27.8B dense | 7 | 6 | 1 (add_panel, doubtful: uses a plain Qt Popup) | 0 | 0 | Apache-2.0 |
| 2 | Qwen3.8-27B | 27.8B dense VL | 4 | 4 | 0 | 0 | 0 | Apache-2.0 |
| 3 | Qwen3.6-35B-A3B | 36B MoE (3B active) | 3 | 3 | 0 | 2 | 0 | Apache-2.0 |
| 4 | Qwen3-Coder-30B-A3B | 30.5B MoE (3B active) | 4 | 2 | 0 | 0 | 0 | Apache-2.0 |
| 5 | Gemma-4-31B-it | 31.3B dense | 1 | 1 (weak stub tablet.py) | 0 | 0 | 0 | Apache-2.0 |
| 6 | gpt-oss-20b | 21B MoE (3.6B active) | 0 | 0 | 0 | 9 | 10 | Apache-2.0 |

Hand-check rejects: Qwen3.6-27B chunk_component (tablet.py opens a logging FileHandler under ~/.cache before mkdir, so it crashes at import);
Qwen3-Coder fix_manifest:reserved_id (id "time-machine", not namespaced) and chunk_component (imports invented functions from sibling modules).
Most passes everywhere are the 4 trivial fix_manifest rows. Noise is +/-1, so ranks 2-4 are a tie. Reference points: stock 14B 4, v3 7B FT 4.
Not tested: Devstral-Small-2-24B (not on OpenRouter; only the 123B Devstral 2 is there).
Spend: ~$1.86 logged + under $1 for killed first-pass runs, about $3 total.
Best-of-4 skipped (time budget). Qwen3.6-27B scored >=5, so it's the next run to do.

Pick: **Qwen3.6-27B**. LoRA/QLoRA, Unsloth/PEFT support it.
SFT cost (619 rows, about 3 epochs, 8k ctx, QLoRA r=16-64): 1x A100/H100 80GB about 1-2 h, roughly $2-5 on Vast. MoE 30-36B costs about the same but has weaker MoE LoRA tooling.
Local run: Q4 is about 17GB, fits a 24GB GPU or a 32GB+ Mac (64GB Mac is fine at Q8). The 3B-active MoEs run faster; gpt-oss-20b fits 16GB.
