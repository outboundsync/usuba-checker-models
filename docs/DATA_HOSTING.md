# Data and weights hosting (Hugging Face, not Git LFS)

This repository contains no datasets above 2 MB and no weights; there is no Git LFS. Prepared for upload (not yet uploaded):

| Hugging Face repo (proposed) | Content | Licence tag |
|---|---|---|
| `outboundsync/usuba-checker-data` (dataset) | `clean/train_final.jsonl`, `clean/train_clean.jsonl`, `clean/holdout_clean.jsonl`, `clean/pool_*.jsonl`, `v3/train_v3.jsonl`, `data/train.jsonl`, `data/holdout.jsonl`, `data/source_usage.json`, plugin catalogs, and `v3_r4_public/{train,val}.jsonl.gz` (the final r4 build, public subset); paths mirror this repo. Rows from repos that are in the sealed holdout id list were removed (`hf/GUARD_FILTER.json`) | `other` (per-row licence, see NOTICE) |
| `outboundsync/usuba-checker-adapters` (model) | **Nothing yet.** Adapter weights (the two early Qwen2.5-Coder-7B experiments, the Qwen3.5-9B LoRA(s)) are withheld; only their SHA-256 hashes are listed in `hf/ADAPTERS_CARD.md`. Final weights will be uploaded after the v3 run. | `apache-2.0` |

`hf/MANIFEST.sha256` lists SHA-256 of every file to upload in plain `sha256sum` format; paths are relative to the dataset repo root (the first column is the digest, the second the path inside the Hugging Face dataset repo). Verify from the download directory with `sha256sum -c MANIFEST.sha256`. Adapter weights are withheld; their hashes are in `hf/ADAPTERS_CARD.md`.
Layout used by the scripts: download the dataset into the repo root so that `clean/`, `v3/`, `data/`, `sources/` paths line up
(`huggingface-cli download outboundsync/usuba-checker-data --repo-type dataset --local-dir .`).

The Qwen3.5-9B adapter of the Usuba v1 run (`best/`, val loss 1.0735, step 568; the v2 adapter is a separate later run, and which of the two the hash in `hf/ADAPTERS_CARD.md` belongs to is unresolved, see the identity note there) and its Q4_K_M GGUF were produced on a rented GPU and archived in a private bucket; they still have to be copied
into the adapters repo (see `docs/TRAINING_CHECKLIST.md` step 12). GGUF SHA-256 recorded in `docs/TRAINING_PLAN.md` run log.

## Known gaps in the hosting records (audit F3, not reproducible from this repo)
- `hf/GUARD_FILTER.json` has no entry for `v3_r4_public/{train,val}.jsonl.gz`. Those files are not in this repository, so the sealed-holdout filter counts cannot be recomputed here; run `train/holdout_guard.py` against the r4 build and add the entry before upload.
- The pool_chunked count differs between `hf/GUARD_FILTER.json` (313 kept + 21 dropped = 334) and `clean/README.md` (328 after final dedupe, 334 built). These are different stages (before and after dedupe); the dataset files are not in this repo, so I could not confirm which one the staged file matches.
