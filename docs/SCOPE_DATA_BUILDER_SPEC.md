# Training-data builder spec for the Checker Model scope (for the data worker)

Status: SPEC, not code. Written 2026-10-15 against `docs/MODEL_SCOPE.md` and `docs/DEFINITION_OF_DONE.md` (terms: Checker Scripts, Checker Model, System). Nothing here changes `train/` or the r5 builders; the data worker owns those.
The r5 rows (`v3/r5`) are in the previous scope's format (verdict + findings over load/in-use categories) and cannot be reused as targets without re-deriving them as below.

## 0. Row format (all four row types)
- `messages` = `scope.prompt_scope.messages(code, findings, target)`: system prompt `scope-v4` (hash `PROMPT_SHA256`), user = numbered Checker Scripts report + `code_blob` rendering of the plugin, assistant = target JSON in the schema of `scope/schema.py`.
- The Checker Scripts report in the row is the REAL report of the Checker Scripts at the pinned SHA (`scope.checker_findings.findings_for`), regenerated for the exact file tree shown. Never hand-edited, never from an older rules version. Runtime-stage findings come from a real runtime run or are absent (record which).
- `meta`: row type, source, label basis (see each type), Checker Scripts git SHA + rules hash, `prompt_sha256`, licence, repo, commit, `hand_reviewed` bool, `provisional` bool.
- Hard asserts at build time (fail the build, do not drop silently): target passes `schema.validate(target, findings)`; every `quote` is in the cited file (`postfilter.quote_in_file`) and, for added findings, within 2 lines of `line`; no added finding has the same (file, line) as a Checker Scripts finding; categories only the seven focus slugs; severity `blocker` only where a user would be harmed (rubric below).
- Training loss only on the assistant tail (unchanged). Truncated or omitted files: no finding in the unseen part (the prompt says so; the builder enforces it with `code_blob.line_visible`).

## 1. Triage rows (job 1; highest priority, most rows)
Input: a real plugin + its real Checker Scripts report with >= 1 finding. Target `scripts_triage`: one item per finding, in report order.
- `confirm`: the finding is real. Label basis, strongest first: (a) hand label in S1-style data; (b) the Checker Scripts FAIL agrees with a hardware-observed break of that plugin (`grader-verified broken`) AND the finding's file/line is the cause named by the hardware note; (c) a verified upstream fix commit changed exactly that location. A FAIL on a hardware-broken plugin without (b)/(c) is NOT labelled: the plugin being broken does not make this particular finding real.
- `dismiss`: the finding is a false alarm. Label basis: (a) hand label; (b) hardware says the plugin works and the finding is fail-level (a blocking claim that hardware contradicts). Warn-level findings on working plugins are NOT auto-dismissed (a warning can be a real quality issue); they need a hand label. Measured today: 0 fail-level false alarms exist on the Dell key because the Checker Scripts were calibrated on it, so dismissal data must come from OTHER hardware-run plugins (the Dell sweep corpus, `dell/sweep`, 3,942 works labels) or from hand labelling (S1).
- `reason`: one line, written by an open-weights teacher (Qwen3.5-397B-A17B or another open-weights model, never a proprietary one) from the label and the code, then validated: it must not contradict the label and must not mention the label source ("hardware", "Dell", "key").
- `quote`: a code line from the file that supports the decision, exact; for confirm it is the offending code (or the nearest line when the rule has no line), for dismiss the code that shows why it is fine (a guard, a try/catch, a constant).
- Runtime-stage fails: always `confirm` in the targets (they cannot be dismissed); never create a dismiss row for them.
- Balance: dismiss share about 25-35% of triage items (the model must learn that dismissing is possible without learning to dismiss everything); M3 needs <= 5% dismissals of real failures, so confirm-of-real rows must dominate the real class and include every rule family. Cap items per rule so USB-A/Q rules do not dominate.

## 2. Extend rows (job 2; never repeat Checker Scripts findings)
Input: a plugin where the Checker Scripts report does NOT already contain the finding. Target `added_findings`: only findings from verified sources, in the seven focus categories.
- Source: HANCORE reviewer findings with a concrete file:line and `strength in {strong, likely}` (raw pool `usuba-runs/hancore-labels/concrete_findings.jsonl`: 1,446 findings; focus-category counts before the holdout/guard/attribution filters: secrets 437, url/network 306, rich-text 315, remote-code pinning 203, listing/metadata 193, user-config 181, scope/policy 140). The r5 build kept only 16 secrets, 13 remote-code and ZERO of the other five after its strict exact-line, commit-attribution and retraction filters (r5 `GATE_REPORT` section 5): re-check which filter removes them before adding rows, and report the final per-slug count. The scope needs >= 15 per slug (the r5 rule), more for training to matter.
- Dedup: drop the added finding if the Checker Scripts report of THAT row already has a finding at the same (file, line), or the same rule family on the same file (e.g. USB-S02 remote-exec covers a `curl | sh` the model would add as remote-code-pinning). The row then becomes a triage row, not an extend row.
- `quote`/`line` come from the verified location, not from a teacher. `finding` (plain English) and `fix` are written by an open-weights teacher, or taken from the real upstream fix when one exists (preferred, licence permitting); the `fix` must be concrete replacement code or a concrete edit, checked mechanically: non-empty, differs from the quote, and (where the language allows) the patched file still parses (JSON via `json`, QML via qmllint if available, shell via `bash -n`).
- Severity rubric (write it into the teacher prompt and the audit): `blocker` = secret literal, remote code executed unpinned/unverified, write that overwrites user config without consent, markup injection of untrusted text into an interactive surface; everything else (http instead of https, missing licence, generic id, vague metadata) = `warning`.
- Negatives: extend rows on plugins with an EMPTY `added_findings` list. M2 allows at most 0.3 added findings per clean plugin, so at least 50% of all rows must have an empty list, drawn from clean plugins (section 4) and from plugins whose only reviewer findings are out of scope.

