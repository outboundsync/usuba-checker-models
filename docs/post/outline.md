# Usuba post: outline + open TKs

Draft: `/workspace/usuba-post/draft.md` (~9,300 words, DRAFT v0.1, written Mon Oct 12, 2026, 4:37 PM MT)
Author: Harris Kenny · OutboundSync · usuba.dev

## Sources used
- `/workspace/omarchy-specialist`: git log (7 commits, Oct 12 08:28 to 15:38 MT), README.md, DATASET.md, legacy/clean/README.md, reviews/SYNTHESIS.md, legacy/runs/smoke-2026-10-11/PROGRESS.md + summary.json + panel_costs.txt + rr_/big_ logs, functest/results.json + rescore.log, legacy/runs/clean/results49_oldft.json (old grader), legacy/runs/clean/results49.json (Dell-calibrated grader), legacy/runs/v3/rescore_refs.log, functest/ref49_results.json, dell-smoke/README.md, dell-batch2/, dell-batch3/README.md + labels_final.md/.tsv, dell_loop/README.md, dell_rounds/blind1/REPORT.md, runs/rl/PLAN.md + bo16.json + pass_at_k.py, legacy/runs/clean/loopdet.py, legacy/qwen25-coder-v3/build_v3.py + build.log + train_v3_manifest.json, legacy/runs/v3/pipe.sh, file mtimes for timing.
- Transcripts: none found. A grep of /home/user/agent-data for omarchy-specialist / Santoku / Usuba / Quickshell turned up no project conversation files dated Oct 10 or later. The few hits were older and unrelated.

## Sections
1. **The idea: a local specialist for one very specific kind of code (Sun Oct 11).** Why Omarchy Quattro plugins are a good niche, the base models (Qwen2.5-Coder 7B/14B), and the validator contract with a 25/25 Python-port parity check.
2. **The data rule, v1: 254 examples, each with a paper trail (Sun night).** License provenance at pinned commits, 117 repos verified, 55 sources, 254 examples (198/56), 254/254 validator- and qmllint-clean.
3. **The overnight smoke run (Mon 2:51-6:26 AM).** Overfit loops, the vLLM/rep-penalty red herring, the "long targets" diagnosis, and the RFT "SUCCESS" (42/56 validator) built on model-written data.
4. **The frontier panel (Mon morning).** OpenRouter panel with ZDR kept on (Qwen2.5-32B and GLM 5.3 Prime blocked), credit ran out mid-run, about $33.50 from logs; validator scores made a 7B look like it beat GPT-5.6.
5. **The first box test with real Quickshell (by ~8:15 AM).** Functest vs. validator: tuned 7B 42 → 8, GPT 29, Opus 28, refs 51/56; the dell-smoke read-through found fake JS modules and a config-wiping plugin.
6. **The data rule, v2: merged and reviewed code only (9:44 AM).** RFT set and synthetic rows dropped, no frontier distillation, registry curation (418 → 152 + 328 rows), holdout deduped 56 → 49, 593 rows with provenance.
7. **The first clean fine-tune (late morning).** 7B 10/49 vs. GPT 24 / Opus 23 on the old grader; 40 truncated, 41 looping, outputs ~2x gold length; outside reviews and what they got wrong.
8. **The Dell becomes ground truth (midday to 3:38 PM).** Batch 2 false passes (flush-bar `css gap data:` bug), real captures, batch 3 (61 plugins); old grader 44/58 on 76 labeled; rebuild → 58/58; sealed blind round 30/32 with 0 false passes; 89/90 after the deno fix.
9. **Honest rescoring (afternoon).** GPT 22, Opus 21, 7B fine-tune 6, stock 14B 5, 14B warm-up 4, stock 7B 3; build-from-spec 0/26 for our fine-tunes; grader still tightening (GPT 21 / Opus 20 after the 4:35 PM change).
10. **The decoding sweep (afternoon).** 6 settings × 49 prompts at up to 28k tokens: all 6-7/49 with 30-39 truncated; looping is learned.
11. **A compression-based loop detector (afternoon).** zlib ratio on the last 20k chars (<0.06; loops 0.002-0.015 vs. frontier ≥0.118), plus tandem, n-gram and repeated-line checks; why it matters for an RL reward.
12. **Best-of-16 (3:49 PM).** pass@1 0.006, pass@16 3/32 by grader, 60.9% truncated, 44.3% looping; why GRPO gets all-zero groups; RL plan on hold.
13. **The manifest `entryPoints` lesson (afternoon).** Stock 14B 9/9 nested-kinds manifests in blind1; GPT/Opus missing barWidget entry; the v3 guard found 0 rows to fix, so it's a base-model prior.
14. **Where we are now: SFT retrain v3 running (4:37 PM).** 607 rows, 8,192-token cap (median 4,595), entryPoints guard, built-ins attempted (38 → 0 kept), same recipe; outcome TBD; next RL → held-out Dell test → real user.
15. **Cost discipline (whole project).** Documented spend (Vast $1.07/h + ~$0.79, OpenRouter ~$33.50, reviews $0.12), habits (destroy instances, hold Opus, read before trusting, gate big spend), RL budget $150-250 with a hard stop at $300.
- **Closing: What's next.** Honest middle of the story; the next section is added when v3 lands.

