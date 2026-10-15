# r6 GATE_REPORT (draft build, 2026-10-15; no training run)

Builder: train/v3data/build_r6.py; env R6_HIST_SHARE=0.92 R6_REUSE_GUARDED=1; Checker pin f611028 rows; guard = r6 (per-file J>=0.5, same-name, same-author); attribution = explicit-mention plurality; fix_upstream rows dropped (scope trim: no fix rows, upstream fixes stay S4 gold only).

```
rows 581 66 approve 306 0.473 dell share 192 0.297
sources {'hancore_clean_approve': 20, 'hancore_concrete': 22, 'version_history': 413, 'dell_broken_verified': 49, 'dell_works_verified': 138, 'dell_inuse_missing_binary': 1, 'nudged_approve': 3, 'dell_inuse_close': 1}
approve by source {'hancore_clean_approve': 20, 'dell_works_verified': 138, 'version_history': 145, 'nudged_approve': 3}
kinds {'load:undefined-reference': 72, 'runtime:logic-error': 68, 'runtime:state-or-race': 51, 'in-use:stale-or-wrong-display': 47, 'in-use:invalid-command-arg': 32, 'unbounded-input-resource': 22, 'runtime-qml-api-compat': 22, 'file-safety-symlink-perms': 19, 'shell-lua-injection': 19}
```

Stage drops are in build_stats.json. Why not ~1,000 rows: stricter guard rejects 83 same-name + 171 per-file + 47 content + 18 same-author rows; attribution drops 110 HANCORE rows (98 ties); near-dup dedupe 141 hist-vs-hist; 20% per-kind caps; the hist share cap (0.92) and the kind floor (secrets-credentials 7, remote-code-pinning 7, in-use:missing-binary 11, in-use:missing-file 5 and others fall below 15 and are merged or dropped). Scored slugs with no data: secrets-credentials, remote-code-pinning, privileged-system etc (eval n/a).

Spot-check of version-history labels (gpt-oss-120b, 40 random): 29/40 agree (0.725; r5 was 0.875): LLM-written finding text is not exact by construction.
