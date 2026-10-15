# Usuba v3-data-r3 — gate report
Generated Thu Oct 15 08:54:44 MDT 2026 on branch v3-data-r3. No training, no GPU, no Dell commands. Rows: train 516, val 66 (r2 was train 523 / val 20).

Changes vs r2: (0, r3) Checker false positives fixed and reports regenerated, 66-row val set, recovered HANCORE rows, v3-fixes merged (new prompt_v3, lifecycle rules, retractions); carried over from r2: (1) HANCORE findings re-anchored to the exact statement; (2) Dell-sourced findings audited against source + Checker/Dell evidence; (3) HANCORE kind labels checked by an independent open-model vote. Open model = qwen/qwen3.5-397b-a17b via OpenRouter (open weights); no Anthropic/DeepSeek/proprietary output.

## 1. Row counts by source
| source | train | val | r2 (train+val) |
|---|--:|--:|--:|
| dell_broken_verified | 101 | 16 | 123 |
| dell_inuse_close | 1 | 0 | 1 |
| dell_inuse_missing_binary | 4 | 1 | 5 |
| dell_works_verified | 224 | 0 | 229 |
| fix_upstream | 8 | 15 | 23 |
| hancore_concrete | 156 | 16 | 158 |
| nudged_approve | 3 | 18 | 4 |
| synthetic_lifecycle | 16 | 0 | 0 |
| winners_mit | 3 | 0 | 0 |

## 2. Broken vs approve
- train: {'broken': 269, 'works': 244, 'unsure': 3} (approve share 0.473)
- val: {'broken': 33, 'works': 33} (approve share 0.5)
- all: broken 305, approve 277, approve share 0.476 (target 40-50%)
- HANCORE rows 172, HANCORE findings 172; Dell-sourced broken rows 123 (167 blockers)

## 3. Exact-line check over ALL rows (train+val, every finding that cites file+line, blockers and warnings)
Check = a backticked construct from the finding prose occurs on the cited line ('strict') or within the 2-line statement ('two_line'); blank lines, comment lines and lines without the construct fail. 'nocheck' = the finding names no backticked construct, so it cannot be verified mechanically (counted separately, excluded from the pass rate; the conservative rate counts them as not passing).
| | r3 (this build) | r2 |
|---|--:|--:|
| strict | 340 | 327 |
| two_line | 0 | 0 |
| fail | 3 | 0 |
| blank_or_comment | 0 | 0 |
| out_of_range | 0 | 0 |
| file_missing | 3 | 0 |
| nocheck | 6 | 6 |
| **pass rate over checkable findings** | **98.3%** (340/346) | 100.0% |
| conservative pass rate (nocheck counts as fail) | 96.6% | 98.2% |
| independent open-model re-check 'cited line is the exact statement' (fresh prompt, all findings) | 334/349 = 95.7% | n/a |
| rows with a cited line where every finding passes or is nocheck | 302/308 = 98.1% | 288/288 = 100.0% |

Open-model re-check by group: dell_broken: exact 169/174, defect-stated 173/174; hancore: exact 162/172, defect-stated 170/172; approve_warning: exact 3/3, defect-stated 2/3

Pass rate by group (r2): dell/load: 120/120 (+3 nocheck); unbounded-input-resource: 58/58 (+0 nocheck); file-safety-symlink-perms: 26/26 (+0 nocheck); secrets-credentials: 21/21 (+0 nocheck); dell/in-use: 18/18 (+2 nocheck); remote-code-pinning: 18/18 (+0 nocheck); privileged-system: 16/16 (+0 nocheck); approve-warning: 7/13 (+0 nocheck); shell-lua-injection: 13/13 (+0 nocheck); dell/runtime: 12/12 (+0 nocheck); rich-text-markup-injection: 10/10 (+0 nocheck); process-lifecycle-timeouts: 6/6 (+0 nocheck); dell/qml: 4/4 (+0 nocheck); dell/config: 3/3 (+0 nocheck); dell/missing-file: 0/0 (+1 nocheck); runtime-qml-api-compat: 1/1 (+0 nocheck); url-scheme-network: 1/1 (+0 nocheck); dell/syntax: 1/1 (+0 nocheck); listing-metadata-docs: 1/1 (+0 nocheck); dell/packaging: 1/1 (+0 nocheck); dell/logic: 1/1 (+0 nocheck); user-config-modification: 1/1 (+0 nocheck); dell/security: 1/1 (+0 nocheck)

