# Usuba v3-data-r2 — gate report
Generated Thu Oct 15 07:05:07 MDT 2026 on branch v3-data-r2. No training, no GPU, no Dell commands. Rows: train 523, val 20 (v3 draft was train 1013 / val 41).

Changes vs the v3 draft: (1) HANCORE findings re-anchored to the exact statement; (2) Dell-sourced findings audited against source + Checker/Dell evidence; (3) HANCORE kind labels checked by an independent open-model vote. Open model = qwen/qwen3.5-397b-a17b via OpenRouter (open weights); no Anthropic/DeepSeek/proprietary output.

## 1. Row counts by source
| source | train | val | v3 draft (train+val) |
|---|--:|--:|--:|
| dell_broken_verified | 116 | 7 | 202 |
| dell_inuse_close | 1 | 0 | 1 |
| dell_inuse_missing_binary | 4 | 1 | 7 |
| dell_works_verified | 222 | 7 | 472 |
| fix_upstream | 21 | 2 | 23 |
| hancore_concrete | 156 | 2 | 345 |
| nudged_approve | 3 | 1 | 4 |

## 2. Broken vs approve
- train: {'broken': 277, 'works': 246} (approve share 0.47)
- val: {'broken': 10, 'works': 10} (approve share 0.5)
- all: broken 287, approve 256, approve share 0.471 (target 40-50%)
- HANCORE rows 158, HANCORE findings 158; Dell-sourced broken rows 129 (174 blockers)

## 3. Exact-line check over ALL rows (train+val, every finding that cites file+line, blockers and warnings)
Check = a backticked construct from the finding prose occurs on the cited line ('strict') or within the 2-line statement ('two_line'); blank lines, comment lines and lines without the construct fail. 'nocheck' = the finding names no backticked construct, so it cannot be verified mechanically (counted separately, excluded from the pass rate; the conservative rate counts them as not passing).
| | r2 (this build) | v3 draft |
|---|--:|--:|
| strict | 327 | 419 |
| two_line | 0 | 35 |
| fail | 0 | 160 |
| blank_or_comment | 0 | 39 |
| out_of_range | 0 | 2 |
| file_missing | 0 | 0 |
| nocheck | 6 | 19 |
| **pass rate over checkable findings** | **100.0%** (327/327) | 69.3% |
| conservative pass rate (nocheck counts as fail) | 98.2% | 67.4% |
| independent open-model re-check 'cited line is the exact statement' (fresh prompt, all findings) | 319/333 = 95.8% | n/a |
| rows with a cited line where every finding passes or is nocheck | 288/288 = 100.0% | 378/570 = 66.3% |

Open-model re-check by group: hancore: exact 149/158, defect-stated 156/158; dell_broken: exact 170/174, defect-stated 173/174; approve_warning: exact 0/1, defect-stated 0/1

Pass rate by group (r2): dell/load: 126/126 (+3 nocheck); unbounded-input-resource: 44/44 (+0 nocheck); file-safety-symlink-perms: 27/27 (+0 nocheck); secrets-credentials: 21/21 (+0 nocheck); dell/in-use: 18/18 (+2 nocheck); remote-code-pinning: 17/17 (+0 nocheck); privileged-system: 15/15 (+0 nocheck); shell-lua-injection: 13/13 (+0 nocheck); dell/runtime: 12/12 (+0 nocheck); rich-text-markup-injection: 10/10 (+0 nocheck); process-lifecycle-timeouts: 7/7 (+0 nocheck); dell/qml: 5/5 (+0 nocheck); dell/config: 3/3 (+0 nocheck); dell/packaging: 1/1 (+0 nocheck); runtime-qml-api-compat: 1/1 (+0 nocheck); dell/missing-file: 0/0 (+1 nocheck); dell/syntax: 1/1 (+0 nocheck); user-config-modification: 1/1 (+0 nocheck); url-scheme-network: 1/1 (+0 nocheck); approve-warning: 1/1 (+0 nocheck); listing-metadata-docs: 1/1 (+0 nocheck); dell/security: 1/1 (+0 nocheck); dell/logic: 1/1 (+0 nocheck)

