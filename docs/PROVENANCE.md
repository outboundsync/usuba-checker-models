# Provenance

| Material | Origin | Licence | Published where |
|---|---|---|---|
| Plugin source rows | Public plugin repos pinned by commit (`sources/plugin_sources.json`, `NOTICE`) | per row: MIT / Apache-2.0 / ISC (BSD allowed by policy) | rows on Hugging Face; attribution in NOTICE |
| Teacher review text | Qwen3.5-397B-A17B via OpenRouter | Apache-2.0 | rows on Hugging Face |
| Fix pairs | Real upstream fix commits (version-history, jankeesvw-history) | upstream licence per row | rows on Hugging Face |
| Checker reports | `usuba-checker-scripts` | MIT | inside rows |
| Review findings | Public marketplace GitHub threads (other people's text) | no licence: **raw text not published**, only derived rule evidence | `hancore/rule_metrics.json` in the scripts repo |
| Hardware-verified labels / answer key | Private device runs | private | **not published** |
| Sealed holdout | 329 public plugins | contents private | ids + manifest hash in the scripts repo |
| Proprietary-model outputs | evaluation baselines only | provider terms | **raw outputs not published**, score tables only |

Email addresses of third-party plugin authors were replaced by `REDACTED_EMAIL` in the staged Hugging Face files. Home-directory paths were replaced by `/home/user/`.
The `meta` manifests in git (`clean/*_manifest.json`, `v3/train_v3_manifest.json`) were written before that scrub, so their embedded file hashes refer to the pre-scrub files; use `hf/MANIFEST.sha256` to verify the published files.
