# Checker Model: definition of done

Companion of `docs/MODEL_SCOPE.md` (same terms: **Checker Scripts**, **Checker Model**, **System**). Release 1 is ADVISORY.

## Prerequisite data sets (all hand-labelled; machine drafts do not count)
| Set | Content | Minimum |
|---|---|---|
| **S1 triage set** | labelled Checker Scripts findings, each `real` or `false alarm` (Unsure items are kept out of the counts) | >= 300 |
| **S2 clean set** | plugins that work on hardware, pass the Checker Scripts, and were hand-reviewed | >= 150 |
| **S3 adjudication** | sampled ADDED findings (of the Checker Model and of B0), each adjudicated real / not real / unsure, per eval | >= 100 per eval |
| **S4 bug set** | hand-verified bug locations (file:line) in published plugins | >= 50 |

Machine-built drafts (`scope/build_drafts.py`) are marked DRAFT / provisional, are never trained on, and a gate computed on a set below its minimum is reported `provisional-*`, never `pass`.

## Baseline
**B0** = stock Qwen3.5-9B with the same input, schema and post-filter, scored on S1-S4 (`scope/run_b0.py`).

## Release gates
| Gate | Requirement | Measured on | Code |
|---|---|---|---|
| **M1** | added-finding precision >= 0.60, and the 95% CI lower bound >= 0.50 | S3 | `scoring.added_precision` (plugin-clustered bootstrap + Wilson) |
| **M2** | <= 15% of clean plugins get a blocker, and <= 0.3 added findings per clean plugin | S2 | `scoring.clean_metrics` (an invalid answer counts as a blocker) |
| **M3** | dismisses <= 5% of real Checker Scripts failures | S1 real items | `scoring.triage_metrics` (`dismiss_of_real`; raw and post-filtered both reported) |
| **M4** | beats B0 beyond the CI | S1-S4 | paired comparison: `scoring.mcnemar_paired` (shared exact McNemar) + `scoring.paired_triage_diff` / `paired_precision_diff` (plugin-clustered paired bootstrap) on triage accuracy and M1 precision; the CI of the difference must exclude 0 (operationalisation proposed here; Harris to confirm) |
| **M5** | practical: Q4_K_M, 32 GB laptop, <= 10 s median, >= 99% schema-valid, deterministic | local run | `scoring.practical` (an API run gives only schema validity and provisional latency) |
| **M6** | >= 10 issues found in published plugins filed upstream | S4 + Checker Model output | manual, human files each issue |
| **M7** | hygiene: pytest, ruff, `tools/scan_public.py`, gitleaks all exit 0; sealed Dell key and holdout never in training; no proprietary-model output used | CI | existing gates |

## Tracked (T1-T5): reported every run, never gating
The scope message names T1-T5 without definitions. These are the definitions implemented in `scoring.tracked` (an interpretation, to be confirmed or replaced by Harris):
- **T1** added findings dropped by the post-filter (ungrounded quote or file) / added findings emitted
- **T2** line accuracy: kept added findings whose quote sits within 2 lines of the cited line
- **T3** triage quotes ungrounded (confirm with a quote not in the file, or dismissals dropped by the post-filter) / triage items
- **T4** verdict inconsistency: model verdict contradicts its own triage and added findings
- **T5** fix concreteness: kept added findings whose `fix` is a real replacement (not empty, not a copy of the quote)

## Stop rule
If one cleaned-up run fails M1 or M2, or does not beat B0, pause training.

## Metric hygiene (all gates)
- Intervals: percentile bootstrap resampling plugins (items of one plugin are not independent) plus Wilson for proportions; one run per system unless stated.
- Invalid output = wrong. Missing triage decision = wrong, never a dismissal.
- The shared scorer (`usuba-checker-scripts/eval/hancore_holdout/scoring.py`) does plugin-level verdicts and McNemar; nothing re-implements those.
