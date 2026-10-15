# r5 GATE_REPORT

rows: train 454, val 96; prompt_sha256 `9660af1be70d76d3890246f9f2d50e40703de2837a12b00ad3de1f9a38766897`; code_blob policy `code_blob/v1 file_cap=12000 code_cap=40000 numbered=1`; checker_git_sha `f61102851d95229397dd4588295e4e8085c73546`; rules_hash `793a7a7de937bf83355b705206203b0bdf99fcd989dda8d80cbdf03c4de6e1ef`

## 1. Exact-line pass rate (recomputed from the written rows)

- train findings: 258; cited file+line visible (numbered) in the shown code: **258 (100.0%)**; val: 55/55 (100.0%)
- builder-side exact-line gate: findings dropped before assembly because the cited line is not visible under the shared policy: 362; failed exact-line gate: 50; rows left without a finding: 411 (+46 all-failed)

## 2. Per-kind file+line share (train, broken rows)

| kind | findings | has file+line | exact-line visible |
|---|---|---|---|
| load:undefined-reference | 45 | 45 (100%) | 45 (100%) |
| unbounded-input-resource | 33 | 33 (100%) | 33 (100%) |
| runtime:logic-error | 22 | 22 (100%) | 22 (100%) |
| file-safety-symlink-perms | 18 | 18 (100%) | 18 (100%) |
| secrets-credentials | 17 | 17 (100%) | 17 (100%) |
| runtime-qml-api-compat | 17 | 17 (100%) | 17 (100%) |
| shell-lua-injection | 14 | 14 (100%) | 14 (100%) |
| privileged-system | 14 | 14 (100%) | 14 (100%) |
| remote-code-pinning | 14 | 14 (100%) | 14 (100%) |
| load:unknown-type | 9 | 9 (100%) | 9 (100%) |
| in-use:missing-binary | 9 | 9 (100%) | 9 (100%) |
| runtime:error-handling | 9 | 9 (100%) | 9 (100%) |
| load:component-not-created | 8 | 8 (100%) | 8 (100%) |
| load:missing-import | 7 | 7 (100%) | 7 (100%) |
| in-use:stale-or-wrong-display | 5 | 5 (100%) | 5 (100%) |
| in-use:missing-file | 4 | 4 (100%) | 4 (100%) |
| load:panel-lifecycle | 3 | 3 (100%) | 3 (100%) |
| load:invalid-binding | 3 | 3 (100%) | 3 (100%) |
| in-use:placeholder-data | 3 | 3 (100%) | 3 (100%) |
| in-use:invalid-command-arg | 2 | 2 (100%) | 2 (100%) |
| runtime:state-or-race | 2 | 2 (100%) | 2 (100%) |

## 3. Source mix (train / val)

| source | train | val |
|---|---|---|
| dell_broken_verified | 52 | 13 |
| dell_inuse_close | 0 | 1 |
| dell_inuse_missing_binary | 3 | 1 |
| dell_works_verified | 188 | 41 |
| hancore_clean_approve | 22 | 1 |
| hancore_concrete | 83 | 16 |
| nudged_approve | 5 | 0 |
| synthetic_lifecycle | 8 | 0 |
| version_history | 93 | 23 |

## 4. Approve mix by source (A2)

| source | approve train | approve val | broken train |
|---|---|---|---|
| dell_broken_verified | 0 | 0 | 52 |
| dell_inuse_close | 0 | 0 | 0 |
| dell_inuse_missing_binary | 0 | 0 | 3 |
| dell_works_verified | 188 | 41 | 0 |
| hancore_clean_approve | 22 | 1 | 0 |
| hancore_concrete | 0 | 0 | 83 |
| nudged_approve | 5 | 0 | 0 |
| synthetic_lifecycle | 0 | 0 | 8 |
| version_history | 0 | 6 | 93 |

approve share of train 47%; of the approves, real clean plugins (HANCORE-clean + Dell-sweep-verified + nudged) = 215 (100%); fixed-twin/synthetic = 0. Only 53 review-clean HANCORE candidates exist (23 survive the gates/guard/dedupe into train): the supply, not the policy, is the limit.

