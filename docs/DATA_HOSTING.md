# Data and weights hosting (Hugging Face, not Git LFS)

This repository contains no datasets above 2 MB and no weights; there is no Git LFS. Prepared for upload (not yet uploaded):

| Hugging Face repo (proposed) | Content | Licence tag |
|---|---|---|
| `outboundsync/usuba-checker-data` (dataset) | `clean/train_final.jsonl`, `clean/train_clean.jsonl`, `clean/holdout_clean.jsonl`, `clean/pool_*.jsonl`, `v3/train_v3.jsonl`, `data/train.jsonl`, `data/holdout.jsonl`, `data/source_usage.json`, plugin catalogs, and `v3_r4_public/{train,val}.jsonl.gz` (the final r4 build, public subset); paths mirror this repo. Rows from repos that are in the sealed holdout id list were removed (`hf/GUARD_FILTER.json`) | `other` (per-row licence, see NOTICE) |
| `outboundsync/usuba-checker-adapters` (model) | **Nothing yet.** Adapter weights (the two early Qwen2.5-Coder-7B experiments, the Qwen3.5-9B LoRA(s)) are withheld; only their SHA-256 hashes are listed in `hf/ADAPTERS_CARD.md`. Final weights will be uploaded after the v3 run. | `apache-2.0` |

`hf/MANIFEST.sha256` lists SHA-256 of every file to upload in plain `sha256sum` format; paths are relative to the dataset repo root (the first column is the digest, the second the path inside the Hugging Face dataset repo). Verify from the download directory with `sha256sum -c MANIFEST.sha256`. Adapter weights are withheld; their hashes are in `hf/ADAPTERS_CARD.md`.
Layout used by the scripts: download the dataset into the repo root so that `clean/`, `v3/`, `data/`, `sources/` paths line up
(`huggingface-cli download outboundsync/usuba-checker-data --repo-type dataset --local-dir .`; **not yet uploaded: this repo does not exist on Hugging Face yet**).

The Qwen3.5-9B adapter of the Usuba v1 run (`best/`, val loss 1.0735, step 568; the v2 adapter is a separate later run, and which of the two the hash in `hf/ADAPTERS_CARD.md` belongs to is unresolved, see the identity note there) and its Q4_K_M GGUF were produced on a rented GPU and archived in a private bucket; they still have to be copied
into the adapters repo (see `docs/TRAINING_CHECKLIST.md` step 12). GGUF SHA-256 recorded in `docs/TRAINING_PLAN.md` run log.

## Repo paths vs Hugging Face paths (audit F7)
The GitHub repo moved the legacy builders to `legacy/clean/`, `legacy/qwen25-coder-v3/` (was `v3/`), `legacy/data/`, `legacy/runs/`. The Hugging Face dataset keeps its own layout (`clean/`, `v3/`, `data/`, `v3_r4_public/`) and so do `hf/MANIFEST.sha256` and `hf/GUARD_FILTER.json`: the keys there are dataset-repo paths, not paths in this repo. Mapping: HF `clean/X` = repo `legacy/clean/X`, HF `v3/X` = repo `legacy/qwen25-coder-v3/X`, HF `data/X` = repo `legacy/data/X`.

## Known gaps in the hosting records (audit F3, not reproducible from this repo)
- **Resolved (F3):** `hf/GUARD_FILTER.json` now has entries for `v3_r4_public/{train,val}.jsonl.gz` (464 / 55 rows kept, 0 dropped, with file sha256), recomputed by `tools/recompute_guard_filter.py` from the staged files (sha256 matches `hf-staging/.../SHA256SUMS`). The full r4 build (896 / 138 rows) also has 0 overlap; its files are private, so only the public subset is listed.
- **Resolved (F3): the pool_chunked 334 vs 328 discrepancy.** Recomputed from the raw file (`clean/pool_chunked.jsonl`, 334 rows, all distinct messages): the guard drops 21 rows from sealed-holdout repos -> **313 kept**, which is exactly the staged file (313 rows). `clean/README.md`'s "328 after final dedupe" does not describe this file: there is no dedupe step that yields 328 (all 334 are distinct), so 328 is a stale figure from an intermediate build and the README now says 334 built / 313 after the holdout guard. (`tools/recompute_guard_filter.py --source <dir> clean/pool_chunked.jsonl` reproduces 313/21.)
