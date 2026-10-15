# q27: QLoRA-style LoRA SFT of Qwen3.6-27B on train_v3 (2026-10-13)
Recipe: bf16 base (no 4-bit, fit on 1x H100 NVL 94GB, peak 70.5GB), LoRA r16/a32/drop .05 on q/k/v/o/gate/up/down + linear-attn in_proj_qkv/in_proj_z/out_proj (108.8M params), lr 1e-4 cosine, 2 epochs, bs1 x ga4 (310 steps), grad ckpt, no packing, sdpa (cuDNN SDPA off), chunked CE loss.
Template: Qwen3.6 chat template with enable_thinking=False (prompt ends `<think>\n\n</think>\n\n`), `<|im_end|>` in labels (checked). 619/619 rows, 3.26M tokens/epoch.
Loss: epoch1 mean 0.583, epoch2 mean 0.467, train_loss 0.525 (v3 7B recipe identical except model).
Gen: vLLM 0.31 on merged weights, eager, prefix caching off. Greedy rp1.05 16k on 49 clean holdout; bo16 T0.8 top_p .95 rp1.05 16k on the 32 build_from_spec probes.

| model | checker /49 | hand /49 | full /32 | trunc/loop | bo16 checker /32 | bo16 hand /32 |
|---|---|---|---|---|---|---|
| q27 FT (this) | 7 (6 after loop rule) | 4 | 2 (hand 0) | 31/31 | 15 | 7 lenient / 4 firm |
| stock Qwen3.6-27B | 7 | 6 | 1 | 0/0 | - | - |
| v3 7B FT | 4 | 4 | 3 | -/32 | 11 | 9 |
| GPT-5.6 | | 20 | | | | |
| Opus | | 18 | | | | |

Greedy hand-check: fix_manifest x4 correct. Rejects: chunk_add_kind:service (row 40, loops, 71k chars), acme.weather and zeru.portwatch (render, but call helper scripts bin/omarchy-weather / portwatch that are never written; weather also uses moduleName omarchy.weather), so they never show data.
bo16 hand-check (passing prompt: verdict): 3 copytracker accept (sample 9, wl-paste --watch helper shipped; moduleName omarchy.*), 4 peek accept-doubtful (hyprctl eval hl.dsp.windowalpha), 17 day-in-history accept, 19 gitnotice accept-doubtful, 23 bar-studio accept-doubtful, 29 flappy accept, 30 stardate accept (trivial date string).
Rejected: 0 gotospace, 6 readest, 9 fresh-wallpaper, 21 scrolling-columns, 11/15 slack (helper scripts referenced but not written), 7 draw-it (bin/drawit missing), 11/12 slack (summons a service it never defines), 1 lid switch (no lid handling / invented omarchy-hyprland-systemd-inhibit / unshipped status.sh), 15 jumpy (hardcoded /usr/share path + invented omarchy-shell subcommands).
Main failure mode: greedy runaway loops (31/49 hit 16k), and inventing helper binaries.
Verdict: no greedy gain over stock 27B (4 vs 6 hand); bo16 hand 4-7/32, about v3 7B (9). Not worth adopting as is; loops need fixing (rp, more epochs, or thinking-off data quality) before more spend.
Spend: ~$11.8 Vast (H100 NVL $3.03/h, ~3.9h incl. 2 train crashes: cuDNN SDPA failure, then OOM->device assert from fp32 full-vocab logits; 2 vLLM hangs: cudagraph capture, prefix caching). Instance 55688145 destroyed, 0 instances remain. Adapter: runs/q27/adapter_q27.tgz (local, gitignored).