## 4. Fix 1 — HANCORE exact-line anchoring
- HANCORE findings entering the stage: 353 (rows 345). Before-state of the cited line under the new check (after text clean-up, before anchoring): strict 110, two_line 24, construct-not-on-line 97, blank/comment 22, out of range 1, no checkable construct 0.
- **Re-anchored: 134 findings** (moved to the nearest line carrying the quoted construct, within -12/+60 lines, else <=150); kept as-is: 110; **dropped for no exact line: 10 + 0 (no checkable construct) + 0**.
- Second gate (open model, per finding, shown the +-10 lines around the cited line): 'is the cited line the exact statement the finding describes' and 'does the finding state a defect (not safe behaviour / scope / a fix confirmation)'. HANCORE: 47 findings dropped as not-exact (no better visible line), 17 moved to the line the model named (accepted only if the mechanical check also passes), 39 dropped because the prose states no defect. Dell-sourced: 3 dropped, 4 moved; approve warnings: 13 dropped, 0 moved.
- Stale `file:12-34` / `lines 38-56` references inside the prose were stripped (the cited line lives in the structured field); framing like 'Additional current-tree finding:' removed; findings ending in a 300-char ellipsis cut were cut back to the last full sentence or dropped.
- Row-level: HANCORE rows dropped because no finding was left: 187. All drop reasons: `{"hancore_finding:llm_not_exact_line": 47, "hancore_row:no_finding_left": 187, "hancore_finding:kind_disagreement": 36, "hancore_finding:review_framing_or_url": 20, "dell_finding:llm_not_exact_line": 3, "row:no_blocker_left:dell_broken_verified": 79, "dell_finding:audit_construct_absent": 29, "hancore_finding:not_a_defect_statement": 39, "hancore_finding:text_unusable_after_cleanup": 43, "approve_finding:llm_not_exact_line": 13, "dell_finding:audit_not_a_defect": 24, "dell_finding:no_exact_line_found": 9, "dell_finding:qt_labs_import_rule": 13, "dell_finding:audit_optional_fallback": 7, "dell_finding:hedged": 5, "row:no_blocker_left:dell_inuse_missing_binary": 2, "dell_finding:audit_not_executable": 21, "approve_finding:no_exact_line_found": 1, "dell_finding:audit_stock_binary": 8, "dell_finding:audit_hedged": 2, "dell_finding:audit_unverifiable": 8, "dell_finding:stock_binary_rule": 3, "hancore_finding:no_exact_line_found": 10, "cap:approve_trim_to_<=50pct": 241, "cap:approve_trim_per_split_val": 2}`

## 5. Fix 2 — Dell-sourced answer audit
- Audited: 210 rows / 306 findings (dell_broken_verified, dell_inuse_close, dell_inuse_missing_binary). Evidence per finding: the cited code ±8 lines, other occurrences of the quoted constructs, the Checker report as shown in the prompt, the Dell sweep run record (qml_errors, missing_bins) from dell/sweep/results.jsonl, and stock-binary lookups. No Dell key labels were read; key ids are only used for exclusion.
- Outcome by action: {'kept': 186, 'dropped:construct_absent': 29, 'dropped:not_a_defect': 24, 'dropped:qt_labs_import_rule': 13, 'dropped:optional_fallback': 7, 'dropped:hedged': 7, 'dropped:not_executable': 21, 'dropped:stock_binary': 8, 'dropped:unverifiable': 8, 'dropped:stock_rule': 3}.
- Dell broken rows kept: 129 (v3: 210). Dell blocker categories left: `{'load:undefined-property': 22, 'load:unknown-type': 17, 'load:component-not-created': 13, 'load:method-not-found': 11, 'in-use:missing-binary': 9, 'load:invalid-signal-handler': 7, 'load:undefined-method': 6, 'runtime:undefined-method': 5, 'load:qml-type-error': 5, 'load:undefined-identifier': 5, 'load:undefined-reference': 4, 'in-use:missing-file': 4}`.
- The two known errors: gpasswd@setup.sh:108 -> dropped (stock `shadow` tool); mpv `get_property` -> dropped (IPC method string). The sibling finding for the same razer plugin, `Qt.resolvedUrl` passed as a file:// URL, was ALSO dropped: `Service.qml:18` wraps it in `root.pluginPath()` which strips `file://` (my earlier note called it right; it was wrong). Details per finding in `r2_dell_audit_log.jsonl`.
- Evidence class of the 129 kept Dell broken rows: {'checker_static_only': 74, 'dell_runtime_error_or_missing_bin': 55} (runtime = Dell run recorded QML errors or missing binaries; static-only = the Checker flagged it, the Dell run showed no error but did not necessarily open the panel).
- `in-use:missing-binary` blockers remaining: 9 (v3: 47); `security:*` remaining: 1 (v3: 5).

