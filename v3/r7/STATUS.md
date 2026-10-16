# r7 status (2026-10-15 ~19:00 MT)

## 0. Inventory of what earlier passes already produced (reuse, do not redo)
| asset | count | notes |
|---|---|---|
| universe (plugin repos) | 5,149 | version-history/data/universe.json; 5,128 cloned earlier (clones deleted) |
| candidate fix-like commits mined | 12,109 commits / 50,676 hunks / 2,633 repos | mechanical (message regex + hunk verify), candidates.jsonl |
| LLM-verified fix pairs (round 1+2) | 2,787 pairs / 1,499 repos | MIT 2,619; kinds: logic 728, ui 520, **security 214 (183 repos)**, api 206, lifecycle 192, race 189, path 169, env 166, error 136, syntax 84, null 69, dep 62, shell 47 |
| r4 prepared pairs (licence+guards+trees pre/post ON DISK) | 2,616 (207 security) | /workspace/r4/trees2, 3.8 GB, all trees present |
| r6 pool (pre-scope) | 3,248 candidates: version_history 1,939 (779 plugins), dell_works 1,047, dell_broken 117, hancore_concrete 62, hancore_clean 53, nudged 21, other 9 | Checker reports regenerated: /workspace/r6/scope/findings_pool.json |
| HANCORE concrete findings | 1,446 (+398 file-level) | 538 source trees at the exact SHA on disk |
| r6 draft (old scope) | 647 rows (581/66), approve 47%, Dell 29.7% | v3-data-r6/{train,val}.jsonl.gz |
| r6 scope-v4 build | 90 rows (82/8): triage 53 (23 verified/30 prov), extend 27 (12/15), clean 10 (verified) | 88 plugins; v3-data-r6/scope/ |
| below-floor extend rows | 44 | secrets 13, remote 12, url 10, user-config 5, listing 4 |

Plugin coverage of r6 scope build by source (repos): hancore_concrete 48, dell_broken 17, version_history 11, hancore_clean 9, dell_works 3, nudged 1.
Earlier mining that is NOT redone: fix-commit discovery, LLM verification, kind classification, pre/post trees, HANCORE verification, attribution. The GAP (what r7 mines): (a) Checker diff pre->post on the existing 2,616 pairs (local, no clone); (b) security-pair sub-classification into the weak slugs (214 pairs, local); (c) DISMISS/CLEAN persistence labels, which need later versions of a plugin (only this part needs clones, only for repos that already have pairs).

## 1. Drop-off table (rows), largest earlier datasets -> 90-row scope-v4 build
Datasets by size: v1 legacy 1,054 | r2 543 | r3 582 | r4 1,034 | r5 473 | r6 draft 647 | scope-v4 90. (r1->r5 audit counters in each GATE_REPORT.)
r5 (pool ~4.4k candidates -> 473): not visible under code_blob 353 findings, no finding left 420, all-failed gate 46, v2-val repos 164, near-dup 164, source cap (version_history 40%) 346, approve twins 218+51, guard content 41 / repo 29, no full source 95, synthetic 16, attribution 11, unmappable category 79.
r6 draft (pool 3,248 -> 647): attribution ties/sha-after/unresolvable/mismatch 110 | retraction 1 | no full source 95 | synthetic 16 | no finding left 541 (471 findings cited a line hidden by code_blob, 82 unmappable category) | failed exact-line gate 57 findings (53 rows) | no file/line 12 | guards: same-name 83, per-file J>=.5 171, content 47, same-author 18, repo 29 (=348) | v2-val repos 183 | near-dup 237 | caps: history 40% 280, logic-error 20% 70, undefined-ref 20% 41 | approve twins/minority 303 | kind floor 69 rows.
r6 scope-v4 (3,066 units -> 90): old pool rows not in scope spec 65 (hancore_concrete rebuilt, fix_upstream) | history fixed twins not clean 881 | prefilter (cannot become a row) 1,203 | **unlabelled Checker items (verified tier) 1,542** | teachers disagree 114 | no quotable (hidden) line 81 | nothing to teach 248 | guards: content 23, same-name 32, file 33, author 4, repo 13 | v2-val 42 | near-dup 7 | Dell-share/approve caps 381 | slug floor 44 | reason/label-source 4.
Concrete findings funnel (focus slugs, 462 raw incl. file-level): weak strength / no line / ties / gate / hidden line / checker-dedup / floor -> 90 rows (see v3/r6/scope/build_stats.json).

## 2. Filters flagged
- **Too aggressive but NOT safely loosenable**: code_blob visibility (471+353 findings; the cap is the shared eval/train renderer, changing it breaks the golden hash and train/eval parity); fuzzy guards and holdout/Dell guards (kept by rule); Anthropic ToS exclusion (b3.opus55 ids untouched); Dell share and approve caps (Harris rules).
- **Loosened already** (r6 scope): tie attribution via verified quote / two-model gate; file-level findings located by two models; default-confirm only for extend rows.
- **Main loss is labelling, not guards**: 1,542 + 1,203 units lack a mechanical label for some Checker finding. r7 gap (c) targets exactly this.
- **Candidate to review with Harris**: `v2-val repos` exclusion (183 rows in r6, 42 in scope): legacy v2 validation plugins are not sealed; loosening needs his OK because it changes the v2-vs-v3 comparability.

## 3. Progress
- 18:56 gap (b) security pairs: 207 -> 77 classified into weak slugs (two models agree) -> 6 rows only (61 units dropped: unlabelled Checker items). security_subset/ in this dir.
- 18:56 gap (c) pilot mining of later versions started (300 repos that already have candidate fix commits; resumable; clones deleted per repo; log pilot_mine.log)
- mine pilot finished 19:08
- 19:16 PILOT DONE: 292 of 300 repos processed (7 no permissive licence, 1 too few commits), 2,403 versions checked; labels: 57 verified confirm, 702 provisional dismiss, 446 unlabelled. 349 candidates -> 266 units -> 91 rows (68 verified, 23 provisional). Merged with r6 scope + security subset: pilot_merged/ = 110 rows (98/12), 102 plugins; report GATE_REPORT_R7_PILOT.md.
- Main loss found: 538 of 759 labelled triage items sit in files the code_blob 40k-char cap omits (not visible, so no quote); 74 rows dropped. A design issue for scope-v4, not a guard.
