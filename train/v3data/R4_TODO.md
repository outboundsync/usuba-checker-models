# TODO: r4 dataset (pending)

The r4 data build (`reproduce_r4.sh`, `r4_prepare.py`, `build_r4_hist.py`, `assemble_r4.py`, `finalize_r4.py`) is in this directory as it stood at the integration commit, but the **r4 dataset,
its final reports and its replication check are not part of this release yet**: another job was still finishing them when this repository was assembled
(`/workspace/usuba-runs/v3-data-r4/reproduce_r4.sh` did not exist).

When it lands:
1. Replace `train/v3data/r4_out/*` and `docs/V3_DATA_R4.md` with the final versions.
2. Copy the final `train.jsonl.gz` / `val.jsonl.gz` and `SHA256SUMS` to the Hugging Face dataset repo (`docs/DATA_HOSTING.md`), add them to `hf/MANIFEST.sha256`.
3. Remove this file and tick checklist step 8 in `docs/TRAINING_CHECKLIST.md`.

Known gaps in the current r4/r3 scripts: they read private inputs (hardware-verified key for exclusion ids, the sweep run records, the review-label corpus) and an offline LLM-reply cache
(`r3_cache/llm_cache.jsonl.gz`) that is not published; see `docs/REPLICATION.md`.