## 6. Fix 3 — HANCORE bug-kind labels (independent open-model vote)
Method: 3 votes per finding from the finding prose only (assigned kind never shown; category order shuffled per vote; temperature 0.3). Keep when 3/3 agree with the assigned kind; relabel when 3/3 agree on another kind; otherwise drop the finding.
- **Before** (v3 labels, 353 findings): majority vote == assigned 261/353 = **73.9%**; unanimous == assigned 69.1%.
- Actions: kept 244, **relabelled 73**, **dropped 36** (split votes).
- **After** (independent re-vote with fresh seeds on the final 158 findings and final kinds): majority == assigned 153/158 = **96.8%**; unanimous == assigned 93.0%.
- Caveat: relabels follow one model's reading; kinds are not human-verified. Many findings genuinely span two kinds (e.g. unbounded read AND no deadline); the vote picks the primary one.

## 7. Per bug kind (blocker findings in broken rows)
| kind | rows | findings | share with file+line |
|---|--:|--:|--:|
| dell-sourced/load:* | 99 | 129 | 100.0% |
| unbounded-input-resource | 44 | 44 | 100.0% |
| file-safety-symlink-perms | 27 | 27 | 100.0% |
| secrets-credentials | 21 | 21 | 100.0% |
| dell-sourced/in-use:* | 18 | 20 | 100.0% |
| remote-code-pinning | 17 | 17 | 100.0% |
| privileged-system | 15 | 15 | 100.0% |
| shell-lua-injection | 13 | 13 | 100.0% |
| rich-text-markup-injection | 10 | 10 | 100.0% |
| dell-sourced/runtime:* | 10 | 12 | 100.0% |
| process-lifecycle-timeouts | 7 | 7 | 100.0% |
| dell-sourced/qml:* | 4 | 5 | 100.0% |
| dell-sourced/config:* | 3 | 3 | 100.0% |
| dell-sourced/packaging:* | 1 | 1 | 100.0% |
| runtime-qml-api-compat | 1 | 1 | 100.0% |
| dell-sourced/missing-file:* | 1 | 1 | 100.0% |
| dell-sourced/syntax:* | 1 | 1 | 100.0% |
| user-config-modification | 1 | 1 | 100.0% |
| url-scheme-network | 1 | 1 | 100.0% |
| listing-metadata-docs | 1 | 1 | 100.0% |
| dell-sourced/security:* | 1 | 1 | 100.0% |
| dell-sourced/logic:* | 1 | 1 | 100.0% |

HANCORE rows whose only kind is unbounded-input-resource: 44 (27.8% of HANCORE rows, 15.3% of broken rows; cap 20% of broken).
File+line share over all blocker findings: 332/332.

## 8. Token lengths
`{'min': 4469, 'p50': 13442, 'p90': 26722, 'p99': 31431, 'max': 31948, 'mean': 15326, 'over_32768': 0, 'over_32000': 0}` (Qwen3.5 tokenizer over json(messages); cap 32000, train max_len 32768).

## 9. Leakage + dedupe checks (recomputed on the written files)
```
{
 "rows_checked": 543,
 "dell_key_ids": 116,
 "dell_key_trees_loaded": 101,
 "holdout_repos": 329,
 "holdout_trees": 329,
 "holdout_manifest_ids": 329,
 "hits": {
  "INFO_incidental_key_id_string_in_other_plugin_text": 4
 },
 "hard_hit_examples": [],
 "duplicate_row_ids": 0,
 "exact_duplicate_trees": 0,
 "train_val_repo_overlap": 0,
 "near_dup_pairs_ge50pct_among_kept": 0
}
```
'INFO_incidental' = a Dell-key id string occurs inside a different plugin's text; manifest id, repo and tree do not match (same as v3). Schema unchanged (same record keys as v3/v2; train_lora.py unchanged).

