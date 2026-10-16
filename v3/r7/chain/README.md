# r7 chain scripts (verbatim copies, 2026-10-15 ~23:05 MT)

These are the orchestration scripts that were running or armed on the build box when this directory was committed. They are copies for the record and for replication; **nothing in this repo runs them**, and the originals on the box were not touched. All paths (`/workspace/...`) are box paths and are env-overridable only where the script says so. No credentials are in these files; the LLM and GPU keys are read from the environment by the tools they call (`train/launch_r7.sh`, `llm_client.py`).

| file | what it does |
|---|---|
| `r7_final.sh` | Original driver: wait for mining, build 40 hash shards (`run_r7_units.sh`), merge (`r7_merge.py`), gate report. It started shards before mining finished (see `v3/r7/STATUS.md`), so it was stopped and replaced by the next file. Kept as the template the armed script derives its merge-only step from. |
| `r7_final_armed.sh` | Waits for the mining process to exit **and** write a new "mine scale finished" line, moves the partial pre-mining shards aside (never deletes), rebuilds all 40 shards, merges only if all 40 have a `DONE` marker, otherwise writes a "FINAL blocked/stopped" line and exits. Resumable. The mining PID inside it is the PID of that one run and is not reusable. |
| `r7_tradeoff_after.sh` | After the final merge, writes the tradeoff table over all candidate rows without caps (`final_tradeoff.md`; tool `train/v3data/r7_tradeoff.py`). |
| `r7_post_chain.sh` | Post-merge chain. Waits for final merge and tradeoff, writes `SHA256SUMS`, runs `r7_hard_checks.py`, widens the eval interval in the train config (backup kept), runs the launch gates (`launch_r7.sh`, no spend), and **only if the file `r7_post_chain.ARMED` exists** runs `launch_r7.sh --go` (rent GPU, train). Single instance (flock), restart-safe, refuses to retry a launch that may have rented an instance (`GO_LAUNCHING` guard). |
| `r7_hard_checks.py` | CPU-only hard checks on the final dataset: train >= 20 rows, val >= 1, train/val repo-disjoint, unique ids (these FAIL the chain); row count, approve share (45-50%), per-kind floor and file+line share (these WARN only). Writes `hard_checks.json` and `NOTIFY_HARRIS.md`. |

## Decision recorded in the code
A final set below 300 rows (`R7_MIN_ROWS`) used to mean "stop rule, no training". Harris overrode that on 2026-10-15: the chain now **warns and trains regardless of row count**. The per-kind and file+line thresholds (`R7_FL_MIN` 0.95, `R7_FL_KIND_MIN` 0.90) are ASSUMED values, not measured ones.

Story and status: `docs/PROJECT_STORY.md`, `v3/r7/STATUS.md`.
