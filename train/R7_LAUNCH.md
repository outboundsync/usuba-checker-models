# r7 overnight run: readiness (prepared 2026-10-15, nothing launched, no GPU spend)
Launch (only when /workspace/usuba-runs/v3-data-r7/final_merged exists and preflight passes):
`bash train/launch_r7.sh` (gates only) then `bash train/launch_r7.sh --go` (rent + start + watch, AUTO_DOWN after verified fetch, local checkpoint pruning).
Hard gates (train/r7_preflight.py): SHA256SUMS, prompt sha == scope.prompt_scope, code_blob policy == one `code_blob/v2` id == installed usuba_checker.code_blob.POLICY_ID_V2, schema, guards, drop rate <= 2%, schedule, estimated hours <= max_hours.
Config: evals + checkpoints every 14 steps, max_hours 8 (instance limit 10 h), midcheck off (old schema). Watchdog restarts only when /workspace/usuba/ARMED exists (written by launch_vast.sh start).
Proof of auto-resume: real train_lora.py + real watchdog.sh, tiny CPU model, kill -9 at step 7 -> restart from checkpoint 6 -> step 8, no duplicate/reset (see report).
B0: `OPENROUTER_API_KEY=... bash scope/run_b0_r7.sh` (stock Qwen3.5-9B, scope prompt v4, same schema + post-filter; ~$1.2).
