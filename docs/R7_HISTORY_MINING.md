# r7: history mining (gap only)
Reuses the earlier mining (candidates.jsonl fix commits, 2,787 verified pairs, r4 trees). New: `train/v3data/build_r7_mine.py` (later versions + Checker per version, confirm/dismiss/clean labels, clones deleted per repo),
`r7_security_units.py` (security-pair sub-classification), `r7_units.py` (mined cands -> build_scope units), `r7_merge.py` (merge, floor, caps, plugin-level split). Numbers: `v3/r7/STATUS.md`, `v3/r7/GATE_REPORT_R7_PILOT.md`.
Dismiss labels are provisional (warn-level, line unchanged in >= 3 later versions), tagged `meta.provisional` and `label_basis`; exclude with `meta.provisional == false`.
