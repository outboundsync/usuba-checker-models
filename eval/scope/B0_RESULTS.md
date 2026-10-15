# B0 (stock Qwen3.5-9B, same prompt / schema / post-filter) on the data that exists today, 2026-10-15

Model `qwen/qwen3.5-9b` on OpenRouter (open weights), temperature 0, no thinking, scope prompt v4 (`scope/prompt_scope.py`), `scope/schema.py`, `scope/postfilter.py`, `scope/scoring.py`. One run per set. Spend for the whole job: about $1.15 of the $5 cap (includes one crashed holdout run that was re-run).
Aggregates only (`eval/scope/results/*.summary.json`); per-plugin rows stay outside git. **Every label set below is a machine DRAFT, below its Definition-of-Done minimum; no gate is reported as pass or fail, only provisional.** The Checker scripts report here is static-stage only (the box has no Quickshell runtime), so the "System verdict" numbers are static-only.

| Set | n | What it is |
|---|---:|---|
| Dell key (draft S1/S2) | 75 plugins (28 broken, 47 works; 11 key plugins have no code on the box, 4 Claude-written excluded) | hardware truth vs Checker scripts |
| S4 draft, security kind | 60 plugins | version-history fix commits, pre-fix line checked in the parent commit |
| S4 draft, all kinds | 60 plugins | same, all bug kinds (mostly runtime/logic = out of scope) |
| HANCORE holdout | 329 (300 pos / 29 neg) | reviewer-category proxy only |

## Practical / validity (M5 inputs; API run, not Q4_K_M on a laptop)
| Set | schema-valid [Wilson] | median s | invalid reasons |
|---|---|---:|---|
| Dell | 0.840 [0.741-0.906] (63/75) | 4.1 | schema 11, unparseable 1 |
| S4 security | 0.600 [0.474-0.714] | 10.9 | schema 16, unparseable 6, truncated 2 |
| Holdout | 0.650 [0.597-0.700] | 7.6 | schema 88, unparseable 21, truncated 6 |
Most schema failures: `reason` longer than 240 chars or containing a newline, or an empty `quote`. Raising the cap to 2000 chars only lifts Dell to 65/75 and S4 to 41/60, so validity stays below the 99% gate for the stock model. Invalid = wrong everywhere below.

## Dell key (DRAFT labels)
- **M3 (S1 draft)**: only 6 labelled Checker findings exist (all `real`, from 1 plugin, label = key reason names the file); dismissals of real: 0/6, Wilson [0.00-0.39]. Meaningless at this n.
- **Hardware-observable false alarms: 0.** No fail-level Checker scripts finding fires on a hardware-working Dell plugin (the Checker scripts were calibrated on this key, so it cannot supply false alarms). 52 warn-level findings on working plugins are queued unlabelled for human labelling.
- **M2 (S2 draft, 47 clean, unreviewed)**: 14/47 get an added blocker = 0.298 (Wilson [0.187-0.440], bootstrap [0.17-0.43]); 0.83 added findings per clean plugin (bootstrap [0.53-1.15]). Gate is <=0.15 and <=0.3: provisional-fail. An invalid answer counts as a blocker.
- Dismissal rate over all 53 Checker findings in valid rows: 22 (0.415, Wilson [0.29-0.55]); the post-filter reverted 6 further dismissals (quote not in file).
- Model verdict vs hardware (shared scorer, invalid = wrong): accuracy 0.480 [0.36-0.60], positive recall 0.393 [0.21-0.57], false alarm 0.277 [0.15-0.40], n=75 (12 invalid). Checker scripts verdict (static only) = System verdict: 58/75 = 0.773 [0.667-0.853]. Always-flag = 0.373.
- Tracked: T1 drop rate 0.024 (1/41), T2 line accuracy 1.00 (37), T3 ungrounded triage quotes 0.151 (n=53), T4 verdict inconsistency 0.143, T5 fix concrete 1.00.

## S4 draft (bug recall, hit = added or confirmed finding within 3 lines in the same file)
- security kind: 3/60 = 0.050 [0.017-0.137]. All kinds: 1/60 = 0.017 [0.003-0.089].
- Of 60 all-kind pairs only 3 are `security`; most mined bugs are runtime/logic bugs, which are outside the Checker model scope. The mined pool is therefore a poor S4 for this scope until bugs are re-selected by in-scope category and hand-verified.
- Dismissals: 36/63 findings in valid rows (0.571).

## HANCORE holdout (proxy, NOT S1-S4)
Added findings kept 140 (of 180 raw; 28 dropped for ungrounded quote, 12 duplicates of Checker findings). Category-match precision against reviewer categories 0.243 [0.179-0.320]; focus-category recall 0.036 [0.024-0.054]. Negatives (29): 8 with an added blocker or invalid answer = 0.276 [0.147-0.457]; 0.83 added per negative. Post-filter reverted 142 of 394 dismissals; T1 0.156, T3 0.374. These proxies say the stock model adds many findings the reviewers did not list; only S3 adjudication can say whether they are real.

## Gaps against the Definition of Done
| Set | Have | Need | Missing |
|---|---|---|---|
| S1 triage | 6 draft `real`, 0 `false_alarm`, 0 hand labels | 300 hand-labelled | 294+, and false alarms must come from hardware-run plugins other than the Dell key or from hand labels; queue: 52 unlabelled warn findings + any new Checker runs |
| S2 clean | 47 machine-selected, unreviewed | 150 hand-reviewed | 103 plugins and all 150 hand reviews |
| S3 adjudication | 0 | 100 per eval (B0 and Checker model) | all; B0 added findings to adjudicate exist: 37 (Dell), 40 (S4), 140 (holdout) |
| S4 bug set | 60 mechanical, 3 in scope, 0 hand-verified | 50 hand-verified in-scope | hand verification and an in-scope re-selection |
| Not measured | | | Q4_K_M latency/determinism on a 32 GB laptop, runtime-stage Checker findings, M4 (no Checker model yet), M6 |