## 10. Build drops and cost
- stats: `{"hancore_rows_in": 345, "hancore_findings_in": 353, "kind_keep_unanimous": 244, "hancore_anchor_before_fail": 97, "hancore_findings_reanchored": 134, "hancore_anchor_before_strict": 110, "hancore_findings_line_kept": 110, "kind_relabel_unanimous": 73, "dell_rows_in": 210, "dell_findings_in": 306, "dell_findings_reanchored": 9, "hancore_anchor_before_blank_or_comment": 22, "hancore_anchor_before_two_line": 24, "dell_findings_llm_moved": 4, "hancore_findings_llm_moved": 17, "approve_findings_reanchored": 7, "dell_findings_rewritten": 1, "hancore_anchor_before_out_of_range": 1}`
- drops: `{"hancore_finding:llm_not_exact_line": 47, "hancore_row:no_finding_left": 187, "hancore_finding:kind_disagreement": 36, "hancore_finding:review_framing_or_url": 20, "dell_finding:llm_not_exact_line": 3, "row:no_blocker_left:dell_broken_verified": 79, "dell_finding:audit_construct_absent": 29, "hancore_finding:not_a_defect_statement": 39, "hancore_finding:text_unusable_after_cleanup": 43, "approve_finding:llm_not_exact_line": 13, "dell_finding:audit_not_a_defect": 24, "dell_finding:no_exact_line_found": 9, "dell_finding:qt_labs_import_rule": 13, "dell_finding:audit_optional_fallback": 7, "dell_finding:hedged": 5, "row:no_blocker_left:dell_inuse_missing_binary": 2, "dell_finding:audit_not_executable": 21, "approve_finding:no_exact_line_found": 1, "dell_finding:audit_stock_binary": 8, "dell_finding:audit_hedged": 2, "dell_finding:audit_unverifiable": 8, "dell_finding:stock_binary_rule": 3, "hancore_finding:no_exact_line_found": 10, "cap:approve_trim_to_<=50pct": 241, "cap:approve_trim_per_split_val": 2}`
- Open-model spend (OpenRouter usage.cost, qwen/qwen3.5-397b-a17b, all stages): see COST.md

## 11. Samples
See SAMPLES.md (12 fresh random examples + 3 approve, each with its automated cited-line check).

## 12. Remaining weaknesses
1. **Volume fell a lot**: 1,054 rows -> 543 (train 523 / val 20). HANCORE 345 -> 158 rows (every row now has exactly one finding), Dell broken 210 -> 129, approve 499 -> 256 (trimmed to keep 47% approve). This is the price of exact lines + audited labels; 158 HANCORE rows is thin for 12 kinds. Val has only 2 HANCORE rows and 20 rows in total: it is a smoke check, not a measurement.
2. **Kind coverage collapsed in the tail**: HANCORE rows per kind: unbounded-input 44, file-safety 27, secrets 21, remote-code-pinning 17, privileged-system 15, shell/lua injection 13, rich-text 10, process-lifecycle 7, and ONE row each for url-scheme-network, user-config-modification, listing-metadata-docs, runtime-qml-api-compat. install-deps-packaging has none. Expect no learning on those kinds; unbounded-only rows are 27.8% of HANCORE rows (18.6% of broken, under the 20% cap).
3. **Kind labels are one model's reading**: the 96.8% 'after' agreement is measured with the SAME open model (fresh seeds, shuffled category order), so it is inflated by self-consistency; the 73.9% 'before' number is the honest disagreement between the v3 keyword/labeler kinds and the model. Bundled findings still carry a single noisy kind. No human check of the relabels.
4. **Mechanical exact-line check is weaker than it looks**: 100% pass = a backticked construct (word-boundary match) is on the cited line. A generic construct (`StdioCollector`, `pip`, `python3`) can match a line that is a neighbour of the real statement. The independent open-model re-check (different prompt) says the cited line is the exact statement for 149/158 HANCORE and 170/174 Dell findings (95.8% overall); I kept those rows because the cited line still contains the described construct, but about 4% are probably not the exact line.
5. **Dell audit is judge + rules, not execution**: 74 of 129 kept Dell broken rows have Checker static evidence only (the Dell run recorded no QML error / missing binary, though it may never have opened the panel); 55 have Dell runtime errors or missing binaries. Static `load:undefined-property` findings about `Style.*`/`Color.*` members rest on the Checker's view of the shell tree. Remaining `in-use:missing-binary` (9) are third-party tools (cava, anki, perf, zenity, magic-mouse-config, omarchy-pomodoro, blueferry bridge, ...); only magic-mouse-config and omarchy-pomodoro are Dell-confirmed, the rest are 'not stock' by model knowledge and could be wrong if Omarchy ships them.
6. **The Checker report in the prompt still contains false positives** for dropped findings (gpasswd, `Qt.labs` imports, `file://` args that are stripped). Rows whose only finding was wrong were dropped, not converted to 'approve + ignore the Checker line', so the model is not yet taught to veto a bad Checker lead.
7. **Systematic Checker false positive found and removed**: USB-A01 flags `import Qt.labs.*` as 'Qt.labs does not exist on the Qt global object' (13 findings, all dropped; `functest/static_checks.py` itself lists Qt.labs.* as valid Qt6 modules). The Checker rule should be fixed or scoped to JS expressions.
8. **Approve rows**: 255 of 256 carry no cited-line warning; the unbounded-warning 'trusted-and-small' boundary is still taught by only a handful of rows.
9. Partial source trees (hancore_cache) are still used for most HANCORE rows, so extensionless helpers may be absent from the prompt; `low_confidence_sample.jsonl` of v3 is not part of r2.
