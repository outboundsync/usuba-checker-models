# r5 GATE_REPORT

rows: train 383, val 90; prompt_sha256 `8f55c5f198695b4b00f02f0b364681faa7c5679e7b6cbd82e84e50e5181f221a`; code_blob policy `code_blob/v1 file_cap=12000 code_cap=40000 numbered=1`; checker_git_sha `f61102851d95229397dd4588295e4e8085c73546`; rules_hash `793a7a7de937bf83355b705206203b0bdf99fcd989dda8d80cbdf03c4de6e1ef`

## 1. Exact-line pass rate (recomputed from the written rows)

- train findings: 219; cited file+line visible (numbered) in the shown code: **219 (100.0%)**; val: 53/53 (100.0%)
- builder-side exact-line gate: findings dropped before assembly because the cited line is not visible under the shared policy: 353; failed exact-line gate: 50; rows left without a finding: 420 (+46 all-failed)

## 2. Per-kind file+line share (train, broken rows)

| kind | findings | has file+line | exact-line visible |
|---|---|---|---|
| load:undefined-reference | 43 | 43 (100%) | 43 (100%) |
| unbounded-input-resource | 31 | 31 (100%) | 31 (100%) |
| runtime:logic-error | 20 | 20 (100%) | 20 (100%) |
| file-safety-symlink-perms | 16 | 16 (100%) | 16 (100%) |
| secrets-credentials | 16 | 16 (100%) | 16 (100%) |
| shell-lua-injection | 14 | 14 (100%) | 14 (100%) |
| runtime-qml-api-compat | 13 | 13 (100%) | 13 (100%) |
| remote-code-pinning | 13 | 13 (100%) | 13 (100%) |
| load:unknown-type | 9 | 9 (100%) | 9 (100%) |
| runtime:error-handling | 8 | 8 (100%) | 8 (100%) |
| in-use:missing-binary | 7 | 7 (100%) | 7 (100%) |
| load:missing-import | 7 | 7 (100%) | 7 (100%) |
| in-use:stale-or-wrong-display | 4 | 4 (100%) | 4 (100%) |
| in-use:missing-file | 4 | 4 (100%) | 4 (100%) |
| load:component-not-created | 4 | 4 (100%) | 4 (100%) |
| in-use:placeholder-data | 3 | 3 (100%) | 3 (100%) |
| load:invalid-binding | 3 | 3 (100%) | 3 (100%) |
| in-use:invalid-command-arg | 2 | 2 (100%) | 2 (100%) |
| runtime:state-or-race | 2 | 2 (100%) | 2 (100%) |

## 3. Source mix (train / val)

| source | train | val |
|---|---|---|
| dell_broken_verified | 51 | 14 |
| dell_inuse_close | 0 | 1 |
| dell_inuse_missing_binary | 4 | 0 |
| dell_works_verified | 157 | 38 |
| hancore_clean_approve | 22 | 1 |
| hancore_concrete | 69 | 13 |
| nudged_approve | 2 | 0 |
| version_history | 78 | 23 |

## 4. Approve mix by source (A2)

| source | approve train | approve val | broken train |
|---|---|---|---|
| dell_broken_verified | 0 | 0 | 51 |
| dell_inuse_close | 0 | 0 | 0 |
| dell_inuse_missing_binary | 0 | 0 | 4 |
| dell_works_verified | 157 | 38 | 0 |
| hancore_clean_approve | 22 | 1 | 0 |
| hancore_concrete | 0 | 0 | 69 |
| nudged_approve | 2 | 0 | 0 |
| version_history | 0 | 6 | 78 |

approve share of train 47%; of the approves, real clean plugins (HANCORE-clean + Dell-sweep-verified + nudged) = 181 (100%); fixed-twin/synthetic = 0. Only 53 review-clean HANCORE candidates exist (23 survive the gates/guard/dedupe into train): the supply, not the policy, is the limit.

## 5. Label space (A3)

slugs in train (min 15 findings per scored slug, train+val); out-of-scope (not in the prompt, never labelled, eval n/a): ['install-deps-packaging', 'listing-metadata-docs', 'privileged-system', 'process-lifecycle-timeouts', 'rich-text-markup-injection', 'scope-policy-duplicate', 'url-scheme-network', 'user-config-modification']

