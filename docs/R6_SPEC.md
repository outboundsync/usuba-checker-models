# r6 row spec (scope trim, Release 1)

Model jobs: (1) triage of Checker-script findings (confirm/dismiss with quoted line); (2) added findings (category, severity, file, line, quote, finding). Fix text is advisory plain language only.

- No fix rows from upstream commits; `fix_upstream` is dropped (`R6_DROP_SOURCES` default). No patch training or scoring; T4 fix-validity metric dropped.
- Upstream fix commits are kept only as S4 gold for location/kind.
- Per-kind >=15 rule applies to kinds present in triage/added findings.
- prompt_v4 schema unchanged.
- r6 draft: 647 rows (581 train / 66 val), approve 47.3%, Dell share 29.7%; see v3/r6/GATE_REPORT.md.

## Scope-v4 conversion (build_scope.py)
`train/v3data/build_scope.py` builds triage / extend / clean rows in the `scope-v4` format (no fix rows). Gate numbers: `v3/r6/scope/GATE_REPORT_SCOPE.md` (`tools/scope_gate_report.py`).
Knobs: R6S_RELAX_TIES (0 strict, 1 quoted-verified ties, 2 gate-verified ties), R6S_LOCATE_FILE_LEVEL, R6S_DELL_SHARE, R6S_APPROVE_MAX. Rows below the per-slug floor go to `below_floor.jsonl.gz` (not training data).