## 4. Fix 1 — HANCORE exact-line anchoring
- HANCORE findings entering the stage: 408 (rows 400). Before-state of the cited line under the new check (after text clean-up, before anchoring): strict 137, two_line 25, construct-not-on-line 103, blank/comment 22, out of range 1, no checkable construct 0.
- **Re-anchored: 138 findings** (moved to the nearest line carrying the quoted construct, within -12/+60 lines, else <=150); kept as-is: 137; **dropped for no exact line: 13 + 0 (no checkable construct) + 0**.
- Second gate (open model, per finding, shown the +-10 lines around the cited line): 'is the cited line the exact statement the finding describes' and 'does the finding state a defect (not safe behaviour / scope / a fix confirmation)'. HANCORE: 50 findings dropped as not-exact (no better visible line), 17 moved to the line the model named (accepted only if the mechanical check also passes), 43 dropped because the prose states no defect. Dell-sourced: 3 dropped, 4 moved; approve warnings: 34 dropped, 1 moved.
- Stale `file:12-34` / `lines 38-56` references inside the prose were stripped (the cited line lives in the structured field); framing like 'Additional current-tree finding:' removed; findings ending in a 300-char ellipsis cut were cut back to the last full sentence or dropped.
- Row-level: HANCORE rows dropped because no finding was left: 218. All drop reasons: `{"hancore_finding:llm_not_exact_line": 50, "hancore_row:no_finding_left": 218, "hancore_finding:not_a_defect_statement": 43, "hancore_finding:kind_disagreement": 40, "hancore_finding:review_framing_or_url": 25, "hancore_finding:text_unusable_after_cleanup": 55, "hancore_finding:no_exact_line_found": 13, "dell_finding:audit_not_executable": 21, "row:no_blocker_left:dell_broken_verified": 78, "dell_finding:hedged": 5, "dell_finding:audit_unverifiable": 8, "dell_finding:audit_construct_absent": 29, "dell_finding:audit_not_a_defect": 24, "dell_finding:audit_optional_fallback": 7, "dell_finding:no_exact_line_found": 9, "dell_finding:audit_stock_binary": 8, "dell_finding:qt_labs_import_rule": 12, "dell_finding:llm_not_exact_line": 3, "dell_finding:audit_hedged": 2, "dell_finding:stock_binary_rule": 3, "row:no_blocker_left:dell_inuse_missing_binary": 2, "approve_finding:llm_not_exact_line": 34, "approve_finding:no_exact_line_found": 4, "cap:train_rows_dropped_near_dup_with_val": 1, "cap:cap_approve_trim_train": 819}`

## 5. Fix 2 — Dell-sourced answer audit
- Audited: 208 rows / 304 findings (dell_broken_verified, dell_inuse_close, dell_inuse_missing_binary). Evidence per finding: the cited code ±8 lines, other occurrences of the quoted constructs, the Checker report as shown in the prompt, the Dell sweep run record (qml_errors, missing_bins) from dell/sweep/results.jsonl, and stock-binary lookups. No Dell key labels were read; key ids are only used for exclusion.
- Outcome by action: {'dropped:not_executable': 21, 'dropped:hedged': 7, 'kept': 185, 'dropped:unverifiable': 8, 'dropped:construct_absent': 29, 'dropped:not_a_defect': 24, 'dropped:optional_fallback': 7, 'dropped:stock_binary': 8, 'dropped:qt_labs_import_rule': 12, 'dropped:stock_rule': 3}.
- Dell broken rows kept: 123 (v3: 129). Dell blocker categories left: `{'load:undefined-property': 20, 'load:unknown-type': 17, 'load:component-not-created': 13, 'in-use:missing-binary': 9, 'load:method-not-found': 9, 'load:invalid-signal-handler': 7, 'load:undefined-method': 6, 'load:undefined-identifier': 5, 'runtime:undefined-method': 5, 'load:qml-type-error': 5, 'in-use:missing-file': 4, 'load:undefined-reference': 4}`.
- The two known errors: gpasswd@setup.sh:108 -> dropped (stock `shadow` tool); mpv `get_property` -> dropped (IPC method string). The sibling finding for the same razer plugin, `Qt.resolvedUrl` passed as a file:// URL, was ALSO dropped: `Service.qml:18` wraps it in `root.pluginPath()` which strips `file://` (my earlier note called it right; it was wrong). Details per finding in `r3_dell_audit_log.jsonl`.
- Evidence class of the 123 kept Dell broken rows: {'checker_static_only': 68, 'dell_runtime_error_or_missing_bin': 55} (runtime = Dell run recorded QML errors or missing binaries; static-only = the Checker flagged it, the Dell run showed no error but did not necessarily open the panel).
- `in-use:missing-binary` blockers remaining: 9 (v3: 9); `security:*` remaining: 1 (v3: 1).