## Open TKs (in draft order)
1. §1: Harris: why local matters to you (privacy, cost, offline, Omarchy ethos).
2. §1: The origin moment on Sun Oct 11. The repo's earliest timestamps are the 2:07 PM MT snapshot and the ~9:38 PM MT catalog pull; no transcripts were found.
3. §1 figures: optional photo of the reference laptop running Omarchy.
4. §4: Confirm the ~$33.50 panel cost against the OpenRouter dashboard (the log sum may differ from the invoice; the account showed $38.49 of $40 spent account-wide when credit ran out).
5. §4 figures: cost chart caveat (same as #4).
6. §5: Did Harris install any of the 9 dell-smoke plugins, and what happened? The checklist is blank.
7. §7: How was the 454-row `train_b` cut from the 593-row `train_final`?
8. §8: **"49 of 61" can't be reproduced.** batch3 labels give 34/46 decided (44/61 if likely-works UNSUREs count as works); all 76 labeled give 44/58 decided. Pick the number and definition to publish.
9. §9: The "capped 7B" label. The results file calls the 6/49 model `clean_b` (7B clean fine-tune, greedy, up to 28k tokens). Confirm the naming.
10. §9: Final rescored numbers for all models after the 4:35 PM fix_manifest id rule (latest rescore: GPT 21, Opus 20; others not rerun).
11. §9: Reference-answer ceiling under the final grader (an earlier rescore had references at 25/49, file written 14:36, before the 14:54 rebuild commit).
12. §10: Actual Vast cost of the decoding sweep (reviewers estimated $5-10).
13. §12: Which checkpoint generated the best-of-16 file (`bo16_7b`)?
14. §12: **"2/32" vs. 3/32.** bo16.json shows pass@16 = 3/32 by the grader. If a hand check rejected one, name it and update.
15. §14: Confirm the v3 run is actually live (pipe.sh staged 4:25 PM; no remote log in the repo).
16. §14: `v3/README.md` (cited for the 8,192 cap) doesn't exist. Write the justification.
17. §14: Built-ins: all 38 excluded (8 already in, 8 holdout, 22 functest fail). Relax the gate for first-party code, or state it plainly.
18. §14: v3 results (overall /49, full /32, bfs /26, truncated, looping, median length, pass@1, pass@16).
19. §14 figures: v3 column of the scorecard.
20. §14: Who is the real user, and what plugin will they build?
21. §15: Vast spend for the clean fine-tunes, 14B warm-ups, sweep, best-of-16 and v3 (pull from Vast billing).
22. §15: Total spend to date.
23. §15 figures: cumulative spend chart (needs the Vast billing export).
24. Closing: Release paragraph (usuba.dev plan, weights/data license, NOTICE completeness, how to try it).

## Discrepancies vs. the brief (flag to Harris)
- **First fine-tune.** The first fine-tunes were the overnight smoke runs (validator 42/56, functest 8/56), trained on model-written RFT data. The "10/49 vs. GPT 24 / Opus 23" run is the first *clean* (merged-and-reviewed) fine-tune. The draft tells both stories, in order.
- **Chronology.** The provenance rule came in two steps: v1 license rule (254 examples, Sun night) and v2 merged/reviewed rule (Mon 9:44 AM, after the box test). The frontier panel (5:24 AM) ran *before* the first real-Quickshell box test (~8:16 AM).
- **Built-ins in v3.** The brief says the retrain includes Omarchy built-in plugins. The build log shows 0 of 38 got through the gates. The draft says so.
- **Manifest fix in v3.** The entryPoints guard fixed 0 rows; the training data was already correct. The draft frames that as the lesson.
- **Loop detector timing.** `loopdet.py` (2:09 PM) predates the grader rebuild (2:54 PM) and the rescoring (~3:06 PM). The draft keeps the brief's section order but places all three in the same afternoon.
- **Training method.** The scripts do bf16 LoRA (r16/α32), not QLoRA as the repo README says. The draft says LoRA.
