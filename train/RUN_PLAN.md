# Run plan (generated from config.yaml by gen_train_docs.py; do not edit)

- base: `Qwen/Qwen3.5-9B` @ `c202236235762e1c871ad0ccb60c8ee5ba337b9a`; LoRA r=32 alpha=64 dropout=0.05
- data: `data/r5/train.jsonl.gz` (454 rows), `data/r5/val.jsonl.gz` (96 rows), checked against `data/r5/SHA256SUMS`; output `out/usuba-9b-lora-r5`
- optimiser: lr 0.0001, cosine, warmup 0.03, batch 1 x grad_accum 16 = 16 sequences/step, 2 epochs
- schedule: 29 steps/epoch (last window 6 micro-batches), 58 total, warmup 1 steps
- mid-run evals (and midcheck) at steps [14, 28, 42, 56] plus the end; checkpoint every 20 steps, keep 3; hard stop after 11 h
- example weights: OFF