## 6. Fix 3 — HANCORE bug-kind labels (independent open-model vote)
Method: 3 votes per finding from the finding prose only (assigned kind never shown; category order shuffled per vote; temperature 0.3). Keep when 3/3 agree with the assigned kind; relabel when 3/3 agree on another kind; otherwise drop the finding.
- **Before** (v3 labels, 408 findings): majority vote == assigned 303/408 = **74.3%**; unanimous == assigned 69.4%.
- Actions: kept 283, **relabelled 85**, **dropped 40** (split votes).
- **After** (independent re-vote with fresh seeds on the final 172 findings and final kinds): majority == assigned 168/172 = **97.7%**; unanimous == assigned 95.3%.
- Caveat: relabels follow one model's reading; kinds are not human-verified. Many findings genuinely span two kinds (e.g. unbounded read AND no deadline); the vote picks the primary one.

## 7. Per bug kind (blocker findings in broken rows)
| kind | rows | findings | share with file+line |
|---|--:|--:|--:|
| dell-sourced/load:* | 101 | 130 | 100.0% |
| unbounded-input-resource | 58 | 58 | 100.0% |
| file-safety-symlink-perms | 26 | 26 | 100.0% |
| secrets-credentials | 21 | 21 | 100.0% |
| remote-code-pinning | 18 | 18 | 100.0% |
| dell-sourced/in-use:* | 18 | 20 | 100.0% |
| privileged-system | 16 | 16 | 100.0% |
| shell-lua-injection | 13 | 13 | 100.0% |
| dell-sourced/runtime:* | 10 | 12 | 100.0% |
| rich-text-markup-injection | 10 | 10 | 100.0% |
| process-lifecycle-timeouts | 6 | 6 | 100.0% |
| dell-sourced/qml:* | 3 | 4 | 100.0% |
| dell-sourced/config:* | 3 | 3 | 100.0% |
| dell-sourced/url-scheme-network:* | 1 | 1 | 100.0% |
| dell-sourced/missing-file:* | 1 | 1 | 100.0% |
| dell-sourced/remote-code-pinning:* | 1 | 1 | 100.0% |
| dell-sourced/privileged-system:* | 1 | 1 | 100.0% |
| runtime-qml-api-compat | 1 | 1 | 100.0% |
| url-scheme-network | 1 | 1 | 100.0% |
| dell-sourced/syntax:* | 1 | 1 | 100.0% |
| listing-metadata-docs | 1 | 1 | 100.0% |
| dell-sourced/packaging:* | 1 | 1 | 100.0% |
| dell-sourced/logic:* | 1 | 1 | 100.0% |
| user-config-modification | 1 | 1 | 100.0% |
| dell-sourced/security:* | 1 | 1 | 100.0% |

HANCORE rows whose only kind is unbounded-input-resource: 58 (33.7% of HANCORE rows, 19.0% of broken rows; cap 20% of broken).
File+line share over all blocker findings: 349/349.

## 8. Token lengths
`{'min': 4184, 'p50': 13483, 'p90': 26652, 'p99': 31182, 'max': 31783, 'mean': 15657, 'over_32768': 0, 'over_32000': 0}` (Qwen3.5 tokenizer over json(messages); cap 32000, train max_len 32768).

## 9. Leakage + dedupe checks (recomputed on the written files)
```
{
 "rows_checked": 582,
 "dell_key_ids": 116,
 "dell_key_trees_loaded": 101,
 "holdout_repos": 329,
 "holdout_trees": 329,
 "holdout_manifest_ids": 329,
 "hits": {
  "INFO_incidental_key_id_string_in_other_plugin_text": 3
 },
 "hard_hit_examples": [],
 "duplicate_row_ids": 0,
 "exact_duplicate_trees": 0,
 "train_val_repo_overlap": 0,
 "near_dup_pairs_ge50pct_among_kept": 5
}
```
'INFO_incidental' = a Dell-key id string occurs inside a different plugin's text; manifest id, repo and tree do not match (same as v3). Schema unchanged (same record keys as v3/v2; train_lora.py unchanged).