| slug | train findings | val findings | scored by HANCORE eval |
|---|---|---|---|
| file-safety-symlink-perms | 16 | 3 | yes |
| in-use:invalid-command-arg | 2 | 1 | no |
| in-use:missing-binary | 7 | 3 | no |
| in-use:missing-file | 4 | 1 | no |
| in-use:placeholder-data | 3 | 1 | no |
| in-use:stale-or-wrong-display | 4 | 3 | no |
| load:component-not-created | 4 | 4 | no |
| load:invalid-binding | 3 | 5 | no |
| load:missing-import | 7 | 3 | no |
| load:undefined-reference | 43 | 3 | no |
| load:unknown-type | 9 | 3 | no |
| remote-code-pinning | 13 | 3 | yes |
| runtime-qml-api-compat | 13 | 3 | no |
| runtime:error-handling | 8 | 3 | no |
| runtime:logic-error | 20 | 3 | no |
| runtime:state-or-race | 2 | 1 | no |
| secrets-credentials | 16 | 3 | yes |
| shell-lua-injection | 14 | 3 | yes |
| unbounded-input-resource | 31 | 4 | yes |

in-scope scored slugs below MIN_PER_SLUG=15 (train+val): none. Scored slugs with no data are OUT_OF_SCOPE: eval reports n/a for them (not recall 0).

## 5b. Label-quality filters (audit E)

- commit attribution: HANCORE rows are kept only when the recorded commit equals the plugin's plurality reviewed SHA (strict mode: 'fixed in <sha>' and foreign-repo commit URLs are not reviewed commits); drops: {"attribution:row_commit_is_not_the_reviewed_sha": 10, "attribution:no_reviewed_sha": 1}
- retractions (findings the reviewer later withdrew, whole or partial): rows dropped 1
- synthetic generator rows: policy `exclude` (template-id tell sample.*/syn.*); excluded 16; remaining synthetic rows in train: 0
- template-id share by verdict (train+val; a skew between verdicts would be a label tell): `{"approve": {"rows": 226, "template_id": 0, "share": 0.0}, "changes_requested": {"rows": 247, "template_id": 0, "share": 0.0}}`
- line numbers shown at train and eval (numbered blob), few-shots swapped to holdout-clean themes (prompt_v4); the explicit-evidence check is the fail-closed LLM gate

## 6. Guards, drops, spend

drops: `{"attribution:row_commit_is_not_the_reviewed_sha": 10, "attribution:no_reviewed_sha": 1, "retraction:withdrawn_finding_row_dropped": 1, "pool:no_full_source_and_shown_may_be_truncated": 95, "synthetic:excluded_template_artefact": 16, "hancore_clean:no_source": 2, "finding:cited_line_not_visible_under_shared_policy": 353, "row:no_finding_left": 420, "finding:unmappable_category": 79, "render:checker_unavailable_or_timeout": 1, "finding:failed_exact_line_gate": 50, "row:all_findings_failed_gate": 46, "row:v2_val_repo_in_pool": 164, "guard:content": 41, "row:over_32k_tokens": 2, "guard:repo": 29, "row:finding_without_file_or_line": 18, "dedupe_near_dup:dell_works_verified_vs_hancore_clean_approve": 3, "dedupe_near_dup:version_history_vs_version_history": 89, "dedupe_near_dup:version_history_vs_dell_works_verified": 56, "dedupe_near_dup:version_history_vs_fix_upstream": 2, "dedupe_near_dup:version_history_vs_dell_broken_verified": 4, "dedupe_near_dup:version_history_vs_hancore_concrete": 8, "dedupe_near_dup:version_history_vs_hancore_clean_approve": 2, "cap:source_version_history_40pct": 346, "approve_history_twin_dropped": 218, "approve_history_minority_cap": 51}`

- holdout/Dell guard rejects: content 41, repo/id 29; v2-val repos kept out of the pool: 164
- LLM gates (qwen/qwen3.5-397b-a17b + openai/gpt-oss-120b, fail-closed): `{"findings": 606, "mech_pass": 606, "qwen_pass": 583, "gptoss_pass": 575, "all_pass": 556, "fail_gptoss": 27, "fail_qwen": 19, "fail_qwengptoss": 4, "calls": 1212, "hits": 1212, "live": 0, "errors": 0, "spent_usd": 0.1265, "cache_entries": 11338}`
- LLM spend this run: $0.1265; stats `{"calls": 0, "hits": 0, "live": 0, "errors": 0, "error_samples": [], "spent_usd": 0.1265, "cache_entries": 11338}`
- LLM cache (replayable, published hash): `6c761367f7cad803dd99e7b59c3795ac6e3a2a14f03676a5b0c9ad4a89ced281`
