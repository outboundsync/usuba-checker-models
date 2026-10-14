# Usuba 9B training (bf16 LoRA, Qwen 3.5 9B)

## Data-loss protection
- **On the instance**, `train_lora.py` writes a full resumable checkpoint every `save_every_steps` (25 optimizer steps, about 15 min on an H100).
  - Each checkpoint holds the adapter, optimizer, scheduler, data position, RNG state and `SHA256SUMS`, in `out/usuba-9b-lora/checkpoints/step-NNNNNN/`.
  - It is written to a temp dir, then renamed, and marked `COMPLETE`. The newest 3 are kept.
  - `best/` (lowest val loss) and `last/` adapters are saved alongside.
- **Stops always save.** On the `max_hours` hard stop (9 h, counted across resumes) and on SIGTERM/SIGINT, it checkpoints, saves `last/`, writes `STOPPED`, then exits.
- **Resume:** `train_lora.py --resume` continues from the newest complete checkpoint, with the same data order. `remote_setup.sh` always passes `--resume`, so re-running it after a crash continues the run.
- **Off the instance:** `launch_vast.sh watch` runs on the box with nohup. Every 10 min it copies new or changed artifacts to `/workspace/usuba-runs/<instance>/` (sha256-verified against the instance). It then uploads them to the private R2 bucket `usuba-training` under `runs/<instance>/...`. Files over 200 MB go up as parts plus `parts.sha256`.
  - The Cloudflare token and the Vast key stay on the box; neither is sent to the instance.
- **`down` refuses to destroy the instance** unless `fetch` produced `FETCH_VERIFIED`, the instance's current file list and checksums equal the verified copy, and the local copy still verifies. `--i-accept-data-loss` overrides this, for when the instance is already gone.
- **Lost instance:** `launch_vast.sh resume --yes` rents a new instance, pushes the newest synced checkpoint and continues.

## Steps
1. `python3 train/build_train_set.py`: deterministic; sha256 is in `data/manifest.json`, and `launch_vast.sh` refuses data that doesn't match it.
2. `train/launch_vast.sh plan`: no spend.
3. Paid smoke test (about 10-20 min): `train/launch_vast.sh up --yes --smoke`, then `nohup train/launch_vast.sh watch > /workspace/usuba-runs/watch.log 2>&1 &`.
   - Check: steps run, memory and tokens/s are reasonable, a checkpoint syncs to the box and R2, and the GGUF export works.
   - Then `fetch`, then `down`.
4. Real run: `train/launch_vast.sh up --yes`, plus `watch` as above. Wait for `FETCH VERIFIED` in the watch log, then run `down`.
5. Eval: `eval/hancore_holdout/run_eval.py`. Thinking is off by default, matching training. For the local GGUF: `eval/hancore_holdout/serve_llama.sh usuba-9b-Q4_K_M.gguf` (32k per slot x 4 slots = `-c 131072 -np 4 -ngl 99 --jinja`). Do not use `-c 16384` with 4 slots; see "Exam pitfall" in docs/TRAINING_PLAN.md.