## 10. Build drops and cost
- stats: `{"hancore_rows_in": 400, "hancore_findings_in": 408, "kind_relabel_unanimous": 85, "hancore_anchor_before_strict": 137, "hancore_findings_line_kept": 137, "hancore_anchor_before_fail": 103, "hancore_findings_reanchored": 138, "kind_keep_unanimous": 283, "hancore_findings_llm_moved": 17, "hancore_anchor_before_two_line": 25, "hancore_anchor_before_blank_or_comment": 22, "hancore_anchor_before_out_of_range": 1, "dell_rows_in": 208, "dell_findings_in": 304, "dell_findings_reanchored": 9, "dell_findings_llm_moved": 4, "dell_findings_rewritten": 1, "approve_findings_reanchored": 18, "approve_findings_llm_moved": 1, "hancore_reports_regenerated_from_full_tree": 181, "rows_with_changed_report": 96, "report_lines_removed": 29, "report_lines_added": 2, "report_lines_unexplained_kept": 43, "regen_checker_unavailable": 2, "prompt_v3_rewrap_over_32k_dropped": 21, "v3fixes_dropped_retraction_whole": 9, "v3fixes_dropped_approve_lifecycle_audit": 5, "v3fixes_dell_label_noise_rows_dropped": 1, "fx_synthetic_in": 16, "fx_winners_in": 3, "fx_winners_excluded_include_in_train_false": 3}`
- drops: `{"hancore_finding:llm_not_exact_line": 50, "hancore_row:no_finding_left": 218, "hancore_finding:not_a_defect_statement": 43, "hancore_finding:kind_disagreement": 40, "hancore_finding:review_framing_or_url": 25, "hancore_finding:text_unusable_after_cleanup": 55, "hancore_finding:no_exact_line_found": 13, "dell_finding:audit_not_executable": 21, "row:no_blocker_left:dell_broken_verified": 78, "dell_finding:hedged": 5, "dell_finding:audit_unverifiable": 8, "dell_finding:audit_construct_absent": 29, "dell_finding:audit_not_a_defect": 24, "dell_finding:audit_optional_fallback": 7, "dell_finding:no_exact_line_found": 9, "dell_finding:audit_stock_binary": 8, "dell_finding:qt_labs_import_rule": 12, "dell_finding:llm_not_exact_line": 3, "dell_finding:audit_hedged": 2, "dell_finding:stock_binary_rule": 3, "row:no_blocker_left:dell_inuse_missing_binary": 2, "approve_finding:llm_not_exact_line": 34, "approve_finding:no_exact_line_found": 4, "cap:train_rows_dropped_near_dup_with_val": 1, "cap:cap_approve_trim_train": 819}`
- Open-model spend (OpenRouter usage.cost, qwen/qwen3.5-397b-a17b, all stages): see COST.md

## 11. Samples
See SAMPLES.md (12 fresh random examples + 3 approve, each with its automated cited-line check).