## 3. Fix rows (job 3; from verified upstream commits)
Source: `usuba-runs/version-history/data/verified_pairs{,_2}.jsonl` (2,787 verified fix commits; the pre-fix line is checked against the parent commit by `scope/build_drafts.py s4`). Rules:
- Only bug kinds inside the scope become `added_findings`. By kind, of 2,787: `security` 214 is the only kind that can map to the seven categories (after a per-pair sub-classification into secrets / url / remote-code / user-config / rich-text; unmappable pairs are dropped and counted); `wrong-condition-or-logic` 728, `ui-layout-or-state` 520, `api-compat-change` 206, `process-or-resource-lifecycle` 192, `race-or-timing` 189, `wrong-path-or-command` 169, `env-or-config-assumption` 166, `error-handling` 136, `syntax-or-parse-error` 84, `null-or-missing-guard` 69, `missing-dependency-or-install` 62 and `shell-quoting-or-expansion` 47 are runtime/logic behaviour and are OUT of scope for the Checker Model (they were useful for the old scope). Expect low hundreds of usable fix rows, not thousands.
- Input is the PARENT-commit tree (the bug present), with its real Checker Scripts report; the target adds one finding at the pre-fix line with `quote` = the pre-fix line text, `fix` = the upstream diff (removed -> added) rendered as a replacement, `finding` from the commit message/defect text rewritten by an open-weights teacher.
- If the Checker Scripts report of the parent tree already flags that line, the row is a TRIAGE `confirm` row (the fix commit is the evidence), not an extend row.
- The matching FIXED-commit tree is a clean-style row (section 4) only if it still has no in-scope finding; never train on both sides of a pair without keeping them in the same split.
- Licence: MIT/Apache-2.0/ISC/BSD only (as everywhere); upstream commit URL + SHA in `meta`; attribution in `NOTICE`.
- Repo-disjoint splits, and the S4 repos are excluded (section 5).

## 4. Clean rows (dismiss every false alarm, add nothing)
Input: plugins that work on hardware and have no real problem in scope. Two kinds:
- Checker-pass: empty report -> `scripts_triage: []`, `added_findings: []`, verdict `approve`. Source: hardware-works + Checker Scripts pass (the S2 shape). Hand-review before they count for M2; unreviewed ones may be trained on but never evaluated on, and the reviewed ones must not be trained on.
- Checker-warn-only: the report has only warn-level findings that were adjudicated as not real (hand or non-circular hardware evidence): every finding `dismiss` with reason + quote, `added_findings: []`, verdict `approve`. Include a share of clean rows whose report is noisy (>= 3 warnings), otherwise the model learns "no warnings = approve" only.
- Never put a runtime-stage fail in a clean row.

## 5. Exclusions and guards (hard, tested)
- The sealed Dell key (116 ids, plus near-duplicate trees as in `train/holdout_guard.py`) and the 329 HANCORE holdout plugins: never in training, never in few-shot examples in the prompt.
- S1-S4 evaluation sets, once labelled: their plugins and repos are excluded from every training split (record the list in the manifest). Today's drafts: `S4_EXCLUDE_REPOS.txt` written by `scope/build_drafts.py s4` (60 repos) and the Dell plugin ids; the data worker must read them from `$USUBA_RUNS/scope-v4/drafts`.
- Few-shot examples in the prompt are synthetic (no real plugin), so no real plugin can leak through the prompt.
- No proprietary-model output (labels, reasons, fixes, judging). Teacher and judge: open-weights models via OpenRouter within the spend cap.
- Same-name forks and near-duplicates: reuse `train/holdout_guard.py`; do not edit it from this spec.

## 6. Targets for a first build (starting numbers, to be revised once S1 exists)
| Row type | Rows | Notes |
|---|---:|---|
| Triage (confirm + dismiss) | 1,500+ items over >= 600 plugins | confirm >= 65% of items; dismiss only with a non-circular label |
| Extend (non-empty) | >= 15 per focus slug (target 60), 7 slugs | from the hancore concrete pool after re-checking the r5 filters |
| Fix rows | low hundreds | `security` pairs only, after sub-classification |
| Clean | >= 40% of all rows | Checker-pass and Checker-warn-only, repo-disjoint |
Report per row type and per slug in the gate report; a slug with < 15 rows is marked OUT_OF_SCOPE for the build (not silently trained) and its eval is n/a, exactly as r5 did.

## 7. What must exist before anything trains
S1 >= 300 labelled Checker Scripts findings (real/false alarm), S2 >= 150, S3 >= 100 per eval, S4 >= 50, and the B0 scores on them (`docs/DEFINITION_OF_DONE.md`). Until then training stays paused; provisional drafts exist only to test the harness.
