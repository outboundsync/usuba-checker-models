# r6 row spec (scope trim, Release 1)

Model jobs: (1) triage of Checker-script findings (confirm/dismiss with quoted line); (2) added findings (category, severity, file, line, quote, finding). Fix text is advisory plain language only.

- No fix rows from upstream commits; `fix_upstream` is dropped (`R6_DROP_SOURCES` default). No patch training or scoring; T4 fix-validity metric dropped.
- Upstream fix commits are kept only as S4 gold for location/kind.
- Per-kind >=15 rule applies to kinds present in triage/added findings.
- prompt_v4 schema unchanged.
- r6 draft: 647 rows (581 train / 66 val), approve 47.3%, Dell share 29.7%; see v3/r6/GATE_REPORT.md.
