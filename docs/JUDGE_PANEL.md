# Provisional open-weights judge panel (Janus, 2026-10-15) - FINAL

Tool: `tools/judge_panel.py`. Judges: qwen/qwen3.5-397b-a17b, openai/gpt-oss-120b, deepseek/deepseek-v3.2 via OpenRouter (ZDR, no data collection; no Anthropic, no proprietary OpenAI). Every vote, majority and flag is PROVISIONAL; nothing here is a final label. Scope per Harris: Checker Scripts triage findings (S1), added findings (S3) and S2 clean candidates only; patches/fixes are not judged.

Outputs: `scripts/results/s1s2/panel/{scope,hw}/` (votes, summary, review_queue; no code context) and `ledger-final.json`. `review_sheet.csv` carries `panel_majority_provisional` and `panel_needs_human` columns.

## Spend
$13.84 of the $25 cap (3,195 calls). The ledger now counts the estimated cost of in-flight calls (x1.5 margin) against the cap before a call starts (`Ledger.reserve/release`, tested), so parallel workers cannot overshoot (the first $8 run overshot by $0.07). The run is resumable: same command, cache and ledger persist. Qwen 397B (thinking) is most of the cost and all of the latency.

## Results (3 judges each; failed calls are abstains)
| Set | n | unanimous | Fleiss kappa | needs human | majority |
|---|---|---|---|---|---|
| S1 warn-level (scope drafts) | 52 | 48% | 0.28 | 29 | false_alarm 35, unsure 12, real 4, no majority 1 |
| S3 added findings | 217 | 49% | 0.38 | 113 | false_alarm 96, real 95, no majority 16, unsure 10 |
| S1 hardware-observable items | 378 | 38% | 0.37 | 278 | false_alarm 117, unsure 122, real 107, no majority 32 |
| S2 clean candidates (before guard) | 267 | 53% | 0.30 | 125 | clean 193, not_clean 43, no majority 23, unsure 8 |

Pairwise Cohen kappa 0.17-0.51 (S1 scope: qwen/deepseek 0.48; S3: gpt-oss/deepseek 0.44; S2: qwen/gpt-oss 0.42, qwen/deepseek 0.23). Calls that failed after retries (all qwen timeouts): S1 hw 28, S2 24 (+1 deepseek), S3 5 (those items have 2 valid votes and are flagged `missing_vote`).

S2 after the current guard (221 candidates): panel majority clean 158, not_clean 34, no majority 21, unsure 8. Cross with the hardware auto verdict: 123 PASS_AUTO+clean, 34 REVIEW+clean, 25 PASS_AUTO+not_clean, 9 REVIEW+not_clean, 16 PASS_AUTO+no majority, 5+3 unsure, 5 REVIEW+no majority, 1 FAIL+clean. The 25 PASS_AUTO+not_clean rows are the first ones for a human to read.

Against hardware truth (S1 hw items after the guard, majority label): real_hw 15/22 judged real; no_symptom_hw 18/81 judged false_alarm (49 unsure/no majority); present_hw 40/100 judged false_alarm. Reading code and the Checker Scripts message alone does not recover the hardware false-alarm labels.

## Conclusion
Agreement is moderate to low (kappa 0.3-0.4). The panel is a triage aid that orders human review; do not use majority labels as truth. Roughly half of all items need a human.
