---
license: other
license_name: per-row-original-licences
pretty_name: Usuba Checker training data
language: [en]
tags: [omarchy, quickshell, qml, code-review]
---
# Usuba Checker data (prepared, not yet uploaded)
Training and holdout rows used for the Usuba Checker reviewer model. **Each row keeps the licence of the plugin it came from** (`meta.license`: MIT, Apache-2.0, ISC);
attribution is in `NOTICE` of https://github.com/outboundsync/usuba-checker-models and `sources/licenses/` there. Rows are not relicensed.
No raw review text, no answer keys, no proprietary-model outputs. Third-party author e-mail addresses were replaced by `REDACTED_EMAIL`; home paths by `/home/user/`.
Verify files with `hf/MANIFEST.sha256` (`cd <download dir> && sha256sum -c MANIFEST.sha256`). Paths mirror the GitHub repo layout (`clean/`, `v3/`, `data/`, `sources/`). `v3_r4_public/{train,val}.jsonl.gz` is the final r4 build, **public subset only** (464/896 train, 55/138 val rows): rows built from private device-run records are withheld. Rows from repos on the sealed-holdout id list were removed from every file (`GUARD_FILTER.json` in the GitHub repo hf/ folder).
