# Provisional open-weights judge panel (Janus, 2026-10-15)

Tool: `tools/judge_panel.py`. Judges: qwen/qwen3.5-397b-a17b, openai/gpt-oss-120b, deepseek/deepseek-v3.2 via OpenRouter (no Anthropic, no proprietary OpenAI). Every vote, majority and flag is PROVISIONAL; nothing here is a final label. Scope: Checker triage findings (S1), added findings (S3) and S2 clean candidates only; patch/fix validity is not judged.

Outputs: `scripts/results/s1s2/panel/{scope,hw}/` (votes, summary, review_queue; no code context).

## Spend
$8.07 of the $8 cap (2,099 calls). The ledger checks the cap before each call, but 16 in-flight calls overshot by $0.07. Qwen 397B (thinking) is ~85% of the cost.

## Scope set (S1 warn-level 52 + S3 added findings 217), complete
- S1: unanimous 50%, Fleiss kappa 0.31, 28/52 flagged for human review. Majority: false_alarm 34, real 5, unsure 12, no majority 1.
- S3: unanimous 40%, Fleiss kappa 0.36, 132/217 flagged. Majority: real 83, false_alarm 78, no majority 47, unsure 9. 105 judge calls failed (timeouts/unparseable) and count as abstains.
- Pairwise Cohen kappa 0.14-0.50 (qwen/deepseek highest on S1; gpt-oss/deepseek highest on S3). gpt-oss labels "real" far more often on S3 (110) than qwen (55).
## Hardware set (S1 hw items 378, S2 candidates 267), partial (budget spent)
- S1: 313 items have all 3 votes; unanimous 35% overall, Fleiss kappa 0.34.
- S2: only 5 of 267 got 3 votes (247 have none). The S2 panel pass is NOT done; it needs ~$3 more.
- Against hardware truth (S1, items after the guard): real_hw 15/22 majority "real"; no_symptom_hw 16/81 "false_alarm" (53 unsure/no majority); present_hw 37/100 "false_alarm". Judges see Checker messages as plausibly real, so hardware "false alarm" labels are not recoverable from reading code alone.
## Conclusion
Agreement is moderate-to-low (kappa 0.3-0.4); the panel is a triage aid. Roughly 55-60% of items need a human. Do not use majority labels as truth.
