# Run records: the r7 data build and Run 2

Concise record of the build and training run behind the current final model. Everything here comes from files in this repository, from the run notes and result files kept on the build box (not in git; archived privately), or from the Hugging Face model card. Anything not recorded is marked **UNKNOWN**; nothing was reconstructed from memory.

## Names (see also `README.md`)
| Name | Meaning |
|---|---|
| Usuba v1 | First Qwen3.5-9B adapter, previous scope. Vast run, finished 2026-10-14, val loss 1.073459 at step 568 (`docs/TRAINING_PLAN.md` run log). The launch post calls this training run "run 1". |
| Usuba v2 | Second, earlier adapter (prompt v2, distilled data). Scored in `holdout-v2-usuba-v2-best-q4km.json`. |
| **Run 2** | The training run of 2026-10-16 on the r7 data build below. Released as **Usuba Checker Model v0.1.0** (tag `model-v0.1.0`, 2026-10-17). **Not** Usuba v2. |

## r7 full build (scope prompt v4 data)
- Pipeline: `docs/R7_HISTORY_MINING.md`, `v3/r7/`, `docs/SCOPE_DATA_BUILDER_SPEC.md`. Mining covered the plugin universe of 5,149 repos (5,033 in the final mining universe); version-history fix pairs, HANCORE concrete findings, Dell-verified rows.
- Built in **40 shards**. Two earlier merges were partial (28 and 31 shards; the build stopped at an LLM-spend cap) and are not what Run 2 trained on. After the cap was raised (hard stop of $40 total build spend) all 40 shards finished and were merged: **3,100 candidate rows** in, **244 rows out** (**221 train / 23 validation**, 226 plugins). The merge entry is stamped 05:37 MT; the date (2026-10-16) is inferred from its position before the Run 2 start.
- Merge settings of that 244-row build: history cap 55%, dismiss share max 35%, per-slug floor 15 rows, Dell cap 30%.
- Composition: row types triage 183, extend 61 (rows with an empty added-findings list: 183, 75%); tier verified 121, provisional 123. Added-finding slugs kept after the floor: rich-text-markup-injection 35, secrets-credentials 26; every other slug fell below the floor and is out of scope for this build. Sources (share of rows): version_history 0.55, hancore_concrete 0.32, dell_broken_verified 0.11, hancore_clean_approve 0.01.
- Triage items: 555 over 218 rows, confirm 410, dismiss 145 (26.1%).
- LLM spend on the build: $30.74 cumulative ledger at the last recorded point (Harris's caps were first $20, then a hard stop of $40 total).
- Data hashes: `train.jsonl.gz` sha256 `203415e0fa21e5bfc132c0cd9bb0d3c5bd6175bf0be6c5efea82e03d3b53aec2`, `val.jsonl.gz` sha256 `12767196ecfedeaf3e41d0fcd93074dca24498d46595fb86ee7dd68008437c57`. Prompt: `scope-v4` (hash recorded only as the prefix `a2317251f69e`).
- Known issue with the same shape in every run note: the validation set is small (23 rows), so per-slug validation rows are too few to measure (`UNMEASURED` marks in the trade-off table).

## Run 2 (training)
- Base Qwen/Qwen3.5-9B, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`. LoRA r=32, alpha=64, dropout 0.05 on the attention and MLP projections. Learning rate 1e-4 cosine, 2 epochs, per-device batch 1 with gradient accumulation 16, seed 1337, max length 32,768, no example weighting.
- Schedule: 221 examples per epoch, 14 steps per epoch, **28 optimizer steps**, evaluation at step 14 (val loss 0.276) and at the end (**final val loss 0.263**, 0.26326). Start val loss 0.480. Final train loss at step 28: 0.224.
- Hardware: rented Vast.ai instance (id kept in the private run notes), NVIDIA H100 PCIe, $2.624/h, python 3.11.14, torch 2.9.1+cu128; launched about 06:30 MT; step 28 was logged at 07:15 MT on 2026-10-16 (0.661 training hours in the log).
- Outputs: `best` adapter `adapter_model.safetensors` sha256 `79cb47183b6577aa046ae2c89f961bd5538f3353ab3eee48455b026946242bb2`; Q4_K_M GGUF (5,629,108,800 bytes) sha256 `7d2b54a24f335aa31d53a47fca8e0848add83bef8246f0f7f831c0e80c9e4f8e`. Both are in the private `osiharris/usuba-checker-adapters` (see `docs/DATA_HOSTING.md`).
- Export hiccup: the GGUF export script crashed on writing run metadata (`git_info()` missing an argument) after the GGUF and its checksum were written; the checksum was verified after fetching to the box.
- Not recorded (**UNKNOWN**): the models-repo and scripts-repo commit SHAs at training time (the run metadata fields are empty), the rules hash, the full prompt hash, the total rental cost (the instance stayed up for exam serving after training and its destroy time is not recorded here), and whether a second seed was run (none is recorded; the card says one run, one seed).

## Run 2 scores (bf16 merge, one-shot, scope prompt v4; machine-draft labels)
All scores are for the **bf16 merge of base + adapter**; the Q4_K_M file has not been scored and no Dell CPU test or GGUF parity run was done. Stock Qwen3.5-9B is the comparison (OpenRouter), same harness, schema, quote filter and greedy decoding. Invalid answers count as wrong. Sets are small, so differences of a few points are noise.

| Metric | Run 2 | stock |
|---|---|---|
| Dell 75: schema-valid | 0.987 | 0.893 |
| Dell 75: verdict accuracy | 0.480 [0.373-0.587] | 0.507 [0.40-0.613] |
| Dell 75: broken plugins flagged | 0.607 | 0.286 |
| Dell 75: false alarm on 47 working plugins | 0.574 | 0.277 |
| S4 60: schema-valid | 0.917 | 0.567 |
| S4 60: bugs found within 3 lines | 8/60 | 4/60 |
| HANCORE holdout 329: schema-valid | 0.939 | 0.638 |
| HANCORE holdout: negatives with a blocker or invalid answer | 8/29 | 11/29 |

Reading: Run 2 learned the answer format; it did not beat stock on judgment (verdict accuracy flat; more false alarms on working Dell plugins). The Usuba Checker Scripts alone score 0.773 [0.667-0.853] on the Dell 75 with no model. Interpretation and caveats live in the Hugging Face model card and the launch post draft (in `usuba-checker-scripts`).

**Stock-model numbers:** the stock Qwen3.5-9B columns above (Dell 75 schema-valid 0.893, verdict accuracy 0.507) come from the 2026-10-16 re-run (run files stamped 2026-10-15 22:59 to 23:56 MT, which is 2026-10-16 UTC), the only reported stock-model Dell numbers; they pair with Run 2. An earlier 2026-10-15 stock run is archived as superseded under `legacy/eval-scope/`.