## 12. Remaining weaknesses
1. **Volume is small**: 582 rows (train 516 / val 66; broken 305, approve 277 = 47.6%). HANCORE rows 172 (28 from the recovered file:line job, 22 of them from plugins that had no row before), one finding per row; Dell broken 123. 21 rows were dropped only because the longer 7-shot prompt_v3 pushed them over 32k tokens; the 218 HANCORE rows that lost every finding (exact-line gate, kind vote, not-a-defect) are the main loss (400 in, 172 out).
2. **Kind tail is still empty/thin**: HANCORE rows per kind: unbounded-input 58 (33.7% of HANCORE rows, 19.0% of broken), file-safety 26, secrets 21, remote-code-pinning 18, privileged-system 16, shell/lua injection 13, rich-text 10, process-lifecycle 6, and ONE row each for runtime-qml-api-compat, url-scheme-network, listing-metadata-docs, user-config-modification; install-deps-packaging has none. The recovered rows did not fix this: most failed the exact-line/kind gates. Expect no learning on those kinds.
3. **Val is balanced but small and kind-sparse**: 66 rows (33 broken / 33 approve; HANCORE 16 rows over 6 kinds, Dell 17). Per-kind val counts are 1-5, so it is a smoke/regression set, not a per-kind measurement. It is repo-disjoint from train and near-dup-filtered against train (1 train row dropped), holdout and the Dell key.
4. **Kind labels are one model's reading**: 'after' agreement (97.7%) is the same open model re-voting with fresh seeds, so inflated; the 74.3% 'before' is the honest disagreement with the keyword labels. Relabels (85) are unreviewed by a human.
5. **Mechanical exact-line check is weak for generic constructs**: pass 98.3% (340/346 checkable); the 6 non-pass are all synthetic v3-fixes rows (cite manifest.json or a file whose construct is described structurally, not by a backticked token). The independent open-model re-check (different prompt) says the cited line is the exact statement for 334/349 findings (95.7%); HANCORE 162/172, Dell 169/174. About 4% are probably neighbour lines.
6. **Checker fixes are partial**: A01 import lines, B01 (stock Arch tools, snake_case/prose words, words only inside quotes/jq/echo, functions/case patterns), F01 (absolute and non-script paths) and J04 (path-stripping wrappers) are fixed; 29 stale report lines were removed from rows and 2 lifecycle lines added (v3-fixes). B01 still flags real-but-dev-only tools (cargo, meson, qmllint, perf, zenity, update-desktop-database) on stock Omarchy and fires on a few remaining prose words; these remain in 22 report lines and teach the model to judge relevance (the row keeps the line; the answer ignores it). Dell/approve reports were regenerated by diff on the visible files (43 stored lines the old Checker could not reproduce were kept, `USB-Hnn warn` renamed to `HC`); HANCORE reports were regenerated by running the new Checker on the full source tree.
7. **Veto examples are few**: approve rows that still show Checker error lines (A08/B01/A01 heuristics, mostly Dell-verified working plugins) are the only 'ignore the lead' examples; rows whose only finding was a Checker false positive were dropped, not converted.
8. **Dell audit is judge + rules**: 68 of 123 kept Dell broken rows have Checker static evidence only. Third-party binaries listed as missing are Dell-confirmed for only two.
9. **v3-fixes folded in**: re-wrapped with the new prompt_v3 (7 shots); dropped 9 retracted HANCORE rows, the partially retracted omapass row (kept out because the remaining blocker could not be verified) and 5 approve rows that contradict the lifecycle rule (1 of the 6 listed ids was not in the pool); dropped the go-idasen Dell row (label noise: bad-import on unreachable QML; not converted to approve because there is no Dell evidence for the approve answer; the other 6 relabel candidates have no Dell-broken row in the pool); added 16 synthetic rows (9 broken/7 approve, train only, ~3%) and 3 winners rows; the 3 omagotchi rows (include_in_train=false) are written to excluded_include_in_train_false.jsonl, not trained. 3 of the 19 extra rows have load 'unsure'.
10. **Not used**: /workspace/usuba-runs/version-history/ (absent at build). Plugin sources come from partial trees for many HANCORE rows, so extensionless helpers can be missing from the prompt.


## 13. r3 additions
- **Checker false positives fixed** (functest/usuba/checks.py): A01 no longer fires on `import Qt.labs.*` lines; B01 skips stock Arch base tools, MIME/snake_case/trailing-dash tokens, shell functions and case patterns defined in the plugin, and words never in command position; F01 only for relative/./-style or extension paths and not absolute paths; J04 skips Qt.resolvedUrl wrapped in a path-stripping helper. Regeneration = old-checker vs fixed-checker diff on each row's visible files; only lines the fixed Checker no longer emits were removed. Lines removed per rule across all rows: `{'USB-F01': 12, 'USB-B01': 15, 'USB-J04': 2}` (rows touched 0). Most Dell findings that restated these false positives were already dropped by the r2 audit; the remaining Checker lines in rows are ones the fixed Checker still emits.
- **Val set**: 66 rows (33 broken, 33 approve), repo-disjoint from train, selected kind-stratified (about 12% quota per kind), near-dup checked vs train (train rows near-dup with val dropped: 1). Val broken kinds: `{'H:unbounded-input-resource': 5, 'D:load:qml-type-error': 1, 'D:in-use:missing-asset': 2, 'H:remote-code-pinning': 5, 'D:load:missing-property': 1, 'D:in-use:missing-file': 1, 'H:shell-lua-injection': 1, 'D:load:qml-property-error': 1, 'D:load:component-not-created': 4, 'D:load:undefined-property': 3, 'H:file-safety-symlink-perms': 3, 'D:load:method-not-found': 5, 'D:load:property-not-found': 1, 'D:load:undefined-method': 1, 'D:load:missing-file': 1, 'H:privileged-system': 1, 'D:security:placeholder-credential': 1, 'D:in-use:missing-binary': 1, 'H:secrets-credentials': 1, 'D:load:module-not-installed': 1}`.
- **Recovered HANCORE rows** (hancore-labels-r2/recovered.jsonl, 319 findings, 306 plugins) WERE folded in: they went through the same build, kind vote, text clean-up, exact-line anchoring and model gate as other HANCORE findings. HANCORE rows in the final set: 172.
- Version-history dataset (/workspace/usuba-runs/version-history/): not used (not present at build time).
