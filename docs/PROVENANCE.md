# Provenance

| Material | Origin | Licence | Published where |
|---|---|---|---|
| Plugin source rows | Public plugin repos pinned by commit (`sources/plugin_sources.json`, `NOTICE`) | per row: MIT / Apache-2.0 / ISC (BSD allowed by policy) | rows on Hugging Face; attribution in NOTICE |
| Teacher review text | Qwen3.5-397B-A17B via OpenRouter | Apache-2.0 | rows on Hugging Face |
| Fix pairs | Real upstream fix commits (version-history, jankeesvw-history) | upstream licence per row | rows on Hugging Face |
| Checker reports | `usuba-checker-scripts` | MIT | inside rows |
| Review findings | Public marketplace GitHub threads (other people's text) | no licence: **raw text not published**, only derived rule evidence | `hancore/rule_metrics.json` in the scripts repo |
| Hardware-verified labels / answer key | Private device runs | private | **not published**. r4 rows built from device-sweep records (`dell_*` sources, 432 train / 83 val) are withheld from the public dataset; their per-row ids were redacted from the reports in git (`<id-withheld>`). |
| Sealed holdout | 329 public plugins | contents private | ids + manifest hash in the scripts repo |
| Proprietary-model outputs | evaluation baselines only | provider terms | **raw outputs not published**, score tables only |

Email addresses of third-party plugin authors were replaced by `REDACTED_EMAIL` in the staged Hugging Face files. Home-directory paths were replaced by `/home/user/`.
The `meta` manifests in git (`clean/*_manifest.json`, `v3/train_v3_manifest.json`) were written before that scrub, so their embedded file hashes refer to the pre-scrub files; use `hf/MANIFEST.sha256` to verify the published files.

Sealed-holdout hygiene: `train/holdout_guard.py` found that the older 7B-era sets (`clean/train_final.jsonl` 26 rows, `v3/train_v3.jsonl` 30, `clean/pool_chunked.jsonl` 21, `data/train.jsonl` 5, `clean/pool_registry.jsonl` 4, `clean/train_clean.jsonl` 1) contained rows from repos that are in the sealed HANCORE holdout (the 56-task functest holdout, not HANCORE, was the only one used when they were built). Those rows were removed from the published files (`hf/GUARD_FILTER.json`). The 9B training set (`build_train_set.py` / r4) excludes the holdout and the guard reports 0 overlap for it.
