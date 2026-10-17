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
