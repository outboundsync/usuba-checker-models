# v3-data-r4

Built on v3-data-r3 (branch `v3-data-r4`). Commit only: no training, no GPU, no Dell commands; Dell key used for ids/paths only; hancore_holdout used only as exclusion fingerprints.

Replicate: `train/v3data/reproduce_r4.sh` (runs r4_prepare, build_r4_hist, assemble_r4, finalize_r4). With `train/v3data/r3_cache/llm_cache.jsonl.gz` every model reply is cached, so a rerun makes no API calls and costs nothing.

Inputs: `version-history/data/verified_pairs.jsonl` (669 pairs; `verified_pairs_2.jsonl` did not exist, so it is not included), `jankeesvw-history/rows.jsonl` (72 rows; rows_tierB and rows_extra unused), r3 pool, v3-fixes synthetic/winners rows.

Policy: MIT/Apache-2.0/BSD/ISC only; exact_removed pairs first, insertion anchors only if they pass the same exact-line checks (none ended up kept); approve rows from post-fix files need Checker with no error lines plus qwen showing no remaining defect near the fix, and are at most 1/3 of history broken. 40-pair spot check by openai/gpt-oss-120b: 35/40 agree (87.5%), the 5 failures dropped. Caps: source <=40% of broken, kind <=20%, unbounded-input-only <=20%. Val repo-disjoint from train, per-kind quota min 3 where available.

Models: qwen/qwen3.5-397b-a17b (reasoning none, temp 0; kind votes temp 0.3, seeds 1700-1702), openai/gpt-oss-120b (reasoning low). Seeds: spot check 4040, assemble 2027, samples 20261015+404. Cost: see `r4_out/COST.md` (r4 extra $1.22).

Outputs and counts: `r4_out/GATE_REPORT.md`, `report.json`, `SAMPLES.md`.