## 5. Label space (A3)

slugs in train (min 15 findings per scored slug, train+val); OUT_OF_SCOPE = not in the prompt, never labelled, eval n/a: ['install-deps-packaging', 'listing-metadata-docs', 'process-lifecycle-timeouts', 'rich-text-markup-injection', 'scope-policy-duplicate', 'url-scheme-network', 'user-config-modification']

| slug | train findings | val findings | scored by HANCORE eval |
|---|---|---|---|
| file-safety-symlink-perms | 18 | 3 | yes |
| in-use:invalid-command-arg | 2 | 1 | no |
| in-use:missing-binary | 9 | 3 | no |
| in-use:missing-file | 4 | 1 | no |
| in-use:placeholder-data | 3 | 1 | no |
| in-use:stale-or-wrong-display | 5 | 3 | no |
| load:component-not-created | 8 | 3 | no |
| load:invalid-binding | 3 | 5 | no |
| load:missing-import | 7 | 3 | no |
| load:panel-lifecycle | 3 | 0 | no |
| load:undefined-reference | 45 | 3 | no |
| load:unknown-type | 9 | 3 | no |
| privileged-system | 14 | 3 | yes |
| remote-code-pinning | 14 | 3 | yes |
| runtime-qml-api-compat | 17 | 3 | no |
| runtime:error-handling | 9 | 3 | no |
| runtime:logic-error | 22 | 3 | no |
| runtime:state-or-race | 2 | 1 | no |
| secrets-credentials | 17 | 3 | yes |
| shell-lua-injection | 14 | 3 | yes |
| unbounded-input-resource | 33 | 4 | yes |

in-scope scored slugs below MIN_PER_SLUG=15 (train+val): none. Scored slugs with no data are OUT_OF_SCOPE: eval reports n/a for them (not recall 0).

## 6. Guards, drops, spend

drops: `{"pool:no_full_source_and_shown_may_be_truncated": 95, "hancore_clean:no_source": 2, "finding:cited_line_not_visible_under_shared_policy": 362, "row:no_finding_left": 411, "finding:unmappable_category": 61, "render:checker_unavailable_or_timeout": 1, "finding:failed_exact_line_gate": 50, "row:all_findings_failed_gate": 46, "row:v2_val_repo_in_pool": 164, "guard:content": 33, "row:over_32k_tokens": 2, "guard:repo": 29, "row:finding_without_file_or_line": 18, "dedupe_near_dup:dell_works_verified_vs_hancore_clean_approve": 3, "dedupe_near_dup:version_history_vs_version_history": 89, "dedupe_near_dup:version_history_vs_dell_works_verified": 57, "dedupe_near_dup:version_history_vs_fix_upstream": 2, "dedupe_near_dup:version_history_vs_dell_broken_verified": 4, "dedupe_near_dup:version_history_vs_hancore_concrete": 9, "dedupe_near_dup:version_history_vs_hancore_clean_approve": 2, "cap:source_version_history_40pct": 324, "approve_history_twin_dropped": 216, "approve_history_minority_cap": 58}`

- holdout/Dell guard rejects: content 33, repo/id 29; v2-val repos kept out of the pool: 164
- LLM gates (qwen/qwen3.5-397b-a17b + openai/gpt-oss-120b, fail-closed): `{"findings": 627, "mech_pass": 627, "qwen_pass": 604, "gptoss_pass": 596, "all_pass": 577, "fail_gptoss": 27, "fail_qwen": 19, "fail_qwengptoss": 4, "calls": 1254, "hits": 1254, "live": 0, "errors": 0, "spent_usd": 0.1265, "cache_entries": 11338}`
- LLM spend this run: $0.1265; stats `{"calls": 0, "hits": 0, "live": 0, "errors": 0, "error_samples": [], "spent_usd": 0.1265, "cache_entries": 11338}`
- LLM cache (replayable, published hash): `6c761367f7cad803dd99e7b59c3795ac6e3a2a14f03676a5b0c9ad4a89ced281`
